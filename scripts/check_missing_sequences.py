#!/usr/bin/env python3
"""
Check for missing sequences across all patients
Generates a simple table showing which sequences each patient is missing
"""

import pandas as pd
from pathlib import Path

def check_patient_sequences(organized_dir):
    """Check which sequences are present/missing for each patient"""

    organized_dir = Path(organized_dir)

    # Expected sequence folders
    expected_sequences = [
        'T1_conv',
        'T1_STAGE',
        'T2_conv',
        'T2_STAGE',
        'SWI_conv',
        'SWI_STAGE'
    ]

    results = []

    # Get all patient folders
    patient_folders = sorted([d for d in organized_dir.iterdir()
                             if d.is_dir() and d.name.startswith('Anon')])

    print(f"Checking {len(patient_folders)} patients...")

    for patient_dir in patient_folders:
        patient_id = patient_dir.name

        # Check which sequences exist
        present = []
        missing = []

        for seq in expected_sequences:
            seq_path = patient_dir / seq
            if seq_path.exists() and seq_path.is_dir():
                # Check if folder has files
                files = list(seq_path.glob('*'))
                if files:
                    present.append(seq)
                else:
                    missing.append(seq)
            else:
                missing.append(seq)

        # Only record if patient has any missing sequences
        if missing:
            results.append({
                'Patient': patient_id,
                'Missing_Sequences': ', '.join(missing),
                'Present_Sequences': ', '.join(present),
                'Missing_Count': len(missing),
                'Present_Count': len(present)
            })

    return pd.DataFrame(results)

def create_summary_table(df):
    """Create a summary of missing sequence patterns"""

    print("\n" + "="*80)
    print("MISSING SEQUENCES SUMMARY")
    print("="*80)

    # Overall statistics
    total_patients = len(df)

    print(f"\nTotal patients with missing sequences: {total_patients}")

    # Count missing by sequence type
    print("\n" + "-"*80)
    print("Missing Sequence Counts:")
    print("-"*80)

    sequence_types = ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']

    for seq in sequence_types:
        count = df['Missing_Sequences'].str.contains(seq).sum()
        if count > 0:
            print(f"  {seq:12s}: {count:3d} patients")

    # Group by missing pattern
    print("\n" + "-"*80)
    print("Common Missing Patterns:")
    print("-"*80)

    pattern_counts = df['Missing_Sequences'].value_counts().head(10)
    for pattern, count in pattern_counts.items():
        print(f"  {count:3d} patients missing: {pattern}")

def main():
    organized_dir = Path('data/raw/organized')
    output_dir = Path('output/statistics')

    print("="*80)
    print("CHECKING FOR MISSING SEQUENCES")
    print("="*80)

    # Check all patients
    df = check_patient_sequences(organized_dir)

    # Create summary
    create_summary_table(df)

    # Save detailed table
    output_file = output_dir / 'patients_with_missing_sequences.csv'
    df.to_csv(output_file, index=False)

    print(f"\n" + "="*80)
    print(f"Detailed table saved to: {output_file}")
    print("="*80)

    # Also create a simple view
    simple_df = df[['Patient', 'Missing_Sequences']].copy()
    simple_file = output_dir / 'missing_sequences_simple.csv'
    simple_df.to_csv(simple_file, index=False)

    print(f"Simple table saved to: {simple_file}")

    # Print first 20 rows for preview
    if len(df) > 0:
        print("\n" + "="*80)
        print("FIRST 20 PATIENTS WITH MISSING SEQUENCES:")
        print("="*80)
        print(df[['Patient', 'Missing_Sequences', 'Missing_Count']].head(20).to_string(index=False))

if __name__ == '__main__':
    main()
