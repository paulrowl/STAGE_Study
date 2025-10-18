#!/usr/bin/env python3
"""
Fix gm_wm_tissue_stats_MERGED.csv by consolidating duplicate columns.
Data is split between capitalized (GM_mean) and lowercase (gm_mean) columns.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

MERGED_STATS_FILE = Path('output/statistics/gm_wm_tissue_stats_MERGED.csv')

def main():
    print("=" * 80)
    print("FIXING MERGED STATISTICS FILE - CONSOLIDATING COLUMNS")
    print("=" * 80)

    # Backup existing file
    backup_name = f"gm_wm_tissue_stats_MERGED_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    backup_path = MERGED_STATS_FILE.parent / backup_name
    MERGED_STATS_FILE.rename(backup_path)
    print(f"\n✓ Backed up existing file to: {backup_name}")

    # Load data
    print(f"\nLoading data from backup: {backup_path}")
    df = pd.read_csv(backup_path)

    print(f"  Total rows: {len(df)}")
    print(f"  Rows with NaN in GM_mean (uppercase): {df['GM_mean'].isna().sum()}")
    print(f"  Rows with NaN in gm_mean (lowercase): {df['gm_mean'].isna().sum()}")

    # Consolidate columns: use lowercase as primary, fill from uppercase where needed
    print("\nConsolidating columns...")

    # For each lowercase column, fill NaN values from corresponding uppercase column
    column_pairs = [
        ('gm_mean', 'GM_mean'),
        ('gm_std', 'GM_std'),
        ('wm_mean', 'WM_mean'),
        ('wm_std', 'WM_std'),
        ('gm_wm_ratio', 'GM_WM_ratio'),
        ('gm_voxel_count', 'GM_voxels'),
        ('wm_voxel_count', 'WM_voxels'),
    ]

    for lowercase_col, uppercase_col in column_pairs:
        # Fill NaN values in lowercase column with values from uppercase column
        mask = df[lowercase_col].isna() & ~df[uppercase_col].isna()
        df.loc[mask, lowercase_col] = df.loc[mask, uppercase_col]
        filled_count = mask.sum()
        print(f"  {lowercase_col:20s} filled {filled_count:3d} values from {uppercase_col}")

    # Drop the uppercase columns
    uppercase_cols = [pair[1] for pair in column_pairs]
    df = df.drop(columns=uppercase_cols)

    print(f"\n✓ Dropped {len(uppercase_cols)} uppercase columns")

    # Verify no NaN values remain
    print("\nVerifying data integrity...")
    nan_count = df[['gm_mean', 'wm_mean', 'gm_wm_ratio']].isna().sum().sum()

    if nan_count > 0:
        print(f"  ⚠️  WARNING: {nan_count} NaN values still remain!")
        # Show which subjects still have NaN
        subjects_with_nan = df[df['gm_mean'].isna()]['subject_id'].unique()
        print(f"  Subjects with NaN: {sorted(subjects_with_nan)}")
    else:
        print(f"  ✓ No NaN values - all data complete!")

    # Save fixed file
    df.to_csv(MERGED_STATS_FILE, index=False)
    print(f"\n✓ Saved fixed file to: {MERGED_STATS_FILE}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total sequences: {len(df)}")
    print(f"Complete sequences: {(~df['gm_mean'].isna()).sum()}")
    print(f"Subjects: {len(df['subject_id'].unique())}")

    # Show sample data
    print("\nSample data (first 5 rows):")
    print(df[['subject_id', 'sequence', 'gm_mean', 'wm_mean', 'gm_wm_ratio']].head())

    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
