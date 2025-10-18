#!/usr/bin/env python3
"""
Inspect what a specific folder ID corresponds to in DICOMDIR
"""

import pydicom
from pathlib import Path

subject_dir = Path('/Users/paul/Projects/STAGE_Study/data/raw/Anon11271')
target_folder_id = '10011A2A'

dicomdir_path = subject_dir / 'DICOMDIR'

if not dicomdir_path.exists():
    print(f"ERROR: DICOMDIR not found at {dicomdir_path}")
    exit(1)

print(f"Searching for folder ID: {target_folder_id}")
print("=" * 80)

dicomdir = pydicom.dcmread(str(dicomdir_path))

for patient in dicomdir.patient_records:
    patient_id = getattr(patient, 'PatientID', 'N/A')

    for study in patient.children:
        study_uid = getattr(study, 'StudyInstanceUID', 'N/A')
        study_desc = getattr(study, 'StudyDescription', 'N/A')

        for series in study.children:
            series_num = getattr(series, 'SeriesNumber', 'N/A')
            series_desc = getattr(series, 'SeriesDescription', 'N/A')
            series_uid = getattr(series, 'SeriesInstanceUID', 'N/A')
            modality = getattr(series, 'Modality', 'N/A')

            # Check if any image in this series references our folder
            if hasattr(series, 'children'):
                for image in series.children:
                    if hasattr(image, 'ReferencedFileID'):
                        file_path_parts = image.ReferencedFileID

                        # Check if target_folder_id is in the path
                        if target_folder_id in file_path_parts:
                            print(f"\n✓ FOUND IN SERIES:")
                            print(f"  Series Number: {series_num}")
                            print(f"  Series Description: {series_desc}")
                            print(f"  Modality: {modality}")
                            print(f"  Number of Images: {len(series.children)}")
                            print(f"\n  Full path structure:")
                            print(f"    Patient: {patient_id}")
                            print(f"    Study: {study_desc}")
                            print(f"    Series UID: {series_uid[:50]}...")
                            print(f"\n  Example file path: {'/'.join(file_path_parts)}")

                            # Check the position of our folder in the path
                            folder_position = file_path_parts.index(target_folder_id)
                            print(f"\n  Folder position in hierarchy: {folder_position}")
                            print(f"  Path components: {' → '.join(file_path_parts)}")

                            # Read one DICOM file to get more details
                            full_path = subject_dir / Path(*file_path_parts)
                            if full_path.exists():
                                print(f"\n  Reading DICOM file for details...")
                                try:
                                    dcm = pydicom.dcmread(full_path, stop_before_pixels=True)
                                    print(f"\n  DICOM Properties:")
                                    print(f"    Manufacturer: {getattr(dcm, 'Manufacturer', 'N/A')}")
                                    print(f"    Sequence Name: {getattr(dcm, 'SequenceName', 'N/A')}")
                                    print(f"    Protocol Name: {getattr(dcm, 'ProtocolName', 'N/A')}")
                                    print(f"    Echo Time (TE): {getattr(dcm, 'EchoTime', 'N/A')} ms")
                                    print(f"    Repetition Time (TR): {getattr(dcm, 'RepetitionTime', 'N/A')} ms")
                                    print(f"    Flip Angle: {getattr(dcm, 'FlipAngle', 'N/A')}°")
                                    print(f"    Pixel Bandwidth: {getattr(dcm, 'PixelBandwidth', 'N/A')}")
                                    print(f"    Image Orientation: {getattr(dcm, 'ImageOrientationPatient', 'N/A')}")
                                    print(f"    Slice Thickness: {getattr(dcm, 'SliceThickness', 'N/A')} mm")
                                    print(f"    Rows x Columns: {getattr(dcm, 'Rows', 'N/A')} x {getattr(dcm, 'Columns', 'N/A')}")
                                except Exception as e:
                                    print(f"    Error reading DICOM file: {e}")

                            print("\n" + "=" * 80)
                            exit(0)

print(f"\n✗ Folder ID '{target_folder_id}' not found in DICOMDIR")
