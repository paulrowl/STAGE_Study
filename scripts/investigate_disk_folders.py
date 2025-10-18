#!/usr/bin/env python3
"""
Investigate folders on disk that exist but aren't in ground truth or current stats
"""
import pandas as pd
from pathlib import Path
import os

BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
ORGANIZED_DATA_DIR = BASE_DIR / 'data' / 'raw' / 'organized'
NIFTI_DIR = BASE_DIR / 'output' / 'nifti'
MASK_DIR = BASE_DIR / 'output' / 'brain_masks'
MERGED_STATS = BASE_DIR / 'output' / 'statistics' / 'gm_wm_tissue_stats_MERGED.csv'
GROUND_TRUTH = BASE_DIR / 'output' / 'classifier_training' / 'ground_truth_training_data.csv'

print("=" * 100)
print("INVESTIGATING ADDITIONAL FOLDERS ON DISK")
print("=" * 100)

# Load current data
df_stats = pd.read_csv(MERGED_STATS)
df_ground_truth = pd.read_csv(GROUND_TRUTH)

# Create sets of what we have
stats_set = set(df_stats['subject_id'] + '_' + df_stats['sequence'])
gt_set = set(df_ground_truth['subject_id'] + '_' + df_ground_truth['sequence_type'])

print(f"\nCurrent stats has: {len(stats_set)} sequence entries")
print(f"Ground truth has: {len(gt_set)} sequence entries")

# Subjects to investigate based on audit findings
subjects_to_check = {
    'Anon13609': ['T1_conv'],  # Critical mismatch
    'Anon21108': ['T1_conv'],  # Critical mismatch
    'Anon29308': ['T2_STAGE'],
    'Anon31528': ['T2_STAGE'],
    'Anon36763': ['T2_STAGE'],
    'Anon39768': ['T1_conv', 'SWI_STAGE'],
    'Anon45477': ['T2_STAGE'],
    'Anon46581': ['T2_STAGE'],
    'Anon50326': ['T2_STAGE'],
    'Anon65144': ['T2_STAGE', 'SWI_STAGE'],
}

print("\n" + "=" * 100)
print("CHECKING EACH FOLDER FOR VALID DATA")
print("=" * 100)

investigation_results = []

for subject_id, sequences in subjects_to_check.items():
    print(f"\n{'='*100}")
    print(f"Subject: {subject_id}")
    print(f"{'='*100}")
    
    for seq in sequences:
        print(f"\n  Sequence: {seq}")
        print(f"  {'-'*96}")
        
        result = {
            'subject_id': subject_id,
            'sequence': seq,
            'in_stats': False,
            'in_ground_truth': False,
            'organized_folder_exists': False,
            'organized_dicom_count': 0,
            'nifti_exists': False,
            'nifti_size_mb': 0,
            'mask_exists': False,
            'mask_size_mb': 0,
            'recommendation': 'SKIP'
        }
        
        # Check if in stats
        key = f"{subject_id}_{seq}"
        result['in_stats'] = key in stats_set
        result['in_ground_truth'] = key in gt_set
        
        print(f"    In current stats: {result['in_stats']}")
        print(f"    In ground truth:  {result['in_ground_truth']}")
        
        # Check organized folder
        organized_folder = ORGANIZED_DATA_DIR / subject_id / seq
        if organized_folder.exists():
            result['organized_folder_exists'] = True
            dicom_files = list(organized_folder.glob('*.dcm'))
            result['organized_dicom_count'] = len(dicom_files)
            print(f"    Organized folder: EXISTS ({len(dicom_files)} DICOM files)")
        else:
            print(f"    Organized folder: DOES NOT EXIST")
        
        # Check NIfTI
        nifti_file = NIFTI_DIR / subject_id / f"{seq}.nii.gz"
        if nifti_file.exists():
            result['nifti_exists'] = True
            result['nifti_size_mb'] = nifti_file.stat().st_size / (1024 * 1024)
            print(f"    NIfTI file:       EXISTS ({result['nifti_size_mb']:.2f} MB)")
        else:
            print(f"    NIfTI file:       DOES NOT EXIST")
        
        # Check mask
        mask_file = MASK_DIR / subject_id / f"{seq}_mask.nii.gz"
        if mask_file.exists():
            result['mask_exists'] = True
            result['mask_size_mb'] = mask_file.stat().st_size / (1024 * 1024)
            print(f"    Brain mask:       EXISTS ({result['mask_size_mb']:.2f} MB)")
        else:
            print(f"    Brain mask:       DOES NOT EXIST")
        
        # Determine recommendation
        if result['nifti_exists'] and result['mask_exists'] and not result['in_stats']:
            result['recommendation'] = 'PROCESS - Ready for tissue segmentation'
            print(f"    ✓ RECOMMENDATION: PROCESS (has NIfTI + mask, missing stats)")
        elif result['organized_folder_exists'] and result['organized_dicom_count'] > 0 and not result['nifti_exists']:
            result['recommendation'] = 'CONVERT - Has DICOM, needs NIfTI conversion'
            print(f"    ⚠️  RECOMMENDATION: CONVERT (has DICOM, needs processing)")
        elif not result['organized_folder_exists'] and result['nifti_exists']:
            result['recommendation'] = 'INVESTIGATE - Has NIfTI but no organized folder'
            print(f"    ⚠️  RECOMMENDATION: INVESTIGATE (unusual state)")
        else:
            result['recommendation'] = 'SKIP - Insufficient data'
            print(f"    ✗ RECOMMENDATION: SKIP (insufficient data)")
        
        investigation_results.append(result)

# Summary
print("\n" + "=" * 100)
print("INVESTIGATION SUMMARY")
print("=" * 100)

df_results = pd.DataFrame(investigation_results)

print("\n1. READY TO PROCESS (has NIfTI + mask, just needs tissue segmentation):")
ready = df_results[df_results['recommendation'].str.contains('PROCESS')]
if len(ready) > 0:
    for _, row in ready.iterrows():
        print(f"   {row['subject_id']}/{row['sequence']}")
else:
    print("   None")

print("\n2. NEEDS CONVERSION (has DICOM, needs full processing):")
convert = df_results[df_results['recommendation'].str.contains('CONVERT')]
if len(convert) > 0:
    for _, row in convert.iterrows():
        print(f"   {row['subject_id']}/{row['sequence']} ({row['organized_dicom_count']} DICOM files)")
else:
    print("   None")

print("\n3. NEEDS INVESTIGATION (unusual state):")
investigate = df_results[df_results['recommendation'].str.contains('INVESTIGATE')]
if len(investigate) > 0:
    for _, row in investigate.iterrows():
        print(f"   {row['subject_id']}/{row['sequence']}")
else:
    print("   None")

print("\n4. SKIP (insufficient data):")
skip = df_results[df_results['recommendation'].str.contains('SKIP')]
if len(skip) > 0:
    for _, row in skip.iterrows():
        print(f"   {row['subject_id']}/{row['sequence']}")
else:
    print("   None")

# Save results
output_file = BASE_DIR / 'output' / 'statistics' / 'disk_folder_investigation.csv'
df_results.to_csv(output_file, index=False)
print(f"\n✓ Saved detailed results to: {output_file}")

print("\n" + "=" * 100)
print("POTENTIAL IMPACT")
print("=" * 100)

ready_count = len(ready)
convert_count = len(convert)
total_recoverable = ready_count + convert_count

print(f"\nCurrently missing from analysis:")
print(f"  - Ready to process immediately: {ready_count} sequences")
print(f"  - Can be recovered with full pipeline: {convert_count} sequences")
print(f"  - TOTAL POTENTIALLY RECOVERABLE: {total_recoverable} sequences")

# Estimate pair impact
print(f"\nPotential paired comparison impact:")
for seq_type in ['T1', 'T2', 'SWI']:
    ready_this_type = ready[(ready['sequence'].str.contains(seq_type))]
    convert_this_type = convert[(convert['sequence'].str.contains(seq_type))]
    total_this_type = len(ready_this_type) + len(convert_this_type)
    if total_this_type > 0:
        print(f"  {seq_type}: +{total_this_type} sequences could enable additional pairs")

print("\n" + "=" * 100)
print("✓ Investigation complete")
print("=" * 100)
