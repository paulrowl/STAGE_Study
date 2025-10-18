#!/usr/bin/env python3
"""
Extract DICOM properties for Anon13609 to diagnose processing failures

This patient is missing T1_conv (series: 1000C9D0) but has other sequences successfully processed.
"""

import pydicom
from pathlib import Path
import pandas as pd
from collections import defaultdict

BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
SUBJECT_ID = 'Anon13609'

def safe_get(ds, tag, default='N/A'):
    """Safely get DICOM tag value"""
    try:
        return str(getattr(ds, tag, default))
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

        # Determine which axis is most perpendicular to slice
        abs_row = [abs(row_x), abs(row_y), abs(row_z)]
        abs_col = [abs(col_x), abs(col_y), abs(col_z)]

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

def extract_properties(folder_path):
    """Extract DICOM properties from a folder"""
    dicom_files = list(folder_path.glob('*.dcm'))

    if not dicom_files:
        return None

    # Read first DICOM file
    try:
        ds = pydicom.dcmread(dicom_files[0], stop_before_pixels=True)

        properties = {
            'Folder': folder_path.name,
            'Full_Path': str(folder_path),
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
            'Folder': folder_path.name,
            'Full_Path': str(folder_path),
            'Error': str(e),
            'Num_DICOM_Files': len(dicom_files)
        }

def main():
    print("="*80)
    print(f"DICOM Properties Analysis for {SUBJECT_ID}")
    print("="*80)

    # Find subject directory
    subject_dirs = list(BASE_DIR.glob(f'data/raw/{SUBJECT_ID}'))

    if not subject_dirs:
        print(f"ERROR: Subject directory not found for {SUBJECT_ID}")
        return

    subject_dir = subject_dirs[0]
    print(f"\nSubject directory: {subject_dir}")

    # Find all potential sequence folders
    # Look in both direct subfolders and nested IHE_PDI structure
    sequence_folders = []

    # Direct subfolders
    for item in subject_dir.iterdir():
        if item.is_dir():
            # Check if it contains DICOM files
            dicom_files = list(item.glob('*.dcm'))
            if dicom_files:
                sequence_folders.append(item)

            # Check nested folders (100*/100*)
            for nested1 in item.glob('100*'):
                if nested1.is_dir():
                    dicom_files = list(nested1.glob('*.dcm'))
                    if dicom_files:
                        sequence_folders.append(nested1)

                    for nested2 in nested1.glob('100*'):
                        if nested2.is_dir():
                            dicom_files = list(nested2.glob('*.dcm'))
                            if dicom_files:
                                sequence_folders.append(nested2)

    print(f"\nFound {len(sequence_folders)} folders with DICOM files")

    # Extract properties from each folder
    all_properties = []

    for folder in sorted(sequence_folders):
        print(f"\nProcessing: {folder.relative_to(subject_dir)}")
        props = extract_properties(folder)
        if props:
            all_properties.append(props)

    # Create DataFrame
    if all_properties:
        df = pd.DataFrame(all_properties)

        # Sort by Series Number if available
        if 'Series_Number' in df.columns:
            df = df.sort_values('Series_Number')

        # Save to CSV
        output_file = BASE_DIR / 'output' / 'statistics' / f'{SUBJECT_ID}_dicom_properties.csv'
        df.to_csv(output_file, index=False)
        print(f"\n{'='*80}")
        print(f"Saved detailed properties to: {output_file}")
        print(f"{'='*80}")

        # Display summary table
        print("\n" + "="*80)
        print("SUMMARY TABLE")
        print("="*80)

        # Key columns to display
        display_cols = [
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

        # Highlight the problematic T1_conv series (103)
        print("\n" + "="*80)
        print("SEARCHING FOR MISSING T1_conv (Series: 103)")
        print("="*80)

        target_series = '103'
        matching = df[df['Series_Number'].astype(str).str.upper() == target_series.upper()]

        if not matching.empty:
            print(f"\nFOUND Series {target_series}!")
            print("\nDetailed properties:")
            for col in df.columns:
                print(f"  {col}: {matching.iloc[0][col]}")
        else:
            print(f"\nSeries {target_series} NOT FOUND in DICOM files")
            print("\nAvailable series numbers:")
            if 'Series_Number' in df.columns:
                for sn in sorted(df['Series_Number'].unique()):
                    desc = df[df['Series_Number']==sn]['Series_Description'].iloc[0]
                    print(f"  {sn}: {desc}")

        # Check ground truth expectation
        print("\n" + "="*80)
        print("GROUND TRUTH EXPECTATION for Anon13609")
        print("="*80)
        print("Expected sequences:")
        print("  T1_conv: Series 103 <- MISSING in processed data")
        print("  T1_STAGE: OK")
        print("  T2_conv: OK")
        print("  T2_STAGE: OK")
        print("  SWI_conv: OK")
        print("  SWI_STAGE: OK")

    else:
        print("\nNo DICOM properties could be extracted")

if __name__ == '__main__':
    main()
