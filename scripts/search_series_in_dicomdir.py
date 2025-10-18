#!/usr/bin/env python3
"""
Search for specific series numbers in DICOMDIR for Anon13609
"""

import pydicom
from pathlib import Path

SUBJECT_ID = 'Anon13609'
BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
SUBJECT_DIR = BASE_DIR / 'data' / 'raw' / SUBJECT_ID
DICOMDIR_PATH = SUBJECT_DIR / 'DICOMDIR'

TARGET_SERIES = 8165  # T1_STAGE

print("="*80)
print(f"Searching for Series {TARGET_SERIES} in {SUBJECT_ID}")
print("="*80)

if not DICOMDIR_PATH.exists():
    print(f"\nERROR: DICOMDIR not found at {DICOMDIR_PATH}")
    exit(1)

print(f"\nReading DICOMDIR: {DICOMDIR_PATH}")

try:
    dicomdir = pydicom.dcmread(str(DICOMDIR_PATH))

    print("\nAll series found in DICOMDIR:")
    print("-" * 80)

    all_series = []

    for patient in dicomdir.patient_records:
        for study in patient.children:
            for series in study.children:
                series_num = series.SeriesNumber if hasattr(series, 'SeriesNumber') else 'N/A'
                series_desc = series.SeriesDescription if hasattr(series, 'SeriesDescription') else 'N/A'
                num_images = len(series.children) if hasattr(series, 'children') else 0

                all_series.append({
                    'SeriesNumber': series_num,
                    'SeriesDescription': series_desc,
                    'NumImages': num_images
                })

                print(f"Series {series_num}: {series_desc} ({num_images} images)")

                # Check if this is our target
                if series_num == TARGET_SERIES:
                    print(f"\n{'='*80}")
                    print(f"FOUND TARGET SERIES {TARGET_SERIES}!")
                    print(f"{'='*80}")
                    print(f"  Series Description: {series_desc}")
                    print(f"  Number of Images: {num_images}")

                    if hasattr(series, 'children') and len(series.children) > 0:
                        first_image = series.children[0]
                        if hasattr(first_image, 'ReferencedFileID'):
                            file_path_parts = first_image.ReferencedFileID
                            folder_path = SUBJECT_DIR / Path(*file_path_parts[:-1])
                            print(f"  Folder Path: {folder_path}")
                            print(f"  Exists: {folder_path.exists()}")

                            if folder_path.exists():
                                # Count actual files
                                dicom_files = []
                                for f in folder_path.iterdir():
                                    if f.is_file():
                                        try:
                                            ds = pydicom.dcmread(f, stop_before_pixels=True, force=True)
                                            dicom_files.append(f)
                                        except:
                                            pass
                                print(f"  Actual DICOM files in folder: {len(dicom_files)}")

                                if dicom_files:
                                    # Read first file to get properties
                                    ds = pydicom.dcmread(dicom_files[0], stop_before_pixels=True)
                                    print(f"\n  DICOM Properties:")
                                    print(f"    Series Description: {ds.SeriesDescription if hasattr(ds, 'SeriesDescription') else 'N/A'}")
                                    print(f"    Protocol Name: {ds.ProtocolName if hasattr(ds, 'ProtocolName') else 'N/A'}")
                                    print(f"    Sequence Name: {ds.SequenceName if hasattr(ds, 'SequenceName') else 'N/A'}")
                                    print(f"    Manufacturer: {ds.Manufacturer if hasattr(ds, 'Manufacturer') else 'N/A'}")
                                    print(f"    TE: {ds.EchoTime if hasattr(ds, 'EchoTime') else 'N/A'} ms")
                                    print(f"    TR: {ds.RepetitionTime if hasattr(ds, 'RepetitionTime') else 'N/A'} ms")
                                    print(f"    Flip Angle: {ds.FlipAngle if hasattr(ds, 'FlipAngle') else 'N/A'} degrees")

                                    # Check orientation
                                    if hasattr(ds, 'ImageOrientationPatient'):
                                        iop = ds.ImageOrientationPatient
                                        row_x, row_y, row_z = iop[0:3]
                                        col_x, col_y, col_z = iop[3:6]
                                        normal_x = row_y * col_z - row_z * col_y
                                        normal_y = row_z * col_x - row_x * col_z
                                        normal_z = row_x * col_y - row_y * col_x
                                        abs_normal = [abs(normal_x), abs(normal_y), abs(normal_z)]
                                        max_idx = abs_normal.index(max(abs_normal))
                                        orientation = ['Sagittal', 'Coronal', 'Axial'][max_idx]
                                        print(f"    Orientation: {orientation}")

    print(f"\n{'='*80}")
    print(f"Summary: Found {len(all_series)} series total")
    print(f"{'='*80}")

    if TARGET_SERIES not in [s['SeriesNumber'] for s in all_series]:
        print(f"\nSeries {TARGET_SERIES} NOT FOUND in DICOMDIR")
        print("\nAll series numbers found:")
        for s in sorted(all_series, key=lambda x: x['SeriesNumber'] if isinstance(x['SeriesNumber'], int) else 0):
            print(f"  {s['SeriesNumber']}: {s['SeriesDescription']}")

except Exception as e:
    print(f"\nERROR reading DICOMDIR: {e}")
    import traceback
    traceback.print_exc()
