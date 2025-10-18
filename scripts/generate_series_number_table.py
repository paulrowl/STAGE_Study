#!/usr/bin/env python3
"""
Generate table showing series numbers for each sequence (PACS thumbnail order)
"""

import pandas as pd
from pathlib import Path
import pydicom

def get_series_number(patient_id, sequence_type):
    """
    Get the DICOM SeriesNumber for a given patient and sequence type
    Returns the series number (e.g., '5') or None if not found
    """
    # Check if organized folder exists
    organized_path = Path(f'data/raw/organized/{patient_id}/{sequence_type}')
    if not organized_path.exists():
        return None
    
    # Get a sample DICOM file from the organized folder
    dicom_files = list(organized_path.iterdir())
    if not dicom_files:
        return None
    
    # Read the first DICOM file
    try:
        sample_file = dicom_files[0]
        ds = pydicom.dcmread(sample_file, stop_before_pixels=True)
        series_number = getattr(ds, 'SeriesNumber', None)
        return int(series_number) if series_number is not None else None
    except Exception as e:
        print(f"Error reading {sample_file}: {e}")
        return None

def main():
    print("Generating series number table (PACS thumbnail order)...")
    print("=" * 80)
    
    # Get all patients from organized directory
    organized_dir = Path('data/raw/organized')
    if not organized_dir.exists():
        print("Error: Organized directory not found!")
        return
    
    patients = sorted([d.name for d in organized_dir.iterdir() if d.is_dir()])
    
    print(f"Found {len(patients)} patients")
    
    # Sequence types to check
    sequence_types = ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']
    
    results = []
    
    for i, patient_id in enumerate(patients, 1):
        print(f"Processing {patient_id} ({i}/{len(patients)})...")
        
        row = {'rAccession': patient_id}
        
        for seq_type in sequence_types:
            series_num = get_series_number(patient_id, seq_type)
            row[seq_type] = series_num if series_num is not None else ''
        
        results.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Reorder columns
    columns = ['rAccession', 'T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']
    df = df[columns]
    
    # Save to CSV
    output_file = 'output/statistics/series_number_mapping.csv'
    df.to_csv(output_file, index=False)
    
    print("\n" + "=" * 80)
    print(f"Saved to: {output_file}")
    print("=" * 80)
    
    # Print summary
    print("\nSummary:")
    for col in columns[1:]:
        found = df[col].astype(bool).sum()
        print(f"  {col}: {found}/{len(patients)} patients")
    
    # Show first few rows
    print("\nFirst 10 rows:")
    print(df.head(10).to_string(index=False))
    
    # Show some statistics about series numbers
    print("\n" + "=" * 80)
    print("Series Number Statistics (for ordering in PACS):")
    print("=" * 80)
    for col in columns[1:]:
        series_nums = df[col][df[col] != ''].astype(int)
        if len(series_nums) > 0:
            print(f"\n{col}:")
            print(f"  Range: {series_nums.min()} - {series_nums.max()}")
            print(f"  Mean: {series_nums.mean():.1f}")
            print(f"  Most common: {series_nums.mode().values[0] if len(series_nums.mode()) > 0 else 'N/A'}")

if __name__ == '__main__':
    main()
