#!/usr/bin/env python3
"""
Create summary of merged data
"""

import pandas as pd
from pathlib import Path

# File paths
BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
MERGED_STATS = BASE_DIR / 'output' / 'statistics' / 'gm_wm_tissue_stats_MERGED.csv'
PAIRED_DATA = BASE_DIR / 'output' / 'statistics' / 'paired_comparisons_MERGED.csv'

print("=" * 100)
print("MERGED DATA SUMMARY")
print("=" * 100)

# Load data
df_merged = pd.read_csv(MERGED_STATS)
df_paired = pd.read_csv(PAIRED_DATA)

print(f"\nTotal sequences: {len(df_merged)}")
print(f"Total paired comparisons: {len(df_paired)}")

# Count by sequence type
print("\nSequences by type:")
for seq_type in ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']:
    count = len(df_merged[df_merged['sequence'] == seq_type])
    print(f"  {seq_type}: {count}")

# Count subjects with each pair
print("\nPaired comparisons:")
for seq_type in ['T1', 'T2', 'SWI']:
    count = len(df_paired[df_paired['sequence_type'] == seq_type])
    subjects = df_paired[df_paired['sequence_type'] == seq_type]['subject_id'].tolist()
    print(f"  {seq_type}: {count} pairs")
    print(f"    Subjects: {', '.join(sorted(subjects))}")

#Check missing pairs
print("\nAnalyzing missing T2 pairs...")
all_subjects = df_merged['subject_id'].unique()
t2_paired_subjects = set(df_paired[df_paired['sequence_type'] == 'T2']['subject_id'])

print(f"Total subjects: {len(all_subjects)}")
print(f"Subjects with T2 pairs: {len(t2_paired_subjects)}")

# Find subjects with T2_conv but no T2_STAGE
for subject in sorted(all_subjects):
    subject_data = df_merged[df_merged['subject_id'] == subject]
    has_t2_conv = len(subject_data[subject_data['sequence'] == 'T2_conv']) > 0
    has_t2_stage = len(subject_data[subject_data['sequence'] == 'T2_STAGE']) > 0

    if has_t2_conv and not has_t2_stage:
        print(f"  {subject}: Has T2_conv but MISSING T2_STAGE")
    elif has_t2_stage and not has_t2_conv:
        print(f"  {subject}: Has T2_STAGE but MISSING T2_conv")

print("\n" + "=" * 100)
