#!/usr/bin/env python3
"""
Merge recovered sequences with existing statistics and regenerate analysis
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

# File paths
BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
EXISTING_STATS = BASE_DIR / 'output' / 'statistics' / 'gm_wm_tissue_stats_20251017_025955.csv'
RECOVERED_STATS = BASE_DIR / 'output' / 'statistics' / 'gm_wm_tissue_stats_recovered_20251017_091038.csv'
MERGED_OUTPUT = BASE_DIR / 'output' / 'statistics' / 'gm_wm_tissue_stats_MERGED.csv'
PAIRED_OUTPUT = BASE_DIR / 'output' / 'statistics' / 'paired_comparisons_MERGED.csv'

print("=" * 100)
print("MERGING RECOVERED DATA WITH EXISTING STATISTICS")
print("=" * 100)

# Load data
print("\n1. Loading data...")
df_existing = pd.read_csv(EXISTING_STATS)
df_recovered = pd.read_csv(RECOVERED_STATS)

print(f"   Existing statistics: {len(df_existing)} sequences")
print(f"   Recovered statistics: {len(df_recovered)} sequences")

# Check for duplicates
print("\n2. Checking for duplicates...")
existing_keys = set(df_existing['subject_id'] + '_' + df_existing['sequence'])
recovered_keys = set(df_recovered['subject_id'] + '_' + df_recovered['sequence'])
duplicates = existing_keys & recovered_keys

if duplicates:
    print(f"   ⚠️  Found {len(duplicates)} duplicates:")
    for dup in sorted(duplicates):
        print(f"      - {dup}")
    print(f"   → Will use RECOVERED version (newer processing)")

    # Remove duplicates from existing data
    df_existing['key'] = df_existing['subject_id'] + '_' + df_existing['sequence']
    df_existing = df_existing[~df_existing['key'].isin(duplicates)]
    df_existing = df_existing.drop('key', axis=1)
else:
    print(f"   ✓ No duplicates found")

# Merge data
print("\n3. Merging data...")
df_merged = pd.concat([df_existing, df_recovered], ignore_index=True)
print(f"   Merged total: {len(df_merged)} sequences")

# Sort by subject and sequence
df_merged = df_merged.sort_values(['subject_id', 'sequence']).reset_index(drop=True)

# Save merged data
df_merged.to_csv(MERGED_OUTPUT, index=False)
print(f"   ✓ Saved to: {MERGED_OUTPUT}")

# Summary by sequence type
print("\n4. Summary by sequence type:")
for seq_type in ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']:
    count = len(df_merged[df_merged['sequence'] == seq_type])
    print(f"   {seq_type}: {count}")

# Create paired comparisons
print("\n5. Creating paired comparisons...")

paired_data = []

for subject_id in df_merged['subject_id'].unique():
    subject_data = df_merged[df_merged['subject_id'] == subject_id]

    # T1 pairs
    t1_conv = subject_data[subject_data['sequence'] == 'T1_conv']
    t1_stage = subject_data[subject_data['sequence'] == 'T1_STAGE']
    if not t1_conv.empty and not t1_stage.empty:
        paired_data.append({
            'subject_id': subject_id,
            'sequence_type': 'T1',
            'conv_gm_mean': t1_conv.iloc[0]['gm_mean'],
            'stage_gm_mean': t1_stage.iloc[0]['gm_mean'],
            'conv_wm_mean': t1_conv.iloc[0]['wm_mean'],
            'stage_wm_mean': t1_stage.iloc[0]['wm_mean'],
            'conv_gm_wm_ratio': t1_conv.iloc[0]['gm_wm_ratio'],
            'stage_gm_wm_ratio': t1_stage.iloc[0]['gm_wm_ratio'],
        })

    # T2 pairs
    t2_conv = subject_data[subject_data['sequence'] == 'T2_conv']
    t2_stage = subject_data[subject_data['sequence'] == 'T2_STAGE']
    if not t2_conv.empty and not t2_stage.empty:
        paired_data.append({
            'subject_id': subject_id,
            'sequence_type': 'T2',
            'conv_gm_mean': t2_conv.iloc[0]['gm_mean'],
            'stage_gm_mean': t2_stage.iloc[0]['gm_mean'],
            'conv_wm_mean': t2_conv.iloc[0]['wm_mean'],
            'stage_wm_mean': t2_stage.iloc[0]['wm_mean'],
            'conv_gm_wm_ratio': t2_conv.iloc[0]['gm_wm_ratio'],
            'stage_gm_wm_ratio': t2_stage.iloc[0]['gm_wm_ratio'],
        })

    # SWI pairs
    swi_conv = subject_data[subject_data['sequence'] == 'SWI_conv']
    swi_stage = subject_data[subject_data['sequence'] == 'SWI_STAGE']
    if not swi_conv.empty and not swi_stage.empty:
        paired_data.append({
            'subject_id': subject_id,
            'sequence_type': 'SWI',
            'conv_gm_mean': swi_conv.iloc[0]['gm_mean'],
            'stage_gm_mean': swi_stage.iloc[0]['gm_mean'],
            'conv_wm_mean': swi_conv.iloc[0]['wm_mean'],
            'stage_wm_mean': swi_stage.iloc[0]['wm_mean'],
            'conv_gm_wm_ratio': swi_conv.iloc[0]['gm_wm_ratio'],
            'stage_gm_wm_ratio': swi_stage.iloc[0]['gm_wm_ratio'],
        })

df_paired = pd.DataFrame(paired_data)
df_paired.to_csv(PAIRED_OUTPUT, index=False)
print(f"   ✓ Created {len(df_paired)} paired comparisons")
print(f"   ✓ Saved to: {PAIRED_OUTPUT}")

# Summary by sequence type
print("\n6. Paired comparisons by type:")
for seq_type in ['T1', 'T2', 'SWI']:
    count = len(df_paired[df_paired['sequence_type'] == seq_type])
    print(f"   {seq_type}: {count} pairs")

# Calculate improvements
print("\n7. Impact of recovery:")
print("   BEFORE recovery:")
print("   - T1 pairs: 33")
print("   - T2 pairs: 37")
print("   - SWI pairs: 38")
print("   - Total: 108 paired comparisons")
print()
print("   AFTER recovery:")
t1_pairs = len(df_paired[df_paired['sequence_type'] == 'T1'])
t2_pairs = len(df_paired[df_paired['sequence_type'] == 'T2'])
swi_pairs = len(df_paired[df_paired['sequence_type'] == 'SWI'])
total_pairs = len(df_paired)
print(f"   - T1 pairs: {t1_pairs} (+{t1_pairs - 33})")
print(f"   - T2 pairs: {t2_pairs} (+{t2_pairs - 37})")
print(f"   - SWI pairs: {swi_pairs} (+{swi_pairs - 38})")
print(f"   - Total: {total_pairs} paired comparisons (+{total_pairs - 108})")
print()
improvement = ((total_pairs - 108) / 108) * 100
print(f"   📊 Improvement: +{improvement:.1f}% increase in statistical power")

print("\n" + "=" * 100)
print("MERGE COMPLETE!")
print("=" * 100)
print(f"\nOutput files:")
print(f"  1. Merged statistics: {MERGED_OUTPUT}")
print(f"  2. Paired comparisons: {PAIRED_OUTPUT}")
