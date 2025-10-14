#!/usr/bin/env python3
"""
DICOM Sequence Classifier for STAGE Study
Identifies and organizes MRI sequences based on DICOM properties
"""

import os
import sys
import json
import shutil
import logging
from pathlib import Path
from collections import defaultdict
import pydicom
import pandas as pd
from datetime import datetime

class DICOMSequenceClassifier:
    """
    Classifies MRI sequences based on DICOM properties:
    - SeriesDescription
    - PixelBandwidth
    - PixelData (presence/size)
    - PixelRepresentation
    """
    
    def __init__(self, base_dir, output_dir=None, dry_run=True, min_images=30,
                 exclude_t1_stage_variants=True):
        self.base_dir = Path(base_dir)
        self.output_dir = Path(output_dir) if output_dir else self.base_dir / "organized"
        self.dry_run = dry_run
        self.min_images = min_images
        self.exclude_t1_stage_variants = exclude_t1_stage_variants
        
        # Setup logging (console only)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Define sequence signatures based on DICOM properties
        self.sequence_signatures = {
            'T1_conv': {
                'series_desc_patterns': ['T1 MPRAGE SAG NON-SEL', 'T1 MPRAGE', 'MPRAGE'],
                'pixel_bandwidth_range': (150, 250),
                'pixel_representation': 0,
                'expected_slices': (100, 120)
            },
            'T1_STAGE': {
                'series_desc_patterns': ['STAGE-T1W', 'STAGE T1', 'T1W_STAGE'],
                'pixel_bandwidth_range': (150, 300),
                'pixel_representation': 0,
                'expected_slices': (100, 120)
            },
            'PD_STAGE': {
                'series_desc_patterns': ['STAGE-PDW', 'STAGE PD', 'PDW_STAGE'],
                'pixel_bandwidth_range': (150, 300),
                'pixel_representation': 0,
                'expected_slices': (100, 120)
            },
            'T2_conv': {
                'series_desc_patterns': ['T2 AX 3mm', 'T2 AX', 'T2 AXIAL', 't2_space', 'T2_SPACE', 'FLAIR'],
                'pixel_bandwidth_range': (150, 350),
                'pixel_representation': 0,
                'expected_slices': (35, 180)
            },
            'T2_STAGE': {
                'series_desc_patterns': ['STAGE-T2W', 'T2w_STAGE'],  # Includes derived T2w from PD_STAGE
                'pixel_bandwidth_range': (200, 350),
                'pixel_representation': [0, 1],  # Can be primary (0) or derived (1)
                'expected_slices': (100, 120)
            },
            'SWI_conv': {
                'series_desc_patterns': ['SWI AX_SWI', 'SWI AX', 'SWI'],
                'pixel_bandwidth_range': (100, 200),
                'pixel_representation': 0,
                'expected_slices': (80, 100)
            },
            'SWI_STAGE': {
                'series_desc_patterns': ['SWI_STAGE', 'STAGE SWI', 'SWI_Ax_STAGE'],
                'pixel_bandwidth_range': (200, 350),
                'pixel_representation': 1,  # Derived images often use signed pixels
                'expected_slices': (1, 120)  # May be small derived products
            }
        }
        
        self.results = []
        self.summary = defaultdict(int)
    
    def find_subject_folders(self):
        """Find all subject folders in the base directory"""
        subject_folders = []
        
        for item in self.base_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                subject_folders.append(item)
        
        self.logger.info(f"Found {len(subject_folders)} subject folders")
        return sorted(subject_folders)
    
    def find_sequence_folders(self, subject_dir):
        """
        Navigate: subject_ID/1000xxxxx/1000xxxxx/sequence_folders
        Returns list of sequence folder paths
        """
        sequence_folders = []
        
        # Find folders starting with "1000" at first level
        level1_folders = [f for f in subject_dir.iterdir() 
                         if f.is_dir() and f.name.startswith('1000')]
        
        for level1 in level1_folders:
            # Find folders starting with "1000" at second level
            level2_folders = [f for f in level1.iterdir() 
                            if f.is_dir() and f.name.startswith('1000')]
            
            for level2 in level2_folders:
                # Get all folders at third level (sequence folders)
                seq_folders = [f for f in level2.iterdir() 
                              if f.is_dir() and not f.name.startswith('.')]
                sequence_folders.extend(seq_folders)
        
        return sequence_folders
    
    def is_axial_orientation(self, ds):
        """
        Check if image is in axial/transverse orientation
        Returns True if axial, False otherwise
        """
        try:
            img_orient = ds.ImageOrientationPatient
            # Standard axial: [1,0,0,0,1,0] or close to it
            # Check if first two components are close to [1, 0] or [0, 1]
            # and 4th-5th components are close to [1, 0] or [0, 1]
            if abs(img_orient[0]) > 0.7 and abs(img_orient[4]) > 0.7:
                return True
            return False
        except:
            # If can't determine, check series description for orientation hints
            series_desc = str(getattr(ds, 'SeriesDescription', '')).lower()
            if 'ax' in series_desc or 'tra' in series_desc:
                return True
            if 'sag' in series_desc or 'cor' in series_desc:
                return False
            # Default to True for STAGE and SWI sequences (typically axial)
            if 'stage' in series_desc or 'swi' in series_desc:
                return True
            return True  # Default to including if uncertain

    def extract_dicom_properties(self, folder_path):
        """Extract DICOM properties from first valid DICOM file"""
        # Get all files including those without extensions
        dicom_files = [f for f in folder_path.iterdir() if f.is_file() and not f.name.startswith('.')]

        if not dicom_files:
            self.logger.warning(f"No files found in {folder_path}")
            return None

        # Try to read first valid DICOM file
        for dicom_file in dicom_files[:10]:
            try:
                ds = pydicom.dcmread(dicom_file, force=True)
                
                # Helper function to safely get numeric values
                def safe_float(attr_name, default=0.0):
                    val = getattr(ds, attr_name, None)
                    return float(val) if val is not None else default

                def safe_int(attr_name, default=0):
                    val = getattr(ds, attr_name, None)
                    return int(val) if val is not None else default

                def safe_str(attr_name, default='UNKNOWN'):
                    val = getattr(ds, attr_name, None)
                    return str(val) if val is not None else default

                properties = {
                    'series_description': safe_str('SeriesDescription'),
                    'pixel_bandwidth': safe_float('PixelBandwidth'),
                    'pixel_representation': safe_int('PixelRepresentation'),
                    'rows': safe_int('Rows'),
                    'columns': safe_int('Columns'),
                    'has_pixel_data': hasattr(ds, 'PixelData'),
                    'pixel_data_size': len(ds.PixelData) if hasattr(ds, 'PixelData') else 0,
                    'series_number': safe_int('SeriesNumber'),
                    'modality': safe_str('Modality', ''),
                    'slice_thickness': safe_float('SliceThickness'),
                    # Additional properties for differentiation
                    'echo_time': safe_float('EchoTime'),
                    'repetition_time': safe_float('RepetitionTime'),
                    'inversion_time': safe_float('InversionTime'),
                    'flip_angle': safe_float('FlipAngle'),
                    'echo_number': safe_int('EchoNumbers') if hasattr(ds, 'EchoNumbers') else 0,
                    'image_type': safe_str('ImageType'),
                    'sequence_name': safe_str('SequenceName'),
                    'protocol_name': safe_str('ProtocolName'),
                    'acquisition_number': safe_int('AcquisitionNumber'),
                    'series_time': safe_str('SeriesTime'),
                    'acquisition_time': safe_str('AcquisitionTime'),
                    'is_axial': self.is_axial_orientation(ds),
                }
                
                # Count total files in folder
                all_files = list(folder_path.iterdir())
                properties['num_files'] = len([f for f in all_files if f.is_file()])
                
                return properties
                
            except Exception as e:
                self.logger.debug(f"Could not read {dicom_file}: {e}")
                continue
        
        self.logger.error(f"Could not read any DICOM files in {folder_path}")
        return None
    
    def get_sequence_suffix(self, properties):
        """
        Generate suffix for sequence name based on unique identifiers
        Returns: suffix string (e.g., '_echo1_phase', '_mag', '_derived')
        """
        suffix_parts = []

        # Check for echo number
        echo_num = properties.get('echo_number', 0)
        if echo_num > 0:
            suffix_parts.append(f"echo{echo_num}")

        # Check for image type (phase vs magnitude)
        image_type = properties.get('image_type', '')
        if isinstance(image_type, str):
            if "'P'" in image_type and "'DIS2D'" in image_type:
                suffix_parts.append('phase')
            elif "'M'" in image_type and "'NORM'" in image_type:
                suffix_parts.append('mag')
            elif 'DERIVED' in image_type:
                # For derived images, check for specific types
                if 'QSM' in properties['series_description']:
                    suffix_parts.append('qsm')
                elif 'PDMap' in properties['series_description']:
                    suffix_parts.append('pdmap')
                elif 'R2*Map' in properties['series_description'] or 'R2*' in properties['series_description']:
                    suffix_parts.append('r2star')
                elif 'MRA' in properties['series_description']:
                    suffix_parts.append('mra')
                elif 'DIRWM' in properties['series_description']:
                    suffix_parts.append('dirwm')
                elif 'DIRGM' in properties['series_description']:
                    suffix_parts.append('dirgm')
                elif 'EDGE' in properties['series_description']:
                    suffix_parts.append('edge')
                elif 'FGATIR' in properties['series_description'] or 'FLAIR' in properties['series_description']:
                    suffix_parts.append('flair')
                elif 'T2w' in properties['series_description']:
                    suffix_parts.append('t2w')
                elif 'T1w' in properties['series_description']:
                    suffix_parts.append('t1w')
                elif 'SWI' in properties['series_description']:
                    suffix_parts.append('swi')
                else:
                    suffix_parts.append('derived')

        # Check for specific SWI variants (only if not already added)
        series_desc = properties['series_description']
        if 'SWI' in series_desc:
            if '_Pha' in series_desc and 'phase' not in suffix_parts:
                suffix_parts.append('phase')
            elif '_Mag' in series_desc and 'mag' not in suffix_parts:
                suffix_parts.append('mag')
            elif ('_mIP' in series_desc or 'mIP' in series_desc) and 'mip' not in suffix_parts:
                suffix_parts.append('mip')

        # Remove duplicates while preserving order
        seen = set()
        unique_parts = []
        for part in suffix_parts:
            if part not in seen:
                seen.add(part)
                unique_parts.append(part)

        return '_' + '_'.join(unique_parts) if unique_parts else ''

    def classify_sequence(self, properties):
        """
        Classify sequence based on DICOM properties
        Returns: (sequence_type, confidence_score, matching_criteria)
        """
        if not properties:
            return ('UNKNOWN', 0.0, [])

        best_match = None
        best_score = 0.0
        best_criteria = []

        series_desc = properties['series_description'].upper()
        pixel_bw = properties['pixel_bandwidth']
        pixel_rep = properties['pixel_representation']
        num_slices = properties['num_files']
        
        for seq_type, signature in self.sequence_signatures.items():
            score = 0.0
            criteria = []
            
            # Check SeriesDescription (highest weight: 50 points)
            desc_match = False
            for pattern in signature['series_desc_patterns']:
                if pattern.upper() in series_desc:
                    score += 50.0
                    criteria.append(f"SeriesDesc matches '{pattern}'")
                    desc_match = True
                    break
            
            if not desc_match:
                # Partial match (20 points)
                for pattern in signature['series_desc_patterns']:
                    words = pattern.upper().split()
                    if any(word in series_desc for word in words if len(word) > 3):
                        score += 20.0
                        criteria.append(f"SeriesDesc partial match")
                        break
            
            # Check PixelBandwidth (20 points)
            bw_min, bw_max = signature['pixel_bandwidth_range']
            if pixel_bw > 0 and bw_min <= pixel_bw <= bw_max:
                score += 20.0
                criteria.append(f"PixelBandwidth in range ({pixel_bw:.1f})")
            elif pixel_bw > 0 and bw_min * 0.8 <= pixel_bw <= bw_max * 1.2:
                score += 10.0
                criteria.append(f"PixelBandwidth close ({pixel_bw:.1f})")
            
            # Check PixelRepresentation (10 points)
            expected_pixel_rep = signature['pixel_representation']
            if isinstance(expected_pixel_rep, list):
                if pixel_rep in expected_pixel_rep:
                    score += 10.0
                    criteria.append(f"PixelRep matches ({pixel_rep})")
            else:
                if pixel_rep == expected_pixel_rep:
                    score += 10.0
                    criteria.append(f"PixelRep matches ({pixel_rep})")
            
            # Check slice count (20 points)
            slice_min, slice_max = signature['expected_slices']
            if slice_min <= num_slices <= slice_max:
                score += 20.0
                criteria.append(f"Slice count in range ({num_slices})")
            elif slice_min * 0.8 <= num_slices <= slice_max * 1.2:
                score += 10.0
                criteria.append(f"Slice count close ({num_slices})")
            
            if score > best_score:
                best_score = score
                best_match = seq_type
                best_criteria = criteria.copy()
        
        # Require minimum score
        if best_score < 40.0:
            # Still generate suffix even for unknown sequences
            suffix = self.get_sequence_suffix(properties)
            return ('UNKNOWN' + suffix, best_score, best_criteria)

        # Add suffix to differentiate multi-echo and other variants
        suffix = self.get_sequence_suffix(properties)
        return (best_match + suffix, best_score, best_criteria)
    
    def should_include_sequence(self, full_classification, num_files, properties=None):
        """
        Determine if a sequence should be included based on filtering criteria
        Returns: (should_include, reason)
        """
        # Check minimum image count
        if num_files < self.min_images:
            return False, f"Too few images ({num_files} < {self.min_images})"

        # Check if axial orientation (only include axial/transverse)
        if properties and not properties.get('is_axial', True):
            return False, f"Non-axial orientation excluded (sagittal/coronal)"

        # Exclude all PD_STAGE sequences (not used in this study)
        if full_classification.startswith('PD_STAGE'):
            return False, f"PD_STAGE excluded (not used in this study)"

        # Exclude all phase images
        if '_phase' in full_classification:
            return False, f"Phase image excluded (phase data not needed)"

        # Exclude multi-echo variants for T1_STAGE (keep only echo1_mag)
        if self.exclude_t1_stage_variants:
            if full_classification.startswith('T1_STAGE'):
                if full_classification not in ['T1_STAGE', 'T1_STAGE_echo1_mag']:
                    return False, f"T1_STAGE variant excluded (keeping only echo1_mag)"

        return True, "Included"

    def organize_sequence(self, subject_id, sequence_folder, sequence_type, num_files, properties=None):
        """Copy sequence folder to organized structure with filtering"""

        # Check if sequence should be included
        should_include, reason = self.should_include_sequence(sequence_type, num_files, properties)

        if not should_include:
            self.logger.info(f"[EXCLUDED] {sequence_folder.name}: {reason}")
            return False

        # Remove suffixes for cleaner folder names (keep base type only)
        # T1_STAGE_echo1_mag -> T1_STAGE, T1_conv_derived -> T1_conv
        base_type = sequence_type
        for suffix in ['_echo', '_phase', '_mag', '_qsm', '_pdmap', '_r2star',
                      '_mra', '_dirwm', '_dirgm', '_edge', '_flair', '_t2w',
                      '_t1w', '_swi', '_mip', '_derived']:
            if suffix in base_type:
                base_type = base_type.split(suffix)[0]

        output_subject_dir = self.output_dir / subject_id
        output_sequence_dir = output_subject_dir / base_type

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would copy:")
            self.logger.info(f"  From: {sequence_folder}")
            self.logger.info(f"  To:   {output_sequence_dir}")
            return True

        output_sequence_dir.mkdir(parents=True, exist_ok=True)

        try:
            for item in sequence_folder.iterdir():
                if item.is_file():
                    shutil.copy2(item, output_sequence_dir / item.name)

            self.logger.info(f"Organized: {sequence_folder.name} -> {base_type}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to organize {sequence_folder}: {e}")
            return False
    
    def process_subject(self, subject_dir):
        """Process all sequences for one subject"""
        subject_id = subject_dir.name
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Processing: {subject_id}")
        self.logger.info(f"{'='*60}")
        
        sequence_folders = self.find_sequence_folders(subject_dir)
        
        if not sequence_folders:
            self.logger.warning(f"No sequence folders found for {subject_id}")
            return
        
        self.logger.info(f"Found {len(sequence_folders)} sequence folders")
        
        subject_results = []
        
        for seq_folder in sequence_folders:
            properties = self.extract_dicom_properties(seq_folder)
            
            if not properties:
                continue
            
            seq_type, confidence, criteria = self.classify_sequence(properties)
            
            self.logger.info(f"\nFolder: {seq_folder.name}")
            self.logger.info(f"  SeriesDescription: {properties['series_description']}")
            self.logger.info(f"  PixelBandwidth: {properties['pixel_bandwidth']:.1f}")
            self.logger.info(f"  PixelRepresentation: {properties['pixel_representation']}")
            self.logger.info(f"  Files: {properties['num_files']}")
            self.logger.info(f"  → Classified: {seq_type} ({confidence:.1f}%)")
            if criteria:
                self.logger.info(f"  → Criteria: {', '.join(criteria)}")
            
            # Split seq_type into base type and suffix for analysis
            if seq_type.startswith('UNKNOWN'):
                base_type = 'UNKNOWN'
                full_type = seq_type
            else:
                # Try to extract base type by splitting on common suffixes
                for split_str in ['_echo', '_phase', '_mag', '_qsm', '_pdmap', '_r2star',
                                 '_mra', '_dirwm', '_dirgm', '_edge', '_flair', '_t2w', '_t1w', '_swi', '_mip']:
                    if split_str in seq_type:
                        base_type = seq_type.split(split_str)[0]
                        break
                else:
                    base_type = seq_type
                full_type = seq_type

            result = {
                'subject_id': subject_id,
                'original_folder': str(seq_folder),
                'folder_name': seq_folder.name,
                'classified_as': base_type,
                'full_classification': full_type,
                'confidence': confidence,
                'series_description': properties['series_description'],
                'pixel_bandwidth': properties['pixel_bandwidth'],
                'pixel_representation': properties['pixel_representation'],
                'num_files': properties['num_files'],
                'slice_thickness': properties['slice_thickness'],
                'echo_time': properties['echo_time'],
                'repetition_time': properties['repetition_time'],
                'inversion_time': properties['inversion_time'],
                'flip_angle': properties['flip_angle'],
                'echo_number': properties['echo_number'],
                'image_type': properties['image_type'],
                'sequence_name': properties['sequence_name'],
                'protocol_name': properties['protocol_name'],
                'acquisition_number': properties['acquisition_number'],
                'series_time': properties['series_time'],
                'acquisition_time': properties['acquisition_time'],
                'matching_criteria': '; '.join(criteria)
            }
            
            subject_results.append(result)
            self.results.append(result)
            self.summary[full_type] += 1

            if confidence >= 50.0 and not full_type.startswith('UNKNOWN'):
                self.organize_sequence(subject_id, seq_folder, full_type, properties['num_files'], properties)
        
        # Check completeness (check base types without suffixes)
        classified = [r['classified_as'].split('_echo')[0].split('_phase')[0].split('_mag')[0] for r in subject_results]
        expected = ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']

        missing = set(expected) - set(classified)
        if missing:
            self.logger.warning(f"⚠️  Missing: {missing}")

        duplicates = [seq for seq in expected if classified.count(seq) > 1]
        if duplicates:
            self.logger.warning(f"⚠️  Duplicates: {duplicates}")
    
    def process_all(self):
        """Process all subjects"""
        self.logger.info(f"\n{'#'*60}")
        self.logger.info(f"DICOM Sequence Classification - STAGE Study")
        self.logger.info(f"{'#'*60}")
        self.logger.info(f"Base directory: {self.base_dir}")
        self.logger.info(f"Output directory: {self.output_dir}")
        self.logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        
        subject_folders = self.find_subject_folders()
        
        if not subject_folders:
            self.logger.error("No subject folders found!")
            return
        
        for subject_dir in subject_folders:
            self.process_subject(subject_dir)
        
        self.generate_summary()
    
    def analyze_duplicate_series(self):
        """Analyze sequences with the same SeriesDescription to find differentiating properties"""
        if not self.results:
            return

        # Group by SeriesDescription
        series_groups = defaultdict(list)
        for result in self.results:
            series_groups[result['series_description']].append(result)

        # Find groups with multiple sequences
        duplicates = {k: v for k, v in series_groups.items() if len(v) > 1}

        if not duplicates:
            self.logger.info("\nNo duplicate SeriesDescriptions found.")
            return

        self.logger.info(f"\n{'='*60}")
        self.logger.info("DUPLICATE SERIES ANALYSIS")
        self.logger.info(f"{'='*60}")

        for series_desc, sequences in duplicates.items():
            self.logger.info(f"\nSeriesDescription: '{series_desc}' ({len(sequences)} sequences)")
            self.logger.info("-" * 60)

            # Properties to compare
            compare_props = ['echo_time', 'repetition_time', 'inversion_time', 'flip_angle',
                           'echo_number', 'image_type', 'sequence_name', 'protocol_name',
                           'acquisition_number', 'series_time', 'acquisition_time',
                           'pixel_bandwidth', 'slice_thickness', 'num_files']

            # Find which properties differ
            differing_props = []
            for prop in compare_props:
                values = set(str(seq[prop]) for seq in sequences)
                if len(values) > 1:
                    differing_props.append(prop)

            if differing_props:
                self.logger.info(f"Properties that DIFFER: {', '.join(differing_props)}")
                self.logger.info("")

                # Show detailed comparison
                for seq in sequences:
                    self.logger.info(f"  Folder: {seq['folder_name']}")
                    for prop in differing_props:
                        self.logger.info(f"    {prop}: {seq[prop]}")
                    self.logger.info("")
            else:
                self.logger.info("All compared properties are IDENTICAL")
                self.logger.info("Folders:")
                for seq in sequences:
                    self.logger.info(f"  - {seq['folder_name']}")

    def generate_summary(self):
        """Generate summary report"""
        self.logger.info(f"\n{'='*60}")
        self.logger.info("CLASSIFICATION SUMMARY")
        self.logger.info(f"{'='*60}")

        self.logger.info("\nSequences by Type:")
        for seq_type in sorted(self.summary.keys()):
            self.logger.info(f"  {seq_type}: {self.summary[seq_type]}")

        if self.results:
            df = pd.DataFrame(self.results)

            self.logger.info(f"\nConfidence Statistics:")
            self.logger.info(f"  Mean: {df['confidence'].mean():.1f}%")
            self.logger.info(f"  Min: {df['confidence'].min():.1f}%")
            self.logger.info(f"  Max: {df['confidence'].max():.1f}%")

            low_conf = df[df['confidence'] < 50.0]
            if not low_conf.empty:
                self.logger.warning(f"\n⚠️  {len(low_conf)} sequences with low confidence (<50%)")

        # Analyze duplicate SeriesDescriptions
        self.analyze_duplicate_series()

        self.logger.info(f"\n{'='*60}")
        self.logger.info("Complete!")
        self.logger.info(f"{'='*60}\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Classify and organize DICOM sequences for STAGE study'
    )
    parser.add_argument(
        'base_dir',
        type=str,
        help='Base directory containing subject folders'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Output directory (default: base_dir/organized)'
    )
    parser.add_argument(
        '--live',
        action='store_true',
        help='Actually organize files (default is dry run)'
    )
    parser.add_argument(
        '--min-images',
        type=int,
        default=30,
        help='Minimum number of images required (default: 30)'
    )
    parser.add_argument(
        '--include-t1-variants',
        action='store_true',
        help='Include all T1_STAGE phase and echo variants (default: exclude, keep only echo1_mag)'
    )

    args = parser.parse_args()

    classifier = DICOMSequenceClassifier(
        base_dir=args.base_dir,
        output_dir=args.output_dir,
        dry_run=not args.live,
        min_images=args.min_images,
        exclude_t1_stage_variants=not args.include_t1_variants
    )

    classifier.process_all()


if __name__ == '__main__':
    main()
