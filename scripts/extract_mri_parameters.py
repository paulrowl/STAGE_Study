#!/usr/bin/env python3
"""
Extract MRI acquisition parameters from metadata for publication
"""

import pandas as pd
import pydicom
from pathlib import Path
import numpy as np

def get_dicom_params(patient_dir, sequence_folder):
    """Extract parameters from first DICOM file in a sequence folder"""
    seq_path = patient_dir / sequence_folder
    if not seq_path.exists():
        return None

    # Find first DICOM directory
    dicom_dirs = [d for d in seq_path.iterdir() if d.is_dir()]
    if not dicom_dirs:
        return None

    # DICOM files are the directories themselves in this structure
    dicom_file = dicom_dirs[0]

    try:
        dcm = pydicom.dcmread(dicom_file, stop_before_pixels=True)

        params = {
            'field_strength': getattr(dcm, 'MagneticFieldStrength', None),
            'tr': getattr(dcm, 'RepetitionTime', None),
            'te': getattr(dcm, 'EchoTime', None),
            'flip_angle': getattr(dcm, 'FlipAngle', None),
            'slice_thickness': getattr(dcm, 'SliceThickness', None),
            'pixel_bandwidth': getattr(dcm, 'PixelBandwidth', None),
            'matrix': getattr(dcm, 'AcquisitionMatrix', None),
            'pixel_spacing': getattr(dcm, 'PixelSpacing', None),
            'manufacturer': getattr(dcm, 'Manufacturer', None),
            'model': getattr(dcm, 'ManufacturerModelName', None),
            'rows': getattr(dcm, 'Rows', None),
            'columns': getattr(dcm, 'Columns', None),
        }
        return params
    except Exception as e:
        print(f"Error reading {dicom_file}: {e}")
        return None

def main():
    organized_dir = Path('data/raw/organized')

    # Get list of patients
    patients = [d for d in organized_dir.iterdir() if d.is_dir() and d.name.startswith('Anon')]

    results = []

    sequences = {
        'T1_conv': 'T1 Conventional',
        'T1_STAGE': 'T1 STAGE',
        'T2_conv': 'T2 Conventional',
        'T2_STAGE': 'T2 STAGE',
        'SWI_conv': 'SWI Conventional',
        'SWI_STAGE': 'SWI STAGE',
    }

    print("Extracting MRI parameters from DICOM files...")

    for patient in sorted(patients)[:5]:  # Sample first 5 patients
        print(f"Processing {patient.name}...")
        for seq_folder, seq_name in sequences.items():
            params = get_dicom_params(patient, seq_folder)
            if params:
                params['patient'] = patient.name
                params['sequence'] = seq_name
                params['seq_type'] = seq_folder
                results.append(params)

    # Convert to DataFrame
    df = pd.DataFrame(results)

    # Save detailed results
    output_file = Path('output/statistics/mri_acquisition_parameters.csv')
    df.to_csv(output_file, index=False)
    print(f"\nSaved detailed parameters to: {output_file}")

    # Generate summary statistics
    print("\n" + "="*80)
    print("MRI ACQUISITION PARAMETERS SUMMARY")
    print("="*80)

    for seq_name in df['sequence'].unique():
        seq_data = df[df['sequence'] == seq_name]

        print(f"\n{seq_name}:")
        print(f"  N patients: {len(seq_data)}")

        if seq_data['field_strength'].notna().any():
            fs = seq_data['field_strength'].dropna()
            print(f"  Field Strength: {fs.iloc[0]:.1f} T" if len(fs) > 0 else "  Field Strength: N/A")

        if seq_data['tr'].notna().any():
            tr = seq_data['tr'].dropna()
            print(f"  TR: {tr.mean():.1f} ± {tr.std():.1f} ms (range: {tr.min():.1f}-{tr.max():.1f})")

        if seq_data['te'].notna().any():
            te = seq_data['te'].dropna()
            print(f"  TE: {te.mean():.1f} ± {te.std():.1f} ms (range: {te.min():.1f}-{te.max():.1f})")

        if seq_data['flip_angle'].notna().any():
            fa = seq_data['flip_angle'].dropna()
            print(f"  Flip Angle: {fa.mean():.1f} ± {fa.std():.1f}° (range: {fa.min():.1f}-{fa.max():.1f})")

        if seq_data['slice_thickness'].notna().any():
            st = seq_data['slice_thickness'].dropna()
            print(f"  Slice Thickness: {st.mean():.2f} ± {st.std():.2f} mm")

        if seq_data['pixel_bandwidth'].notna().any():
            pb = seq_data['pixel_bandwidth'].dropna()
            print(f"  Pixel Bandwidth: {pb.mean():.1f} ± {pb.std():.1f} Hz/pixel")

        if seq_data['rows'].notna().any() and seq_data['columns'].notna().any():
            rows = seq_data['rows'].dropna()
            cols = seq_data['columns'].dropna()
            print(f"  Matrix: {int(rows.mode()[0])}×{int(cols.mode()[0])} (typical)")

        if seq_data['manufacturer'].notna().any():
            mfg = seq_data['manufacturer'].iloc[0]
            model = seq_data['model'].iloc[0] if seq_data['model'].notna().any() else 'Unknown'
            print(f"  Scanner: {mfg} {model}")

    return df

if __name__ == '__main__':
    df = main()
