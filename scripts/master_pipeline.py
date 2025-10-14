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

    def apply_brain_mask(self, input_nifti, mask_file, output_file):
        """Apply brain mask to create skull-stripped image"""
        try:
            import nibabel as nib
            import numpy as np

            # Load input image and mask
            img = nib.load(input_nifti)
            mask = nib.load(mask_file)

            # Get data
            img_data = img.get_fdata()
            mask_data = mask.get_fdata()

            # Apply mask
            brain_data = img_data * mask_data

            # Create new NIfTI image
            brain_img = nib.Nifti1Image(brain_data, img.affine, img.header)

            # Save
            nib.save(brain_img, output_file)

            return True

        except Exception as e:
            self.logger.error(f"      ✗ Error applying mask: {e}")
            return False

    def register_images_ants(self, fixed_img, moving_img, output_dir, output_name):
        """Register moving image to fixed image using ANTs (rigid transformation)"""
        try:
            import ants

            # Create output directory
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Output files
            registered_output = output_dir / f"{output_name}_registered.nii.gz"
            transform_prefix = output_dir / f"{output_name}_transform_"

            self.logger.info(f"      Running: ANTs registration")
            self.logger.info(f"        Fixed: {fixed_img.name}")
            self.logger.info(f"        Moving: {moving_img.name}")

            # Load images with ANTsPy
            fixed = ants.image_read(str(fixed_img))
            moving = ants.image_read(str(moving_img))

            # Perform rigid registration
            # type_of_transform: 'Rigid' for within-patient registration
            # metric: 'MI' (Mutual Information) works well for multi-modal registration
            registration = ants.registration(
                fixed=fixed,
                moving=moving,
                type_of_transform='Rigid',
                metric='MI',
                verbose=False
            )

            # Save registered image
            ants.image_write(registration['warpedmovout'], str(registered_output))
            self.logger.info(f"      ✓ Registered image: {registered_output.name}")

            # Save transformation matrix
            # ANTs saves transforms automatically with specific names
            # We'll just return the registered image
            return registered_output

        except ImportError:
            self.logger.error(f"      ✗ ANTsPy not installed (pip install antspyx)")
            return None
        except Exception as e:
            self.logger.error(f"      ✗ Error during registration: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return None

    def calculate_metrics(self, conv_img, stage_img, output_dir, comparison_name):
        """Calculate comprehensive metrics between conventional and STAGE images"""
        try:
            import nibabel as nib
            import numpy as np
            from scipy import stats
            from skimage.metrics import structural_similarity as ssim
            import pandas as pd

            # Create output directory
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            self.logger.info(f"      Calculating metrics...")

            # Load images
            conv_data = nib.load(conv_img).get_fdata()
            stage_data = nib.load(stage_img).get_fdata()

            # Create brain mask (exclude background zeros)
            brain_mask = (conv_data > 0) & (stage_data > 0)

            # Extract brain voxels only
            conv_brain = conv_data[brain_mask]
            stage_brain = stage_data[brain_mask]

            # Initialize metrics dictionary
            metrics = {
                'comparison': comparison_name,
                'num_voxels': int(np.sum(brain_mask))
            }

            # 1. Basic statistics
            metrics['conv_mean'] = float(np.mean(conv_brain))
            metrics['conv_std'] = float(np.std(conv_brain))
            metrics['conv_median'] = float(np.median(conv_brain))
            metrics['stage_mean'] = float(np.mean(stage_brain))
            metrics['stage_std'] = float(np.std(stage_brain))
            metrics['stage_median'] = float(np.median(stage_brain))

            # 2. Correlation metrics
            metrics['pearson_r'], metrics['pearson_p'] = stats.pearsonr(conv_brain, stage_brain)
            metrics['spearman_r'], metrics['spearman_p'] = stats.spearmanr(conv_brain, stage_brain)

            # 3. Normalized Cross-Correlation (NCC)
            conv_norm = (conv_brain - np.mean(conv_brain)) / np.std(conv_brain)
            stage_norm = (stage_brain - np.mean(stage_brain)) / np.std(stage_brain)
            metrics['ncc'] = float(np.mean(conv_norm * stage_norm))

            # 4. Mutual Information (MI)
            # Compute 2D histogram
            hist_2d, x_edges, y_edges = np.histogram2d(conv_brain, stage_brain, bins=50)
            pxy = hist_2d / float(np.sum(hist_2d))
            px = np.sum(pxy, axis=1)
            py = np.sum(pxy, axis=0)

            # Calculate MI
            px_py = px[:, None] * py[None, :]
            nzs = pxy > 0  # Only non-zero entries
            metrics['mutual_information'] = float(np.sum(pxy[nzs] * np.log(pxy[nzs] / px_py[nzs])))

            # 5. Structural Similarity Index (SSIM)
            # SSIM requires same range, so normalize
            conv_norm_img = (conv_data - np.min(conv_data)) / (np.max(conv_data) - np.min(conv_data))
            stage_norm_img = (stage_data - np.min(stage_data)) / (np.max(stage_data) - np.min(stage_data))

            # Calculate SSIM on 2D slices (middle third of volume)
            depth = conv_norm_img.shape[2]
            start_slice = depth // 3
            end_slice = 2 * depth // 3
            ssim_values = []

            for z in range(start_slice, end_slice):
                if np.sum(brain_mask[:, :, z]) > 100:  # Only slices with enough brain
                    ssim_val = ssim(conv_norm_img[:, :, z], stage_norm_img[:, :, z],
                                   data_range=1.0)
                    ssim_values.append(ssim_val)

            metrics['ssim_mean'] = float(np.mean(ssim_values)) if ssim_values else 0.0
            metrics['ssim_std'] = float(np.std(ssim_values)) if ssim_values else 0.0

            # 6. Mean Absolute Error (MAE) and Root Mean Square Error (RMSE)
            mae = np.mean(np.abs(conv_brain - stage_brain))
            rmse = np.sqrt(np.mean((conv_brain - stage_brain) ** 2))
            metrics['mae'] = float(mae)
            metrics['rmse'] = float(rmse)
            metrics['nrmse'] = float(rmse / (np.max(conv_brain) - np.min(conv_brain)))  # Normalized RMSE

            # 7. Peak Signal-to-Noise Ratio (PSNR)
            max_val = max(np.max(conv_brain), np.max(stage_brain))
            if rmse > 0:
                metrics['psnr'] = float(20 * np.log10(max_val / rmse))
            else:
                metrics['psnr'] = float('inf')

            # 8. Signal-to-Noise Ratio (SNR)
            # Estimate noise from background
            background_mask = (conv_data == 0) | (stage_data == 0)
            if np.sum(background_mask) > 1000:
                conv_noise = np.std(conv_data[background_mask])
                stage_noise = np.std(stage_data[background_mask])
            else:
                # Estimate noise from signal
                conv_noise = np.std(conv_brain) * 0.1
                stage_noise = np.std(stage_brain) * 0.1

            metrics['conv_snr'] = float(np.mean(conv_brain) / conv_noise) if conv_noise > 0 else 0
            metrics['stage_snr'] = float(np.mean(stage_brain) / stage_noise) if stage_noise > 0 else 0

            # 9. Contrast-to-Noise Ratio (CNR)
            # Use upper and lower quartiles as "tissues"
            conv_upper = np.percentile(conv_brain, 75)
            conv_lower = np.percentile(conv_brain, 25)
            stage_upper = np.percentile(stage_brain, 75)
            stage_lower = np.percentile(stage_brain, 25)

            metrics['conv_cnr'] = float(abs(conv_upper - conv_lower) / conv_noise) if conv_noise > 0 else 0
            metrics['stage_cnr'] = float(abs(stage_upper - stage_lower) / stage_noise) if stage_noise > 0 else 0

            # 10. Coefficient of Variation (CV)
            metrics['conv_cv'] = float(metrics['conv_std'] / metrics['conv_mean']) if metrics['conv_mean'] > 0 else 0
            metrics['stage_cv'] = float(metrics['stage_std'] / metrics['stage_mean']) if metrics['stage_mean'] > 0 else 0

            # Save metrics to CSV
            metrics_file = output_dir / f"{comparison_name}_metrics.csv"
            df = pd.DataFrame([metrics])
            df.to_csv(metrics_file, index=False)

            self.logger.info(f"      ✓ Metrics calculated and saved")
            self.logger.info(f"        SSIM: {metrics['ssim_mean']:.4f}, NCC: {metrics['ncc']:.4f}, Pearson r: {metrics['pearson_r']:.4f}")

            return metrics

        except ImportError as e:
            self.logger.error(f"      ✗ Missing Python package: {e}")
            return None
        except Exception as e:
            self.logger.error(f"      ✗ Error calculating metrics: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return None

    def extract_brain_hdbet(self, input_nifti, output_dir, output_name):
        """Extract brain using HD-BET"""
        try:
            # Create output directory
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Output files (without extension - HD-BET adds it)
            brain_output_base = output_dir / f"{output_name}_brain"
            brain_output = output_dir / f"{output_name}_brain.nii.gz"
            mask_output = output_dir / f"{output_name}_mask.nii.gz"

            # Get device from config
            device = self.config.get('device', 'cpu')

            self.logger.info(f"      Running: HD-BET on {input_nifti.name} (device: {device})")

            # Run HD-BET via Python module
            # Import here to avoid issues if not installed
            from HD_BET.run import run_hd_bet

            run_hd_bet(
                mri_fnames=str(input_nifti),
                output_fnames=str(brain_output_base),
                mode='fast',  # 'fast' or 'accurate'
                device=device,  # 'cpu' or GPU device number (0, 1, etc.)
                postprocess=False,
                do_tta=False,  # Test time augmentation
                keep_mask=True,
                overwrite=True
            )

            # HD-BET creates mask with truncated name - find it
            # Pattern: HD-BET shortens long filenames (typically to ~7 chars before _mask)
            mask_files = list(output_dir.glob('*_mask.nii.gz'))
            potential_mask = None

            # Sort by modification time (most recent first) to get the one we just created
            mask_files_sorted = sorted(mask_files, key=lambda x: x.stat().st_mtime, reverse=True)

            for mf in mask_files_sorted:
                # Check if this mask is from the current run (matches output_name prefix)
                # HD-BET truncates long names, so check if output_name starts with mask name prefix
                mask_base = mf.name.replace('_mask.nii.gz', '')  # Remove _mask.nii.gz from filename
                if output_name.startswith(mask_base):
                    potential_mask = mf
                    break

            if potential_mask and potential_mask.exists():
                # Rename to standardized name
                if potential_mask != mask_output:
                    potential_mask.rename(mask_output)

                self.logger.info(f"      ✓ Mask created: {mask_output.name}")

                # Apply mask to create brain-extracted image
                if self.apply_brain_mask(input_nifti, mask_output, brain_output):
                    self.logger.info(f"      ✓ Brain extracted: {brain_output.name}")
                    return brain_output, mask_output
                else:
                    return None, mask_output
            else:
                self.logger.warning(f"      ⚠ HD-BET completed but no mask found")
                return None, None

        except ImportError:
            self.logger.error(f"      ✗ HD-BET not installed (pip install HD-BET)")
            return None, None
        except Exception as e:
            self.logger.error(f"      ✗ Error during brain extraction: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return None, None

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
                # Create patient output directory
                patient_brain_dir = self.output_dirs['brain_masks'] / patient_id

                # Extract brain from conventional sequence
                conv_brain, conv_mask = self.extract_brain_hdbet(
                    input_nifti=conv_nifti,
                    output_dir=patient_brain_dir,
                    output_name=conv_seq
                )

                # Extract brain from STAGE sequence
                stage_brain, stage_mask = self.extract_brain_hdbet(
                    input_nifti=stage_nifti,
                    output_dir=patient_brain_dir,
                    output_name=stage_seq
                )

                if conv_brain and stage_brain:
                    self.logger.info(f"      ✓ Both brains extracted successfully")
                else:
                    self.logger.warning(f"      ⚠ One or both extractions failed")
                    continue

            # Step 3: Registration
            self.logger.info(f"    Step 3: Co-registration (ANTs)")
            if self.dry_run:
                self.logger.info(f"      Would register {stage_seq} → {conv_seq}")
            else:
                # Create patient output directory
                patient_reg_dir = self.output_dirs['registered'] / patient_id

                # Register STAGE brain to conventional brain
                stage_registered = self.register_images_ants(
                    fixed_img=conv_brain,
                    moving_img=stage_brain,
                    output_dir=patient_reg_dir,
                    output_name=f"{stage_seq}_to_{conv_seq}"
                )

                if stage_registered:
                    self.logger.info(f"      ✓ Registration successful")
                else:
                    self.logger.warning(f"      ⚠ Registration failed")
                    continue

            # Step 4: Tissue segmentation (SKIPPED for now)
            # Note: Tissue segmentation (GM/WM/CSF) would be useful for tissue-specific
            # metrics, but the global metrics below work on brain-extracted images
            self.logger.info(f"    Step 4: Tissue segmentation (SKIPPED - not required for basic metrics)")

            # Step 5: Metrics calculation
            self.logger.info(f"    Step 5: Calculate metrics")
            if self.dry_run:
                self.logger.info(f"      Would calculate comprehensive metrics")
            else:
                # Create patient output directory
                patient_metrics_dir = self.output_dirs['metrics'] / patient_id

                # Calculate metrics between conventional and registered STAGE
                metrics = self.calculate_metrics(
                    conv_img=conv_brain,
                    stage_img=stage_registered,
                    output_dir=patient_metrics_dir,
                    comparison_name=f"{patient_id}_{conv_seq}_vs_{stage_seq}"
                )

                if metrics:
                    self.logger.info(f"      ✓ Metrics calculation complete")
                else:
                    self.logger.warning(f"      ⚠ Metrics calculation failed")

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
