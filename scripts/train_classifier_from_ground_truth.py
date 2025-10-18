#!/usr/bin/env python3
"""
Train DICOM Sequence Classifier Using Verified Ground Truth Data

Analyzes the verified ground truth sequences to extract optimal classification
rules and improve the automated DICOM sequence classifier.

Steps:
1. Load ground truth CSV with verified series numbers
2. Read DICOM properties from verified sequences
3. Analyze discriminative features for each sequence type
4. Generate updated classification rules
5. Test classifier accuracy on ground truth data

Usage:
    python scripts/train_classifier_from_ground_truth.py

Author: STAGE Study Analysis
Date: 2025-10-17
"""

import pandas as pd
import numpy as np
from pathlib import Path
import pydicom
import json
from collections import defaultdict
import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
RAW_DIR = BASE_DIR / 'data' / 'raw'
GROUND_TRUTH_CSV = '/Users/paul/Downloads/sequence_folder_mapping - sequence_folder_mapping.csv'
OUTPUT_DIR = BASE_DIR / 'output' / 'classifier_training'
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

SEQUENCES = ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']


def parse_series_number(cell_value: str):
    """Extract series number from CSV cell"""
    import re
    if pd.isna(cell_value) or str(cell_value).strip() == '':
        return None
    cell_str = str(cell_value).strip()
    match = re.match(r'([A-F0-9]+)\s*\(#\d+\)', cell_str)
    if match:
        return match.group(1)
    match = re.match(r'\(#(\d+)\)', cell_str)
    if match:
        return match.group(1)
    if re.match(r'^[A-F0-9]+$', cell_str):
        return cell_str
    return None


def get_series_path_from_dicomdir(subject_dir: Path, series_number: str):
    """Find DICOM folder using DICOMDIR"""
    dicomdir_path = subject_dir / 'DICOMDIR'
    if not dicomdir_path.exists():
        return None

    try:
        dicomdir = pydicom.dcmread(str(dicomdir_path))
        target_series = int(series_number)

        for patient in dicomdir.patient_records:
            for study in patient.children:
                for series in study.children:
                    if hasattr(series, 'SeriesNumber') and series.SeriesNumber == target_series:
                        if hasattr(series, 'children') and len(series.children) > 0:
                            first_image = series.children[0]
                            if hasattr(first_image, 'ReferencedFileID'):
                                file_path_parts = first_image.ReferencedFileID[:-1]
                                folder_path = subject_dir / Path(*file_path_parts)
                                return folder_path
        return None
    except Exception as e:
        logger.debug(f"Error parsing DICOMDIR: {e}")
        return None


def find_dicom_folder(subject_id: str, series_number: str):
    """Find DICOM folder for given series"""
    subject_raw_dir = RAW_DIR / subject_id
    if not subject_raw_dir.exists():
        return None

    # Try DICOMDIR first
    if series_number.isdigit():
        dicomdir_path = get_series_path_from_dicomdir(subject_raw_dir, series_number)
        if dicomdir_path and dicomdir_path.exists():
            return dicomdir_path

    # Fallback to glob search
    patterns = [f"**/{series_number}", f"**/*{series_number}*"]
    for pattern in patterns:
        matches = list(subject_raw_dir.glob(pattern))
        matches = [m for m in matches if m.is_dir()]
        if len(matches) >= 1:
            return matches[0]

    return None


def extract_dicom_properties(folder_path: Path):
    """Extract DICOM properties from folder"""
    dicom_files = [f for f in folder_path.iterdir() if f.is_file() and not f.name.startswith('.')]
    if not dicom_files:
        return None

    for dicom_file in dicom_files[:5]:
        try:
            ds = pydicom.dcmread(dicom_file, stop_before_pixels=True)

            def safe_get(attr, default=None):
                val = getattr(ds, attr, default)
                if val is None:
                    return default
                return val

            properties = {
                'SeriesDescription': safe_get('SeriesDescription', 'UNKNOWN'),
                'Manufacturer': safe_get('Manufacturer', 'UNKNOWN'),
                'ManufacturerModelName': safe_get('ManufacturerModelName', 'UNKNOWN'),
                'PixelBandwidth': float(safe_get('PixelBandwidth', 0)),
                'PixelRepresentation': int(safe_get('PixelRepresentation', 0)),
                'Rows': int(safe_get('Rows', 0)),
                'Columns': int(safe_get('Columns', 0)),
                'SeriesNumber': int(safe_get('SeriesNumber', 0)),
                'Modality': safe_get('Modality', ''),
                'SliceThickness': float(safe_get('SliceThickness', 0)),
                'EchoTime': float(safe_get('EchoTime', 0)),
                'RepetitionTime': float(safe_get('RepetitionTime', 0)),
                'InversionTime': float(safe_get('InversionTime', 0)),
                'FlipAngle': float(safe_get('FlipAngle', 0)),
                'ImageType': str(safe_get('ImageType', '')),
                'SequenceName': safe_get('SequenceName', ''),
                'ProtocolName': safe_get('ProtocolName', ''),
                'MagneticFieldStrength': float(safe_get('MagneticFieldStrength', 0)),
                'ImagingFrequency': float(safe_get('ImagingFrequency', 0)),
            }

            return properties
        except Exception as e:
            continue

    return None


def collect_training_data():
    """Collect DICOM properties from all verified ground truth sequences"""
    logger.info("="*80)
    logger.info("Collecting Training Data from Ground Truth")
    logger.info("="*80)

    # Load ground truth
    df_gt = pd.read_csv(GROUND_TRUTH_CSV)
    logger.info(f"Loaded {len(df_gt)} subjects from ground truth")

    # Parse series numbers
    for seq in SEQUENCES:
        df_gt[f'{seq}_series'] = df_gt[seq].apply(parse_series_number)

    # Collect properties for each sequence type
    training_data = defaultdict(list)

    for idx, row in df_gt.iterrows():
        subject_id = row['rAccession']
        logger.info(f"\nProcessing {subject_id} ({idx+1}/{len(df_gt)})")

        for seq in SEQUENCES:
            series_col = f'{seq}_series'
            if pd.notna(row[series_col]):
                series_number = row[series_col]
                logger.info(f"  {seq}: series {series_number}")

                # Find DICOM folder
                dicom_folder = find_dicom_folder(subject_id, series_number)

                if dicom_folder:
                    logger.info(f"    Found: {dicom_folder}")
                    # Extract properties
                    props = extract_dicom_properties(dicom_folder)

                    if props:
                        props['subject_id'] = subject_id
                        props['sequence_type'] = seq
                        props['series_number'] = series_number
                        training_data[seq].append(props)
                        logger.info(f"    ✓ Extracted properties")
                    else:
                        logger.warning(f"    ✗ Could not extract DICOM properties")
                else:
                    logger.warning(f"    ✗ DICOM folder not found")

    # Convert to DataFrames
    training_dfs = {}
    for seq in SEQUENCES:
        if training_data[seq]:
            training_dfs[seq] = pd.DataFrame(training_data[seq])
            logger.info(f"\n{seq}: {len(training_data[seq])} samples collected")

    return training_dfs


def analyze_discriminative_features(training_dfs):
    """Analyze which features best discriminate between sequence types"""
    logger.info("\n" + "="*80)
    logger.info("Analyzing Discriminative Features")
    logger.info("="*80)

    # Combine all data
    all_data = []
    for seq, df in training_dfs.items():
        all_data.append(df)
    df_all = pd.concat(all_data, ignore_index=True)

    # Numeric features to analyze
    numeric_features = ['PixelBandwidth', 'EchoTime', 'RepetitionTime',
                       'InversionTime', 'FlipAngle', 'SliceThickness']

    # Analyze each feature
    feature_analysis = {}

    for feature in numeric_features:
        logger.info(f"\n{feature}:")
        logger.info("-" * 60)

        feature_stats = {}
        for seq in SEQUENCES:
            seq_data = df_all[df_all['sequence_type'] == seq][feature]
            if len(seq_data) > 0:
                stats = {
                    'mean': seq_data.mean(),
                    'std': seq_data.std(),
                    'min': seq_data.min(),
                    'max': seq_data.max(),
                    'median': seq_data.median(),
                    'count': len(seq_data)
                }
                feature_stats[seq] = stats

                logger.info(f"  {seq}:")
                logger.info(f"    Mean: {stats['mean']:.2f} ± {stats['std']:.2f}")
                logger.info(f"    Range: [{stats['min']:.2f}, {stats['max']:.2f}]")
                logger.info(f"    Median: {stats['median']:.2f}")
                logger.info(f"    N: {stats['count']}")

        feature_analysis[feature] = feature_stats

    # Categorical features
    logger.info("\n" + "="*80)
    logger.info("Categorical Features")
    logger.info("="*80)

    categorical_features = ['SeriesDescription', 'Manufacturer', 'SequenceName']

    for feature in categorical_features:
        logger.info(f"\n{feature}:")
        logger.info("-" * 60)

        for seq in SEQUENCES:
            seq_data = df_all[df_all['sequence_type'] == seq][feature]
            if len(seq_data) > 0:
                unique_values = seq_data.unique()
                logger.info(f"  {seq}:")
                for val in unique_values[:5]:  # Show top 5
                    count = (seq_data == val).sum()
                    logger.info(f"    '{val}': {count}/{len(seq_data)}")

    return feature_analysis, df_all


def generate_updated_rules(feature_analysis, df_all):
    """Generate updated classification rules based on analysis"""
    logger.info("\n" + "="*80)
    logger.info("Generating Updated Classification Rules")
    logger.info("="*80)

    updated_signatures = {}

    for seq in SEQUENCES:
        logger.info(f"\n{seq}:")

        seq_data = df_all[df_all['sequence_type'] == seq]

        if len(seq_data) == 0:
            logger.warning(f"  No data for {seq}")
            continue

        # Get SeriesDescription patterns
        series_descs = seq_data['SeriesDescription'].unique()
        logger.info(f"  SeriesDescription patterns: {list(series_descs)[:3]}")

        # Get numeric ranges (mean ± 2*std to capture ~95% of data)
        pixel_bw_mean = seq_data['PixelBandwidth'].mean()
        pixel_bw_std = seq_data['PixelBandwidth'].std()
        pixel_bw_range = (max(0, pixel_bw_mean - 2*pixel_bw_std),
                         pixel_bw_mean + 2*pixel_bw_std)

        echo_time_mean = seq_data['EchoTime'].mean()
        echo_time_std = seq_data['EchoTime'].std()
        echo_time_range = (max(0, echo_time_mean - 2*echo_time_std),
                          echo_time_mean + 2*echo_time_std)

        flip_angle_mean = seq_data['FlipAngle'].mean()
        flip_angle_std = seq_data['FlipAngle'].std()
        flip_angle_range = (max(0, flip_angle_mean - 2*flip_angle_std),
                           flip_angle_mean + 2*flip_angle_std)

        logger.info(f"  PixelBandwidth: {pixel_bw_range[0]:.1f} - {pixel_bw_range[1]:.1f}")
        logger.info(f"  EchoTime: {echo_time_range[0]:.1f} - {echo_time_range[1]:.1f} ms")
        logger.info(f"  FlipAngle: {flip_angle_range[0]:.1f} - {flip_angle_range[1]:.1f}°")

        updated_signatures[seq] = {
            'series_desc_patterns': list(series_descs),
            'pixel_bandwidth_range': pixel_bw_range,
            'echo_time_range': echo_time_range,
            'flip_angle_range': flip_angle_range,
            'n_samples': len(seq_data)
        }

    return updated_signatures


def test_classifier_accuracy(training_dfs, updated_signatures):
    """Test classifier accuracy using updated rules"""
    logger.info("\n" + "="*80)
    logger.info("Testing Classifier Accuracy on Ground Truth")
    logger.info("="*80)

    # Simple rule-based classifier using updated rules
    def classify_sequence(props, signatures):
        """Classify based on updated signatures"""
        series_desc = props['SeriesDescription'].upper()
        pixel_bw = props['PixelBandwidth']

        scores = {}

        for seq, sig in signatures.items():
            score = 0

            # Check SeriesDescription patterns
            for pattern in sig.get('series_desc_patterns', []):
                if pattern.upper() in series_desc or series_desc in pattern.upper():
                    score += 50
                    break

            # Check PixelBandwidth range
            bw_range = sig.get('pixel_bandwidth_range', (0, 1000))
            if bw_range[0] <= pixel_bw <= bw_range[1]:
                score += 30

            # Check EchoTime range if available
            if 'EchoTime' in props and props['EchoTime'] > 0:
                et_range = sig.get('echo_time_range', (0, 1000))
                if et_range[0] <= props['EchoTime'] <= et_range[1]:
                    score += 10

            # Check FlipAngle range if available
            if 'FlipAngle' in props and props['FlipAngle'] > 0:
                fa_range = sig.get('flip_angle_range', (0, 180))
                if fa_range[0] <= props['FlipAngle'] <= fa_range[1]:
                    score += 10

            scores[seq] = score

        # Return sequence with highest score
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        return 'UNKNOWN'

    # Test on all training data
    results = {'correct': 0, 'incorrect': 0, 'total': 0}
    confusion_matrix = defaultdict(lambda: defaultdict(int))

    for seq, df in training_dfs.items():
        for idx, row in df.iterrows():
            predicted = classify_sequence(row.to_dict(), updated_signatures)
            actual = row['sequence_type']

            results['total'] += 1
            if predicted == actual:
                results['correct'] += 1
            else:
                results['incorrect'] += 1

            confusion_matrix[actual][predicted] += 1

    # Print results
    accuracy = (results['correct'] / results['total'] * 100) if results['total'] > 0 else 0

    logger.info(f"\nAccuracy: {accuracy:.1f}% ({results['correct']}/{results['total']})")

    logger.info("\nConfusion Matrix:")
    logger.info("-" * 60)

    header = "Actual\\Predicted"
    for seq in SEQUENCES:
        header += f"\t{seq.split('_')[0][:2]}_{seq.split('_')[1][:2]}"
    logger.info(header)

    for actual_seq in SEQUENCES:
        row_str = f"{actual_seq.split('_')[0][:2]}_{actual_seq.split('_')[1][:2]}"
        for pred_seq in SEQUENCES:
            row_str += f"\t{confusion_matrix[actual_seq][pred_seq]}"
        logger.info(row_str)

    return accuracy, confusion_matrix


def save_results(training_dfs, updated_signatures, accuracy, confusion_matrix):
    """Save training results and updated rules"""
    logger.info("\n" + "="*80)
    logger.info("Saving Results")
    logger.info("="*80)

    # Save combined training data
    all_training = []
    for seq, df in training_dfs.items():
        all_training.append(df)
    df_combined = pd.concat(all_training, ignore_index=True)

    training_file = OUTPUT_DIR / 'ground_truth_training_data.csv'
    df_combined.to_csv(training_file, index=False)
    logger.info(f"Saved training data: {training_file}")

    # Save updated signatures
    signatures_file = OUTPUT_DIR / 'updated_classification_rules.json'
    # Convert numpy types to Python types for JSON serialization
    signatures_json = {}
    for seq, sig in updated_signatures.items():
        signatures_json[seq] = {
            k: [float(v) for v in value] if isinstance(value, tuple) else
               [str(v) for v in value] if isinstance(value, list) else
               int(value) if isinstance(value, (int, np.integer)) else
               value
            for k, value in sig.items()
        }

    with open(signatures_file, 'w') as f:
        json.dump(signatures_json, f, indent=2)
    logger.info(f"Saved updated rules: {signatures_file}")

    # Save accuracy report
    report_file = OUTPUT_DIR / 'CLASSIFIER_TRAINING_REPORT.md'
    with open(report_file, 'w') as f:
        f.write("# DICOM Classifier Training Report\n\n")
        f.write(f"**Date:** 2025-10-17\n\n")
        f.write(f"**Ground Truth Source:** {GROUND_TRUTH_CSV}\n\n")

        f.write("## Training Data Summary\n\n")
        for seq in SEQUENCES:
            if seq in training_dfs:
                f.write(f"- **{seq}:** {len(training_dfs[seq])} samples\n")

        f.write(f"\n## Classifier Accuracy\n\n")
        f.write(f"**Overall Accuracy:** {accuracy:.1f}%\n\n")

        f.write("### Confusion Matrix\n\n")
        f.write("| Actual \\ Predicted | ")
        for seq in SEQUENCES:
            f.write(f"{seq} | ")
        f.write("\n")

        f.write("|" + ("-" * 20) + "|")
        for _ in SEQUENCES:
            f.write("-" * 10 + "|")
        f.write("\n")

        for actual_seq in SEQUENCES:
            f.write(f"| {actual_seq} | ")
            for pred_seq in SEQUENCES:
                f.write(f"{confusion_matrix[actual_seq][pred_seq]} | ")
            f.write("\n")

        f.write("\n## Updated Classification Rules\n\n")
        for seq, sig in updated_signatures.items():
            f.write(f"### {seq}\n\n")
            f.write(f"- **Samples:** {sig['n_samples']}\n")
            f.write(f"- **PixelBandwidth:** {sig['pixel_bandwidth_range'][0]:.1f} - {sig['pixel_bandwidth_range'][1]:.1f}\n")
            f.write(f"- **EchoTime:** {sig['echo_time_range'][0]:.1f} - {sig['echo_time_range'][1]:.1f} ms\n")
            f.write(f"- **FlipAngle:** {sig['flip_angle_range'][0]:.1f} - {sig['flip_angle_range'][1]:.1f}°\n")
            f.write(f"- **SeriesDescription patterns:** {', '.join(sig['series_desc_patterns'][:3])}\n\n")

    logger.info(f"Saved training report: {report_file}")


def main():
    """Main execution"""
    logger.info("="*80)
    logger.info("DICOM Classifier Training from Ground Truth")
    logger.info("="*80)

    # Step 1: Collect training data
    training_dfs = collect_training_data()

    if not training_dfs:
        logger.error("No training data collected!")
        return

    # Step 2: Analyze discriminative features
    feature_analysis, df_all = analyze_discriminative_features(training_dfs)

    # Step 3: Generate updated rules
    updated_signatures = generate_updated_rules(feature_analysis, df_all)

    # Step 4: Test classifier accuracy
    accuracy, confusion_matrix = test_classifier_accuracy(training_dfs, updated_signatures)

    # Step 5: Save results
    save_results(training_dfs, updated_signatures, accuracy, confusion_matrix)

    logger.info("\n" + "="*80)
    logger.info("TRAINING COMPLETE!")
    logger.info("="*80)
    logger.info(f"\nFinal Accuracy: {accuracy:.1f}%")
    logger.info(f"\nOutput files saved to: {OUTPUT_DIR}")


if __name__ == '__main__':
    main()
