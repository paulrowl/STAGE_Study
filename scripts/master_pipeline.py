#!/usr/bin/env python3
"""
STAGE MRI Study - Master Pipeline Script
==========================================
Complete automated pipeline from raw DICOM data to final analysis results.

Usage:
    # Create configuration file
    python master_pipeline.py --create-config

    # Run with configuration
    python master_pipeline.py --config config.yaml

    # Dry run (check only, no processing)
    python master_pipeline.py --config config.yaml --dry-run
"""

import os
import sys
import argparse
import logging
import yaml
from pathlib import Path
from datetime import datetime
import subprocess
import shutil

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class PipelineRunner:
    """Master pipeline orchestrator"""

    def __init__(self, config_path, dry_run=False):
        self.config_path = Path(config_path)
        self.dry_run = dry_run
        self.logger = logging.getLogger(__name__)

        # Load configuration
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Setup paths
        self.base_dir = Path(self.config['base_dir']).expanduser()
        self.output_dir = Path(self.config['output_dir']).expanduser()

        # Create output directories
        self.output_dirs = {
            'nifti': self.output_dir / 'nifti',
            'brain_masks': self.output_dir / 'brain_masks',
            'registered': self.output_dir / 'registered',
            'segmentations': self.output_dir / 'segmentations',
            'metrics': self.output_dir / 'metrics',
            'statistics': self.output_dir / 'statistics',
            'logs': self.output_dir / 'logs',
            'report': self.output_dir / 'report',
        }

    def check_dependencies(self):
        """Check if all required tools are installed"""
        self.logger.info("=" * 60)
        self.logger.info("Checking Dependencies")
        self.logger.info("=" * 60)

        dependencies = {
            'dcm2niix': {'required': True, 'install': 'brew install dcm2niix'},
            'python': {'required': True, 'install': 'Already installed'},
        }

        # Check Python packages
        python_packages = {
            'numpy': 'pip install numpy',
            'pandas': 'pip install pandas',
            'nibabel': 'pip install nibabel',
            'pydicom': 'pip install pydicom',
            'ants': 'pip install antspyx',
        }

        missing = []
        warnings = []

        # Check command-line tools
        for tool, info in dependencies.items():
            if shutil.which(tool):
                self.logger.info(f"✓ {tool}: Found")
            else:
                self.logger.error(f"✗ {tool}: Not found")
                missing.append(f"{tool} (install: {info['install']})")

        # Check Python packages
        for package, install_cmd in python_packages.items():
            try:
                __import__(package)
                self.logger.info(f"✓ {package}: Installed")
            except ImportError:
                self.logger.warning(f"⚠ {package}: Not installed")
                warnings.append(f"{package} (install: {install_cmd})")

        # Check for HD-BET
        try:
            result = subprocess.run(['which', 'hd-bet'], capture_output=True, text=True)
            if result.returncode == 0:
                self.logger.info("✓ HD-BET: Found")
            else:
                self.logger.warning("⚠ HD-BET: Not found")
                warnings.append("HD-BET (install: pip install HD-BET)")
        except:
            self.logger.warning("⚠ HD-BET: Not found")
            warnings.append("HD-BET (install: pip install HD-BET)")

        # Check for SynthSeg
        try:
            result = subprocess.run(['which', 'mri_synthseg'], capture_output=True, text=True)
            if result.returncode == 0:
                self.logger.info("✓ SynthSeg: Found")
            else:
                self.logger.warning("⚠ SynthSeg: Not found")
                warnings.append("SynthSeg (install: pip install SynthSeg)")
        except:
            self.logger.warning("⚠ SynthSeg: Not found")
            warnings.append("SynthSeg (install: pip install SynthSeg)")

        # Summary
        self.logger.info("")
        if missing:
            self.logger.error("CRITICAL: Missing required dependencies:")
            for item in missing:
                self.logger.error(f"  - {item}")
            return False

        if warnings:
            self.logger.warning("WARNING: Missing optional dependencies:")
            for item in warnings:
                self.logger.warning(f"  - {item}")
            self.logger.warning("\nSome pipeline steps may fail without these.")

        self.logger.info("\nDependency check complete!")
        return True

    def check_data_structure(self):
        """Verify data is organized correctly"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("Checking Data Structure")
        self.logger.info("=" * 60)

        if not self.base_dir.exists():
            self.logger.error(f"Base directory not found: {self.base_dir}")
            return False

        # Find patient folders
        patient_folders = [d for d in self.base_dir.iterdir() if d.is_dir()]

        if not patient_folders:
            self.logger.error(f"No patient folders found in {self.base_dir}")
            return False

        self.logger.info(f"Found {len(patient_folders)} patient folders")

        # Check first patient for sequence structure
        test_patient = patient_folders[0]
        expected_sequences = ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']

        found_sequences = [s for s in expected_sequences if (test_patient / s).exists()]

        self.logger.info(f"\nChecking {test_patient.name}:")
        for seq in expected_sequences:
            seq_path = test_patient / seq
            if seq_path.exists():
                file_count = len(list(seq_path.iterdir()))
                self.logger.info(f"  ✓ {seq}: {file_count} files")
            else:
                self.logger.warning(f"  ✗ {seq}: Not found")

        if len(found_sequences) == 0:
            self.logger.error("\nNo organized sequences found!")
            self.logger.error("Please run DICOM organization first:")
            self.logger.error("  python scripts/dicom_folder_renamer.py data/raw --live")
            return False

        return True

    def create_output_directories(self):
        """Create output directory structure"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("Creating Output Directories")
        self.logger.info("=" * 60)

        for name, path in self.output_dirs.items():
            if not self.dry_run:
                path.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"✓ Created: {path}")
            else:
                self.logger.info(f"  Would create: {path}")

    def find_patients(self):
        """Find all patient folders to process"""
        patient_folders = []

        for item in self.base_dir.iterdir():
            if item.is_dir():
                # Check if it has sequence folders
                expected_sequences = ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']
                found_sequences = [s for s in expected_sequences if (item / s).exists()]

                if found_sequences:
                    patient_folders.append(item)

        return sorted(patient_folders)

    def convert_dicom_to_nifti(self, dicom_dir, output_dir, output_name):
        """Convert DICOM directory to NIfTI using dcm2niix"""
        try:
            # Create output directory
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Run dcm2niix
            # -f: output filename
            # -o: output directory
            # -z y: compress output (.nii.gz)
            # -b n: don't create BIDS sidecar
            # -s n: don't convert single file
            cmd = [
                'dcm2niix',
                '-f', output_name,
                '-o', str(output_dir),
                '-z', 'y',  # Compress
                '-b', 'n',  # No BIDS
                '-s', 'n',  # No single file mode
                str(dicom_dir)
            ]

            self.logger.info(f"      Running: dcm2niix on {dicom_dir.name}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                # Find the created NIfTI file
                nifti_files = list(output_dir.glob(f'{output_name}*.nii.gz'))
                if nifti_files:
                    self.logger.info(f"      ✓ Created: {nifti_files[0].name}")
                    return nifti_files[0]
                else:
                    self.logger.warning(f"      ⚠ Conversion completed but no output file found")
                    return None
            else:
                self.logger.error(f"      ✗ dcm2niix failed: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            self.logger.error(f"      ✗ Conversion timed out (>5 min)")
            return None
        except Exception as e:
            self.logger.error(f"      ✗ Error during conversion: {e}")
            return None

    def process_patient(self, patient_folder):
        """Process a single patient through the pipeline"""
        patient_id = patient_folder.name
        self.logger.info("\n" + "=" * 60)
        self.logger.info(f"Processing Patient: {patient_id}")
        self.logger.info("=" * 60)

        sequence_pairs = [
            ('T1_conv', 'T1_STAGE'),
            ('T2_conv', 'T2_STAGE'),
            ('SWI_conv', 'SWI_STAGE'),
        ]

        for conv_seq, stage_seq in sequence_pairs:
            conv_path = patient_folder / conv_seq
            stage_path = patient_folder / stage_seq

            if not conv_path.exists() or not stage_path.exists():
                self.logger.warning(f"  Skipping {conv_seq}/{stage_seq} (missing data)")
                continue

            self.logger.info(f"\n  Processing: {conv_seq} vs {stage_seq}")

            # Step 1: DICOM to NIfTI conversion
            self.logger.info(f"    Step 1: DICOM → NIfTI conversion")
            if self.dry_run:
                self.logger.info(f"      Would convert: {conv_path}")
                self.logger.info(f"      Would convert: {stage_path}")
            else:
                # Create patient output directory
                patient_nifti_dir = self.output_dirs['nifti'] / patient_id

                # Convert conventional sequence
                conv_nifti = self.convert_dicom_to_nifti(
                    dicom_dir=conv_path,
                    output_dir=patient_nifti_dir,
                    output_name=conv_seq
                )

                # Convert STAGE sequence
                stage_nifti = self.convert_dicom_to_nifti(
                    dicom_dir=stage_path,
                    output_dir=patient_nifti_dir,
                    output_name=stage_seq
                )

                if conv_nifti and stage_nifti:
                    self.logger.info(f"      ✓ Both sequences converted successfully")
                else:
                    self.logger.warning(f"      ⚠ One or both conversions failed")
                    continue

            # Step 2: Brain extraction
            self.logger.info(f"    Step 2: Brain extraction (HD-BET)")
            if self.dry_run:
                self.logger.info(f"      Would extract brain from both sequences")
            else:
                self.logger.info(f"      [NOT IMPLEMENTED] Need HD-BET")

            # Step 3: Registration
            self.logger.info(f"    Step 3: Co-registration (ANTs)")
            if self.dry_run:
                self.logger.info(f"      Would register {stage_seq} → {conv_seq}")
            else:
                self.logger.info(f"      [NOT IMPLEMENTED] Need ANTs")

            # Step 4: Tissue segmentation
            self.logger.info(f"    Step 4: Tissue segmentation (SynthSeg)")
            if self.dry_run:
                self.logger.info(f"      Would segment into GM/WM/CSF")
            else:
                self.logger.info(f"      [NOT IMPLEMENTED] Need SynthSeg")

            # Step 5: Metrics calculation
            self.logger.info(f"    Step 5: Calculate metrics")
            if self.dry_run:
                self.logger.info(f"      Would calculate 60+ metrics")
            else:
                self.logger.info(f"      [NOT IMPLEMENTED] Need implementation")

        self.logger.info(f"\n  Patient {patient_id} complete!")

    def run(self):
        """Run the complete pipeline"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("STAGE MRI Analysis Pipeline")
        self.logger.info("=" * 60)

        mode = "DRY RUN" if self.dry_run else "LIVE RUN"
        self.logger.info(f"Mode: {mode}")
        self.logger.info(f"Config: {self.config_path}")
        self.logger.info(f"Base directory: {self.base_dir}")
        self.logger.info(f"Output directory: {self.output_dir}")
        self.logger.info("")

        # Check dependencies
        if not self.check_dependencies():
            self.logger.error("\nCannot proceed: missing critical dependencies")
            self.logger.error("Please install required tools and try again.")
            return

        # Check data structure
        if not self.check_data_structure():
            self.logger.error("\nCannot proceed: data not organized")
            return

        # Create output directories
        self.create_output_directories()

        # Find patients to process
        patients = self.find_patients()

        # Allow limiting to specific patients
        if 'patients' in self.config and self.config['patients']:
            patients = [p for p in patients if p.name in self.config['patients']]

        self.logger.info(f"\nWill process {len(patients)} patient(s)")

        # Process each patient
        for patient_folder in patients:
            try:
                self.process_patient(patient_folder)
            except Exception as e:
                self.logger.error(f"Error processing {patient_folder.name}: {e}")
                if not self.dry_run:
                    continue

        self.logger.info("\n" + "=" * 60)
        self.logger.info("Pipeline Complete!")
        self.logger.info("=" * 60)


def create_config_template(output_path='config.yaml'):
    """Create a configuration file template"""
    config = {
        'base_dir': '~/Projects/STAGE_Study/data/raw/organized',
        'output_dir': '~/Projects/STAGE_Study/output',
        'device': 'cpu',  # 'cpu' or 'cuda' (most Macs use cpu)
        'num_parallel': 2,  # Number of parallel processes
        'patients': [],  # Empty = process all, or list specific patient IDs like ['Anon42647']
    }

    with open(output_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print(f"Configuration template created: {output_path}")
    print("\nEdit this file to customize:")
    print("  - base_dir: Path to organized DICOM data")
    print("  - output_dir: Where to save results")
    print("  - patients: Leave empty to process all, or specify patient IDs")
    print("\nExample to process one patient:")
    print("  patients: ['Anon42647']")


def main():
    parser = argparse.ArgumentParser(
        description='STAGE MRI Analysis - Master Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file (YAML)'
    )

    parser.add_argument(
        '--create-config',
        action='store_true',
        help='Create a configuration file template'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run - check dependencies and data structure only'
    )

    args = parser.parse_args()

    if args.create_config:
        create_config_template()
        return

    if not args.config:
        print("Error: --config required (or use --create-config)")
        print("\nUsage:")
        print("  python master_pipeline.py --create-config")
        print("  python master_pipeline.py --config config.yaml --dry-run")
        print("  python master_pipeline.py --config config.yaml")
        sys.exit(1)

    # Run pipeline
    runner = PipelineRunner(args.config, dry_run=args.dry_run)
    runner.run()


if __name__ == '__main__':
    main()
