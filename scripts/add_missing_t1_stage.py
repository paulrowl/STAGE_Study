#!/usr/bin/env python3
"""
Add missing T1_STAGE sequences to already organized patient folders
"""

import sys
import shutil
from pathlib import Path

# Import the updated classifier
sys.path.insert(0, str(Path(__file__).parent))
from dicom_sequence_classifier import DICOMSequenceClassifier

def main():
    base_dir = Path('/Users/paul/Projects/STAGE_Study/data/raw')
    output_dir = Path('/Users/paul/Projects/STAGE_Study/data/raw/organized')

    print("="*80)
    print("ADDING MISSING T1_STAGE SEQUENCES TO ORGANIZED FOLDERS")
    print("="*80)

    # Get all patient folders
    patient_folders = sorted([f for f in base_dir.iterdir()
                             if f.is_dir() and f.name.startswith('Anon')])

    classifier = DICOMSequenceClassifier(
        base_dir=base_dir,
        output_dir=output_dir,
        dry_run=False,  # Actually copy files
        min_images=30,
        exclude_t1_stage_variants=True
    )

    patients_updated = 0
    patients_skipped = 0

    for patient_dir in patient_folders:
        patient_id = patient_dir.name
        output_patient_dir = output_dir / patient_id
        output_t1_stage_dir = output_patient_dir / 'T1_STAGE'

        # Check if T1_STAGE already exists
        if output_t1_stage_dir.exists():
            print(f"{patient_id}: T1_STAGE already exists, skipping")
            patients_skipped += 1
            continue

        # Process this patient to find T1_STAGE sequences
        print(f"\n{patient_id}: Searching for T1_STAGE sequences...")

        sequence_folders = classifier.find_sequence_folders(patient_dir)

        t1_stage_found = False

        for seq_folder in sequence_folders:
            properties = classifier.extract_dicom_properties(seq_folder)
            if not properties:
                continue

            seq_type, confidence, criteria = classifier.classify_sequence(properties)

            # Only process T1_STAGE sequences
            if not seq_type.startswith('T1_STAGE'):
                continue

            # Check if should include
            should_include, reason = classifier.should_include_sequence(
                seq_type, properties['num_files'], properties
            )

            if should_include and confidence >= 50.0:
                # This is a valid T1_STAGE sequence, organize it
                success = classifier.organize_sequence(
                    patient_id, seq_folder, seq_type, properties['num_files'], properties
                )

                if success:
                    print(f"  ✓ Added T1_STAGE from: {properties['series_description']}")
                    print(f"    Files: {properties['num_files']}, Classification: {seq_type}")
                    t1_stage_found = True
                    # Only add one T1_STAGE sequence per patient
                    break

        if t1_stage_found:
            patients_updated += 1
        else:
            print(f"  ⚠ No suitable T1_STAGE sequences found")

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Patients updated with T1_STAGE: {patients_updated}")
    print(f"Patients skipped (already had T1_STAGE): {patients_skipped}")
    print(f"Patients without suitable T1_STAGE: {43 - patients_updated - patients_skipped}")
    print("="*80)

if __name__ == '__main__':
    main()
