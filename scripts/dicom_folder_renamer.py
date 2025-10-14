#!/usr/bin/env python3
"""
DICOM Folder Identifier and Renamer for STAGE Study
=====================================================
Reads DICOM headers to identify sequences and renames folders accordingly.

Directory Structure Expected:
STAGE/
├── patient_01/
│   ├── DICOMDIR
│   └── 1000xxxxx/           (folder starting with 1000)
│       ├── subfolder1/      (sequence folder - will be renamed)
│       ├── subfolder2/      (sequence folder - will be renamed)
│       └── ...

Usage:
    # Dry run (no changes, safe to test)
    python dicom_folder_renamer.py /path/to/STAGE --dry-run

    # Live run (actually renames folders)
    python dicom_folder_renamer.py /path/to/STAGE --live

Sequence Mappings:
    "T1 MPRAGE SAG NON-SEL" → T1_conv    (typically 112 images)
    "STAGE-T1W"             → T1_STAGE   (typically 112 images)
    "T2 AX 3mm"             → T2_conv    (typically 42 images)
    "T2w_STAGE"             → T2_STAGE   (typically 112 images)
    "SWI AX_SWI"            → SWI_conv   (typically 88 images)
    "SWI_STAGE"             → SWI_STAGE  (typically 112 images)
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime
import pydicom
import csv
import json
from collections import defaultdict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)


class DICOMFolderRenamer:
    """Identifies and renames DICOM sequence folders based on SeriesDescription"""

    def __init__(self, base_dir, dry_run=True):
        self.base_dir = Path(base_dir)
        self.dry_run = dry_run
        self.logger = logging.getLogger(__name__)

        # Sequence mapping: SeriesDescription pattern → (folder_name, expected_count, tolerance)
        self.sequence_mapping = {
            'T1 MPRAGE SAG NON-SEL': ('T1_conv', 112, 10),
            'STAGE-T1W': ('T1_STAGE', 112, 10),
            'T2 AX 3mm': ('T2_conv', 42, 5),
            'T2w_STAGE': ('T2_STAGE', 112, 10),
            'SWI AX_SWI': ('SWI_conv', 88, 10),
            'SWI_STAGE': ('SWI_STAGE', 112, 10),
        }

        # Results tracking
        self.results = []
        self.rename_log = []

    def find_patient_folders(self):
        """Find all patient folders in the base directory"""
        patient_folders = []

        for item in self.base_dir.iterdir():
            if item.is_dir():
                # Look for folders starting with 1000
                subfolders = list(item.glob('1000*'))
                if subfolders:
                    patient_folders.append(item)

        self.logger.info(f"Found {len(patient_folders)} patient folders")
        return sorted(patient_folders)

    def read_dicom_header(self, dicom_file):
        """Read DICOM file and extract relevant metadata"""
        try:
            ds = pydicom.dcmread(dicom_file, force=True, stop_before_pixels=True)

            return {
                'SeriesDescription': str(getattr(ds, 'SeriesDescription', '')),
                'SeriesNumber': str(getattr(ds, 'SeriesNumber', 'N/A')),
                'ImageType': str(getattr(ds, 'ImageType', 'N/A')),
                'Rows': getattr(ds, 'Rows', 0),
                'Columns': getattr(ds, 'Columns', 0),
            }
        except Exception as e:
            self.logger.debug(f"Error reading {dicom_file}: {e}")
            return None

    def identify_sequence(self, folder_path):
        """Identify sequence type by reading DICOM headers in folder"""

        # Find DICOM files in folder
        dicom_files = []
        for ext in ['', '.dcm', '.DCM', '.dicom', '.DICOM']:
            dicom_files.extend(list(folder_path.glob(f'*{ext}')))

        # Filter out non-DICOM files
        dicom_files = [f for f in dicom_files if f.is_file() and not f.name.startswith('.')]

        if not dicom_files:
            return None, 0, "No DICOM files found"

        file_count = len(dicom_files)

        # Read first DICOM file to get SeriesDescription
        metadata = self.read_dicom_header(dicom_files[0])

        if metadata is None:
            return None, file_count, "Could not read DICOM header"

        series_desc = metadata['SeriesDescription']

        # Match to known sequences
        for pattern, (target_name, expected_count, tolerance) in self.sequence_mapping.items():
            if pattern in series_desc:
                # Validate file count
                if abs(file_count - expected_count) <= tolerance:
                    status = "match"
                else:
                    status = f"warning: expected {expected_count}±{tolerance}, got {file_count}"

                # Special validation for T2w_STAGE (check it's real brain tissue)
                if target_name == 'T2_STAGE':
                    if not self.validate_t2w_stage(dicom_files[0], metadata):
                        return None, file_count, "T2w_STAGE validation failed (not brain tissue)"

                return target_name, file_count, status

        # No match found
        return None, file_count, f"Unknown sequence: {series_desc}"

    def validate_t2w_stage(self, dicom_file, metadata):
        """Validate that T2w_STAGE contains brain tissue, not source images"""
        try:
            # Check ImageType - should be DERIVED
            image_type = str(metadata.get('ImageType', ''))
            if 'DERIVED' not in image_type:
                self.logger.warning(f"T2w_STAGE may not be derived image: {image_type}")
                return False

            # Check dimensions - brain tissue should have reasonable matrix size
            rows = metadata.get('Rows', 0)
            cols = metadata.get('Columns', 0)

            if rows < 128 or cols < 128:
                self.logger.warning(f"T2w_STAGE dimensions too small: {rows}x{cols}")
                return False

            return True

        except Exception as e:
            self.logger.warning(f"T2w_STAGE validation error: {e}")
            return False

    def process_patient(self, patient_folder):
        """Process a single patient folder"""
        patient_id = patient_folder.name
        self.logger.info(f"\nProcessing patient: {patient_id}")

        patient_result = {
            'patient_id': patient_id,
            'sequences_found': {},
            'warnings': [],
            'errors': []
        }

        # Find the 1000* subfolder
        subfolders_1000 = list(patient_folder.glob('1000*'))

        if not subfolders_1000:
            error = "No 1000* folder found"
            self.logger.error(f"  {patient_id}: {error}")
            patient_result['errors'].append(error)
            return patient_result

        main_folder = subfolders_1000[0]

        # Get all sequence folders
        sequence_folders = [f for f in main_folder.iterdir() if f.is_dir()]

        self.logger.info(f"  Found {len(sequence_folders)} sequence folders")

        # Track sequence names to prevent duplicates
        sequence_counts = defaultdict(int)

        for folder in sequence_folders:
            self.logger.info(f"  Analyzing: {folder.name}")

            # Identify sequence
            sequence_name, file_count, status = self.identify_sequence(folder)

            if sequence_name:
                sequence_counts[sequence_name] += 1

                # Check for duplicate
                if sequence_counts[sequence_name] > 1:
                    warning = f"Multiple folders match {sequence_name}"
                    self.logger.warning(f"    {warning}")
                    patient_result['warnings'].append(warning)
                    continue

                # Build new path
                new_folder_name = sequence_name
                new_path = main_folder / new_folder_name

                # Check if target already exists
                if new_path.exists() and new_path != folder:
                    warning = f"Target folder {new_folder_name} already exists"
                    self.logger.warning(f"    {warning}")
                    patient_result['warnings'].append(warning)
                    continue

                # Log the rename
                self.logger.info(f"    → {sequence_name} ({file_count} files) - {status}")

                patient_result['sequences_found'][sequence_name] = {
                    'original_folder': folder.name,
                    'file_count': file_count,
                    'status': status
                }

                # Perform rename if not dry run and folder needs renaming
                if not self.dry_run and folder.name != new_folder_name:
                    try:
                        folder.rename(new_path)
                        self.logger.info(f"    ✓ Renamed: {folder.name} → {new_folder_name}")

                        self.rename_log.append({
                            'patient_id': patient_id,
                            'original': str(folder),
                            'renamed': str(new_path),
                            'sequence': sequence_name,
                            'file_count': file_count
                        })

                    except Exception as e:
                        error = f"Failed to rename {folder.name}: {e}"
                        self.logger.error(f"    ✗ {error}")
                        patient_result['errors'].append(error)

            else:
                self.logger.info(f"    → Not matched ({file_count} files) - {status}")

        # Check for missing expected sequences
        expected_sequences = set(name for name, _, _ in self.sequence_mapping.values())
        found_sequences = set(patient_result['sequences_found'].keys())
        missing_sequences = expected_sequences - found_sequences

        if missing_sequences:
            warning = f"Missing sequences: {', '.join(sorted(missing_sequences))}"
            self.logger.warning(f"  {warning}")
            patient_result['warnings'].append(warning)

        return patient_result

    def run(self):
        """Run the folder renaming process"""
        mode = "DRY RUN" if self.dry_run else "LIVE RUN"
        self.logger.info(f"=" * 60)
        self.logger.info(f"DICOM Folder Renamer - {mode}")
        self.logger.info(f"=" * 60)
        self.logger.info(f"Base directory: {self.base_dir}")
        self.logger.info("")

        # Find patient folders
        patient_folders = self.find_patient_folders()

        if not patient_folders:
            self.logger.error("No patient folders found!")
            return

        # Process each patient
        for patient_folder in patient_folders:
            result = self.process_patient(patient_folder)
            self.results.append(result)

        # Generate summary
        self.generate_summary()

    def generate_summary(self):
        """Generate summary report"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("SUMMARY")
        self.logger.info("=" * 60)

        total_patients = len(self.results)
        patients_with_all_6 = sum(1 for r in self.results if len(r['sequences_found']) == 6)
        total_warnings = sum(len(r['warnings']) for r in self.results)
        total_errors = sum(len(r['errors']) for r in self.results)

        self.logger.info(f"Total patients processed: {total_patients}")
        self.logger.info(f"Patients with all 6 sequences: {patients_with_all_6}")
        self.logger.info(f"Total warnings: {total_warnings}")
        self.logger.info(f"Total errors: {total_errors}")

        if not self.dry_run:
            self.logger.info(f"Total folders renamed: {len(self.rename_log)}")

        # Save detailed results
        self.save_results()

    def save_results(self):
        """Save results to files"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save summary CSV
        summary_file = self.base_dir / f"renaming_summary_{timestamp}.csv"
        with open(summary_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Patient', 'T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE', 'Warnings', 'Errors'])

            for result in self.results:
                row = [result['patient_id']]

                for seq in ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']:
                    if seq in result['sequences_found']:
                        row.append(result['sequences_found'][seq]['file_count'])
                    else:
                        row.append('MISSING')

                row.append(len(result['warnings']))
                row.append(len(result['errors']))

                writer.writerow(row)

        self.logger.info(f"\nSummary saved to: {summary_file}")

        # Save detailed JSON
        json_file = self.base_dir / f"renaming_results_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        self.logger.info(f"Detailed results saved to: {json_file}")

        # Save rename log if not dry run
        if not self.dry_run and self.rename_log:
            log_file = self.base_dir / f"rename_log_{timestamp}.csv"
            with open(log_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['patient_id', 'sequence', 'original', 'renamed', 'file_count'])
                writer.writeheader()
                writer.writerows(self.rename_log)

            self.logger.info(f"Rename log saved to: {log_file}")


def main():
    parser = argparse.ArgumentParser(
        description='DICOM Folder Renamer - Identifies and renames sequence folders',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (safe, no changes)
  python dicom_folder_renamer.py /path/to/STAGE --dry-run

  # Live run (actually renames)
  python dicom_folder_renamer.py /path/to/STAGE --live

  # With custom base directory
  python dicom_folder_renamer.py ~/Projects/STAGE_Study/data/raw --live
        """
    )

    parser.add_argument(
        'base_dir',
        type=str,
        help='Base directory containing patient folders'
    )

    parser.add_argument(
        '--live',
        action='store_true',
        help='Actually perform renames (default is dry run)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode - show what would happen without making changes (default)'
    )

    args = parser.parse_args()

    # Resolve path
    base_dir = Path(args.base_dir).expanduser().resolve()

    if not base_dir.exists():
        print(f"Error: Directory not found: {base_dir}")
        sys.exit(1)

    # Determine mode (default is dry run)
    dry_run = not args.live  # If --live flag is set, dry_run = False

    # Run renamer
    renamer = DICOMFolderRenamer(base_dir, dry_run=dry_run)
    renamer.run()


if __name__ == '__main__':
    main()
