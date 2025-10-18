#!/usr/bin/env python3
"""
Complete Reprocessing Pipeline Using Ground Truth Series Mappings

This script reads the ground truth spreadsheet with verified series numbers
and reprocesses the entire STAGE study analysis from scratch.

Steps:
1. Parse ground truth CSV
2. Clean up all previous outputs
3. Map series numbers to DICOM folders
4. Convert correct DICOM series to NIfTI
5. Run HD-BET brain extraction
6. Run ANTs registration
7. Run tissue segmentation and GM/WM analysis
8. Generate statistics and visualizations

Usage:
    python scripts/reprocess_with_ground_truth.py [--dry-run] [--subjects SUBJ1 SUBJ2...]

Author: Analysis Pipeline
Date: 2025-10-16
"""

import os
import sys
import re
import argparse
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
import shutil
from typing import Dict, List, Tuple, Optional

# Configure logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'reprocess_ground_truth_{timestamp}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Project paths
BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
RAW_DIR = BASE_DIR / 'data' / 'raw'
NIFTI_DIR = BASE_DIR / 'output' / 'nifti'
MASK_DIR = BASE_DIR / 'output' / 'brain_masks'
REG_DIR = BASE_DIR / 'output' / 'registered'
SEG_DIR = BASE_DIR / 'output' / 'tissue_segmentations'
STATS_DIR = BASE_DIR / 'output' / 'statistics'
PLOTS_DIR = BASE_DIR / 'output' / 'plots'
QC_DIR = BASE_DIR / 'output' / 'qc'

# Ground truth CSV
GROUND_TRUTH_CSV = '/Users/paul/Downloads/sequence_folder_mapping - sequence_folder_mapping.csv'

SEQUENCES = ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']


def parse_series_number(cell_value: str) -> Optional[str]:
    """
    Extract series number from cell value.

    Formats handled:
    - "100087C9 (#17)" -> "100087C9"
    - "(#17)" -> "17"
    - "" or blank -> None

    Args:
        cell_value: Cell value from CSV

    Returns:
        Series number string or None if blank
    """
    if pd.isna(cell_value) or str(cell_value).strip() == '':
        return None

    cell_str = str(cell_value).strip()

    # Match pattern: "SERIES_ID (#NUMBER)" or just "(#NUMBER)"
    # First try to extract series ID before parenthesis
    match = re.match(r'([A-F0-9]+)\s*\(#\d+\)', cell_str)
    if match:
        return match.group(1)

    # If only (#NUMBER), extract the number
    match = re.match(r'\(#(\d+)\)', cell_str)
    if match:
        return match.group(1)

    # If it's just a series ID without parenthesis
    if re.match(r'^[A-F0-9]+$', cell_str):
        return cell_str

    logger.warning(f"Could not parse series number from: '{cell_str}'")
    return None


def load_ground_truth() -> pd.DataFrame:
    """
    Load and parse the ground truth CSV.

    Returns:
        DataFrame with columns: subject_id, T1_conv, T1_STAGE, etc.
    """
    logger.info("=" * 100)
    logger.info("Loading ground truth data...")
    logger.info("=" * 100)

    try:
        df = pd.read_csv(GROUND_TRUTH_CSV)

        # Parse series numbers for each sequence
        for seq in SEQUENCES:
            if seq in df.columns:
                df[f'{seq}_series'] = df[seq].apply(parse_series_number)

        logger.info(f"Loaded {len(df)} subjects from ground truth CSV")

        # Count how many have each sequence
        for seq in SEQUENCES:
            count = df[f'{seq}_series'].notna().sum()
            logger.info(f"  {seq}: {count} subjects")

        return df

    except Exception as e:
        logger.error(f"Failed to load ground truth CSV: {e}")
        raise


def get_series_path_from_dicomdir(subject_dir: Path, series_number: str) -> Optional[Path]:
    """
    Parse DICOMDIR and find the folder path for a given series number.

    Args:
        subject_dir: Path to subject directory
        series_number: Series number as string (e.g., "14")

    Returns:
        Path to the DICOM folder, or None if not found
    """
    import pydicom

    dicomdir_path = subject_dir / 'DICOMDIR'

    if not dicomdir_path.exists():
        return None

    try:
        dicomdir = pydicom.dcmread(str(dicomdir_path))

        # Convert series_number to int for comparison
        try:
            target_series = int(series_number)
        except ValueError:
            return None

        # Iterate through patients, studies, and series
        for patient in dicomdir.patient_records:
            for study in patient.children:
                for series in study.children:
                    series_num = series.SeriesNumber if hasattr(series, 'SeriesNumber') else None

                    if series_num == target_series:
                        # Get the folder path from first image
                        if hasattr(series, 'children') and len(series.children) > 0:
                            first_image = series.children[0]
                            if hasattr(first_image, 'ReferencedFileID'):
                                # ReferencedFileID is a list like ['10008664', '10008665', '100086B7', '100086B8']
                                # We want the folder, not the file
                                file_path_parts = first_image.ReferencedFileID[:-1]  # Remove filename
                                folder_path = subject_dir / Path(*file_path_parts)
                                return folder_path

        return None

    except Exception as e:
        logger.debug(f"Error parsing DICOMDIR: {e}")
        return None


def find_dicom_folder(subject_id: str, series_number: str) -> Optional[Path]:
    """
    Find the DICOM folder for a given subject and series number.

    Args:
        subject_id: Subject ID (e.g., 'Anon10644')
        series_number: Series number (e.g., '100087C9' or '17')

    Returns:
        Path to DICOM folder or None if not found
    """
    subject_raw_dir = RAW_DIR / subject_id

    if not subject_raw_dir.exists():
        logger.warning(f"  Subject directory not found: {subject_raw_dir}")
        return None

    # First, try DICOMDIR lookup if series_number is purely numeric
    # This handles cases like "14", "17", "8165", "8040"
    if series_number.isdigit():
        dicomdir_path = get_series_path_from_dicomdir(subject_raw_dir, series_number)
        if dicomdir_path and dicomdir_path.exists():
            return dicomdir_path

    # Fallback: Search for folder containing the series number
    # DICOM folders are typically nested like: Anon10644/1000XXXX/1000YYYY/1000ZZZZ/

    # Try different search patterns
    patterns = [
        f"**/{series_number}",           # Exact match
        f"**/*{series_number}*",         # Contains series number
    ]

    for pattern in patterns:
        matches = list(subject_raw_dir.glob(pattern))

        # Filter to only directories
        matches = [m for m in matches if m.is_dir()]

        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            # Multiple matches - try to find the one with DICOM files
            for match in matches:
                dicom_files = list(match.glob('*.dcm')) + list(match.glob('*.DCM'))
                if len(dicom_files) > 0:
                    return match
            # If no DICOM files found, return first match
            logger.warning(f"  Multiple folders found for {subject_id}/{series_number}, using first: {matches[0]}")
            return matches[0]

    logger.warning(f"  DICOM folder not found for {subject_id}/{series_number}")
    return None


def clean_previous_outputs(subject_id: str, dry_run: bool = False):
    """
    Clean up all previous analysis outputs for a subject.

    Args:
        subject_id: Subject ID
        dry_run: If True, only show what would be deleted
    """
    dirs_to_clean = [
        NIFTI_DIR / subject_id,
        MASK_DIR / subject_id,
        REG_DIR / subject_id,
        SEG_DIR / subject_id,
        QC_DIR / 'tissue_masks' / subject_id,
    ]

    for dir_path in dirs_to_clean:
        if dir_path.exists():
            if dry_run:
                logger.info(f"  [DRY RUN] Would delete: {dir_path}")
            else:
                shutil.rmtree(dir_path)
                logger.info(f"  Deleted: {dir_path}")


def convert_dicom_to_nifti(subject_id: str, series_mappings: Dict[str, Path],
                           dry_run: bool = False) -> Dict[str, Path]:
    """
    Convert DICOM series to NIfTI format.

    Args:
        subject_id: Subject ID
        series_mappings: Dict mapping sequence names to DICOM folder paths
        dry_run: If True, only show what would be converted

    Returns:
        Dict mapping sequence names to NIfTI file paths
    """
    import subprocess

    nifti_files = {}
    subject_nifti_dir = NIFTI_DIR / subject_id

    if not dry_run:
        subject_nifti_dir.mkdir(parents=True, exist_ok=True)

    for seq_name, dicom_folder in series_mappings.items():
        if dicom_folder is None:
            continue

        output_file = subject_nifti_dir / f"{seq_name}.nii.gz"

        if dry_run:
            logger.info(f"  [DRY RUN] Would convert: {dicom_folder} -> {output_file}")
            continue

        logger.info(f"  Converting {seq_name}...")

        try:
            # Use dcm2niix for conversion
            cmd = [
                'dcm2niix',
                '-z', 'y',  # Compress
                '-f', seq_name,  # Output filename
                '-o', str(subject_nifti_dir),  # Output directory
                str(dicom_folder)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode == 0:
                # dcm2niix might create files with suffixes, find the output
                possible_files = list(subject_nifti_dir.glob(f"{seq_name}*.nii.gz"))
                if possible_files:
                    # Rename to standard name if needed
                    actual_file = possible_files[0]
                    if actual_file != output_file:
                        actual_file.rename(output_file)
                    nifti_files[seq_name] = output_file
                    logger.info(f"    ✓ Created: {output_file.name}")
                else:
                    logger.error(f"    ✗ No NIfTI file created for {seq_name}")
            else:
                logger.error(f"    ✗ Conversion failed: {result.stderr}")

        except Exception as e:
            logger.error(f"    ✗ Error converting {seq_name}: {e}")

    return nifti_files


def run_hdbet(subject_id: str, nifti_files: Dict[str, Path], dry_run: bool = False) -> Dict[str, Path]:
    """
    Run HD-BET brain extraction on NIfTI files.

    Args:
        subject_id: Subject ID
        nifti_files: Dict mapping sequence names to NIfTI file paths
        dry_run: If True, only show what would be done

    Returns:
        Dict mapping sequence names to brain mask paths
    """
    import subprocess

    brain_masks = {}
    subject_mask_dir = MASK_DIR / subject_id

    if not dry_run:
        subject_mask_dir.mkdir(parents=True, exist_ok=True)

    for seq_name, nifti_file in nifti_files.items():
        if nifti_file is None or not nifti_file.exists():
            continue

        brain_file = subject_mask_dir / f"{seq_name}_brain.nii.gz"
        # HD-BET creates mask with _mask.nii.gz appended to brain file name
        hdbet_mask_file = subject_mask_dir / f"{seq_name}_brain.nii_mask.nii.gz"
        # Our standard mask filename
        mask_file = subject_mask_dir / f"{seq_name}_mask.nii.gz"

        if dry_run:
            logger.info(f"  [DRY RUN] Would extract brain: {nifti_file.name}")
            continue

        logger.info(f"  Extracting brain for {seq_name}...")

        try:
            cmd = [
                '/Users/paul/miniforge3/envs/stage_analysis/bin/hd-bet',
                '-i', str(nifti_file),
                '-o', str(brain_file.with_suffix('')),  # HD-BET adds .nii.gz
                '-device', 'cpu',
                '-mode', 'fast',
                '-tta', '0'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            # HD-BET creates files with _mask.nii.gz suffix, rename to our standard
            if result.returncode == 0 and hdbet_mask_file.exists():
                # Rename to standard mask filename
                hdbet_mask_file.rename(mask_file)
                brain_masks[seq_name] = mask_file
                logger.info(f"    ✓ Created mask: {mask_file.name}")
            else:
                logger.error(f"    ✗ HD-BET failed: {result.stderr}")

        except Exception as e:
            logger.error(f"    ✗ Error running HD-BET on {seq_name}: {e}")

    return brain_masks


def run_tissue_segmentation(subject_id: str, nifti_files: Dict[str, Path],
                            brain_masks: Dict[str, Path], dry_run: bool = False) -> Dict[str, Dict[str, Path]]:
    """
    Run intensity-based tissue segmentation.

    Args:
        subject_id: Subject ID
        nifti_files: Dict mapping sequence names to NIfTI file paths
        brain_masks: Dict mapping sequence names to brain mask paths
        dry_run: If True, only show what would be done

    Returns:
        Dict mapping sequence names to dicts of tissue mask paths
    """
    import nibabel as nib

    tissue_masks = {}
    subject_seg_dir = SEG_DIR / subject_id

    if not dry_run:
        subject_seg_dir.mkdir(parents=True, exist_ok=True)

    for seq_name, nifti_file in nifti_files.items():
        if nifti_file is None or not nifti_file.exists():
            continue
        if seq_name not in brain_masks:
            continue

        if dry_run:
            logger.info(f"  [DRY RUN] Would segment tissues: {nifti_file.name}")
            continue

        logger.info(f"  Segmenting tissues for {seq_name}...")

        try:
            # Load images
            img = nib.load(nifti_file)
            data = img.get_fdata()
            mask_img = nib.load(brain_masks[seq_name])
            mask_data = mask_img.get_fdata() > 0

            # Apply brain mask
            masked_data = data * mask_data

            # Determine sequence type and thresholds
            if 'T1' in seq_name:
                # T1: WM is bright, GM is darker
                p_low, p_mid, p_high = np.percentile(masked_data[mask_data], [10, 50, 90])
                gm_mask = (masked_data >= p_mid) & (masked_data < p_high) & mask_data
                wm_mask = (masked_data >= p_high) & mask_data
            elif 'T2' in seq_name:
                # T2: GM is bright, WM is darker
                p_low, p_mid, p_high = np.percentile(masked_data[mask_data], [10, 50, 90])
                wm_mask = (masked_data >= p_mid) & (masked_data < p_high) & mask_data
                gm_mask = (masked_data >= p_high) & mask_data
            elif 'SWI' in seq_name:
                # SWI: Use similar to T2 (GM brighter)
                p_low, p_mid, p_high = np.percentile(masked_data[mask_data], [10, 50, 90])
                wm_mask = (masked_data >= p_mid) & (masked_data < p_high) & mask_data
                gm_mask = (masked_data >= p_high) & mask_data
            else:
                logger.warning(f"    Unknown sequence type: {seq_name}")
                continue

            # Save masks
            gm_path = subject_seg_dir / f"{seq_name}_GM_mask.nii.gz"
            wm_path = subject_seg_dir / f"{seq_name}_WM_mask.nii.gz"

            nib.save(nib.Nifti1Image(gm_mask.astype(np.uint8), img.affine), gm_path)
            nib.save(nib.Nifti1Image(wm_mask.astype(np.uint8), img.affine), wm_path)

            tissue_masks[seq_name] = {'GM': gm_path, 'WM': wm_path}
            logger.info(f"    ✓ Created GM and WM masks")

        except Exception as e:
            logger.error(f"    ✗ Error segmenting {seq_name}: {e}")

    return tissue_masks


def extract_tissue_intensities(subject_id: str, nifti_files: Dict[str, Path],
                               tissue_masks: Dict[str, Dict[str, Path]],
                               dry_run: bool = False) -> pd.DataFrame:
    """
    Extract mean intensities from tissue masks.

    Args:
        subject_id: Subject ID
        nifti_files: Dict mapping sequence names to NIfTI file paths
        tissue_masks: Dict mapping sequence names to tissue mask paths
        dry_run: If True, only show what would be done

    Returns:
        DataFrame with intensity statistics
    """
    import nibabel as nib

    if dry_run:
        logger.info(f"  [DRY RUN] Would extract tissue intensities")
        return pd.DataFrame()

    results = []

    for seq_name, nifti_file in nifti_files.items():
        if seq_name not in tissue_masks:
            continue

        try:
            # Load image
            img = nib.load(nifti_file)
            data = img.get_fdata()

            # Load tissue masks
            gm_mask_img = nib.load(tissue_masks[seq_name]['GM'])
            wm_mask_img = nib.load(tissue_masks[seq_name]['WM'])

            gm_mask = gm_mask_img.get_fdata() > 0
            wm_mask = wm_mask_img.get_fdata() > 0

            # Extract intensities
            gm_intensities = data[gm_mask]
            wm_intensities = data[wm_mask]

            if len(gm_intensities) > 0 and len(wm_intensities) > 0:
                results.append({
                    'subject_id': subject_id,
                    'sequence': seq_name,
                    'GM_mean': float(np.mean(gm_intensities)),
                    'GM_std': float(np.std(gm_intensities)),
                    'GM_voxels': int(np.sum(gm_mask)),
                    'WM_mean': float(np.mean(wm_intensities)),
                    'WM_std': float(np.std(wm_intensities)),
                    'WM_voxels': int(np.sum(wm_mask)),
                    'GM_WM_ratio': float(np.mean(gm_intensities) / np.mean(wm_intensities))
                })

                logger.info(f"  {seq_name}: GM={np.mean(gm_intensities):.1f}, WM={np.mean(wm_intensities):.1f}")

        except Exception as e:
            logger.error(f"  Error extracting intensities for {seq_name}: {e}")

    return pd.DataFrame(results)


def process_subject(subject_id: str, ground_truth_row: pd.Series, dry_run: bool = False) -> Tuple[bool, pd.DataFrame]:
    """
    Process one subject through complete pipeline.

    Args:
        subject_id: Subject ID
        ground_truth_row: Row from ground truth DataFrame
        dry_run: If True, only show what would be done

    Returns:
        Tuple of (success, intensity_dataframe)
    """
    logger.info("=" * 100)
    logger.info(f"Processing subject: {subject_id}")
    logger.info("=" * 100)

    # Step 1: Map series numbers to DICOM folders
    logger.info("\nStep 1: Mapping series numbers to DICOM folders...")
    series_mappings = {}

    for seq in SEQUENCES:
        series_col = f'{seq}_series'
        if series_col in ground_truth_row and pd.notna(ground_truth_row[series_col]):
            series_number = ground_truth_row[series_col]
            logger.info(f"  {seq}: series {series_number}")

            dicom_folder = find_dicom_folder(subject_id, series_number)
            if dicom_folder:
                series_mappings[seq] = dicom_folder
                logger.info(f"    ✓ Found: {dicom_folder}")
            else:
                logger.warning(f"    ✗ Not found")
                series_mappings[seq] = None
        else:
            logger.info(f"  {seq}: not specified (blank)")
            series_mappings[seq] = None

    # Count available sequences
    available_seqs = sum(1 for v in series_mappings.values() if v is not None)
    logger.info(f"\nFound {available_seqs}/{len(SEQUENCES)} sequences")

    if available_seqs == 0:
        logger.warning(f"No sequences found for {subject_id}, skipping")
        return False, pd.DataFrame()

    # Step 2: Clean previous outputs
    logger.info("\nStep 2: Cleaning previous outputs...")
    clean_previous_outputs(subject_id, dry_run)

    # Step 3: Convert DICOM to NIfTI
    logger.info("\nStep 3: Converting DICOM to NIfTI...")
    nifti_files = convert_dicom_to_nifti(subject_id, series_mappings, dry_run)

    if dry_run:
        logger.info(f"\n[DRY RUN] Would process {len(nifti_files)} sequences for {subject_id}")
        return True, pd.DataFrame()

    logger.info(f"\nConverted {len(nifti_files)} sequences to NIfTI")

    if len(nifti_files) == 0:
        logger.warning(f"No NIfTI files created for {subject_id}")
        return False, pd.DataFrame()

    # Step 4: Run HD-BET brain extraction
    logger.info("\nStep 4: Running HD-BET brain extraction...")
    brain_masks = run_hdbet(subject_id, nifti_files, dry_run)
    logger.info(f"Created {len(brain_masks)} brain masks")

    # Step 5: Run tissue segmentation
    logger.info("\nStep 5: Running tissue segmentation...")
    tissue_masks = run_tissue_segmentation(subject_id, nifti_files, brain_masks, dry_run)
    logger.info(f"Created tissue masks for {len(tissue_masks)} sequences")

    # Step 6: Extract intensities
    logger.info("\nStep 6: Extracting tissue intensities...")
    intensity_df = extract_tissue_intensities(subject_id, nifti_files, tissue_masks, dry_run)

    logger.info(f"\n✓ Successfully processed {subject_id}")
    return True, intensity_df


def perform_statistical_analysis(all_intensities: pd.DataFrame) -> None:
    """
    Perform statistical analysis on tissue intensities.

    Args:
        all_intensities: DataFrame with all tissue intensity measurements
    """
    from scipy import stats

    logger.info("=" * 100)
    logger.info("Performing Statistical Analysis")
    logger.info("=" * 100)

    # Save raw intensity data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stats_file = STATS_DIR / f"gm_wm_tissue_stats_{timestamp}.csv"
    all_intensities.to_csv(stats_file, index=False)
    logger.info(f"\nSaved tissue statistics: {stats_file}")

    # Create comparisons for conv vs STAGE
    comparisons = []
    for seq_type in ['T1', 'T2', 'SWI']:
        conv_seq = f"{seq_type}_conv"
        stage_seq = f"{seq_type}_STAGE"

        # Get matching subjects
        conv_data = all_intensities[all_intensities['sequence'] == conv_seq]
        stage_data = all_intensities[all_intensities['sequence'] == stage_seq]

        # Find subjects with both sequences
        common_subjects = set(conv_data['subject_id']) & set(stage_data['subject_id'])

        if len(common_subjects) > 0:
            for subject_id in common_subjects:
                conv_row = conv_data[conv_data['subject_id'] == subject_id].iloc[0]
                stage_row = stage_data[stage_data['subject_id'] == subject_id].iloc[0]

                comparisons.append({
                    'subject_id': subject_id,
                    'sequence_type': seq_type,
                    'GM_conv': conv_row['GM_mean'],
                    'GM_STAGE': stage_row['GM_mean'],
                    'WM_conv': conv_row['WM_mean'],
                    'WM_STAGE': stage_row['WM_mean'],
                    'GM_diff': stage_row['GM_mean'] - conv_row['GM_mean'],
                    'WM_diff': stage_row['WM_mean'] - conv_row['WM_mean'],
                    'GM_pct_diff': ((stage_row['GM_mean'] - conv_row['GM_mean']) / conv_row['GM_mean']) * 100,
                    'WM_pct_diff': ((stage_row['WM_mean'] - conv_row['WM_mean']) / conv_row['WM_mean']) * 100
                })

    df_comparisons = pd.DataFrame(comparisons)
    comp_file = STATS_DIR / f"gm_wm_comparisons_{timestamp}.csv"
    df_comparisons.to_csv(comp_file, index=False)
    logger.info(f"Saved comparisons: {comp_file}")

    # Perform statistical tests
    test_results = []
    for seq_type in ['T1', 'T2', 'SWI']:
        seq_comps = df_comparisons[df_comparisons['sequence_type'] == seq_type]

        if len(seq_comps) >= 3:  # Need at least 3 pairs for meaningful stats
            for tissue in ['GM', 'WM']:
                conv_col = f"{tissue}_conv"
                stage_col = f"{tissue}_STAGE"

                conv_vals = seq_comps[conv_col].values
                stage_vals = seq_comps[stage_col].values

                # Paired t-test
                t_stat, p_val = stats.ttest_rel(conv_vals, stage_vals)

                # Effect size (Cohen's d for paired samples)
                diff = stage_vals - conv_vals
                d = np.mean(diff) / np.std(diff)

                test_results.append({
                    'sequence_type': seq_type,
                    'tissue': tissue,
                    'n_subjects': len(seq_comps),
                    'conv_mean': np.mean(conv_vals),
                    'conv_std': np.std(conv_vals),
                    'stage_mean': np.mean(stage_vals),
                    'stage_std': np.std(stage_vals),
                    't_statistic': t_stat,
                    'p_value': p_val,
                    'cohens_d': d,
                    'mean_diff': np.mean(diff),
                    'pct_diff': (np.mean(diff) / np.mean(conv_vals)) * 100
                })

    df_tests = pd.DataFrame(test_results)
    test_file = STATS_DIR / f"gm_wm_statistical_tests_{timestamp}.csv"
    df_tests.to_csv(test_file, index=False)
    logger.info(f"Saved statistical tests: {test_file}")

    # Print summary
    logger.info("\n" + "=" * 100)
    logger.info("STATISTICAL RESULTS SUMMARY")
    logger.info("=" * 100)

    for _, row in df_tests.iterrows():
        logger.info(f"\n{row['sequence_type']} - {row['tissue']} (n={row['n_subjects']})")
        logger.info(f"  Conv:  {row['conv_mean']:.1f} ± {row['conv_std']:.1f}")
        logger.info(f"  STAGE: {row['stage_mean']:.1f} ± {row['stage_std']:.1f}")
        logger.info(f"  Diff:  {row['mean_diff']:.1f} ({row['pct_diff']:.1f}%)")
        logger.info(f"  Stats: t={row['t_statistic']:.2f}, p={row['p_value']:.4f}, d={row['cohens_d']:.2f}")
        if row['p_value'] < 0.05:
            logger.info(f"  **SIGNIFICANT at p<0.05**")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Reprocess with ground truth data')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without actually doing it')
    parser.add_argument('--subjects', nargs='+',
                       help='Process specific subjects only (default: all)')
    parser.add_argument('--validated-only', action='store_true',
                       help='Process only the 24 validated subjects')

    args = parser.parse_args()

    logger.info("=" * 100)
    logger.info("STAGE Study: Complete Reprocessing with Ground Truth Data")
    logger.info("=" * 100)
    logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("=" * 100)

    # Create output directories
    for dir_path in [NIFTI_DIR, MASK_DIR, REG_DIR, SEG_DIR, STATS_DIR, PLOTS_DIR, QC_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)

    # Load ground truth
    df_ground_truth = load_ground_truth()

    # Filter subjects if specified
    if args.validated_only:
        df_ground_truth = df_ground_truth[df_ground_truth['validated jm'] == 'x']
        logger.info(f"\nProcessing validated subjects only: {len(df_ground_truth)}")

    if args.subjects:
        df_ground_truth = df_ground_truth[df_ground_truth['rAccession'].isin(args.subjects)]
        logger.info(f"\nProcessing specified subjects: {len(df_ground_truth)}")

    logger.info(f"\nTotal subjects to process: {len(df_ground_truth)}")
    logger.info("=" * 100)

    # Process each subject
    success_count = 0
    fail_count = 0
    all_intensities = []

    for idx, row in df_ground_truth.iterrows():
        subject_id = row['rAccession']

        try:
            success, intensity_df = process_subject(subject_id, row, args.dry_run)
            if success:
                success_count += 1
                if not intensity_df.empty:
                    all_intensities.append(intensity_df)
            else:
                fail_count += 1
        except Exception as e:
            logger.error(f"Failed to process {subject_id}: {e}", exc_info=True)
            fail_count += 1
            continue

    logger.info("\n" + "=" * 100)
    logger.info("Subject Processing Complete!")
    logger.info("=" * 100)
    logger.info(f"Successfully processed: {success_count}")
    logger.info(f"Failed: {fail_count}")
    logger.info(f"Total: {success_count + fail_count}")
    logger.info("=" * 100)

    # Perform statistical analysis if not dry run
    if not args.dry_run and len(all_intensities) > 0:
        df_all_intensities = pd.concat(all_intensities, ignore_index=True)
        perform_statistical_analysis(df_all_intensities)

    logger.info("\n" + "=" * 100)
    logger.info("REPROCESSING COMPLETE!")
    logger.info("=" * 100)


if __name__ == '__main__':
    main()
