#!/usr/bin/env python3
"""
Extract DICOM properties for Anon13609 from organized data

This patient is missing T1_conv (series: 103) according to user
"""

import pydicom
from pathlib import Path
import pandas as pd

BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
SUBJECT_ID = 'Anon13609'
ORGANIZED_DIR = BASE_DIR / 'data' / 'raw' / 'organized' / SUBJECT_ID

def safe_get(ds, tag, default='N/A'):
    """Safely get DICOM tag value"""
    try:
        value = getattr(ds, tag, default)
        if isinstance(value, (list, tuple)):
            return str(value)
        return str(value)
    except:
        return default

def get_orientation(ds):
    """Determine image orientation from ImageOrientationPatient"""
    try:
        iop = ds.ImageOrientationPatient
        # Row direction
        row_x, row_y, row_z = iop[0:3]
        # Column direction
        col_x, col_y, col_z = iop[3:6]

        # The normal vector to the slice
        normal_x = row_y * col_z - row_z * col_y
        normal_y = row_z * col_x - row_x * col_z
        normal_z = row_x * col_y - row_y * col_x

        abs_normal = [abs(normal_x), abs(normal_y), abs(normal_z)]
        max_idx = abs_normal.index(max(abs_normal))

        if max_idx == 0:  # X is perpendicular -> Sagittal
            return 'Sagittal'
        elif max_idx == 1:  # Y is perpendicular -> Coronal
            return 'Coronal'
        else:  # Z is perpendicular -> Axial
            return 'Axial'
    except:
        return 'Unknown'

def extract_properties(folder_path, sequence_name):
    """Extract DICOM properties from a folder"""
    # Look for files without extension (common in organized DICOM data)
    all_files = [f for f in folder_path.iterdir() if f.is_file()]

    # Try to find valid DICOM files
    dicom_files = []
    for f in all_files:
        try:
            # Quick check if it's a DICOM file
            ds = pydicom.dcmread(f, stop_before_pixels=True, force=True)
            dicom_files.append(f)
        except:
            pass

    if not dicom_files:
        return None

    # Read first DICOM file
    try:
        ds = pydicom.dcmread(dicom_files[0], stop_before_pixels=True)

        properties = {
            'Sequence_Type': sequence_name,
            'Folder': folder_path.name,
            'Series_Number': safe_get(ds, 'SeriesNumber'),
            'Series_Description': safe_get(ds, 'SeriesDescription'),
            'Sequence_Name': safe_get(ds, 'SequenceName'),
            'Protocol_Name': safe_get(ds, 'ProtocolName'),
            'Manufacturer': safe_get(ds, 'Manufacturer'),
            'Manufacturer_Model': safe_get(ds, 'ManufacturerModelName'),
            'Magnetic_Field_Strength': safe_get(ds, 'MagneticFieldStrength'),
            'Echo_Time_ms': safe_get(ds, 'EchoTime'),
            'Repetition_Time_ms': safe_get(ds, 'RepetitionTime'),
            'Flip_Angle': safe_get(ds, 'FlipAngle'),
            'Pixel_Bandwidth': safe_get(ds, 'PixelBandwidth'),
            'Echo_Train_Length': safe_get(ds, 'EchoTrainLength'),
            'Imaging_Frequency': safe_get(ds, 'ImagingFrequency'),
            'Image_Type': safe_get(ds, 'ImageType'),
            'Scan_Options': safe_get(ds, 'ScanOptions'),
            'MR_Acquisition_Type': safe_get(ds, 'MRAcquisitionType'),
            'Slice_Thickness': safe_get(ds, 'SliceThickness'),
            'Spacing_Between_Slices': safe_get(ds, 'SpacingBetweenSlices'),
            'Rows': safe_get(ds, 'Rows'),
            'Columns': safe_get(ds, 'Columns'),
            'Pixel_Spacing': safe_get(ds, 'PixelSpacing'),
            'Orientation': get_orientation(ds),
            'Image_Orientation_Patient': safe_get(ds, 'ImageOrientationPatient'),
            'Num_DICOM_Files': len(dicom_files),
            'Series_InstanceUID': safe_get(ds, 'SeriesInstanceUID'),
            'Study_Date': safe_get(ds, 'StudyDate'),
            'Study_Time': safe_get(ds, 'StudyTime'),
            'Acquisition_Date': safe_get(ds, 'AcquisitionDate'),
            'Acquisition_Time': safe_get(ds, 'AcquisitionTime'),
        }

        return properties

    except Exception as e:
        return {
            'Sequence_Type': sequence_name,
            'Folder': folder_path.name,
            'Error': str(e),
            'Num_DICOM_Files': len(dicom_files)
        }

def main():
    print("="*80)
    print(f"DICOM Properties Analysis for {SUBJECT_ID}")
    print("="*80)

    if not ORGANIZED_DIR.exists():
        print(f"\nERROR: Organized directory not found: {ORGANIZED_DIR}")
        return

    print(f"\nOrganized directory: {ORGANIZED_DIR}")

    # Find all sequence folders
    sequence_folders = [d for d in ORGANIZED_DIR.iterdir() if d.is_dir()]

    print(f"\nFound {len(sequence_folders)} sequence folders:")
    for folder in sorted(sequence_folders):
        num_dicom = len(list(folder.glob('*.dcm')))
        print(f"  {folder.name}: {num_dicom} DICOM files")

    # Extract properties from each folder
    all_properties = []

    for folder in sorted(sequence_folders):
        print(f"\nProcessing: {folder.name}")
        props = extract_properties(folder, folder.name)
        if props:
            all_properties.append(props)

    # Create DataFrame
    if all_properties:
        df = pd.DataFrame(all_properties)

        # Sort by Sequence Type
        df = df.sort_values('Sequence_Type')

        # Save to CSV
        output_file = BASE_DIR / 'output' / 'statistics' / f'{SUBJECT_ID}_dicom_properties.csv'
        df.to_csv(output_file, index=False)
        print(f"\n{'='*80}")
        print(f"Saved detailed properties to: {output_file}")
        print(f"{'='*80}")

        # Display summary table
        print("\n" + "="*80)
        print("SUMMARY TABLE - ALL ORGANIZED SEQUENCES")
        print("="*80)

        # Key columns to display
        display_cols = [
            'Sequence_Type',
            'Series_Number',
            'Series_Description',
            'Protocol_Name',
            'Orientation',
            'Echo_Time_ms',
            'Repetition_Time_ms',
            'Flip_Angle',
            'Pixel_Bandwidth',
            'Num_DICOM_Files'
        ]

        display_cols = [col for col in display_cols if col in df.columns]

        print(df[display_cols].to_string(index=False))

        # Check for series 103
        print("\n" + "="*80)
        print("SEARCHING FOR T1_conv (Series: 103)")
        print("="*80)

        target_series = 103
        matching = df[df['Series_Number'].astype(str) == str(target_series)]

        if not matching.empty:
            print(f"\nFOUND Series {target_series} in organized data!")
            print(f"  Sequence Type: {matching.iloc[0]['Sequence_Type']}")
            print(f"  Series Description: {matching.iloc[0]['Series_Description']}")
            print(f"  Protocol: {matching.iloc[0]['Protocol_Name']}")
            print(f"  Number of files: {matching.iloc[0]['Num_DICOM_Files']}")
        else:
            print(f"\nSeries {target_series} NOT FOUND in organized data")

        # Ground truth comparison
        print("\n" + "="*80)
        print("GROUND TRUTH EXPECTATION vs ACTUAL")
        print("="*80)

        expected_sequences = {
            'T1_conv': '103',
            'T1_STAGE': '?',
            'T2_conv': '?',
            'T2_STAGE': '?',
            'SWI_conv': '?',
            'SWI_STAGE': '?'
        }

        print("\nExpected sequences (from ground truth):")
        found_sequences = set(df['Sequence_Type'].values)

        for seq_name, series_num in expected_sequences.items():
            if seq_name in found_sequences:
                actual_series = df[df['Sequence_Type'] == seq_name]['Series_Number'].iloc[0]
                print(f"  {seq_name}: Series {actual_series} - FOUND")
            else:
                print(f"  {seq_name}: Series {series_num} - MISSING")

        # Detail all series found
        print("\n" + "="*80)
        print("DETAILED PROPERTIES FOR EACH SEQUENCE")
        print("="*80)

        for idx, row in df.iterrows():
            print(f"\n{row['Sequence_Type']} (Series {row['Series_Number']}):")
            print(f"  Series Description: {row['Series_Description']}")
            print(f"  Protocol Name: {row['Protocol_Name']}")
            print(f"  Sequence Name: {row['Sequence_Name']}")
            print(f"  Manufacturer: {row['Manufacturer']}")
            print(f"  Field Strength: {row['Magnetic_Field_Strength']} T")
            print(f"  Orientation: {row['Orientation']}")
            print(f"  TE: {row['Echo_Time_ms']} ms")
            print(f"  TR: {row['Repetition_Time_ms']} ms")
            print(f"  Flip Angle: {row['Flip_Angle']} degrees")
            print(f"  Pixel Bandwidth: {row['Pixel_Bandwidth']} Hz/pixel")
            print(f"  Echo Train Length: {row['Echo_Train_Length']}")
            print(f"  Slice Thickness: {row['Slice_Thickness']} mm")
            print(f"  Matrix: {row['Rows']} x {row['Columns']}")
            print(f"  Number of DICOM files: {row['Num_DICOM_Files']}")

    else:
        print("\nNo DICOM properties could be extracted")

if __name__ == '__main__':
    main()
