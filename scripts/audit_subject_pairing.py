#!/usr/bin/env python3
"""
Audit subject pairing status - identify which subjects have conv, STAGE, or both
"""
import pandas as pd
from pathlib import Path

BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
MERGED_STATS = BASE_DIR / 'output' / 'statistics' / 'gm_wm_tissue_stats_MERGED.csv'
GROUND_TRUTH = BASE_DIR / 'output' / 'classifier_training' / 'ground_truth_training_data.csv'
ORGANIZED_DATA_DIR = BASE_DIR / 'data' / 'raw' / 'organized'

print("=" * 100)
print("SUBJECT PAIRING AUDIT")
print("=" * 100)

# Load data
df_stats = pd.read_csv(MERGED_STATS)
df_ground_truth = pd.read_csv(GROUND_TRUTH)

print(f"\nTotal sequences in merged stats: {len(df_stats)}")
print(f"Total subjects in merged stats: {df_stats['subject_id'].nunique()}")
print(f"Total entries in ground truth: {len(df_ground_truth)}")
print(f"Unique subjects in ground truth: {df_ground_truth['subject_id'].nunique()}")

# Create pairing matrix
subjects = sorted(df_stats['subject_id'].unique())
sequence_types = ['T1', 'T2', 'SWI']

pairing_data = []

for subject in subjects:
    subject_data = df_stats[df_stats['subject_id'] == subject]
    
    row = {'subject_id': subject}
    
    for seq_type in sequence_types:
        has_conv = len(subject_data[subject_data['sequence'] == f'{seq_type}_conv']) > 0
        has_stage = len(subject_data[subject_data['sequence'] == f'{seq_type}_STAGE']) > 0
        
        if has_conv and has_stage:
            status = 'PAIRED'
        elif has_conv:
            status = 'CONV_ONLY'
        elif has_stage:
            status = 'STAGE_ONLY'
        else:
            status = 'MISSING'
        
        row[f'{seq_type}_status'] = status
        row[f'{seq_type}_conv'] = has_conv
        row[f'{seq_type}_stage'] = has_stage
    
    pairing_data.append(row)

df_pairing = pd.DataFrame(pairing_data)

# Summary statistics
print("\n" + "=" * 100)
print("PAIRING SUMMARY BY SEQUENCE TYPE")
print("=" * 100)

for seq_type in sequence_types:
    print(f"\n{seq_type}:")
    status_counts = df_pairing[f'{seq_type}_status'].value_counts()
    print(f"  PAIRED:     {status_counts.get('PAIRED', 0)}")
    print(f"  CONV_ONLY:  {status_counts.get('CONV_ONLY', 0)}")
    print(f"  STAGE_ONLY: {status_counts.get('STAGE_ONLY', 0)}")
    print(f"  MISSING:    {status_counts.get('MISSING', 0)}")

# List unpaired subjects
print("\n" + "=" * 100)
print("UNPAIRED SUBJECTS (CONV_ONLY or STAGE_ONLY)")
print("=" * 100)

for seq_type in sequence_types:
    unpaired = df_pairing[df_pairing[f'{seq_type}_status'].isin(['CONV_ONLY', 'STAGE_ONLY'])]
    
    if len(unpaired) > 0:
        print(f"\n{seq_type} - {len(unpaired)} unpaired subjects:")
        print("-" * 100)
        for _, row in unpaired.iterrows():
            subject = row['subject_id']
            status = row[f'{seq_type}_status']
            print(f"  {subject}: {status}")

# Check ground truth for these unpaired subjects
print("\n" + "=" * 100)
print("GROUND TRUTH CHECK FOR UNPAIRED SUBJECTS")
print("=" * 100)

all_mismatches = []

for seq_type in sequence_types:
    unpaired = df_pairing[df_pairing[f'{seq_type}_status'].isin(['CONV_ONLY', 'STAGE_ONLY'])]
    
    if len(unpaired) > 0:
        print(f"\n{seq_type} Unpaired Subjects - Ground Truth Analysis:")
        print("-" * 100)
        
        for _, row in unpaired.iterrows():
            subject = row['subject_id']
            status = row[f'{seq_type}_status']
            
            # Check what's in ground truth for this subject
            gt_subject = df_ground_truth[df_ground_truth['subject_id'] == subject]
            
            conv_gt = gt_subject[gt_subject['sequence_type'] == f'{seq_type}_conv']
            stage_gt = gt_subject[gt_subject['sequence_type'] == f'{seq_type}_STAGE']
            
            print(f"\n  {subject} ({status}):")
            print(f"    Ground truth has {seq_type}_conv:  {len(conv_gt) > 0} (Series: {conv_gt['series_number'].values.tolist() if len(conv_gt) > 0 else 'N/A'})")
            print(f"    Ground truth has {seq_type}_STAGE: {len(stage_gt) > 0} (Series: {stage_gt['series_number'].values.tolist() if len(stage_gt) > 0 else 'N/A'})")
            print(f"    Current stats has {seq_type}_conv:  {row[f'{seq_type}_conv']}")
            print(f"    Current stats has {seq_type}_STAGE: {row[f'{seq_type}_stage']}")
            
            # Check if there's a mismatch
            mismatch = False
            if len(conv_gt) > 0 and not row[f'{seq_type}_conv']:
                print(f"    ⚠️  MISSING: Ground truth has {seq_type}_conv but not in current stats!")
                mismatch = True
            if len(stage_gt) > 0 and not row[f'{seq_type}_stage']:
                print(f"    ⚠️  MISSING: Ground truth has {seq_type}_STAGE but not in current stats!")
                mismatch = True
                
            # Check on disk
            subject_dir = ORGANIZED_DATA_DIR / subject
            if subject_dir.exists():
                conv_dir = subject_dir / f'{seq_type}_conv'
                stage_dir = subject_dir / f'{seq_type}_STAGE'
                print(f"    On disk: {seq_type}_conv folder exists: {conv_dir.exists()}")
                print(f"    On disk: {seq_type}_STAGE folder exists: {stage_dir.exists()}")
                
            if mismatch:
                all_mismatches.append({
                    'subject_id': subject,
                    'sequence': seq_type,
                    'status': status,
                    'gt_conv': len(conv_gt) > 0,
                    'gt_stage': len(stage_gt) > 0,
                    'stats_conv': row[f'{seq_type}_conv'],
                    'stats_stage': row[f'{seq_type}_stage']
                })

# Check for subjects in ground truth but not in current stats
print("\n" + "=" * 100)
print("SUBJECTS IN GROUND TRUTH BUT MISSING FROM CURRENT STATS")
print("=" * 100)

gt_subjects = set(df_ground_truth['subject_id'].unique())
stats_subjects = set(df_stats['subject_id'].unique())
missing_subjects = gt_subjects - stats_subjects

if len(missing_subjects) > 0:
    print(f"\nFound {len(missing_subjects)} subjects in ground truth but not in current stats:")
    for subject in sorted(missing_subjects):
        gt_seqs = df_ground_truth[df_ground_truth['subject_id'] == subject]
        seq_types_available = gt_seqs['sequence_type'].unique()
        print(f"  {subject}: {', '.join(seq_types_available)}")
else:
    print("\nNo subjects missing from current stats")

# Summary of mismatches
if len(all_mismatches) > 0:
    print("\n" + "=" * 100)
    print(f"SUMMARY: {len(all_mismatches)} MISMATCHES FOUND")
    print("=" * 100)
    df_mismatches = pd.DataFrame(all_mismatches)
    print(df_mismatches.to_string(index=False))

# Save pairing audit
output_file = BASE_DIR / 'output' / 'statistics' / 'subject_pairing_audit.csv'
df_pairing.to_csv(output_file, index=False)
print(f"\n✓ Saved pairing audit: {output_file}")

print("\n" + "=" * 100)
print("✓ Pairing audit complete")
print("=" * 100)
