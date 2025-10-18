#!/usr/bin/env python3
"""
Investigate all subjects with missing sequences by searching raw DICOM data

Subjects with incomplete pairs:
- T1: Anon13609, Anon21108, Anon27334, Anon28584, Anon39526, Anon39768, Anon43113, Anon50199, Anon72813, Anon88788
- SWI: Anon39768, Anon43113
"""

import pydicom
import pandas as pd
from pathlib import Path
import re

BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
GROUND_TRUTH_CSV = '/Users/paul/Downloads/sequence_folder_mapping - sequence_folder_mapping.csv'
STATS_FILE = BASE_DIR / 'output' / 'statistics' / 'gm_wm_tissue_stats_20251017_025955.csv'
OUTPUT_FILE = BASE_DIR / 'output' / 'statistics' / 'missing_sequences_investigation.csv'

# Subjects with incomplete pairs
SUBJECTS_TO_INVESTIGATE = [
    'Anon13609', 'Anon21108', 'Anon27334', 'Anon28584', 'Anon39526',
    'Anon39768', 'Anon43113', 'Anon50199', 'Anon72813', 'Anon88788'
]

def parse_series_number(cell_value):
    """Extract series number from CSV cell"""
    if pd.isna(cell_value) or str(cell_value).strip() == '':
        return None
    cell_str = str(cell_value).strip()
    match = re.match(r'([A-F0-9]+)\s*\(#(\d+)\)', cell_str)
    if match:
        return match.group(2)  # Return the series number from parentheses
    match = re.match(r'\(#(\d+)\)', cell_str)
    if match:
        return match.group(1)
    if re.match(r'^[A-F0-9]+$', cell_str):
        return None  # Just folder ID, no series number
    if re.match(r'^\d+$', cell_str):
        return cell_str
    return None

def search_dicomdir(subject_id, target_series):
    """Search DICOMDIR for specific series number"""
    subject_dir = BASE_DIR / 'data' / 'raw' / subject_id
    dicomdir_path = subject_dir / 'DICOMDIR'

    if not dicomdir_path.exists():
        return None, "No DICOMDIR found"

    try:
        dicomdir = pydicom.dcmread(str(dicomdir_path))
        target_series_int = int(target_series)

        for patient in dicomdir.patient_records:
            for study in patient.children:
                for series in study.children:
                    if series.SeriesNumber == target_series_int:
                        series_desc = series.SeriesDescription if hasattr(series, 'SeriesDescription') else 'N/A'
                        num_images = len(series.children) if hasattr(series, 'children') else 0

                        # Get folder path
                        if hasattr(series, 'children') and len(series.children) > 0:
                            first_image = series.children[0]
                            if hasattr(first_image, 'ReferencedFileID'):
                                file_path_parts = first_image.ReferencedFileID[:-1]
                                folder_path = subject_dir / Path(*file_path_parts)

                                if folder_path.exists():
                                    # Count actual DICOM files
                                    dicom_files = []
                                    for f in folder_path.iterdir():
                                        if f.is_file():
                                            try:
                                                ds = pydicom.dcmread(f, stop_before_pixels=True, force=True)
                                                dicom_files.append(f)
                                            except:
                                                pass

                                    if dicom_files:
                                        # Read first file for metadata
                                        ds = pydicom.dcmread(dicom_files[0], stop_before_pixels=True)

                                        # Get orientation
                                        try:
                                            iop = ds.ImageOrientationPatient
                                            row_x, row_y, row_z = iop[0:3]
                                            col_x, col_y, col_z = iop[3:6]
                                            normal_x = row_y * col_z - row_z * col_y
                                            normal_y = row_z * col_x - row_x * col_z
                                            normal_z = row_x * col_y - row_y * col_x
                                            abs_normal = [abs(normal_x), abs(normal_y), abs(normal_z)]
                                            max_idx = abs_normal.index(max(abs_normal))
                                            orientation = ['Sagittal', 'Coronal', 'Axial'][max_idx]
                                        except:
                                            orientation = 'Unknown'

                                        return {
                                            'series_number': target_series,
                                            'series_desc': series_desc,
                                            'num_files': len(dicom_files),
                                            'folder_path': str(folder_path.relative_to(subject_dir)),
                                            'manufacturer': ds.Manufacturer if hasattr(ds, 'Manufacturer') else 'N/A',
                                            'orientation': orientation,
                                            'te': ds.EchoTime if hasattr(ds, 'EchoTime') else 'N/A',
                                            'tr': ds.RepetitionTime if hasattr(ds, 'RepetitionTime') else 'N/A',
                                            'flip_angle': ds.FlipAngle if hasattr(ds, 'FlipAngle') else 'N/A',
                                            'pixel_bandwidth': ds.PixelBandwidth if hasattr(ds, 'PixelBandwidth') else 'N/A'
                                        }, "Found"
                                    else:
                                        return None, "Folder exists but no DICOM files"
                                else:
                                    return None, f"Folder doesn't exist: {folder_path}"

        return None, f"Series {target_series} not found in DICOMDIR"

    except Exception as e:
        return None, f"Error reading DICOMDIR: {str(e)}"

def main():
    print("="*80)
    print("INVESTIGATING MISSING SEQUENCES IN RAW DICOM DATA")
    print("="*80)

    # Load ground truth
    print("\nLoading ground truth...")
    df_gt = pd.read_csv(GROUND_TRUTH_CSV)

    # Load processing results
    print("Loading processing results...")
    df_results = pd.read_csv(STATS_FILE)

    # Create set of successfully processed sequences
    processed = set()
    for _, row in df_results.iterrows():
        processed.add((row['subject_id'], row['sequence']))

    print(f"Found {len(processed)} successfully processed sequences")

    # Investigation results
    investigation_results = []

    SEQUENCES = ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']

    for subject_id in SUBJECTS_TO_INVESTIGATE:
        print(f"\n{'='*80}")
        print(f"Investigating: {subject_id}")
        print(f"{'='*80}")

        # Get ground truth row
        gt_row = df_gt[df_gt['rAccession'] == subject_id]
        if gt_row.empty:
            print(f"  WARNING: {subject_id} not in ground truth")
            continue

        gt_row = gt_row.iloc[0]

        # Check each sequence
        for seq in SEQUENCES:
            # Parse series number from ground truth
            series_num = parse_series_number(gt_row[seq])

            # Check if it was processed
            was_processed = (subject_id, seq) in processed

            result = {
                'subject_id': subject_id,
                'sequence': seq,
                'series_number_gt': series_num if series_num else 'N/A',
                'processed': was_processed
            }

            # If it has a series number but wasn't processed, investigate
            if series_num and not was_processed:
                print(f"\n  {seq} (series {series_num}): MISSING from stats, searching raw data...")

                dicom_info, status = search_dicomdir(subject_id, series_num)

                if dicom_info:
                    print(f"    ✓ FOUND in raw data!")
                    print(f"      Description: {dicom_info['series_desc']}")
                    print(f"      Files: {dicom_info['num_files']}")
                    print(f"      Orientation: {dicom_info['orientation']}")
                    print(f"      Manufacturer: {dicom_info['manufacturer']}")
                    print(f"      Folder: {dicom_info['folder_path']}")

                    result.update({
                        'raw_data_status': 'Found',
                        'series_desc': dicom_info['series_desc'],
                        'num_files': dicom_info['num_files'],
                        'orientation': dicom_info['orientation'],
                        'manufacturer': dicom_info['manufacturer'],
                        'te': dicom_info['te'],
                        'tr': dicom_info['tr'],
                        'flip_angle': dicom_info['flip_angle'],
                        'pixel_bandwidth': dicom_info['pixel_bandwidth'],
                        'folder_path': dicom_info['folder_path']
                    })
                else:
                    print(f"    ✗ NOT FOUND: {status}")
                    result.update({
                        'raw_data_status': 'Not Found',
                        'error': status
                    })
            elif not series_num:
                result['raw_data_status'] = 'N/A - not in ground truth'
            elif was_processed:
                result['raw_data_status'] = 'Successfully processed'

            investigation_results.append(result)

    # Create DataFrame
    df_investigation = pd.DataFrame(investigation_results)

    # Save results
    df_investigation.to_csv(OUTPUT_FILE, index=False)
    print(f"\n{'='*80}")
    print(f"Investigation complete! Saved to: {OUTPUT_FILE}")
    print(f"{'='*80}")

    # Print summary
    missing_but_found = df_investigation[
        (df_investigation['processed'] == False) &
        (df_investigation['raw_data_status'] == 'Found')
    ]

    print(f"\n{'='*80}")
    print("SUMMARY: Sequences MISSING from stats but FOUND in raw data")
    print(f"{'='*80}")

    if len(missing_but_found) > 0:
        print(f"\nFound {len(missing_but_found)} sequences in raw data that weren't processed:\n")
        for _, row in missing_but_found.iterrows():
            print(f"{row['subject_id']}, {row['sequence']} (series {row['series_number_gt']})")
            print(f"  Description: {row['series_desc']}")
            print(f"  Files: {row['num_files']}, Orientation: {row['orientation']}")
            print()
    else:
        print("\nNo missing sequences were found in raw DICOM data.")
        print("All 'missing' sequences are truly absent from the dataset.")

    # Print sequences not in ground truth
    not_in_gt = df_investigation[
        df_investigation['raw_data_status'] == 'N/A - not in ground truth'
    ]

    if len(not_in_gt) > 0:
        print(f"\n{'='*80}")
        print("Sequences not expected (not in ground truth)")
        print(f"{'='*80}\n")
        for _, row in not_in_gt.iterrows():
            print(f"{row['subject_id']}, {row['sequence']}")

if __name__ == '__main__':
    main()
