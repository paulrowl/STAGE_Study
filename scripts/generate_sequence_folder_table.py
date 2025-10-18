#!/usr/bin/env python3
"""
Generate table mapping patients to their original raw sequence folder names
"""

import pandas as pd
from pathlib import Path
import pydicom

def find_original_folder(patient_id, sequence_type):
    """
    Find the original raw folder name for a given patient and sequence type
    Returns the folder name (e.g., '10008A97') or None if not found
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
        series_number = str(getattr(ds, 'SeriesNumber', ''))
        series_desc = str(getattr(ds, 'SeriesDescription', ''))
    except:
        return None
    
    # Now search for this series in the raw data
    raw_base = Path(f'data/raw/{patient_id}')
    if not raw_base.exists():
        return None
    
    # Navigate through the nested structure
    for level1 in raw_base.iterdir():
        if not level1.is_dir() or not level1.name.startswith('100'):
            continue
        
        for level2 in level1.iterdir():
            if not level2.is_dir() or not level2.name.startswith('100'):
                continue
            
            for seq_folder in level2.iterdir():
                if not seq_folder.is_dir():
                    continue
                
                # Check if this folder matches by reading a DICOM file
                try:
                    test_files = list(seq_folder.iterdir())[:1]
                    if not test_files:
                        continue
                    
                    test_ds = pydicom.dcmread(test_files[0], stop_before_pixels=True)
                    test_series_num = str(getattr(test_ds, 'SeriesNumber', ''))
                    test_series_desc = str(getattr(test_ds, 'SeriesDescription', ''))
                    
                    # Match by series number and description
                    if test_series_num == series_number and test_series_desc == series_desc:
                        return seq_folder.name
                except:
                    continue
    
    return None

def main():
    print("Generating sequence folder mapping table...")
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
            folder_name = find_original_folder(patient_id, seq_type)
            row[seq_type] = folder_name if folder_name else ''
        
        results.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Reorder columns
    columns = ['rAccession', 'T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']
    df = df[columns]
    
    # Save to CSV
    output_file = 'output/statistics/sequence_folder_mapping.csv'
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
    print("\nFirst 5 rows:")
    print(df.head().to_string(index=False))

if __name__ == '__main__':
    main()
