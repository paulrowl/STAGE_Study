#!/usr/bin/env python3
"""
Extract comprehensive MRI parameters for ALL sequences (T1, T2, SWI) from DICOM metadata
"""

import pandas as pd
import pydicom
from pathlib import Path
import numpy as np

def extract_from_metadata_csv():
    """Extract SWI parameters from existing metadata CSV"""
    csv_file = Path('output/statistics/swi_metadata_deep_inspection.csv')
    if not csv_file.exists():
        return None

    df = pd.read_csv(csv_file)

    # Separate STAGE and conventional
    stage_rows = df[df['SeriesDescription'].str.contains('STAGE', case=False, na=False)]
    conv_rows = df[df['SeriesDescription'].str.contains('SWI AX', case=False, na=False) &
                   ~df['SeriesDescription'].str.contains('STAGE', case=False, na=False)]

    results = {}
    for name, data in [('SWI_STAGE', stage_rows), ('SWI_conv', conv_rows)]:
        if len(data) > 0:
            results[name] = {
                'field_strength': data['Magnetic Field Strength'].mode()[0] if len(data['Magnetic Field Strength'].dropna()) > 0 else None,
                'tr_mean': data['Repetition Time'].mean(),
                'tr_std': data['Repetition Time'].std(),
                'te_mean': data['Echo Time'].mean(),
                'te_std': data['Echo Time'].std(),
                'flip_mean': data['Flip Angle'].mean(),
                'flip_std': data['Flip Angle'].std(),
                'bandwidth_mean': data['Pixel Bandwidth'].mean(),
                'bandwidth_std': data['Pixel Bandwidth'].std(),
                'rows': int(data['Rows'].mode()[0]) if len(data['Rows'].dropna()) > 0 else None,
                'columns': int(data['Columns'].mode()[0]) if len(data['Columns'].dropna()) > 0 else None,
            }

    return results

def extract_from_dicom_dirs():
    """Extract T1 and T2 parameters from DICOM files"""
    organized_dir = Path('data/raw/organized')

    # Get sample patients
    patients = sorted([d for d in organized_dir.iterdir() if d.is_dir() and d.name.startswith('Anon')])[:10]

    results = {}

    for seq_folder in ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE']:
        params_list = []

        for patient in patients:
            seq_path = patient / seq_folder
            if not seq_path.exists():
                continue

            # Find first DICOM file (they are individual files, not in subdirectories)
            dicom_files = sorted([f for f in seq_path.iterdir() if f.is_file()])
            if not dicom_files:
                continue

            try:
                dcm = pydicom.dcmread(dicom_files[0], stop_before_pixels=True)

                params_list.append({
                    'field_strength': getattr(dcm, 'MagneticFieldStrength', None),
                    'tr': getattr(dcm, 'RepetitionTime', None),
                    'te': getattr(dcm, 'EchoTime', None),
                    'flip_angle': getattr(dcm, 'FlipAngle', None),
                    'pixel_bandwidth': getattr(dcm, 'PixelBandwidth', None),
                    'rows': getattr(dcm, 'Rows', None),
                    'columns': getattr(dcm, 'Columns', None),
                })
            except:
                continue

        if params_list:
            df_temp = pd.DataFrame(params_list)
            results[seq_folder] = {
                'field_strength': df_temp['field_strength'].mode()[0] if len(df_temp['field_strength'].dropna()) > 0 else None,
                'tr_mean': df_temp['tr'].mean(),
                'tr_std': df_temp['tr'].std(),
                'te_mean': df_temp['te'].mean(),
                'te_std': df_temp['te'].std(),
                'flip_mean': df_temp['flip_angle'].mean(),
                'flip_std': df_temp['flip_angle'].std(),
                'bandwidth_mean': df_temp['pixel_bandwidth'].mean(),
                'bandwidth_std': df_temp['pixel_bandwidth'].std(),
                'rows': int(df_temp['rows'].mode()[0]) if len(df_temp['rows'].dropna()) > 0 else None,
                'columns': int(df_temp['columns'].mode()[0]) if len(df_temp['columns'].dropna()) > 0 else None,
            }

    return results

def main():
    print("="*80)
    print("COMPREHENSIVE MRI ACQUISITION PARAMETERS")
    print("="*80)

    # Get SWI from CSV
    swi_params = extract_from_metadata_csv()

    # Get T1 and T2 from DICOM
    print("\nExtracting parameters from DICOM files...")
    other_params = extract_from_dicom_dirs()

    # Combine
    all_params = {**swi_params, **other_params} if swi_params else other_params

    # Print formatted results
    print("\n" + "="*80)
    print("RESULTS FOR PUBLICATION (Table 1)")
    print("="*80)

    for seq_name in ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']:
        if seq_name in all_params:
            params = all_params[seq_name]
            print(f"\n{seq_name.replace('_', ' ')}:")
            print(f"  Field Strength: {params['field_strength']:.1f} T" if params['field_strength'] else "  Field Strength: N/A")
            print(f"  TR: {params['tr_mean']:.1f} ± {params['tr_std']:.1f} ms" if not np.isnan(params['tr_mean']) else "  TR: N/A")
            print(f"  TE: {params['te_mean']:.1f} ± {params['te_std']:.1f} ms" if not np.isnan(params['te_mean']) else "  TE: N/A")
            print(f"  Flip Angle: {params['flip_mean']:.1f} ± {params['flip_std']:.1f}°" if not np.isnan(params['flip_mean']) else "  Flip Angle: N/A")
            print(f"  Pixel Bandwidth: {params['bandwidth_mean']:.0f} ± {params['bandwidth_std']:.0f} Hz/px" if not np.isnan(params['bandwidth_mean']) else "  Bandwidth: N/A")
            print(f"  Matrix: {params['rows']}×{params['columns']}" if params['rows'] else "  Matrix: N/A")

    # Save to file
    output_file = Path('output/statistics/comprehensive_mri_parameters.txt')
    with open(output_file, 'w') as f:
        f.write("="*80 + "\n")
        f.write("COMPREHENSIVE MRI ACQUISITION PARAMETERS FOR PUBLICATION\n")
        f.write("="*80 + "\n\n")

        for seq_name in ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']:
            if seq_name in all_params:
                params = all_params[seq_name]
                f.write(f"\n{seq_name.replace('_', ' ')}:\n")
                f.write(f"  Field Strength: {params['field_strength']:.1f} T\n" if params['field_strength'] else "  Field Strength: N/A\n")
                f.write(f"  TR: {params['tr_mean']:.1f} ± {params['tr_std']:.1f} ms\n" if not np.isnan(params['tr_mean']) else "  TR: N/A\n")
                f.write(f"  TE: {params['te_mean']:.1f} ± {params['te_std']:.1f} ms\n" if not np.isnan(params['te_mean']) else "  TE: N/A\n")
                f.write(f"  Flip Angle: {params['flip_mean']:.1f} ± {params['flip_std']:.1f}°\n" if not np.isnan(params['flip_mean']) else "  Flip Angle: N/A\n")
                f.write(f"  Pixel Bandwidth: {params['bandwidth_mean']:.0f} ± {params['bandwidth_std']:.0f} Hz/px\n" if not np.isnan(params['bandwidth_mean']) else "  Bandwidth: N/A\n")
                f.write(f"  Matrix: {params['rows']}×{params['columns']}\n" if params['rows'] else "  Matrix: N/A\n")

    print(f"\n\nSaved to: {output_file}")

    return all_params

if __name__ == '__main__':
    params = main()
