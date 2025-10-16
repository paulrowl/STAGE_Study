#!/usr/bin/env python3
"""
Scan all 43 patients to find T1_STAGE sequences
"""

import pydicom
from pathlib import Path
from collections import defaultdict

def find_sequence_folders(subject_dir):
    """Navigate to sequence folders"""
    sequence_folders = []
    level1_folders = [f for f in subject_dir.iterdir()
                     if f.is_dir() and f.name.startswith('100')]

    for level1 in level1_folders:
        level2_folders = [f for f in level1.iterdir()
                        if f.is_dir() and f.name.startswith('100')]

        for level2 in level2_folders:
            seq_folders = [f for f in level2.iterdir()
                          if f.is_dir() and not f.name.startswith('.')]
            sequence_folders.extend(seq_folders)

    return sequence_folders

def extract_dicom_info(folder_path):
    """Extract key DICOM properties"""
    dicom_files = [f for f in folder_path.iterdir() if f.is_file() and not f.name.startswith('.')]

    if not dicom_files:
        return None

    for dicom_file in dicom_files[:5]:
        try:
            ds = pydicom.dcmread(dicom_file, force=True)

            # Check orientation
            try:
                img_orient = ds.ImageOrientationPatient
                is_axial = abs(img_orient[0]) > 0.7 and abs(img_orient[4]) > 0.7
            except:
                series_desc = str(getattr(ds, 'SeriesDescription', '')).lower()
                is_axial = 'ax' in series_desc or 'tra' in series_desc or 'stage' in series_desc

            return {
                'series_description': str(getattr(ds, 'SeriesDescription', 'UNKNOWN')),
                'manufacturer': str(getattr(ds, 'Manufacturer', 'UNKNOWN')),
                'image_type': str(getattr(ds, 'ImageType', 'UNKNOWN')),
                'pixel_representation': int(getattr(ds, 'PixelRepresentation', 0)),
                'num_files': len([f for f in folder_path.iterdir() if f.is_file()]),
                'is_axial': is_axial
            }
        except:
            continue

    return None

def main():
    base_dir = Path('/Users/paul/Projects/STAGE_Study/data/raw')

    # Get all patient folders
    patient_folders = sorted([f for f in base_dir.iterdir()
                             if f.is_dir() and f.name.startswith('Anon')])

    results = defaultdict(list)

    print("="*80)
    print("SCANNING ALL PATIENTS FOR T1_STAGE SEQUENCES")
    print("="*80)

    for patient_dir in patient_folders:
        patient_id = patient_dir.name

        sequence_folders = find_sequence_folders(patient_dir)

        # Look for T1 STAGE sequences
        t1_stage_found = []

        for seq_folder in sequence_folders:
            info = extract_dicom_info(seq_folder)
            if not info:
                continue

            series_desc = info['series_description'].upper()
            manufacturer = info['manufacturer'].upper()

            # Check if this is a T1 STAGE sequence
            is_t1 = 'T1' in series_desc or 'MPRAGE' in series_desc
            is_stage = 'SPINTECH' in manufacturer or 'STAGE' in series_desc

            if is_t1 and is_stage:
                # Check if it's suitable (axial, enough slices)
                is_axial = info['is_axial']
                num_files = info['num_files']
                is_derived = 'DERIVED' in info['image_type']

                quality = 'GOOD'
                if not is_axial:
                    quality = 'NON-AXIAL'
                elif num_files < 100:
                    quality = 'TOO_FEW_SLICES'
                elif is_derived and num_files < 120:
                    quality = 'DERIVED_LOW_SLICES'

                t1_stage_found.append({
                    'series_desc': info['series_description'],
                    'manufacturer': info['manufacturer'],
                    'num_files': num_files,
                    'is_axial': is_axial,
                    'image_type': info['image_type'],
                    'pixel_rep': info['pixel_representation'],
                    'quality': quality
                })

        if t1_stage_found:
            # Sort by quality
            good_ones = [s for s in t1_stage_found if s['quality'] == 'GOOD']
            results['has_t1_stage'].append({
                'patient': patient_id,
                'sequences': t1_stage_found,
                'has_good': len(good_ones) > 0
            })

            status = "✓ GOOD" if good_ones else "⚠ NEEDS REVIEW"
            print(f"{patient_id}: {status} - Found {len(t1_stage_found)} T1_STAGE sequences ({len(good_ones)} good)")
            for seq in t1_stage_found:
                print(f"    {seq['series_desc']}: {seq['num_files']} files, {seq['quality']}")
        else:
            results['no_t1_stage'].append(patient_id)
            print(f"{patient_id}: ✗ NO T1_STAGE sequences found")

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Patients WITH T1_STAGE data: {len(results['has_t1_stage'])}")
    print(f"Patients WITHOUT T1_STAGE data: {len(results['no_t1_stage'])}")

    good_count = sum(1 for p in results['has_t1_stage'] if p['has_good'])
    needs_review = sum(1 for p in results['has_t1_stage'] if not p['has_good'])

    print(f"\n  With GOOD T1_STAGE: {good_count}")
    print(f"  Needs review: {needs_review}")
    print(f"  Truly missing: {len(results['no_t1_stage'])}")

    if results['no_t1_stage']:
        print(f"\nPatients truly missing T1_STAGE:")
        for p in results['no_t1_stage']:
            print(f"  - {p}")

    print("\n" + "="*80)

if __name__ == '__main__':
    main()
