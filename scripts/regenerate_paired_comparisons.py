#!/usr/bin/env python3
"""
Regenerate paired comparisons file from ground truth and merged statistics.
Uses series numbers from ground truth for accurate matching.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

# File paths
GROUND_TRUTH_FILE = Path('output/classifier_training/ground_truth_training_data.csv')
MERGED_STATS_FILE = Path('output/statistics/gm_wm_tissue_stats_MERGED.csv')
PAIRED_OUTPUT_FILE = Path('output/statistics/paired_comparisons_MERGED.csv')

def main():
    print("=" * 80)
    print("REGENERATING PAIRED COMPARISONS FILE")
    print("=" * 80)

    # Backup existing file
    if PAIRED_OUTPUT_FILE.exists():
        backup_name = f"paired_comparisons_MERGED_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        backup_path = PAIRED_OUTPUT_FILE.parent / backup_name
        PAIRED_OUTPUT_FILE.rename(backup_path)
        print(f"\n✓ Backed up existing file to: {backup_name}")

    # Load data
    print(f"\nLoading ground truth from: {GROUND_TRUTH_FILE}")
    df_gt = pd.read_csv(GROUND_TRUTH_FILE)

    print(f"Loading merged statistics from: {MERGED_STATS_FILE}")
    df_stats = pd.read_csv(MERGED_STATS_FILE)

    print(f"\n  Ground truth: {len(df_gt)} sequences")
    print(f"  Merged stats: {len(df_stats)} sequences")

    # Get unique subjects
    all_subjects = sorted(df_gt['subject_id'].unique())
    print(f"  Subjects: {len(all_subjects)}")

    # Create paired comparisons for each modality
    sequence_modalities = ['T1', 'T2', 'SWI']
    all_paired_data = []

    for modality in sequence_modalities:
        conv_seq = f'{modality}_conv'
        stage_seq = f'{modality}_STAGE'

        print(f"\nProcessing {modality} pairs...")

        pairs_found = 0
        for subject in all_subjects:
            # Get ground truth sequences for this subject
            gt_subject = df_gt[df_gt['subject_id'] == subject]

            # Check if both conv and STAGE exist in ground truth
            conv_gt = gt_subject[gt_subject['sequence_type'] == conv_seq]
            stage_gt = gt_subject[gt_subject['sequence_type'] == stage_seq]

            if len(conv_gt) == 0 or len(stage_gt) == 0:
                continue  # Skip if not a complete pair

            # Get series numbers from ground truth
            conv_series = conv_gt.iloc[0]['series_number']
            stage_series = stage_gt.iloc[0]['series_number']

            # Find corresponding rows in merged stats
            # Match by subject_id and sequence type
            conv_stats = df_stats[(df_stats['subject_id'] == subject) &
                                 (df_stats['sequence'] == conv_seq)]
            stage_stats = df_stats[(df_stats['subject_id'] == subject) &
                                  (df_stats['sequence'] == stage_seq)]

            if len(conv_stats) == 0 or len(stage_stats) == 0:
                print(f"  ⚠️  {subject}: Ground truth has {modality} pair, but missing from stats!")
                print(f"      Conv in stats: {len(conv_stats)}, STAGE in stats: {len(stage_stats)}")
                continue

            # Extract statistics
            conv_row = conv_stats.iloc[0]
            stage_row = stage_stats.iloc[0]

            # Create paired comparison row
            paired_row = {
                'subject_id': subject,
                'sequence_type': modality,
                'conv_series_number': conv_series,
                'stage_series_number': stage_series,
                'conv_gm_mean': conv_row['gm_mean'],
                'conv_gm_std': conv_row['gm_std'],
                'conv_wm_mean': conv_row['wm_mean'],
                'conv_wm_std': conv_row['wm_std'],
                'conv_gm_wm_ratio': conv_row['gm_wm_ratio'],
                'stage_gm_mean': stage_row['gm_mean'],
                'stage_gm_std': stage_row['gm_std'],
                'stage_wm_mean': stage_row['wm_mean'],
                'stage_wm_std': stage_row['wm_std'],
                'stage_gm_wm_ratio': stage_row['gm_wm_ratio'],
                # Calculate differences
                'gm_mean_diff': stage_row['gm_mean'] - conv_row['gm_mean'],
                'wm_mean_diff': stage_row['wm_mean'] - conv_row['wm_mean'],
                'gm_wm_ratio_diff': stage_row['gm_wm_ratio'] - conv_row['gm_wm_ratio'],
            }

            all_paired_data.append(paired_row)
            pairs_found += 1

        print(f"  ✓ Found {pairs_found} complete {modality} pairs")

    # Create DataFrame
    df_paired = pd.DataFrame(all_paired_data)

    # Sort by subject and sequence type
    df_paired = df_paired.sort_values(['subject_id', 'sequence_type'])

    # Save to file
    df_paired.to_csv(PAIRED_OUTPUT_FILE, index=False)

    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print("=" * 80)
    print(f"Total paired comparisons: {len(df_paired)}")
    for modality in sequence_modalities:
        count = len(df_paired[df_paired['sequence_type'] == modality])
        print(f"  {modality}: {count} pairs")

    print(f"\n✓ Saved to: {PAIRED_OUTPUT_FILE}")

    # Verify no NaN values
    nan_count = df_paired.isnull().sum().sum()
    if nan_count > 0:
        print(f"\n⚠️  WARNING: {nan_count} NaN values found in output!")
    else:
        print(f"\n✓ No NaN values - all pairs complete")

    # Show subjects with all 3 modalities
    subjects_with_all = []
    for subject in df_paired['subject_id'].unique():
        subject_data = df_paired[df_paired['subject_id'] == subject]
        if len(subject_data) == 3:  # Has T1, T2, and SWI
            subjects_with_all.append(subject)

    print(f"\nSubjects with ALL 3 modalities: {len(subjects_with_all)}")

    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
