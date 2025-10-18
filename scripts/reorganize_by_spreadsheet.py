#!/usr/bin/env python3
"""
Reorganize sequence folders based on the spreadsheet SeriesInstanceUID mappings.
The spreadsheet is the source of truth for which sequence type each SeriesInstanceUID should be.
"""

import pandas as pd
import pydicom
import os
import shutil
from pathlib import Path
from collections import defaultdict

# Paths
csv_path = '/Users/paul/Downloads/sequence_folder_mapping - partial validatin.csv'
data_dir = Path('/Users/paul/Projects/STAGE_Study/data/raw/organized')

# Sequence types to check
sequence_types = ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']

def extract_series_uid(dicom_file):
    """Extract SeriesInstanceUID from a DICOM file"""
    try:
        dcm = pydicom.dcmread(dicom_file, stop_before_pixels=True)
        return dcm.SeriesInstanceUID if hasattr(dcm, 'SeriesInstanceUID') else None
    except Exception as e:
        print(f"Error reading {dicom_file}: {e}")
        return None

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
            series_number = int(parts[1].replace('#', '').replace(')', '').strip())

    return uid_suffix, series_number

def find_series_in_folders(subject_folder, target_uid_suffix, target_series_num):
    """
    Find which folder contains DICOM files with the given SeriesInstanceUID suffix
    Returns (folder_name, full_series_uid) or (None, None) if not found
    """
    if not subject_folder.exists():
        return None, None

    for seq_folder in subject_folder.iterdir():
        if seq_folder.is_dir() and seq_folder.name in sequence_types:
            # Check first DICOM file
            dicom_files = list(seq_folder.iterdir())
            if dicom_files:
                series_uid = extract_series_uid(dicom_files[0])
                if series_uid:
                    uid_suffix = series_uid[-8:].upper()
                    # Try to get series number too
                    try:
                        dcm = pydicom.dcmread(dicom_files[0], stop_before_pixels=True)
                        series_num = dcm.SeriesNumber if hasattr(dcm, 'SeriesNumber') else None
                    except:
                        series_num = None

                    # Match by UID suffix, or by series number if UID suffix is not available
                    if target_uid_suffix and uid_suffix == target_uid_suffix:
                        return seq_folder.name, series_uid
                    elif target_uid_suffix is None and target_series_num == series_num:
                        return seq_folder.name, series_uid

    return None, None

# Read CSV
print(f"Reading CSV from {csv_path}")
df = pd.read_csv(csv_path)

# Get validated subjects (those with 'x' in column I)
validated_mask = df['validated jm'] == 'x'
validated_subjects = df[df['validated jm'] == 'x']['rAccession'].tolist()

print(f"\nFound {len(validated_subjects)} validated subjects")
print("=" * 80)

# Track changes needed
reorganizations = []

# Process each validated subject
for subject_id in validated_subjects:
    print(f"\n\nAnalyzing {subject_id}...")
    subject_row = df[df['rAccession'] == subject_id].iloc[0]
    subject_folder = data_dir / subject_id

    if not subject_folder.exists():
        print(f"  WARNING: Subject folder not found: {subject_folder}")
        continue

    # For each sequence type in the spreadsheet
    for intended_seq_type in sequence_types:
        # Get what the spreadsheet says this sequence should be
        csv_value = subject_row[intended_seq_type]
        target_uid_suffix, target_series_num = parse_csv_value(csv_value)

        if target_uid_suffix is None and target_series_num is None:
            # Empty cell in spreadsheet - this sequence doesn't exist for this subject
            print(f"  {intended_seq_type}: Not specified in spreadsheet (empty)")
            continue

        # Find where this SeriesInstanceUID currently lives
        current_folder, full_series_uid = find_series_in_folders(
            subject_folder, target_uid_suffix, target_series_num
        )

        if current_folder is None:
            print(f"  {intended_seq_type}: WARNING - Could not find series {csv_value} in any folder!")
            continue

        if current_folder == intended_seq_type:
            print(f"  {intended_seq_type}: Already correct ✓")
        else:
            print(f"  {intended_seq_type}: NEEDS MOVE")
            print(f"    Currently in: {current_folder}")
            print(f"    Should be in: {intended_seq_type}")
            print(f"    Series: {csv_value}")

            reorganizations.append({
                'subject': subject_id,
                'series_uid': full_series_uid,
                'from_folder': current_folder,
                'to_folder': intended_seq_type,
                'series_info': csv_value
            })

# Summary
print("\n\n" + "=" * 80)
print(f"\nSUMMARY: Found {len(reorganizations)} sequences that need reorganization")
print("=" * 80)

if reorganizations:
    print("\nReorganizations needed:")
    for reorg in reorganizations:
        print(f"\n{reorg['subject']}:")
        print(f"  Series: {reorg['series_info']}")
        print(f"  Move: {reorg['from_folder']} → {reorg['to_folder']}")

    # Ask for confirmation before proceeding
    print("\n" + "=" * 80)
    print("Ready to reorganize sequences.")
    print("This will move DICOM files to match the spreadsheet designations.")
    print("=" * 80)

    response = input("\nProceed with reorganization? (yes/no): ")

    if response.lower() in ['yes', 'y']:
        print("\nProceeding with reorganization...\n")

        for reorg in reorganizations:
            subject_folder = data_dir / reorg['subject']
            from_path = subject_folder / reorg['from_folder']
            to_path = subject_folder / reorg['to_folder']

            print(f"{reorg['subject']}: Moving {reorg['from_folder']} → {reorg['to_folder']}...")

            try:
                # Check if destination already exists
                if to_path.exists():
                    # If destination exists, we need to handle this carefully
                    # Create a backup or merge strategy
                    backup_path = subject_folder / f"{reorg['to_folder']}_backup"
                    print(f"  WARNING: {reorg['to_folder']} already exists!")
                    print(f"  Moving existing {reorg['to_folder']} to {backup_path.name}")
                    shutil.move(str(to_path), str(backup_path))

                # Move the folder
                shutil.move(str(from_path), str(to_path))
                print(f"  ✓ Moved successfully")

            except Exception as e:
                print(f"  ✗ ERROR: {e}")

        print("\n" + "=" * 80)
        print("Reorganization complete!")
        print("=" * 80)
    else:
        print("\nReorganization cancelled. No changes made.")
else:
    print("\nNo reorganization needed - all sequences are correctly placed!")
