#!/usr/bin/env python3
"""
Recover missing sequences by reprocessing specific subjects

Targets:
- 8 subjects with missing T1_conv
- 1 subject (Anon43113) with 5 missing sequences
"""

import subprocess
import pandas as pd
import re
import logging
from pathlib import Path
from datetime import datetime
import pydicom
import shutil
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'recovery_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
GROUND_TRUTH_CSV = '/Users/paul/Downloads/sequence_folder_mapping - sequence_folder_mapping.csv'
STATS_FILE = BASE_DIR / 'output' / 'statistics' / f'gm_wm_tissue_stats_recovered_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

# Subjects to recover
SUBJECTS_TO_RECOVER = [
    'Anon13609',
    'Anon21108',
    'Anon27334',
    'Anon28584',
    'Anon39526',
    'Anon43113',
    'Anon50199',
    'Anon72813',
    'Anon88788'
]

def parse_series_number(cell_value):
    """Extract series number from CSV cell"""
    if pd.isna(cell_value) or str(cell_value).strip() == '':
        return None
    cell_str = str(cell_value).strip()
    match = re.match(r'([A-F0-9]+)\s*\(#(\d+)\)', cell_str)
    if match:
        return match.group(2)
    match = re.match(r'\(#(\d+)\)', cell_str)
    if match:
        return match.group(1)
    if re.match(r'^[A-F0-9]+$', cell_str):
        return None
    if re.match(r'^\d+$', cell_str):
        return cell_str
    return None

def get_series_path_from_dicomdir(subject_dir, series_number):
    """Parse DICOMDIR and find folder path for given series number"""
    dicomdir_path = subject_dir / 'DICOMDIR'
    if not dicomdir_path.exists():
        return None

    try:
        dicomdir = pydicom.dcmread(str(dicomdir_path))
        target_series = int(series_number)

        for patient in dicomdir.patient_records:
            for study in patient.children:
                for series in study.children:
                    if series.SeriesNumber == target_series:
                        if hasattr(series, 'children') and len(series.children) > 0:
                            first_image = series.children[0]
                            file_path_parts = first_image.ReferencedFileID[:-1]
                            folder_path = subject_dir / Path(*file_path_parts)
                            return folder_path
        return None
    except Exception as e:
        logging.error(f"Error reading DICOMDIR: {e}")
        return None

def convert_dicom_to_nifti(dicom_folder, output_file):
    """Convert DICOM to NIfTI using dcm2niix"""
    output_dir = output_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        'dcm2niix',
        '-z', 'y',
        '-f', output_file.stem,
        '-o', str(output_dir),
        str(dicom_folder)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            # dcm2niix may add suffix, find the created file
            created_files = list(output_dir.glob(f"{output_file.stem}*.nii.gz"))
            if created_files:
                if created_files[0] != output_file:
                    created_files[0].rename(output_file)
                return True
        return False
    except Exception as e:
        logging.error(f"dcm2niix failed: {e}")
        return False

def run_hdbet(input_file, output_file):
    """Run HD-BET brain extraction"""
    hdbet_path = '/Users/paul/miniforge3/envs/stage_analysis/bin/hd-bet'

    cmd = [
        hdbet_path,
        '-i', str(input_file),
        '-o', str(output_file.parent / output_file.stem),
        '-device', 'cpu',  # Force CPU mode (no CUDA on Mac)
        '-mode', 'fast',
        '-tta', '0'
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        # HD-BET creates {base}_mask.nii.gz
        hdbet_mask_file = output_file.parent / f"{output_file.stem}_mask.nii.gz"
        if hdbet_mask_file.exists():
            hdbet_mask_file.rename(output_file)
            return True

        # Log error if HD-BET failed
        if result.returncode != 0:
            logging.error(f"HD-BET stderr: {result.stderr}")
        return False
    except Exception as e:
        logging.error(f"HD-BET failed: {e}")
        return False

def segment_tissues_simple(nifti_file, mask_file, sequence_type):
    """Simple intensity-based tissue segmentation"""
    import nibabel as nib
    import numpy as np

    # Load data
    nifti_img = nib.load(nifti_file)
    mask_img = nib.load(mask_file)

    nifti_data = nifti_img.get_fdata()
    mask_data = mask_img.get_fdata()

    # Get brain voxels
    brain_voxels = nifti_data[mask_data > 0]

    if len(brain_voxels) < 1000:
        return None, None

    # Threshold based on percentiles
    if 'T1' in sequence_type:
        # T1: WM is bright, GM is darker
        wm_threshold = np.percentile(brain_voxels, 70)
        gm_threshold = np.percentile(brain_voxels, 30)
        wm_mask = (nifti_data > wm_threshold) & (mask_data > 0)
        gm_mask = (nifti_data < wm_threshold) & (nifti_data > gm_threshold) & (mask_data > 0)
    elif 'T2' in sequence_type or 'SWI' in sequence_type:
        # T2/SWI: GM is bright, WM is darker
        gm_threshold = np.percentile(brain_voxels, 70)
        wm_threshold = np.percentile(brain_voxels, 30)
        gm_mask = (nifti_data > gm_threshold) & (mask_data > 0)
        wm_mask = (nifti_data < gm_threshold) & (nifti_data > wm_threshold) & (mask_data > 0)
    else:
        return None, None

    # Calculate statistics
    gm_voxels = nifti_data[gm_mask]
    wm_voxels = nifti_data[wm_mask]

    if len(gm_voxels) < 100 or len(wm_voxels) < 100:
        return None, None

    gm_stats = {
        'mean': float(np.mean(gm_voxels)),
        'std': float(np.std(gm_voxels)),
        'count': int(np.sum(gm_mask))
    }

    wm_stats = {
        'mean': float(np.mean(wm_voxels)),
        'std': float(np.std(wm_voxels)),
        'count': int(np.sum(wm_mask))
    }

    return gm_stats, wm_stats

def process_subject(subject_id, gt_row):
    """Process a single subject"""
    logging.info("="*100)
    logging.info(f"Processing subject: {subject_id}")
    logging.info("="*100)

    subject_dir = BASE_DIR / 'data' / 'raw' / subject_id

    if not subject_dir.exists():
        logging.error(f"Subject directory not found: {subject_dir}")
        return []

    # Output directories
    nifti_dir = BASE_DIR / 'output' / 'nifti' / subject_id
    mask_dir = BASE_DIR / 'output' / 'brain_masks' / subject_id

    nifti_dir.mkdir(parents=True, exist_ok=True)
    mask_dir.mkdir(parents=True, exist_ok=True)

    results = []
    SEQUENCES = ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']

    for seq_name in SEQUENCES:
        series_num = parse_series_number(gt_row[seq_name])

        if not series_num:
            logging.info(f"  {seq_name}: Not in ground truth, skipping")
            continue

        logging.info(f"\n  Processing {seq_name} (series {series_num})...")

        # Find DICOM folder
        dicom_folder = get_series_path_from_dicomdir(subject_dir, series_num)

        if not dicom_folder or not dicom_folder.exists():
            logging.warning(f"    ✗ DICOM folder not found for series {series_num}")
            continue

        logging.info(f"    ✓ Found DICOM folder: {dicom_folder.relative_to(subject_dir)}")

        # Step 1: Convert to NIfTI
        nifti_file = nifti_dir / f"{seq_name}.nii.gz"
        logging.info(f"    Converting to NIfTI...")
        if not convert_dicom_to_nifti(dicom_folder, nifti_file):
            logging.warning(f"    ✗ DICOM to NIfTI conversion failed")
            continue
        logging.info(f"    ✓ Created: {nifti_file.name}")

        # Step 2: HD-BET
        mask_file = mask_dir / f"{seq_name}_mask.nii.gz"
        logging.info(f"    Running HD-BET...")
        if not run_hdbet(nifti_file, mask_file):
            logging.warning(f"    ✗ HD-BET failed")
            continue
        logging.info(f"    ✓ Created mask: {mask_file.name}")

        # Step 3: Tissue segmentation
        logging.info(f"    Segmenting tissues...")
        gm_stats, wm_stats = segment_tissues_simple(nifti_file, mask_file, seq_name)

        if gm_stats is None or wm_stats is None:
            logging.warning(f"    ✗ Tissue segmentation failed")
            continue

        logging.info(f"    ✓ GM mean: {gm_stats['mean']:.1f}, WM mean: {wm_stats['mean']:.1f}")

        # Calculate ratio
        ratio = gm_stats['mean'] / wm_stats['mean'] if wm_stats['mean'] > 0 else 0

        # Store results
        result = {
            'subject_id': subject_id,
            'sequence': seq_name,
            'gm_mean': gm_stats['mean'],
            'gm_std': gm_stats['std'],
            'gm_voxel_count': gm_stats['count'],
            'wm_mean': wm_stats['mean'],
            'wm_std': wm_stats['std'],
            'wm_voxel_count': wm_stats['count'],
            'gm_wm_ratio': ratio
        }

        results.append(result)
        logging.info(f"    ✓ Successfully processed {seq_name}")

    return results

def main():
    logging.info("="*100)
    logging.info("MISSING SEQUENCES RECOVERY")
    logging.info("="*100)

    # Load ground truth
    logging.info("\nLoading ground truth...")
    df_gt = pd.read_csv(GROUND_TRUTH_CSV)

    # Storage for all results
    all_results = []

    # Process each subject
    for subject_id in SUBJECTS_TO_RECOVER:
        gt_row = df_gt[df_gt['rAccession'] == subject_id]

        if gt_row.empty:
            logging.warning(f"Subject {subject_id} not in ground truth")
            continue

        gt_row = gt_row.iloc[0]

        try:
            subject_results = process_subject(subject_id, gt_row)
            all_results.extend(subject_results)
        except Exception as e:
            logging.error(f"Error processing {subject_id}: {e}")
            import traceback
            traceback.print_exc()
            continue

    # Save results
    if all_results:
        df_results = pd.DataFrame(all_results)
        df_results.to_csv(STATS_FILE, index=False)

        logging.info("\n" + "="*100)
        logging.info("RECOVERY COMPLETE")
        logging.info("="*100)
        logging.info(f"\nRecovered {len(all_results)} sequences")
        logging.info(f"Results saved to: {STATS_FILE}")

        # Summary by sequence type
        logging.info("\nRecovered sequences by type:")
        for seq_type in ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']:
            count = len(df_results[df_results['sequence'] == seq_type])
            logging.info(f"  {seq_type}: {count}")

    else:
        logging.error("\nNo sequences recovered!")

if __name__ == '__main__':
    main()
