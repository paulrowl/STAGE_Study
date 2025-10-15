#!/usr/bin/env python3
"""
Deep DICOM Metadata Inspector for SWI Sequences
Examines ALL DICOM properties to find distinguishing features between STAGE and conventional SWI
"""

import pydicom
from pathlib import Path
import pandas as pd
import json
from collections import defaultdict

def get_all_dicom_tags(ds):
    """Extract ALL DICOM tags from a dataset"""
    tags = {}
    for elem in ds:
        try:
            tag_name = elem.name
            tag_value = elem.value

            # Convert to string for consistency
            if isinstance(tag_value, bytes):
                try:
                    tag_value = tag_value.decode('utf-8', errors='ignore')
                except:
                    tag_value = str(tag_value)
            elif isinstance(tag_value, (list, tuple)):
                tag_value = ', '.join(str(v) for v in tag_value)
            else:
                tag_value = str(tag_value)

            tags[tag_name] = tag_value
        except:
            continue
    return tags

def inspect_swi_sequences(raw_data_dir, num_patients=5):
    """Inspect SWI sequences from multiple patients"""

    raw_dir = Path(raw_data_dir)
    patient_dirs = sorted([d for d in raw_dir.iterdir() if d.is_dir() and d.name.startswith('Anon')])[:num_patients]

    all_swi_data = []

    for patient_dir in patient_dirs:
        print(f"\n{'='*80}")
        print(f"PATIENT: {patient_dir.name}")
        print(f"{'='*80}")

        # Find all sequence folders (pattern: patient/100*/100*/sequence/)
        for level1 in patient_dir.glob('100*'):
            if not level1.is_dir():
                continue
            for level2 in level1.glob('100*'):
                if not level2.is_dir():
                    continue
                for seq_folder in level2.iterdir():
                    if not seq_folder.is_dir() or seq_folder.name.startswith('.'):
                        continue

                    # Get first DICOM file
                    dicom_files = [f for f in seq_folder.iterdir() if f.is_file() and not f.name.startswith('.')]
                    if not dicom_files:
                        continue

                    try:
                        ds = pydicom.dcmread(dicom_files[0], force=True)
                        series_desc = str(getattr(ds, 'SeriesDescription', 'UNKNOWN'))

                        # Only process SWI sequences
                        if 'SWI' not in series_desc.upper():
                            continue

                        print(f"\nSeries: {series_desc}")
                        print(f"Folder: {seq_folder.name}")

                        # Extract ALL tags
                        all_tags = get_all_dicom_tags(ds)

                        # Key properties to highlight
                        key_props = [
                            'SeriesDescription',
                            'ProtocolName',
                            'SeriesNumber',
                            'SequenceName',
                            'ScanningSequence',
                            'SequenceVariant',
                            'ScanOptions',
                            'MRAcquisitionType',
                            'AngioFlag',
                            'ImageType',
                            'PixelBandwidth',
                            'EchoTime',
                            'RepetitionTime',
                            'InversionTime',
                            'FlipAngle',
                            'EchoNumbers',
                            'NumberOfAverages',
                            'ImagingFrequency',
                            'MagneticFieldStrength',
                            'EchoTrainLength',
                            'PercentSampling',
                            'PercentPhaseFieldOfView',
                            'PixelSpacing',
                            'SliceThickness',
                            'SpacingBetweenSlices',
                            'AcquisitionMatrix',
                            'InPlanePhaseEncodingDirection',
                            'FlipAngle',
                            'VariableFlipAngleFlag',
                            'SAR',
                            'dB/dt',
                            'TransmitCoilName',
                            'AcquisitionType',
                            'ReceiveCoilName',
                            'ContrastBolusAgent',
                            'SoftwareVersions',
                            'PixelRepresentation',
                            'BitsAllocated',
                            'BitsStored',
                            'HighBit',
                            'RescaleIntercept',
                            'RescaleSlope',
                            'WindowCenter',
                            'WindowWidth',
                        ]

                        print("\nKey DICOM Properties:")
                        print("-" * 80)
                        for prop in key_props:
                            if prop in all_tags:
                                value = all_tags[prop]
                                print(f"  {prop:35s}: {value}")

                        # Store for comparison
                        sequence_data = {
                            'Patient': patient_dir.name,
                            'SeriesDescription': series_desc,
                            'FolderName': seq_folder.name,
                            'NumFiles': len(dicom_files),
                        }

                        # Add all tags to data
                        sequence_data.update(all_tags)
                        all_swi_data.append(sequence_data)

                    except Exception as e:
                        print(f"  Error reading {seq_folder.name}: {e}")
                        continue

    # Create DataFrame for analysis
    if all_swi_data:
        df = pd.DataFrame(all_swi_data)

        # Save full data
        output_file = 'output/statistics/swi_metadata_deep_inspection.csv'
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_file, index=False)
        print(f"\n{'='*80}")
        print(f"Full metadata saved to: {output_file}")

        # Find distinguishing properties
        print(f"\n{'='*80}")
        print("FINDING DISTINGUISHING PROPERTIES")
        print(f"{'='*80}")

        # Group by likely classification (conventional vs STAGE)
        # Use pattern matching on SeriesDescription
        df['IsConventional'] = df['SeriesDescription'].str.contains('AX_SWI|AX SWI', case=False, regex=True)
        df['IsSTAGE'] = df['SeriesDescription'].str.contains('STAGE|_Ax_', case=False, regex=True)

        conventional = df[df['IsConventional'] == True]
        stage = df[df['IsSTAGE'] == True]

        print(f"\nFound {len(conventional)} conventional SWI sequences")
        print(f"Found {len(stage)} STAGE SWI sequences")

        if len(conventional) > 0 and len(stage) > 0:
            print(f"\n{'='*80}")
            print("PROPERTIES THAT DIFFER BETWEEN CONVENTIONAL AND STAGE SWI")
            print(f"{'='*80}\n")

            # Find columns that have different values between groups
            differing_properties = []
            for col in df.columns:
                if col in ['Patient', 'SeriesDescription', 'FolderName', 'IsConventional', 'IsSTAGE']:
                    continue

                try:
                    conv_values = set(conventional[col].dropna().astype(str))
                    stage_values = set(stage[col].dropna().astype(str))

                    if conv_values != stage_values:
                        differing_properties.append(col)

                        print(f"\n{col}:")
                        print(f"  Conventional: {conv_values}")
                        print(f"  STAGE:        {stage_values}")
                except Exception as e:
                    continue

            print(f"\n{'='*80}")
            print(f"Total differing properties: {len(differing_properties)}")
            print(f"{'='*80}")

            # Save differentiating properties
            diff_file = 'output/statistics/swi_differentiating_properties.txt'
            with open(diff_file, 'w') as f:
                f.write("DIFFERENTIATING PROPERTIES FOR SWI CLASSIFICATION\n")
                f.write("="*80 + "\n\n")

                for col in differing_properties:
                    f.write(f"\n{col}:\n")
                    conv_values = set(conventional[col].dropna().astype(str))
                    stage_values = set(stage[col].dropna().astype(str))
                    f.write(f"  Conventional: {conv_values}\n")
                    f.write(f"  STAGE:        {stage_values}\n")

            print(f"\nDifferentiating properties saved to: {diff_file}")

        # Also check for sequences that don't match either pattern
        unknown = df[(df['IsConventional'] == False) & (df['IsSTAGE'] == False)]
        if len(unknown) > 0:
            print(f"\n{'='*80}")
            print(f"WARNING: {len(unknown)} SWI sequences don't match either pattern:")
            print(f"{'='*80}")
            for idx, row in unknown.iterrows():
                print(f"  {row['Patient']}: {row['SeriesDescription']}")

    return all_swi_data

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        raw_dir = sys.argv[1]
    else:
        raw_dir = 'data/raw'

    num_patients = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    print(f"Inspecting SWI sequences from {num_patients} patients in: {raw_dir}")
    inspect_swi_sequences(raw_dir, num_patients)
