#!/usr/bin/env python3
"""
GM and WM Tissue Intensity Analysis for Validated STAGE Study Subjects

This script performs a comprehensive analysis comparing gray matter (GM) and
white matter (WM) signal intensities between conventional and STAGE sequences.

Pipeline:
1. Run SynthSeg tissue segmentation on all brain-masked sequences
2. Extract GM and WM masks from segmentation outputs
3. Calculate mean signal intensities in GM and WM regions
4. Compare GM similarities between conv and STAGE (within subject)
5. Compare WM similarities between conv and STAGE (within subject)
6. Perform statistical analysis across all subjects
7. Generate comprehensive visualizations

Usage:
    python scripts/gm_wm_tissue_analysis.py [--subjects SUBJECT_LIST] [--skip-synthseg]

Author: Analysis Pipeline
Date: 2025-10-16
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
import nibabel as nib
from scipy import stats
from scipy.stats import pearsonr, spearmanr
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'gm_wm_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Project paths
BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
NIFTI_DIR = BASE_DIR / 'output' / 'nifti'
MASK_DIR = BASE_DIR / 'output' / 'brain_masks'
SEG_DIR = BASE_DIR / 'output' / 'segmentations'
STATS_DIR = BASE_DIR / 'output' / 'statistics'
PLOTS_DIR = BASE_DIR / 'output' / 'plots'

# Ensure output directories exist
SEG_DIR.mkdir(parents=True, exist_ok=True)
STATS_DIR.mkdir(parents=True, exist_ok=True)
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

# Validated subjects
VALIDATED_SUBJECTS = [
    'Anon10644', 'Anon11271', 'Anon12335', 'Anon13609', 'Anon15062',
    'Anon16167', 'Anon20584', 'Anon21108', 'Anon26462', 'Anon27334',
    'Anon28027', 'Anon28076', 'Anon28584'
]

SEQUENCES = ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']

# SynthSeg label definitions
# Based on FreeSurfer labels used by SynthSeg
GM_LABELS = [3, 42, 17, 18, 53, 54]  # Left/Right Cerebral Cortex, Left/Right Hippocampus, etc.
WM_LABELS = [2, 41]  # Left and Right Cerebral White Matter
CSF_LABELS = [4, 5, 14, 15, 24, 43, 44]  # Lateral ventricles, 3rd ventricle, 4th ventricle, CSF

# More comprehensive GM labels (including subcortical structures)
GM_LABELS_FULL = [
    3, 42,    # Left/Right Cerebral Cortex
    17, 53,   # Left/Right Hippocampus
    18, 54,   # Left/Right Amygdala
    11, 50,   # Left/Right Caudate
    12, 51,   # Left/Right Putamen
    13, 52,   # Left/Right Pallidum
    10, 49,   # Left/Right Thalamus
]


def run_synthseg(input_file: Path, output_seg: Path, output_vol: Path = None) -> bool:
    """
    Run SynthSeg tissue segmentation on a brain-masked image.

    Args:
        input_file: Path to brain-masked NIfTI file
        output_seg: Path for output segmentation
        output_vol: Optional path for volume file

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Running SynthSeg on {input_file.name}...")

        # Check if SynthSeg is available
        import subprocess
        result = subprocess.run(
            ['which', 'mri_synthseg'],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            logger.error("SynthSeg (mri_synthseg) not found in PATH")
            logger.error("Please install FreeSurfer or ensure SynthSeg is available")
            return False

        # Build command
        cmd = [
            'mri_synthseg',
            '--i', str(input_file),
            '--o', str(output_seg),
            '--robust'  # Use robust mode for better performance on diverse data
        ]

        if output_vol:
            cmd.extend(['--vol', str(output_vol)])

        # Run SynthSeg
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            logger.info(f"✓ SynthSeg completed successfully")
            return True
        else:
            logger.error(f"✗ SynthSeg failed with error:\n{result.stderr}")
            return False

    except Exception as e:
        logger.error(f"Error running SynthSeg: {e}")
        return False


def extract_tissue_masks(seg_file: Path, gm_labels: List[int], wm_labels: List[int]) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extract GM and WM binary masks from SynthSeg segmentation.

    Args:
        seg_file: Path to segmentation file
        gm_labels: List of labels for gray matter
        wm_labels: List of labels for white matter

    Returns:
        Tuple of (gm_mask, wm_mask) as boolean arrays
    """
    try:
        # Load segmentation
        seg_img = nib.load(seg_file)
        seg_data = seg_img.get_fdata().astype(int)

        # Create GM mask
        gm_mask = np.isin(seg_data, gm_labels)

        # Create WM mask
        wm_mask = np.isin(seg_data, wm_labels)

        logger.info(f"  GM voxels: {gm_mask.sum():,} | WM voxels: {wm_mask.sum():,}")

        return gm_mask, wm_mask

    except Exception as e:
        logger.error(f"Error extracting tissue masks: {e}")
        return None, None


def extract_intensity_stats(image_file: Path, brain_mask_file: Path,
                            gm_mask: np.ndarray, wm_mask: np.ndarray) -> Dict:
    """
    Extract mean signal intensities from GM and WM regions.

    Args:
        image_file: Path to original (or registered) NIfTI image
        brain_mask_file: Path to brain mask
        gm_mask: Boolean array for GM
        wm_mask: Boolean array for WM

    Returns:
        Dictionary with intensity statistics
    """
    try:
        # Load image and brain mask
        img = nib.load(image_file)
        img_data = img.get_fdata()

        brain_mask = nib.load(brain_mask_file)
        brain_data = brain_mask.get_fdata() > 0

        # Apply brain mask to image
        masked_img = img_data * brain_data

        # Extract intensities
        gm_intensities = masked_img[gm_mask & brain_data]
        wm_intensities = masked_img[wm_mask & brain_data]
        whole_brain = masked_img[brain_data]

        # Calculate statistics
        stats_dict = {
            'gm_mean': np.mean(gm_intensities) if len(gm_intensities) > 0 else np.nan,
            'gm_std': np.std(gm_intensities) if len(gm_intensities) > 0 else np.nan,
            'gm_median': np.median(gm_intensities) if len(gm_intensities) > 0 else np.nan,
            'gm_n_voxels': len(gm_intensities),
            'wm_mean': np.mean(wm_intensities) if len(wm_intensities) > 0 else np.nan,
            'wm_std': np.std(wm_intensities) if len(wm_intensities) > 0 else np.nan,
            'wm_median': np.median(wm_intensities) if len(wm_intensities) > 0 else np.nan,
            'wm_n_voxels': len(wm_intensities),
            'brain_mean': np.mean(whole_brain) if len(whole_brain) > 0 else np.nan,
            'brain_std': np.std(whole_brain) if len(whole_brain) > 0 else np.nan,
            'gm_wm_ratio': (np.mean(gm_intensities) / np.mean(wm_intensities))
                           if len(gm_intensities) > 0 and len(wm_intensities) > 0
                           and np.mean(wm_intensities) > 0 else np.nan
        }

        return stats_dict

    except Exception as e:
        logger.error(f"Error extracting intensity stats: {e}")
        return None


def calculate_tissue_similarity(conv_intensities: np.ndarray, stage_intensities: np.ndarray) -> Dict:
    """
    Calculate similarity metrics between conventional and STAGE tissue intensities.

    Args:
        conv_intensities: Array of intensity values from conventional sequence
        stage_intensities: Array of intensity values from STAGE sequence

    Returns:
        Dictionary with similarity metrics
    """
    try:
        # Flatten arrays
        conv_flat = conv_intensities.flatten()
        stage_flat = stage_intensities.flatten()

        # Remove NaN values
        valid_mask = ~(np.isnan(conv_flat) | np.isnan(stage_flat))
        conv_valid = conv_flat[valid_mask]
        stage_valid = stage_flat[valid_mask]

        if len(conv_valid) < 2 or len(stage_valid) < 2:
            logger.warning("Not enough valid data points for correlation")
            return {
                'pearson_r': np.nan,
                'pearson_p': np.nan,
                'spearman_r': np.nan,
                'spearman_p': np.nan,
                'mean_diff': np.nan,
                'mean_abs_diff': np.nan,
                'percent_diff': np.nan
            }

        # Pearson correlation
        pearson_r, pearson_p = pearsonr(conv_valid, stage_valid)

        # Spearman correlation
        spearman_r, spearman_p = spearmanr(conv_valid, stage_valid)

        # Difference metrics
        mean_diff = np.mean(stage_valid) - np.mean(conv_valid)
        mean_abs_diff = np.abs(mean_diff)
        percent_diff = (mean_diff / np.mean(conv_valid) * 100) if np.mean(conv_valid) != 0 else np.nan

        return {
            'pearson_r': pearson_r,
            'pearson_p': pearson_p,
            'spearman_r': spearman_r,
            'spearman_p': spearman_p,
            'mean_diff': mean_diff,
            'mean_abs_diff': mean_abs_diff,
            'percent_diff': percent_diff,
            'n_voxels': len(conv_valid)
        }

    except Exception as e:
        logger.error(f"Error calculating similarity: {e}")
        return None


def process_subject(subject_id: str, skip_synthseg: bool = False) -> Dict:
    """
    Process one subject through the complete GM/WM analysis pipeline.

    Args:
        subject_id: Patient ID
        skip_synthseg: If True, skip SynthSeg and use existing segmentations

    Returns:
        Dictionary with analysis results
    """
    logger.info("=" * 100)
    logger.info(f"Processing subject: {subject_id}")
    logger.info("=" * 100)

    subject_results = {
        'subject_id': subject_id,
        'sequences_processed': [],
        'tissue_stats': {},
        'comparisons': {}
    }

    # Create output directories for this subject
    subj_seg_dir = SEG_DIR / subject_id
    subj_seg_dir.mkdir(exist_ok=True)

    # Process each sequence
    for seq in SEQUENCES:
        logger.info(f"\n--- Processing {seq} ---")

        # Check if brain mask exists
        brain_mask_file = MASK_DIR / subject_id / f"{seq}_mask.nii.gz"
        if not brain_mask_file.exists():
            logger.warning(f"  Brain mask not found for {seq}, skipping")
            continue

        # Define paths
        nifti_file = NIFTI_DIR / subject_id / f"{seq}.nii.gz"
        seg_file = subj_seg_dir / f"{seq}_synthseg.nii.gz"
        vol_file = subj_seg_dir / f"{seq}_volumes.csv"

        # Run SynthSeg if needed
        if not skip_synthseg or not seg_file.exists():
            success = run_synthseg(brain_mask_file, seg_file, vol_file)
            if not success:
                logger.error(f"  Failed to segment {seq}")
                continue
        else:
            logger.info(f"  Using existing segmentation: {seg_file.name}")

        # Extract tissue masks
        gm_mask, wm_mask = extract_tissue_masks(seg_file, GM_LABELS_FULL, WM_LABELS)
        if gm_mask is None or wm_mask is None:
            logger.error(f"  Failed to extract tissue masks for {seq}")
            continue

        # Extract intensity statistics
        stats = extract_intensity_stats(nifti_file, brain_mask_file, gm_mask, wm_mask)
        if stats is None:
            logger.error(f"  Failed to extract intensity stats for {seq}")
            continue

        # Store results
        subject_results['sequences_processed'].append(seq)
        subject_results['tissue_stats'][seq] = stats

        logger.info(f"  ✓ GM mean: {stats['gm_mean']:.3f} | WM mean: {stats['wm_mean']:.3f} | "
                   f"GM/WM ratio: {stats['gm_wm_ratio']:.3f}")

    logger.info(f"\n{subject_id}: Processed {len(subject_results['sequences_processed'])} sequences")

    return subject_results


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='GM and WM Tissue Intensity Analysis')
    parser.add_argument('--subjects', nargs='+', default=VALIDATED_SUBJECTS,
                       help='List of subject IDs to process')
    parser.add_argument('--skip-synthseg', action='store_true',
                       help='Skip SynthSeg and use existing segmentations')
    parser.add_argument('--gm-labels', nargs='+', type=int, default=GM_LABELS_FULL,
                       help='SynthSeg labels for gray matter')
    parser.add_argument('--wm-labels', nargs='+', type=int, default=WM_LABELS,
                       help='SynthSeg labels for white matter')

    args = parser.parse_args()

    logger.info("=" * 100)
    logger.info("STAGE Study: GM and WM Tissue Intensity Analysis")
    logger.info("=" * 100)
    logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Subjects to process: {len(args.subjects)}")
    logger.info(f"Skip SynthSeg: {args.skip_synthseg}")
    logger.info(f"GM labels: {args.gm_labels}")
    logger.info(f"WM labels: {args.wm_labels}")
    logger.info("=" * 100)

    # Process all subjects
    all_results = []

    for subject_id in args.subjects:
        try:
            results = process_subject(subject_id, args.skip_synthseg)
            all_results.append(results)
        except Exception as e:
            logger.error(f"Failed to process {subject_id}: {e}")
            continue

    logger.info("=" * 100)
    logger.info("Processing complete!")
    logger.info(f"Successfully processed {len(all_results)} subjects")
    logger.info("=" * 100)

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = STATS_DIR / f'gm_wm_tissue_results_{timestamp}.pkl'

    import pickle
    with open(results_file, 'wb') as f:
        pickle.dump(all_results, f)

    logger.info(f"Results saved to: {results_file}")

    return all_results


if __name__ == '__main__':
    main()
