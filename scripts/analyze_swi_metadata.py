#!/usr/bin/env python3
"""
Analyze DICOM metadata across all patients to identify SWI sequences.
Focus on finding both conventional SWI and STAGE SWI sequences.
"""

import os
import sys
import pydicom
import pandas as pd
from pathlib import Path
from collections import defaultdict

def get_orientation_label(image_orientation):
    """Determine if image is axial, sagittal, or coronal."""
    if image_orientation is None or len(image_orientation) < 6:
        return "unknown"

    # Image Orientation Patient has 6 values: [row_x, row_y, row_z, col_x, col_y, col_z]
    row = image_orientation[:3]
    col = image_orientation[3:6]

    # Cross product gives slice normal direction
    normal = [
        row[1]*col[2] - row[2]*col[1],
        row[2]*col[0] - row[0]*col[2],
        row[0]*col[1] - row[1]*col[0]
    ]

    # Determine primary direction
    abs_normal = [abs(x) for x in normal]
    max_idx = abs_normal.index(max(abs_normal))

    if max_idx == 2:  # Z direction - axial/transverse
        return "axial"
    elif max_idx == 0:  # X direction - sagittal
        return "sagittal"
    elif max_idx == 1:  # Y direction - coronal
        return "coronal"
    else:
        return "unknown"

def extract_dicom_metadata(dcm_file):
    """Extract relevant DICOM metadata for sequence identification."""
    try:
        dcm = pydicom.dcmread(dcm_file, force=True)

        metadata = {
            'SeriesDescription': getattr(dcm, 'SeriesDescription', ''),
            'SequenceName': getattr(dcm, 'SequenceName', ''),
            'ProtocolName': getattr(dcm, 'ProtocolName', ''),
            'SeriesNumber': getattr(dcm, 'SeriesNumber', ''),
            'ImageType': str(getattr(dcm, 'ImageType', '')),
            'ScanningSequence': getattr(dcm, 'ScanningSequence', ''),
            'SequenceVariant': getattr(dcm, 'SequenceVariant', ''),
            'ScanOptions': getattr(dcm, 'ScanOptions', ''),
            'MRAcquisitionType': getattr(dcm, 'MRAcquisitionType', ''),
            'EchoTime': getattr(dcm, 'EchoTime', None),
            'RepetitionTime': getattr(dcm, 'RepetitionTime', None),
            'FlipAngle': getattr(dcm, 'FlipAngle', None),
            'PixelBandwidth': getattr(dcm, 'PixelBandwidth', None),
            'EchoNumber': getattr(dcm, 'EchoNumber', None),
            'ImageOrientationPatient': getattr(dcm, 'ImageOrientationPatient', None),
            'SliceThickness': getattr(dcm, 'SliceThickness', None),
            'Rows': getattr(dcm, 'Rows', None),
            'Columns': getattr(dcm, 'Columns', None),
        }

        # Determine orientation
        metadata['Orientation'] = get_orientation_label(metadata['ImageOrientationPatient'])

        return metadata

    except Exception as e:
        print(f"Error reading {dcm_file}: {e}")
        return None

def analyze_patient_folder(patient_folder):
    """Analyze all DICOM series in a patient folder."""
    patient_id = os.path.basename(patient_folder)
    print(f"\n{'='*80}")
    print(f"Analyzing Patient: {patient_id}")
    print(f"{'='*80}")

    series_metadata = defaultdict(list)

    # Walk through patient folder
    for root, dirs, files in os.walk(patient_folder):
        # Look for DICOM files
        dcm_files = [f for f in files if not f.startswith('.')]

        if not dcm_files:
            continue

        # Get metadata from first DICOM file in this series
        first_dcm = os.path.join(root, dcm_files[0])
        metadata = extract_dicom_metadata(first_dcm)

        if metadata:
            metadata['num_files'] = len(dcm_files)
            metadata['folder_path'] = root

            # Use SeriesNumber as key (convert to string for consistency)
            series_key = str(metadata['SeriesNumber']) if metadata['SeriesNumber'] else 'unknown'
            series_metadata[series_key].append(metadata)

    return patient_id, series_metadata

def analyze_all_patients(raw_data_dir):
    """Analyze all patients in raw data directory."""

    all_data = []

    # Find all patient folders
    patient_folders = []
    for item in os.listdir(raw_data_dir):
        item_path = os.path.join(raw_data_dir, item)
        if os.path.isdir(item_path) and not item.startswith('.'):
            patient_folders.append(item_path)

    patient_folders.sort()

    print(f"Found {len(patient_folders)} patient folders")

    for patient_folder in patient_folders:
        patient_id, series_metadata = analyze_patient_folder(patient_folder)

        # Display series information
        for series_num in sorted(series_metadata.keys()):
            series_list = series_metadata[series_num]

            for series in series_list:
                # Print series info
                print(f"\nSeries {series_num}:")
                print(f"  Description: {series['SeriesDescription']}")
                print(f"  Protocol: {series['ProtocolName']}")
                print(f"  Sequence: {series['SequenceName']}")
                print(f"  Orientation: {series['Orientation']}")
                print(f"  Files: {series['num_files']}")
                print(f"  TE: {series['EchoTime']} ms")
                print(f"  TR: {series['RepetitionTime']} ms")
                print(f"  Flip Angle: {series['FlipAngle']}°")
                print(f"  Pixel Bandwidth: {series['PixelBandwidth']}")
                print(f"  Echo Number: {series['EchoNumber']}")
                print(f"  Image Type: {series['ImageType']}")
                print(f"  Scanning Sequence: {series['ScanningSequence']}")
                print(f"  Sequence Variant: {series['SequenceVariant']}")
                print(f"  Matrix: {series['Rows']}x{series['Columns']}")

                # Add to master list
                series_copy = series.copy()
                series_copy['patient_id'] = patient_id
                all_data.append(series_copy)

    # Create DataFrame
    df = pd.DataFrame(all_data)

    # Save to CSV
    output_file = 'dicom_metadata_analysis.csv'
    df.to_csv(output_file, index=False)
    print(f"\n{'='*80}")
    print(f"Saved metadata to {output_file}")
    print(f"{'='*80}")

    # Analyze potential SWI sequences
    print("\n" + "="*80)
    print("POTENTIAL SWI SEQUENCES (axial only):")
    print("="*80)

    # Filter for axial sequences
    axial_df = df[df['Orientation'] == 'axial']

    # Look for SWI patterns
    swi_keywords = ['swi', 'susceptibility', 'venous', 'swan', 'bold']

    potential_swi = axial_df[
        axial_df['SeriesDescription'].str.lower().str.contains('|'.join(swi_keywords), na=False) |
        axial_df['ProtocolName'].str.lower().str.contains('|'.join(swi_keywords), na=False)
    ]

    if len(potential_swi) > 0:
        print("\nFound sequences with SWI-related keywords:")
        for idx, row in potential_swi.iterrows():
            print(f"\n{row['patient_id']} - Series {row['SeriesNumber']}:")
            print(f"  Description: {row['SeriesDescription']}")
            print(f"  Protocol: {row['ProtocolName']}")
            print(f"  TE: {row['EchoTime']} ms, TR: {row['RepetitionTime']} ms")
            print(f"  Files: {row['num_files']}")

    # Also look for long TE gradient echo sequences (typical of SWI)
    print("\n" + "="*80)
    print("LONG TE GRADIENT ECHO SEQUENCES (potential SWI):")
    print("="*80)

    # SWI typically uses long TE (>20ms) gradient echo
    long_te = axial_df[
        (axial_df['EchoTime'] > 20) &
        (axial_df['ScanningSequence'].str.contains('GR', na=False))
    ].sort_values(['patient_id', 'EchoTime'], ascending=[True, False])

    if len(long_te) > 0:
        for idx, row in long_te.iterrows():
            print(f"\n{row['patient_id']} - Series {row['SeriesNumber']}:")
            print(f"  Description: {row['SeriesDescription']}")
            print(f"  TE: {row['EchoTime']} ms, TR: {row['RepetitionTime']} ms")
            print(f"  Flip Angle: {row['FlipAngle']}°")
            print(f"  Scanning Sequence: {row['ScanningSequence']}")
            print(f"  Sequence Variant: {row['SequenceVariant']}")
            print(f"  Files: {row['num_files']}")

    # Look for STAGE sequences
    print("\n" + "="*80)
    print("STAGE SEQUENCES:")
    print("="*80)

    stage_seqs = axial_df[
        axial_df['SeriesDescription'].str.contains('STAGE', case=False, na=False) |
        axial_df['ProtocolName'].str.contains('STAGE', case=False, na=False)
    ].sort_values(['patient_id', 'SeriesDescription'])

    if len(stage_seqs) > 0:
        for idx, row in stage_seqs.iterrows():
            print(f"\n{row['patient_id']} - Series {row['SeriesNumber']}:")
            print(f"  Description: {row['SeriesDescription']}")
            print(f"  Protocol: {row['ProtocolName']}")
            print(f"  TE: {row['EchoTime']} ms, TR: {row['RepetitionTime']} ms")
            print(f"  Flip Angle: {row['FlipAngle']}°")
            print(f"  Files: {row['num_files']}")

    return df

if __name__ == "__main__":
    raw_data_dir = "/Users/paul/Projects/STAGE_Study/data/raw"

    if not os.path.exists(raw_data_dir):
        print(f"Error: {raw_data_dir} not found")
        sys.exit(1)

    df = analyze_all_patients(raw_data_dir)

    print("\n" + "="*80)
    print("Analysis complete!")
    print("="*80)
    print(f"\nTotal series analyzed: {len(df)}")
    print(f"Total patients: {df['patient_id'].nunique()}")
    print(f"\nOrientation breakdown:")
    print(df['Orientation'].value_counts())
