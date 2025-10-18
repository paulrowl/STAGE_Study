#!/usr/bin/env python3
"""
Validate and correct sequence mappings in the CSV file by checking actual DICOM SeriesInstanceUIDs
"""

import pandas as pd
import pydicom
import os
from pathlib import Path

# Paths
csv_path = '/Users/paul/Downloads/sequence_folder_mapping - partial validatin.csv'
data_dir = Path('/Users/paul/Projects/STAGE_Study/data/raw/organized')

# Sequence types to check
sequence_types = ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']

def extract_series_uid_and_number(sequence_folder):
    """Extract SeriesInstanceUID and SeriesNumber from a DICOM file in the sequence folder"""
    if not sequence_folder.exists():
        return None, None

    # Get first DICOM file
    dicom_files = list(sequence_folder.iterdir())
    if not dicom_files:
        return None, None

    try:
        dcm = pydicom.dcmread(dicom_files[0], stop_before_pixels=True)
        series_uid = dcm.SeriesInstanceUID if hasattr(dcm, 'SeriesInstanceUID') else None
        series_number = dcm.SeriesNumber if hasattr(dcm, 'SeriesNumber') else None
        return series_uid, series_number
    except Exception as e:
        print(f"Error reading {dicom_files[0]}: {e}")
        return None, None

def format_cell_value(series_uid, series_number):
    """Format the cell value as it appears in the CSV"""
    if series_uid is None:
        return ""

    # Get last 8 characters of UID
    uid_suffix = series_uid[-8:].upper() if len(series_uid) >= 8 else series_uid.upper()

    if series_number is not None:
        return f"{uid_suffix} (#{series_number})"
    else:
        return f"({series_number})"

def parse_csv_value(cell_value):
    """Parse the CSV cell value to extract UID suffix and series number"""
    if pd.isna(cell_value) or cell_value.strip() == "":
        return None, None

    cell_value = str(cell_value).strip()

    # Extract UID suffix (8 hex chars before the parenthesis)
    uid_suffix = None
    series_number = None

    # Pattern: "100087C9 (#17)" or "(#17)"
    if '(' in cell_value:
        parts = cell_value.split('(')
        if len(parts[0].strip()) > 0:
            uid_suffix = parts[0].strip().upper()
        if '#' in parts[1]:
            series_number = parts[1].replace('#', '').replace(')', '').strip()

    return uid_suffix, series_number

# Read CSV
print(f"Reading CSV from {csv_path}")
df = pd.read_csv(csv_path)

# Get validated subjects (those with 'x' in column I)
validated_mask = df['validated jm'] == 'x'
validated_subjects = df[validated_mask]['rAccession'].tolist()

print(f"\nFound {len(validated_subjects)} validated subjects")
print("=" * 80)

# Track changes
changes = []

# Process each validated subject
for subject_id in validated_subjects:
    print(f"\n\nProcessing {subject_id}...")
    subject_row_idx = df[df['rAccession'] == subject_id].index[0]
    subject_folder = data_dir / subject_id

    if not subject_folder.exists():
        print(f"  WARNING: Subject folder not found: {subject_folder}")
        continue

    # Check each sequence type
    for seq_type in sequence_types:
        seq_folder = subject_folder / seq_type

        # Get actual SeriesInstanceUID from DICOM
        actual_uid, actual_series_num = extract_series_uid_and_number(seq_folder)

        # Get current CSV value
        csv_value = df.loc[subject_row_idx, seq_type]
        csv_uid_suffix, csv_series_num = parse_csv_value(csv_value)

        # Compare
        actual_uid_suffix = actual_uid[-8:].upper() if actual_uid else None

        if actual_uid_suffix is None and csv_uid_suffix is None:
            print(f"  {seq_type}: Both empty ✓")
        elif actual_uid_suffix != csv_uid_suffix:
            print(f"  {seq_type}: MISMATCH!")
            print(f"    CSV:    {csv_value}")
            print(f"    Actual: {format_cell_value(actual_uid, actual_series_num)}")

            # Update the dataframe
            new_value = format_cell_value(actual_uid, actual_series_num)
            df.loc[subject_row_idx, seq_type] = new_value
            changes.append({
                'subject': subject_id,
                'sequence': seq_type,
                'old': csv_value,
                'new': new_value
            })
        else:
            # Check if series number also matches
            if str(csv_series_num) != str(actual_series_num):
                print(f"  {seq_type}: UID matches, but series number differs")
                print(f"    CSV:    {csv_value}")
                print(f"    Actual: {format_cell_value(actual_uid, actual_series_num)}")

                # Update the dataframe
                new_value = format_cell_value(actual_uid, actual_series_num)
                df.loc[subject_row_idx, seq_type] = new_value
                changes.append({
                    'subject': subject_id,
                    'sequence': seq_type,
                    'old': csv_value,
                    'new': new_value
                })
            else:
                print(f"  {seq_type}: Matches ✓")

# Summary
print("\n\n" + "=" * 80)
print(f"\nSUMMARY: Found {len(changes)} differences")
print("=" * 80)

if changes:
    print("\nChanges to be made:")
    for change in changes:
        print(f"\n{change['subject']} - {change['sequence']}:")
        print(f"  Old: {change['old']}")
        print(f"  New: {change['new']}")

    # Save updated CSV
    output_path = csv_path.replace('.csv', '_corrected.csv')
    df.to_csv(output_path, index=False)
    print(f"\n\nCorrected CSV saved to: {output_path}")
    print(f"\nOriginal CSV unchanged at: {csv_path}")
else:
    print("\nNo changes needed - all validated subjects match!")
