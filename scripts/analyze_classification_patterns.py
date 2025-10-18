#!/usr/bin/env python3
"""
Analyze DICOM classification patterns from ground truth data.
Identify which series numbers and metadata features best predict sequence types.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from collections import Counter

def main():
    print("=" * 80)
    print("DICOM CLASSIFICATION PATTERN ANALYSIS")
    print("=" * 80)

    # Load ground truth
    gt_file = Path('output/classifier_training/ground_truth_training_data.csv')
    df = pd.read_csv(gt_file)

    print(f"\nTotal sequences: {len(df)}")
    print(f"Unique subjects: {len(df['subject_id'].unique())}")
    print(f"Sequence types: {df['sequence_type'].unique()}")

    # Analyze each sequence type
    sequence_types = ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']

    for seq_type in sequence_types:
        print("\n" + "=" * 80)
        print(f"{seq_type}")
        print("=" * 80)

        df_seq = df[df['sequence_type'] == seq_type]
        n = len(df_seq)

        print(f"\nCount: {n} sequences")

        # Series numbers analysis
        print(f"\n--- SERIES NUMBERS ---")
        series_counts = df_seq['series_number'].value_counts()
        print(f"Unique series numbers: {len(series_counts)}")
        print(f"\nMost common series numbers:")
        for series_num, count in series_counts.head(10).items():
            pct = (count / n) * 100
            print(f"  {series_num:>12s}: {count:3d} ({pct:5.1f}%)")

        # Check if there's a dominant series number
        if len(series_counts) > 0:
            top_series = series_counts.iloc[0]
            top_pct = (top_series / n) * 100
            if top_pct > 50:
                print(f"\n  ⭐ Dominant series number: {series_counts.index[0]} ({top_pct:.1f}%)")

        # Metadata analysis
        print(f"\n--- KEY METADATA ---")

        # PixelBandwidth
        if 'PixelBandwidth' in df_seq.columns:
            pbw = df_seq['PixelBandwidth'].dropna()
            if len(pbw) > 0:
                print(f"PixelBandwidth: {pbw.mean():.1f} ± {pbw.std():.1f} Hz/pixel")
                print(f"  Range: [{pbw.min():.1f}, {pbw.max():.1f}]")
                print(f"  Median: {pbw.median():.1f}")

        # FlipAngle
        if 'FlipAngle' in df_seq.columns:
            fa = df_seq['FlipAngle'].dropna()
            if len(fa) > 0:
                print(f"FlipAngle: {fa.mean():.1f} ± {fa.std():.1f} degrees")
                print(f"  Range: [{fa.min():.1f}, {fa.max():.1f}]")
                print(f"  Unique values: {sorted(fa.unique())}")

        # Echo Time
        if 'EchoTime' in df_seq.columns:
            te = df_seq['EchoTime'].dropna()
            if len(te) > 0:
                print(f"EchoTime: {te.mean():.2f} ± {te.std():.2f} ms")
                print(f"  Range: [{te.min():.2f}, {te.max():.2f}]")

        # Repetition Time
        if 'RepetitionTime' in df_seq.columns:
            tr = df_seq['RepetitionTime'].dropna()
            if len(tr) > 0:
                print(f"RepetitionTime: {tr.mean():.1f} ± {tr.std():.1f} ms")
                print(f"  Range: [{tr.min():.1f}, {tr.max():.1f}]")

        # Protocol Names
        print(f"\n--- PROTOCOL NAMES ---")
        protocols = df_seq['ProtocolName'].value_counts()
        print(f"Unique protocol names: {len(protocols)}")
        for proto, count in protocols.head(5).items():
            pct = (count / n) * 100
            print(f"  {count:3d} ({pct:5.1f}%): {proto}")

        # Series Descriptions
        print(f"\n--- SERIES DESCRIPTIONS ---")
        descriptions = df_seq['SeriesDescription'].value_counts()
        print(f"Unique descriptions: {len(descriptions)}")
        for desc, count in descriptions.head(5).items():
            pct = (count / n) * 100
            print(f"  {count:3d} ({pct:5.1f}%): {desc}")

    # Cross-tabulation analysis
    print("\n" + "=" * 80)
    print("CROSS-TABULATION: SERIES NUMBERS BY SEQUENCE TYPE")
    print("=" * 80)

    # Create pivot table
    pivot = pd.crosstab(df['series_number'], df['sequence_type'])

    # Find series numbers that uniquely identify a sequence type
    print("\n--- UNIQUE SERIES NUMBER IDENTIFIERS ---")
    for series_num in pivot.index:
        row = pivot.loc[series_num]
        total = row.sum()
        max_count = row.max()
        max_type = row.idxmax()
        pct = (max_count / total) * 100

        if pct == 100 and total >= 3:  # Perfect identifier with at least 3 instances
            print(f"  {series_num:>12s} → {max_type:15s} ({total} instances, 100% accuracy)")

    # Find series numbers that are ambiguous
    print("\n--- AMBIGUOUS SERIES NUMBERS ---")
    for series_num in pivot.index:
        row = pivot.loc[series_num]
        non_zero = (row > 0).sum()
        if non_zero > 1:  # Used for multiple sequence types
            total = row.sum()
            print(f"  {series_num:>12s}: {total} total uses across {non_zero} sequence types")
            for seq_type in row[row > 0].index:
                count = row[seq_type]
                pct = (count / total) * 100
                print(f"    - {seq_type:15s}: {count:3d} ({pct:5.1f}%)")

    # Metadata-based classification rules
    print("\n" + "=" * 80)
    print("CLASSIFICATION RULES ANALYSIS")
    print("=" * 80)

    # Group by sequence type and calculate metadata ranges
    print("\n--- METADATA RANGES BY SEQUENCE TYPE ---")

    for seq_type in sequence_types:
        df_seq = df[df['sequence_type'] == seq_type]
        print(f"\n{seq_type}:")

        # PixelBandwidth range
        pbw = df_seq['PixelBandwidth'].dropna()
        if len(pbw) > 0:
            print(f"  PixelBandwidth: [{pbw.quantile(0.05):.0f}, {pbw.quantile(0.95):.0f}] (5-95%ile)")

        # FlipAngle range
        fa = df_seq['FlipAngle'].dropna()
        if len(fa) > 0:
            unique_fa = sorted(fa.unique())
            print(f"  FlipAngle: {unique_fa}")

        # EchoTime range
        te = df_seq['EchoTime'].dropna()
        if len(te) > 0:
            print(f"  EchoTime: [{te.quantile(0.05):.2f}, {te.quantile(0.95):.2f}] ms (5-95%ile)")

    # Calculate classification accuracy using simple rules
    print("\n" + "=" * 80)
    print("RULE-BASED CLASSIFICATION ACCURACY")
    print("=" * 80)

    def classify_by_series_number(series_num, series_counts_by_type):
        """Classify based on most common usage of series number"""
        max_count = 0
        best_type = None
        for seq_type, counts in series_counts_by_type.items():
            if series_num in counts and counts[series_num] > max_count:
                max_count = counts[series_num]
                best_type = seq_type
        return best_type

    # Build series number lookup
    series_counts_by_type = {}
    for seq_type in sequence_types:
        df_seq = df[df['sequence_type'] == seq_type]
        series_counts_by_type[seq_type] = df_seq['series_number'].value_counts().to_dict()

    # Test classification
    correct = 0
    total = len(df)

    for idx, row in df.iterrows():
        predicted = classify_by_series_number(row['series_number'], series_counts_by_type)
        if predicted == row['sequence_type']:
            correct += 1

    accuracy = (correct / total) * 100
    print(f"\nSeries number-based classification accuracy: {correct}/{total} = {accuracy:.1f}%")

    # Summary recommendations
    print("\n" + "=" * 80)
    print("SUMMARY RECOMMENDATIONS")
    print("=" * 80)

    print("\n1. SERIES NUMBER RELIABILITY:")
    print("   - Series numbers provide hints but are NOT universally reliable")
    print("   - Some series numbers (like '8040', '8165', '17') appear frequently")
    print("   - Different sites/scanners may use different numbering schemes")

    print("\n2. RECOMMENDED CLASSIFICATION STRATEGY:")
    print("   - PRIMARY: Use metadata (PixelBandwidth, FlipAngle, TE, TR)")
    print("   - SECONDARY: Use protocol/series description strings")
    print("   - TERTIARY: Use series number as weak prior/hint")

    print("\n3. KEY DISCRIMINATIVE FEATURES:")
    print("   - T1 vs T2: FlipAngle, EchoTime")
    print("   - Conv vs STAGE: ProtocolName, SeriesDescription, PixelBandwidth")
    print("   - SWI: Distinct TE range, specific protocol names")

    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
