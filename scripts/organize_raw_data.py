#!/usr/bin/env python3
"""
STAGE Study - Organize Raw DICOM Data
======================================
Copies raw DICOM data and organizes it into standardized sequence folders.
Leaves original raw data completely untouched.

This script:
1. Scans data/raw/ for patient folders
2. Identifies DICOM sequences by reading headers
3. Copies and organizes into data/organized/PatientID/SequenceName/
4. Filters for axial-only images (6 sequences per patient)

Expected sequences:
- T1_conv, T1_STAGE, T2_conv, T2_STAGE, SWI_conv, SWI_STAGE

Usage:
    # Dry run (shows what will happen, no changes)
    python organize_raw_data.py --dry-run

    # Live run (copies and organizes data)
    python organize_raw_data.py --live
"""

import os
import sys
import argparse
import logging
import shutil
from pathlib import Path
from datetime import datetime
import pydicom
import csv
import json
from collections import defaultdict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class RawDataOrganizer:
    """Organizes raw DICOM data into standardized structure"""

    def __init__(self, raw_dir, organized_dir, dry_run=True):
        self.raw_dir = Path(raw_dir)
        self.organized_dir = Path(organized_dir)
        self.dry_run = dry_run
        self.logger = logging.getLogger(__name__)

        # Sequence mapping based on SeriesDescription
        self.sequence_mapping = {
            'T1 MPRAGE': ('T1_conv', 112, 30),
            'STAGE-T1W': ('T1_STAGE', 112, 30),
            'T2 AX': ('T2_conv', 42, 30),
            'T2w_STAGE': ('T2_STAGE', 112, 30),
            'SWI AX': ('SWI_conv', 88, 200),
            'SWI_STAGE': ('SWI_STAGE', 112, 900),
        }

        # Alternative patterns for matching
        self.alternative_patterns = {
            'T1_conv': ['T1 MPRAGE', 'T1_MPRAGE', 'MPRAGE'],
            'T1_STAGE': ['STAGE-T1W', 'STAGE_T1W', 'T1W_STAGE'],
            'T2_conv': ['T2 AX', 'T2_AX', 'T2 SPACE', 'FLAIR'],
            'T2_STAGE': ['T2w_STAGE', 'T2W_STAGE'],
            'SWI_conv': ['SWI AX', 'SWI_AX', 'SWI'],
            'SWI_STAGE': ['SWI_STAGE', 'STAGE-SWI'],
        }

        # Results tracking
        self.results = []
        self.copy_log = []

    def find_patient_folders(self):
        """Find all patient folders in raw directory"""
        patient_folders = []

        for item in self.raw_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Look for DICOM data indicators (DICOMDIR file or 1000* folders)
                has_dicomdir = (item / 'DICOMDIR').exists()
                has_1000_folders = bool(list(item.glob('1000*')))

                if has_dicomdir or has_1000_folders:
                    patient_folders.append(item)

        self.logger.info(f"Found {len(patient_folders)} patient folders in raw directory")
        return sorted(patient_folders)

    def find_dicom_folders(self, patient_folder):
        """Find all folders containing DICOM files for a patient"""
        dicom_folders = []

        # Look for 1000xxxx/1000yyyy/ structure (typical DICOM export)
        for subfolder in patient_folder.glob('1000*'):
            if subfolder.is_dir():
                # Check one level deeper
                for subsubfolder in subfolder.iterdir():
                    if subsubfolder.is_dir():
                        # Look for sequence folders inside
                        for seq_folder in subsubfolder.iterdir():
                            if seq_folder.is_dir() and not seq_folder.name.startswith('.'):
                                dicom_folders.append(seq_folder)

        return dicom_folders

    def read_dicom_header(self, dicom_file):
        """Read DICOM file and extract metadata"""
        try:
            ds = pydicom.dcmread(dicom_file, force=True, stop_before_pixels=True)

            return {
                'SeriesDescription': str(getattr(ds, 'SeriesDescription', '')),
                'SeriesNumber': str(getattr(ds, 'SeriesNumber', 'N/A')),
                'ImageType': str(getattr(ds, 'ImageType', 'N/A')),
                'ImageOrientationPatient': getattr(ds, 'ImageOrientationPatient', None),
                'PixelBandwidth': getattr(ds, 'PixelBandwidth', None),
                'FlipAngle': getattr(ds, 'FlipAngle', None),
                'EchoTime': getattr(ds, 'EchoTime', None),
                'RepetitionTime': getattr(ds, 'RepetitionTime', None),
                'Rows': getattr(ds, 'Rows', 0),
                'Columns': getattr(ds, 'Columns', 0),
            }
        except Exception as e:
            self.logger.debug(f"Error reading {dicom_file}: {e}")
            return None

    def is_axial_orientation(self, metadata):
        """Check if image is axial/transverse orientation"""
        orientation = metadata.get('ImageOrientationPatient')
        if orientation is None:
            return False

        try:
            # ImageOrientationPatient has 6 values: [row_x, row_y, row_z, col_x, col_y, col_z]
            # Axial images have dominant Z component in cross product
            import numpy as np
            row_vec = np.array(orientation[:3])
            col_vec = np.array(orientation[3:])
            cross = np.cross(row_vec, col_vec)

            # If Z component (cross[2]) has largest absolute value, it's axial
            return abs(cross[2]) > abs(cross[0]) and abs(cross[2]) > abs(cross[1])
        except:
            return False

    def identify_sequence(self, folder_path):
        """Identify sequence type by reading DICOM headers"""
        # Find DICOM files
        dicom_files = []
        for ext in ['', '.dcm', '.DCM', '.dicom', '.DICOM']:
            dicom_files.extend(list(folder_path.glob(f'*{ext}')))

        # Filter out non-DICOM files
        dicom_files = [f for f in dicom_files if f.is_file() and not f.name.startswith('.')]

        if not dicom_files:
            return None, 0, "No DICOM files found"

        file_count = len(dicom_files)

        # Read first DICOM file
        metadata = self.read_dicom_header(dicom_files[0])
        if metadata is None:
            return None, file_count, "Could not read DICOM header"

        series_desc = metadata['SeriesDescription']

        # Check if axial orientation
        if not self.is_axial_orientation(metadata):
            return None, file_count, f"Not axial: {series_desc}"

        # Match to known sequences
        for seq_name, patterns in self.alternative_patterns.items():
            for pattern in patterns:
                if pattern.lower() in series_desc.lower():
                    return seq_name, file_count, f"Matched: {series_desc}"

        return None, file_count, f"Unknown sequence: {series_desc}"

    def copy_dicom_folder(self, source_folder, dest_folder):
        """Copy DICOM folder to organized directory"""
        try:
            if dest_folder.exists():
                self.logger.warning(f"      Destination exists, skipping: {dest_folder.name}")
                return False

            # Create parent directory
            dest_folder.parent.mkdir(parents=True, exist_ok=True)

            # Copy entire folder
            shutil.copytree(source_folder, dest_folder)

            return True

        except Exception as e:
            self.logger.error(f"      ✗ Error copying folder: {e}")
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

        # Find all DICOM folders
        dicom_folders = self.find_dicom_folders(patient_folder)

        if not dicom_folders:
            error = "No DICOM folders found"
            self.logger.error(f"  {error}")
            patient_result['errors'].append(error)
            return patient_result

        self.logger.info(f"  Found {len(dicom_folders)} potential sequence folders")

        # Track sequence names to prevent duplicates
        sequence_counts = defaultdict(int)

        for folder in dicom_folders:
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

                self.logger.info(f"  {folder.name} → {sequence_name} ({file_count} files)")

                # Build destination path
                dest_path = self.organized_dir / patient_id / sequence_name

                patient_result['sequences_found'][sequence_name] = {
                    'source_folder': str(folder),
                    'dest_folder': str(dest_path),
                    'file_count': file_count,
                    'status': status
                }

                # Copy if not dry run
                if not self.dry_run:
                    if self.copy_dicom_folder(folder, dest_path):
                        self.logger.info(f"    ✓ Copied to: {dest_path}")

                        self.copy_log.append({
                            'patient_id': patient_id,
                            'sequence': sequence_name,
                            'source': str(folder),
                            'destination': str(dest_path),
                            'file_count': file_count
                        })
                    else:
                        error = f"Failed to copy {sequence_name}"
                        patient_result['errors'].append(error)
            else:
                self.logger.debug(f"  {folder.name} → Not matched ({file_count} files) - {status}")

        # Check for missing expected sequences
        expected_sequences = set(['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE'])
        found_sequences = set(patient_result['sequences_found'].keys())
        missing_sequences = expected_sequences - found_sequences

        if missing_sequences:
            warning = f"Missing sequences: {', '.join(sorted(missing_sequences))}"
            self.logger.warning(f"  {warning}")
            patient_result['warnings'].append(warning)

        return patient_result

    def run(self):
        """Run the organization process"""
        mode = "DRY RUN" if self.dry_run else "LIVE RUN"
        self.logger.info("=" * 60)
        self.logger.info(f"STAGE Study - Organize Raw Data - {mode}")
        self.logger.info("=" * 60)
        self.logger.info(f"Raw directory: {self.raw_dir}")
        self.logger.info(f"Organized directory: {self.organized_dir}")
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
        total_sequences = sum(len(r['sequences_found']) for r in self.results)
        total_warnings = sum(len(r['warnings']) for r in self.results)
        total_errors = sum(len(r['errors']) for r in self.results)

        self.logger.info(f"Total patients processed: {total_patients}")
        self.logger.info(f"Patients with all 6 sequences: {patients_with_all_6}")
        self.logger.info(f"Total sequences identified: {total_sequences}")
        self.logger.info(f"Total warnings: {total_warnings}")
        self.logger.info(f"Total errors: {total_errors}")

        if not self.dry_run:
            self.logger.info(f"Total folders copied: {len(self.copy_log)}")

        # Save results
        if not self.dry_run:
            self.save_results()

    def save_results(self):
        """Save results to files"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = self.organized_dir.parent

        # Save summary CSV
        summary_file = output_dir / f"organization_summary_{timestamp}.csv"
        with open(summary_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Patient', 'T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE',
                           'SWI_conv', 'SWI_STAGE', 'Warnings', 'Errors'])

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
        json_file = output_dir / f"organization_results_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        self.logger.info(f"Detailed results saved to: {json_file}")

        # Save copy log
        if self.copy_log:
            log_file = output_dir / f"copy_log_{timestamp}.csv"
            with open(log_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['patient_id', 'sequence',
                                                       'source', 'destination', 'file_count'])
                writer.writeheader()
                writer.writerows(self.copy_log)

            self.logger.info(f"Copy log saved to: {log_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Organize raw DICOM data into standardized structure',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (safe, shows what will happen)
  python organize_raw_data.py --dry-run

  # Live run (actually copies and organizes data)
  python organize_raw_data.py --live

  # Custom directories
  python organize_raw_data.py --raw-dir ~/data/raw --organized-dir ~/data/organized --live
        """
    )

    parser.add_argument(
        '--raw-dir',
        type=str,
        default='~/Projects/STAGE_Study/data/raw',
        help='Raw DICOM data directory (default: ~/Projects/STAGE_Study/data/raw)'
    )

    parser.add_argument(
        '--organized-dir',
        type=str,
        default='~/Projects/STAGE_Study/data/organized',
        help='Organized output directory (default: ~/Projects/STAGE_Study/data/organized)'
    )

    parser.add_argument(
        '--live',
        action='store_true',
        help='Actually perform copies (default is dry run)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode - show what would happen without making changes (default)'
    )

    args = parser.parse_args()

    # Resolve paths
    raw_dir = Path(args.raw_dir).expanduser().resolve()
    organized_dir = Path(args.organized_dir).expanduser().resolve()

    if not raw_dir.exists():
        print(f"Error: Raw directory not found: {raw_dir}")
        sys.exit(1)

    # Determine mode (default is dry run)
    dry_run = not args.live

    # Run organizer
    organizer = RawDataOrganizer(raw_dir, organized_dir, dry_run=dry_run)
    organizer.run()


if __name__ == '__main__':
    main()
