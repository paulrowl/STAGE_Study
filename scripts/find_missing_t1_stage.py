#!/usr/bin/env python3
"""
Analyze raw DICOM data to find potentially misclassified T1_STAGE sequences
"""

import os
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

            return {
                'series_description': str(getattr(ds, 'SeriesDescription', 'UNKNOWN')),
                'manufacturer': str(getattr(ds, 'Manufacturer', 'UNKNOWN')),
                'protocol_name': str(getattr(ds, 'ProtocolName', 'UNKNOWN')),
                'sequence_name': str(getattr(ds, 'SequenceName', 'UNKNOWN')),
                'pixel_bandwidth': float(getattr(ds, 'PixelBandwidth', 0)),
                'echo_time': float(getattr(ds, 'EchoTime', 0)),
                'repetition_time': float(getattr(ds, 'RepetitionTime', 0)),
                'inversion_time': float(getattr(ds, 'InversionTime', 0)),
                'flip_angle': float(getattr(ds, 'FlipAngle', 0)),
                'image_type': str(getattr(ds, 'ImageType', 'UNKNOWN')),
                'pixel_representation': int(getattr(ds, 'PixelRepresentation', 0)),
                'num_files': len([f for f in folder_path.iterdir() if f.is_file()])
            }
        except:
            continue

    return None

def main():
    # Pick a few patients missing T1_STAGE
    test_patients = ['Anon10644', 'Anon11271', 'Anon42647']

    base_dir = Path('/Users/paul/Projects/STAGE_Study/data/raw')

    print("="*80)
    print("SEARCHING FOR MISSING T1_STAGE SEQUENCES")
    print("="*80)

    for patient_id in test_patients:
        patient_dir = base_dir / patient_id
        if not patient_dir.exists():
            print(f"\n{patient_id}: Directory not found")
            continue

        print(f"\n{patient_id}:")
        print("-"*80)

        sequence_folders = find_sequence_folders(patient_dir)
        print(f"Found {len(sequence_folders)} sequence folders")

        # Look for T1-related sequences
        t1_sequences = []

        for seq_folder in sequence_folders:
            info = extract_dicom_info(seq_folder)
            if not info:
                continue

            series_desc = info['series_description'].upper()
            manufacturer = info['manufacturer'].upper()

            # Look for T1 sequences
            if 'T1' in series_desc or 'MPRAGE' in series_desc:
                is_stage = 'SPINTECH' in manufacturer or 'STAGE' in series_desc
                scanner_type = 'STAGE' if is_stage else 'conventional'

                t1_sequences.append({
                    'folder': seq_folder.name,
                    'series_desc': info['series_description'],
                    'manufacturer': info['manufacturer'],
                    'scanner_type': scanner_type,
                    'protocol': info['protocol_name'],
                    'sequence_name': info['sequence_name'],
                    'pixel_bandwidth': info['pixel_bandwidth'],
                    'image_type': info['image_type'],
                    'pixel_rep': info['pixel_representation'],
                    'num_files': info['num_files'],
                    'TE': info['echo_time'],
                    'TR': info['repetition_time'],
                    'TI': info['inversion_time'],
                    'flip_angle': info['flip_angle']
                })

        if t1_sequences:
            print(f"\nFound {len(t1_sequences)} T1-related sequences:")
            for seq in t1_sequences:
                print(f"\n  Folder: {seq['folder']}")
                print(f"    SeriesDescription: {seq['series_desc']}")
                print(f"    Manufacturer: {seq['manufacturer']}")
                print(f"    Scanner Type: {seq['scanner_type']}")
                print(f"    Protocol: {seq['protocol']}")
                print(f"    SequenceName: {seq['sequence_name']}")
                print(f"    ImageType: {seq['image_type']}")
                print(f"    PixelBandwidth: {seq['pixel_bandwidth']:.1f}")
                print(f"    PixelRepresentation: {seq['pixel_rep']}")
                print(f"    Files: {seq['num_files']}")
                print(f"    TE/TR/TI: {seq['TE']:.2f} / {seq['TR']:.2f} / {seq['TI']:.2f}")
                print(f"    FlipAngle: {seq['flip_angle']:.1f}")
        else:
            print("  NO T1 sequences found!")

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)

if __name__ == '__main__':
    main()
