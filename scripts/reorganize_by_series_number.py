#!/usr/bin/env python3
"""
Reorganize sequence folders based on series numbers from the spreadsheet.
Since the SeriesInstanceUIDs in the spreadsheet are incorrect, we'll use series numbers
to identify which sequence is which, then reorganize based on the spreadsheet's designation.
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

def extract_series_info(dicom_file):
    """Extract SeriesInstanceUID and SeriesNumber from a DICOM file"""
    try:
        dcm = pydicom.dcmread(dicom_file, stop_before_pixels=True)
        series_uid = dcm.SeriesInstanceUID if hasattr(dcm, 'SeriesInstanceUID') else None
        series_num = dcm.SeriesNumber if hasattr(dcm, 'SeriesNumber') else None
        return series_uid, series_num
    except Exception as e:
        print(f"Error reading {dicom_file}: {e}")
        return None, None

def parse_csv_value(cell_value):
    """Parse the CSV cell value to extract series number"""
    if pd.isna(cell_value) or str(cell_value).strip() == "":
        return None

    cell_value = str(cell_value).strip()

    # Extract series number from patterns like "100087C9 (#17)" or "(#17)"
    if '#' in cell_value:
        try:
            series_num_str = cell_value.split('#')[1].split(')')[0].strip()
            return int(series_num_str)
        except:
            pass

    return None

def get_current_folder_mapping(subject_folder):
    """
    Build a mapping of series_number -> folder_name for all sequences in the subject folder
    Returns: {series_number: (folder_name, series_uid)}
    """
    mapping = {}

    if not subject_folder.exists():
        return mapping

    for seq_folder in subject_folder.iterdir():
        if seq_folder.is_dir() and seq_folder.name in sequence_types:
            # Check first DICOM file
            dicom_files = list(seq_folder.iterdir())
            if dicom_files:
                series_uid, series_num = extract_series_info(dicom_files[0])
                if series_num is not None:
                    mapping[series_num] = (seq_folder.name, series_uid)

    return mapping

# Read CSV
print(f"Reading CSV from {csv_path}")
df = pd.read_csv(csv_path)

# Get validated subjects
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

    # Get current mapping of series numbers to folders
    current_mapping = get_current_folder_mapping(subject_folder)

    if not current_mapping:
        print(f"  WARNING: No DICOM sequences found in {subject_folder}")
        continue

    print(f"  Current sequences by series number:")
    for snum, (folder, uid) in sorted(current_mapping.items()):
        print(f"    #{snum}: {folder} ({uid[-8:] if uid else 'N/A'})")

    # For each sequence type in the spreadsheet
    for intended_seq_type in sequence_types:
        # Get what series number the spreadsheet says should be this type
        csv_value = subject_row[intended_seq_type]
        target_series_num = parse_csv_value(csv_value)

        if target_series_num is None:
            # Empty cell in spreadsheet - this sequence doesn't exist for this subject
            continue

        # Find where this series number currently lives
        if target_series_num not in current_mapping:
            print(f"  {intended_seq_type}: WARNING - Series #{target_series_num} not found in any folder!")
            continue

        current_folder, series_uid = current_mapping[target_series_num]

        if current_folder == intended_seq_type:
            print(f"  {intended_seq_type} (#{target_series_num}): Already correct ✓")
        else:
            print(f"  {intended_seq_type} (#{target_series_num}): NEEDS MOVE")
            print(f"    Currently in: {current_folder}")
            print(f"    Should be in: {intended_seq_type}")

            reorganizations.append({
                'subject': subject_id,
                'series_num': target_series_num,
                'series_uid': series_uid,
                'from_folder': current_folder,
                'to_folder': intended_seq_type,
                'csv_value': csv_value
            })

# Summary
print("\n\n" + "=" * 80)
print(f"\nSUMMARY: Found {len(reorganizations)} sequences that need reorganization")
print("=" * 80)

if reorganizations:
    print("\nReorganizations needed:")
    for reorg in reorganizations:
        print(f"\n{reorg['subject']} - Series #{reorg['series_num']}:")
        print(f"  Move: {reorg['from_folder']} → {reorg['to_folder']}")
        print(f"  UID: {reorg['series_uid'][-16:] if reorg['series_uid'] else 'N/A'}")

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

            print(f"{reorg['subject']}: Moving series #{reorg['series_num']} from {reorg['from_folder']} → {reorg['to_folder']}...")

            try:
                # Check if destination already exists
                if to_path.exists():
                    # If destination exists, we need to handle this carefully
                    backup_path = subject_folder / f"{reorg['to_folder']}_OLD"
                    print(f"  WARNING: {reorg['to_folder']} already exists!")
                    print(f"  Moving existing {reorg['to_folder']} to {backup_path.name}")
                    if backup_path.exists():
                        shutil.rmtree(backup_path)
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
