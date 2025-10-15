#!/usr/bin/env python3
"""
Combine all patient metrics into a single CSV file
"""

import pandas as pd
from pathlib import Path
import sys

def combine_metrics():
    """Combine all patient metric CSV files"""

    metrics_dir = Path('output/metrics')

    # Find all metric CSV files
    metric_files = []
    for patient_dir in metrics_dir.iterdir():
        if patient_dir.is_dir():
            for csv_file in patient_dir.glob('*_metrics.csv'):
                metric_files.append(csv_file)

    if not metric_files:
        print("ERROR: No metric files found!")
        sys.exit(1)

    print(f"Found {len(metric_files)} metric files from {len(list(metrics_dir.iterdir()))} patients")

    # Load and combine all metrics
    all_metrics = []
    for csv_file in sorted(metric_files):
        try:
            df = pd.read_csv(csv_file)
            all_metrics.append(df)
        except Exception as e:
            print(f"Warning: Could not read {csv_file}: {e}")

    # Combine into single dataframe
    combined_df = pd.concat(all_metrics, ignore_index=True)

    # Save combined metrics
    output_file = Path('output/statistics/all_patients_metrics.csv')
    output_file.parent.mkdir(parents=True, exist_ok=True)
    combined_df.to_csv(output_file, index=False)

    print(f"\n✓ Combined metrics saved to: {output_file}")
    print(f"  Total comparisons: {len(combined_df)}")
    print(f"  Total patients: {combined_df['patient_id'].nunique()}")

    # Show breakdown by sequence type
    if 'comparison' in combined_df.columns:
        sequence_types = combined_df['comparison'].str.extract(r'_(T1|T2|SWI)_')[0]
        print(f"\n  Sequence breakdown:")
        print(f"    T1: {(sequence_types == 'T1').sum()} comparisons")
        print(f"    T2: {(sequence_types == 'T2').sum()} comparisons")
        print(f"    SWI: {(sequence_types == 'SWI').sum()} comparisons")

    return output_file

if __name__ == '__main__':
    combine_metrics()
