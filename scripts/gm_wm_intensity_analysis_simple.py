#!/usr/bin/env python3
"""
GM and WM Intensity-Based Analysis for Validated STAGE Study Subjects

This script performs intensity-based tissue segmentation and comparative analysis
of gray matter (GM) and white matter (WM) signal intensities between conventional
and STAGE sequences.

Approach:
- Uses intensity-based thresholding to segment GM and WM
- T1: WM is brightest, GM is intermediate
- T2: GM is brighter than WM
- Calculates mean intensities within each tissue type
- Compares similarities between conv and STAGE within subjects

Usage:
    python scripts/gm_wm_intensity_analysis_simple.py

Author: Analysis Pipeline
Date: 2025-10-16
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
import nibabel as nib
from scipy import stats, ndimage
from scipy.stats import pearsonr, spearmanr
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple
from dataclasses import dataclass

# Configure logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'gm_wm_analysis_{timestamp}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Project paths
BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
NIFTI_DIR = BASE_DIR / 'output' / 'nifti'
MASK_DIR = BASE_DIR / 'output' / 'brain_masks'
SEG_DIR = BASE_DIR / 'output' / 'tissue_segmentations'
STATS_DIR = BASE_DIR / 'output' / 'statistics'
PLOTS_DIR = BASE_DIR / 'output' / 'plots'

# Ensure output directories exist
for dir_path in [SEG_DIR, STATS_DIR, PLOTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Validated subjects
VALIDATED_SUBJECTS = [
    'Anon10644', 'Anon11271', 'Anon12335', 'Anon13609', 'Anon15062',
    'Anon16167', 'Anon20584', 'Anon21108', 'Anon26462', 'Anon27334',
    'Anon28027', 'Anon28076', 'Anon28584'
]

SEQUENCES = ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']


@dataclass
class TissueStats:
    """Container for tissue intensity statistics."""
    gm_mean: float
    gm_std: float
    gm_median: float
    gm_n_voxels: int
    wm_mean: float
    wm_std: float
    wm_median: float
    wm_n_voxels: int
    gm_wm_ratio: float
    brain_mean: float
    brain_std: float


def segment_tissues_t1(brain_data: np.ndarray, brain_mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Segment GM and WM from T1-weighted image using intensity-based approach.

    T1 characteristics:
    - WM: Brightest (highest intensity)
    - GM: Intermediate intensity
    - CSF: Darkest (lowest intensity)

    Args:
        brain_data: Brain image data
        brain_mask: Binary brain mask

    Returns:
        Tuple of (gm_mask, wm_mask)
    """
    try:
        # Get masked brain intensities
        brain_intensities = brain_data[brain_mask > 0]

        # Calculate percentiles for tissue segmentation
        p20 = np.percentile(brain_intensities, 20)  # CSF/GM boundary
        p50 = np.percentile(brain_intensities, 50)  # GM median
        p75 = np.percentile(brain_intensities, 75)  # GM/WM boundary
        p95 = np.percentile(brain_intensities, 95)  # Upper WM

        # Create tissue masks
        # WM: top 25% of intensities (75th-95th percentile)
        wm_mask = (brain_data >= p75) & (brain_data <= p95) & brain_mask

        # GM: intermediate intensities (30th-70th percentile)
        p30 = np.percentile(brain_intensities, 30)
        p70 = np.percentile(brain_intensities, 70)
        gm_mask = (brain_data >= p30) & (brain_data < p70) & brain_mask

        # Apply morphological operations to clean up masks
        gm_mask = ndimage.binary_erosion(gm_mask, iterations=1)
        gm_mask = ndimage.binary_dilation(gm_mask, iterations=1)

        wm_mask = ndimage.binary_erosion(wm_mask, iterations=1)
        wm_mask = ndimage.binary_dilation(wm_mask, iterations=1)

        logger.info(f"    T1 segmentation: GM={gm_mask.sum():,} voxels, WM={wm_mask.sum():,} voxels")

        return gm_mask, wm_mask

    except Exception as e:
        logger.error(f"Error in T1 tissue segmentation: {e}")
        return None, None


def segment_tissues_t2(brain_data: np.ndarray, brain_mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Segment GM and WM from T2-weighted image.

    T2 characteristics:
    - CSF: Brightest
    - GM: Bright (more than WM)
    - WM: Darker than GM

    Args:
        brain_data: Brain image data
        brain_mask: Binary brain mask

    Returns:
        Tuple of (gm_mask, wm_mask)
    """
    try:
        brain_intensities = brain_data[brain_mask > 0]

        # T2: CSF is very bright, we want to exclude it
        p10 = np.percentile(brain_intensities, 10)
        p40 = np.percentile(brain_intensities, 40)  # WM range
        p60 = np.percentile(brain_intensities, 60)  # GM range
        p85 = np.percentile(brain_intensities, 85)  # Upper GM, before CSF

        # WM: darker tissues (10th-45th percentile)
        p45 = np.percentile(brain_intensities, 45)
        wm_mask = (brain_data >= p10) & (brain_data < p45) & brain_mask

        # GM: intermediate-bright tissues (45th-85th percentile), excluding CSF
        gm_mask = (brain_data >= p45) & (brain_data < p85) & brain_mask

        # Morphological cleanup
        gm_mask = ndimage.binary_erosion(gm_mask, iterations=1)
        gm_mask = ndimage.binary_dilation(gm_mask, iterations=1)

        wm_mask = ndimage.binary_erosion(wm_mask, iterations=1)
        wm_mask = ndimage.binary_dilation(wm_mask, iterations=1)

        logger.info(f"    T2 segmentation: GM={gm_mask.sum():,} voxels, WM={wm_mask.sum():,} voxels")

        return gm_mask, wm_mask

    except Exception as e:
        logger.error(f"Error in T2 tissue segmentation: {e}")
        return None, None


def segment_tissues_swi(brain_data: np.ndarray, brain_mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Segment GM and WM from SWI image.

    SWI characteristics are complex due to susceptibility weighting.
    We'll use a conservative approach focusing on intensity distribution.

    Args:
        brain_data: Brain image data
        brain_mask: Binary brain mask

    Returns:
        Tuple of (gm_mask, wm_mask)
    """
    try:
        brain_intensities = brain_data[brain_mask > 0]

        # SWI: Use broader ranges due to complex contrast
        p25 = np.percentile(brain_intensities, 25)
        p50 = np.percentile(brain_intensities, 50)
        p75 = np.percentile(brain_intensities, 75)

        # Conservative tissue masks
        wm_mask = (brain_data >= p50) & (brain_data < p75) & brain_mask
        gm_mask = (brain_data >= p25) & (brain_data < p50) & brain_mask

        # More aggressive morphological cleanup for SWI
        gm_mask = ndimage.binary_erosion(gm_mask, iterations=2)
        gm_mask = ndimage.binary_dilation(gm_mask, iterations=2)

        wm_mask = ndimage.binary_erosion(wm_mask, iterations=2)
        wm_mask = ndimage.binary_dilation(wm_mask, iterations=2)

        logger.info(f"    SWI segmentation: GM={gm_mask.sum():,} voxels, WM={wm_mask.sum():,} voxels")

        return gm_mask, wm_mask

    except Exception as e:
        logger.error(f"Error in SWI tissue segmentation: {e}")
        return None, None


def segment_tissues(brain_data: np.ndarray, brain_mask: np.ndarray, sequence_type: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    Segment tissues based on sequence type.

    Args:
        brain_data: Brain image data
        brain_mask: Binary brain mask
        sequence_type: Sequence type ('T1', 'T2', or 'SWI')

    Returns:
        Tuple of (gm_mask, wm_mask)
    """
    if 'T1' in sequence_type:
        return segment_tissues_t1(brain_data, brain_mask)
    elif 'T2' in sequence_type:
        return segment_tissues_t2(brain_data, brain_mask)
    elif 'SWI' in sequence_type:
        return segment_tissues_swi(brain_data, brain_mask)
    else:
        logger.error(f"Unknown sequence type: {sequence_type}")
        return None, None


def extract_tissue_stats(image_file: Path, mask_file: Path, sequence_type: str) -> TissueStats:
    """
    Extract tissue intensity statistics from a brain-masked image.

    Args:
        image_file: Path to NIfTI image
        mask_file: Path to brain mask
        sequence_type: Sequence type for appropriate segmentation

    Returns:
        TissueStats object with intensity statistics
    """
    try:
        # Load image and mask
        img = nib.load(image_file)
        img_data = img.get_fdata()

        mask = nib.load(mask_file)
        mask_data = mask.get_fdata() > 0

        # Segment tissues
        gm_mask, wm_mask = segment_tissues(img_data, mask_data, sequence_type)

        if gm_mask is None or wm_mask is None:
            return None

        # Extract intensities
        gm_intensities = img_data[gm_mask]
        wm_intensities = img_data[wm_mask]
        brain_intensities = img_data[mask_data]

        # Calculate statistics
        stats = TissueStats(
            gm_mean=float(np.mean(gm_intensities)) if len(gm_intensities) > 0 else np.nan,
            gm_std=float(np.std(gm_intensities)) if len(gm_intensities) > 0 else np.nan,
            gm_median=float(np.median(gm_intensities)) if len(gm_intensities) > 0 else np.nan,
            gm_n_voxels=int(len(gm_intensities)),
            wm_mean=float(np.mean(wm_intensities)) if len(wm_intensities) > 0 else np.nan,
            wm_std=float(np.std(wm_intensities)) if len(wm_intensities) > 0 else np.nan,
            wm_median=float(np.median(wm_intensities)) if len(wm_intensities) > 0 else np.nan,
            wm_n_voxels=int(len(wm_intensities)),
            gm_wm_ratio=float(np.mean(gm_intensities) / np.mean(wm_intensities))
                         if len(gm_intensities) > 0 and len(wm_intensities) > 0 and np.mean(wm_intensities) > 0
                         else np.nan,
            brain_mean=float(np.mean(brain_intensities)),
            brain_std=float(np.std(brain_intensities))
        )

        # Save tissue masks for QC
        subj_seg_dir = SEG_DIR / image_file.parent.name
        subj_seg_dir.mkdir(exist_ok=True)

        # Save GM mask
        gm_img = nib.Nifti1Image(gm_mask.astype(np.uint8), img.affine, img.header)
        nib.save(gm_img, subj_seg_dir / f"{image_file.stem.replace('.nii', '')}_GM_mask.nii.gz")

        # Save WM mask
        wm_img = nib.Nifti1Image(wm_mask.astype(np.uint8), img.affine, img.header)
        nib.save(wm_img, subj_seg_dir / f"{image_file.stem.replace('.nii', '')}_WM_mask.nii.gz")

        return stats

    except Exception as e:
        logger.error(f"Error extracting tissue stats: {e}")
        return None


def calculate_similarity_metrics(conv_stats: TissueStats, stage_stats: TissueStats) -> Dict:
    """
    Calculate similarity metrics between conventional and STAGE tissue intensities.

    Args:
        conv_stats: TissueStats for conventional sequence
        stage_stats: TissueStats for STAGE sequence

    Returns:
        Dictionary with similarity metrics
    """
    try:
        results = {}

        # GM comparison
        results['gm_mean_diff'] = stage_stats.gm_mean - conv_stats.gm_mean
        results['gm_percent_diff'] = (results['gm_mean_diff'] / conv_stats.gm_mean * 100) if conv_stats.gm_mean != 0 else np.nan
        results['gm_conv_mean'] = conv_stats.gm_mean
        results['gm_stage_mean'] = stage_stats.gm_mean
        results['gm_conv_std'] = conv_stats.gm_std
        results['gm_stage_std'] = stage_stats.gm_std

        # WM comparison
        results['wm_mean_diff'] = stage_stats.wm_mean - conv_stats.wm_mean
        results['wm_percent_diff'] = (results['wm_mean_diff'] / conv_stats.wm_mean * 100) if conv_stats.wm_mean != 0 else np.nan
        results['wm_conv_mean'] = conv_stats.wm_mean
        results['wm_stage_mean'] = stage_stats.wm_mean
        results['wm_conv_std'] = conv_stats.wm_std
        results['wm_stage_std'] = stage_stats.wm_std

        # GM/WM ratios
        results['gm_wm_ratio_conv'] = conv_stats.gm_wm_ratio
        results['gm_wm_ratio_stage'] = stage_stats.gm_wm_ratio
        results['gm_wm_ratio_diff'] = stage_stats.gm_wm_ratio - conv_stats.gm_wm_ratio

        # Voxel counts
        results['gm_conv_voxels'] = conv_stats.gm_n_voxels
        results['gm_stage_voxels'] = stage_stats.gm_n_voxels
        results['wm_conv_voxels'] = conv_stats.wm_n_voxels
        results['wm_stage_voxels'] = stage_stats.wm_n_voxels

        return results

    except Exception as e:
        logger.error(f"Error calculating similarity metrics: {e}")
        return None


def process_subject(subject_id: str) -> Dict:
    """
    Process one subject through the complete GM/WM analysis pipeline.

    Args:
        subject_id: Patient ID

    Returns:
        Dictionary with analysis results
    """
    logger.info("=" * 100)
    logger.info(f"Processing subject: {subject_id}")
    logger.info("=" * 100)

    results = {
        'subject_id': subject_id,
        'tissue_stats': {},
        'comparisons': {}
    }

    # Process each sequence
    for seq in SEQUENCES:
        nifti_file = NIFTI_DIR / subject_id / f"{seq}.nii.gz"
        mask_file = MASK_DIR / subject_id / f"{seq}_mask.nii.gz"

        if not nifti_file.exists() or not mask_file.exists():
            logger.warning(f"  {seq}: Missing files, skipping")
            continue

        logger.info(f"  Processing {seq}...")

        # Extract tissue statistics
        stats = extract_tissue_stats(nifti_file, mask_file, seq.split('_')[0])

        if stats is None:
            logger.error(f"  {seq}: Failed to extract tissue stats")
            continue

        results['tissue_stats'][seq] = stats
        logger.info(f"    ✓ GM: {stats.gm_mean:.3f} ± {stats.gm_std:.3f} (n={stats.gm_n_voxels:,})")
        logger.info(f"    ✓ WM: {stats.wm_mean:.3f} ± {stats.wm_std:.3f} (n={stats.wm_n_voxels:,})")
        logger.info(f"    ✓ GM/WM ratio: {stats.gm_wm_ratio:.3f}")

    # Calculate comparisons (conv vs STAGE)
    for seq_type in ['T1', 'T2', 'SWI']:
        conv_seq = f"{seq_type}_conv"
        stage_seq = f"{seq_type}_STAGE"

        if conv_seq in results['tissue_stats'] and stage_seq in results['tissue_stats']:
            logger.info(f"\n  Comparing {conv_seq} vs {stage_seq}...")

            metrics = calculate_similarity_metrics(
                results['tissue_stats'][conv_seq],
                results['tissue_stats'][stage_seq]
            )

            if metrics:
                results['comparisons'][seq_type] = metrics
                logger.info(f"    GM mean diff: {metrics['gm_mean_diff']:.3f} ({metrics['gm_percent_diff']:.1f}%)")
                logger.info(f"    WM mean diff: {metrics['wm_mean_diff']:.3f} ({metrics['wm_percent_diff']:.1f}%)")

    logger.info(f"\n{subject_id}: Processed {len(results['tissue_stats'])} sequences, {len(results['comparisons'])} comparisons")

    return results


def save_results_to_csv(all_results: List[Dict]) -> None:
    """
    Save all results to CSV files.

    Args:
        all_results: List of result dictionaries from all subjects
    """
    logger.info("\n" + "=" * 100)
    logger.info("Saving results to CSV files...")
    logger.info("=" * 100)

    # Prepare data for tissue stats CSV
    tissue_rows = []
    for result in all_results:
        subject_id = result['subject_id']
        for seq, stats in result['tissue_stats'].items():
            row = {
                'subject_id': subject_id,
                'sequence': seq,
                'gm_mean': stats.gm_mean,
                'gm_std': stats.gm_std,
                'gm_median': stats.gm_median,
                'gm_n_voxels': stats.gm_n_voxels,
                'wm_mean': stats.wm_mean,
                'wm_std': stats.wm_std,
                'wm_median': stats.wm_median,
                'wm_n_voxels': stats.wm_n_voxels,
                'gm_wm_ratio': stats.gm_wm_ratio,
                'brain_mean': stats.brain_mean,
                'brain_std': stats.brain_std
            }
            tissue_rows.append(row)

    df_tissue = pd.DataFrame(tissue_rows)
    tissue_file = STATS_DIR / f'gm_wm_tissue_stats_{timestamp}.csv'
    df_tissue.to_csv(tissue_file, index=False)
    logger.info(f"✓ Tissue stats saved to: {tissue_file.name}")

    # Prepare data for comparisons CSV
    comparison_rows = []
    for result in all_results:
        subject_id = result['subject_id']
        for seq_type, metrics in result['comparisons'].items():
            row = {'subject_id': subject_id, 'sequence_type': seq_type}
            row.update(metrics)
            comparison_rows.append(row)

    df_comp = pd.DataFrame(comparison_rows)
    comp_file = STATS_DIR / f'gm_wm_comparisons_{timestamp}.csv'
    df_comp.to_csv(comp_file, index=False)
    logger.info(f"✓ Comparisons saved to: {comp_file.name}")

    return df_tissue, df_comp


def perform_statistical_analysis(df_comp: pd.DataFrame) -> pd.DataFrame:
    """
    Perform statistical analysis on GM and WM comparisons.

    Args:
        df_comp: DataFrame with comparison metrics

    Returns:
        DataFrame with statistical test results
    """
    logger.info("\n" + "=" * 100)
    logger.info("Performing Statistical Analysis...")
    logger.info("=" * 100)

    results = []

    for seq_type in ['T1', 'T2', 'SWI']:
        df_seq = df_comp[df_comp['sequence_type'] == seq_type]

        if len(df_seq) < 2:
            logger.warning(f"{seq_type}: Not enough data for statistical analysis (n={len(df_seq)})")
            continue

        logger.info(f"\n{seq_type} (n={len(df_seq)} subjects):")
        logger.info("-" * 50)

        # GM analysis
        gm_conv = df_seq['gm_conv_mean'].values
        gm_stage = df_seq['gm_stage_mean'].values

        # Paired t-test for GM
        if len(gm_conv) >= 2:
            t_stat_gm, p_val_gm = stats.ttest_rel(gm_conv, gm_stage)
            effect_size_gm = (np.mean(gm_stage) - np.mean(gm_conv)) / np.std(gm_conv - gm_stage)

            logger.info(f"  GM:  Conv={np.mean(gm_conv):.3f}±{np.std(gm_conv):.3f}, "
                       f"STAGE={np.mean(gm_stage):.3f}±{np.std(gm_stage):.3f}")
            logger.info(f"       t={t_stat_gm:.3f}, p={p_val_gm:.4f}, d={effect_size_gm:.3f}")

        # WM analysis
        wm_conv = df_seq['wm_conv_mean'].values
        wm_stage = df_seq['wm_stage_mean'].values

        # Paired t-test for WM
        if len(wm_conv) >= 2:
            t_stat_wm, p_val_wm = stats.ttest_rel(wm_conv, wm_stage)
            effect_size_wm = (np.mean(wm_stage) - np.mean(wm_conv)) / np.std(wm_conv - wm_stage)

            logger.info(f"  WM:  Conv={np.mean(wm_conv):.3f}±{np.std(wm_conv):.3f}, "
                       f"STAGE={np.mean(wm_stage):.3f}±{np.std(wm_stage):.3f}")
            logger.info(f"       t={t_stat_wm:.3f}, p={p_val_wm:.4f}, d={effect_size_wm:.3f}")

        # Store results
        result_row = {
            'sequence_type': seq_type,
            'n_subjects': len(df_seq),
            'gm_conv_mean': np.mean(gm_conv),
            'gm_conv_std': np.std(gm_conv),
            'gm_stage_mean': np.mean(gm_stage),
            'gm_stage_std': np.std(gm_stage),
            'gm_t_stat': t_stat_gm,
            'gm_p_value': p_val_gm,
            'gm_effect_size': effect_size_gm,
            'wm_conv_mean': np.mean(wm_conv),
            'wm_conv_std': np.std(wm_conv),
            'wm_stage_mean': np.mean(wm_stage),
            'wm_stage_std': np.std(wm_stage),
            'wm_t_stat': t_stat_wm,
            'wm_p_value': p_val_wm,
            'wm_effect_size': effect_size_wm
        }
        results.append(result_row)

    df_stats = pd.DataFrame(results)
    stats_file = STATS_DIR / f'gm_wm_statistical_tests_{timestamp}.csv'
    df_stats.to_csv(stats_file, index=False)
    logger.info(f"\n✓ Statistical results saved to: {stats_file.name}")

    return df_stats


def main():
    """Main execution function."""
    logger.info("=" * 100)
    logger.info("STAGE Study: GM and WM Intensity-Based Analysis")
    logger.info("=" * 100)
    logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Subjects to process: {len(VALIDATED_SUBJECTS)}")
    logger.info("=" * 100)

    # Process all subjects
    all_results = []

    for subject_id in VALIDATED_SUBJECTS:
        try:
            results = process_subject(subject_id)
            all_results.append(results)
        except Exception as e:
            logger.error(f"Failed to process {subject_id}: {e}", exc_info=True)
            continue

    logger.info("\n" + "=" * 100)
    logger.info(f"Successfully processed {len(all_results)}/{len(VALIDATED_SUBJECTS)} subjects")
    logger.info("=" * 100)

    if len(all_results) == 0:
        logger.error("No subjects were successfully processed!")
        return

    # Save results to CSV
    df_tissue, df_comp = save_results_to_csv(all_results)

    # Perform statistical analysis
    df_stats = perform_statistical_analysis(df_comp)

    logger.info("\n" + "=" * 100)
    logger.info("Analysis Complete!")
    logger.info("=" * 100)
    logger.info(f"Output files saved to: {STATS_DIR}")
    logger.info(f"Tissue masks saved to: {SEG_DIR}")
    logger.info("=" * 100)


if __name__ == '__main__':
    main()
