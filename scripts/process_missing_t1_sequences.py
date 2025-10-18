#!/usr/bin/env python3
"""
Process the 2 missing T1_conv sequences and add to merged statistics
"""
import nibabel as nib
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
NIFTI_DIR = BASE_DIR / 'output' / 'nifti'
MASK_DIR = BASE_DIR / 'output' / 'brain_masks'
MERGED_STATS = BASE_DIR / 'output' / 'statistics' / 'gm_wm_tissue_stats_MERGED.csv'
PAIRED_OUTPUT = BASE_DIR / 'output' / 'statistics' / 'paired_comparisons_MERGED.csv'

# Subjects to process
MISSING_SEQUENCES = [
    ('Anon13609', 'T1_conv'),
    ('Anon21108', 'T1_conv')
]

print("=" * 100)
print("PROCESSING MISSING T1_conv SEQUENCES")
print("=" * 100)

def calculate_tissue_stats(nifti_file, mask_file):
    """Calculate GM/WM tissue statistics from NIfTI and mask"""
    
    # Load data
    img = nib.load(nifti_file)
    data = img.get_fdata()
    
    mask_img = nib.load(mask_file)
    mask = mask_img.get_fdata()
    
    # Get brain voxels
    brain_voxels = data[mask > 0]
    
    if len(brain_voxels) == 0:
        return None
    
    # Tissue segmentation using percentile-based thresholding
    # GM: 60-95th percentile (higher intensity)
    # WM: 25-60th percentile (lower intensity)
    p25 = np.percentile(brain_voxels, 25)
    p60 = np.percentile(brain_voxels, 60)
    p95 = np.percentile(brain_voxels, 95)
    
    gm_mask = (data >= p60) & (data <= p95) & (mask > 0)
    wm_mask = (data >= p25) & (data < p60) & (mask > 0)
    
    gm_voxels = data[gm_mask]
    wm_voxels = data[wm_mask]
    
    if len(gm_voxels) == 0 or len(wm_voxels) == 0:
        return None
    
    stats = {
        'gm_mean': np.mean(gm_voxels),
        'gm_std': np.std(gm_voxels),
        'gm_voxel_count': len(gm_voxels),
        'wm_mean': np.mean(wm_voxels),
        'wm_std': np.std(wm_voxels),
        'wm_voxel_count': len(wm_voxels),
        'gm_wm_ratio': np.mean(gm_voxels) / np.mean(wm_voxels)
    }
    
    return stats

# Process each missing sequence
new_stats = []

for subject_id, sequence in MISSING_SEQUENCES:
    print(f"\nProcessing {subject_id}/{sequence}...")

    # Use .nii.nii.gz file which contains the actual brain image (not the mask)
    nifti_file = NIFTI_DIR / subject_id / f"{sequence}.nii.nii.gz"
    mask_file = MASK_DIR / subject_id / f"{sequence}_mask.nii.gz"
    
    if not nifti_file.exists():
        print(f"  ✗ NIfTI file not found: {nifti_file}")
        continue
    
    if not mask_file.exists():
        print(f"  ✗ Mask file not found: {mask_file}")
        continue
    
    print(f"  Reading NIfTI: {nifti_file.name}")
    print(f"  Reading mask: {mask_file.name}")
    
    stats = calculate_tissue_stats(nifti_file, mask_file)
    
    if stats is None:
        print(f"  ✗ Failed to calculate tissue statistics")
        continue
    
    print(f"  ✓ GM mean: {stats['gm_mean']:.2f}")
    print(f"  ✓ WM mean: {stats['wm_mean']:.2f}")
    print(f"  ✓ GM/WM ratio: {stats['gm_wm_ratio']:.4f}")
    print(f"  ✓ GM voxels: {stats['gm_voxel_count']:,}")
    print(f"  ✓ WM voxels: {stats['wm_voxel_count']:,}")
    
    new_stats.append({
        'subject_id': subject_id,
        'sequence': sequence,
        **stats
    })

if len(new_stats) == 0:
    print("\n✗ No sequences were processed successfully")
    exit(1)

print(f"\n✓ Successfully processed {len(new_stats)} sequences")

# Load existing merged stats
print("\nMerging with existing statistics...")
df_existing = pd.read_csv(MERGED_STATS)
print(f"  Existing: {len(df_existing)} sequences")

# Add new stats
df_new = pd.DataFrame(new_stats)
df_merged = pd.concat([df_existing, df_new], ignore_index=True)
df_merged = df_merged.sort_values(['subject_id', 'sequence']).reset_index(drop=True)

print(f"  New total: {len(df_merged)} sequences (+{len(new_stats)})")

# Save updated merged stats
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_file = BASE_DIR / 'output' / 'statistics' / f'gm_wm_tissue_stats_MERGED_backup_{timestamp}.csv'
df_existing.to_csv(backup_file, index=False)
print(f"  ✓ Backed up original to: {backup_file.name}")

df_merged.to_csv(MERGED_STATS, index=False)
print(f"  ✓ Saved updated stats to: {MERGED_STATS.name}")

# Regenerate paired comparisons
print("\nRegenerating paired comparisons...")

paired_data = []

for subject_id in df_merged['subject_id'].unique():
    subject_data = df_merged[df_merged['subject_id'] == subject_id]
    
    # T1 pairs
    t1_conv = subject_data[subject_data['sequence'] == 'T1_conv']
    t1_stage = subject_data[subject_data['sequence'] == 'T1_STAGE']
    if not t1_conv.empty and not t1_stage.empty:
        paired_data.append({
            'subject_id': subject_id,
            'sequence_type': 'T1',
            'conv_gm_mean': t1_conv.iloc[0]['gm_mean'],
            'stage_gm_mean': t1_stage.iloc[0]['gm_mean'],
            'conv_wm_mean': t1_conv.iloc[0]['wm_mean'],
            'stage_wm_mean': t1_stage.iloc[0]['wm_mean'],
            'conv_gm_wm_ratio': t1_conv.iloc[0]['gm_wm_ratio'],
            'stage_gm_wm_ratio': t1_stage.iloc[0]['gm_wm_ratio'],
        })
    
    # T2 pairs
    t2_conv = subject_data[subject_data['sequence'] == 'T2_conv']
    t2_stage = subject_data[subject_data['sequence'] == 'T2_STAGE']
    if not t2_conv.empty and not t2_stage.empty:
        paired_data.append({
            'subject_id': subject_id,
            'sequence_type': 'T2',
            'conv_gm_mean': t2_conv.iloc[0]['gm_mean'],
            'stage_gm_mean': t2_stage.iloc[0]['gm_mean'],
            'conv_wm_mean': t2_conv.iloc[0]['wm_mean'],
            'stage_wm_mean': t2_stage.iloc[0]['wm_mean'],
            'conv_gm_wm_ratio': t2_conv.iloc[0]['gm_wm_ratio'],
            'stage_gm_wm_ratio': t2_stage.iloc[0]['gm_wm_ratio'],
        })
    
    # SWI pairs
    swi_conv = subject_data[subject_data['sequence'] == 'SWI_conv']
    swi_stage = subject_data[subject_data['sequence'] == 'SWI_STAGE']
    if not swi_conv.empty and not swi_stage.empty:
        paired_data.append({
            'subject_id': subject_id,
            'sequence_type': 'SWI',
            'conv_gm_mean': swi_conv.iloc[0]['gm_mean'],
            'stage_gm_mean': swi_stage.iloc[0]['gm_mean'],
            'conv_wm_mean': swi_conv.iloc[0]['wm_mean'],
            'stage_wm_mean': swi_stage.iloc[0]['wm_mean'],
            'conv_gm_wm_ratio': swi_conv.iloc[0]['gm_wm_ratio'],
            'stage_gm_wm_ratio': swi_stage.iloc[0]['gm_wm_ratio'],
        })

df_paired = pd.DataFrame(paired_data)

# Backup original paired file
paired_backup = BASE_DIR / 'output' / 'statistics' / f'paired_comparisons_MERGED_backup_{timestamp}.csv'
if PAIRED_OUTPUT.exists():
    df_old_paired = pd.read_csv(PAIRED_OUTPUT)
    df_old_paired.to_csv(paired_backup, index=False)
    print(f"  ✓ Backed up original paired data to: {paired_backup.name}")

df_paired.to_csv(PAIRED_OUTPUT, index=False)
print(f"  ✓ Saved updated paired comparisons to: {PAIRED_OUTPUT.name}")

# Summary
print("\n" + "=" * 100)
print("SUMMARY")
print("=" * 100)

print("\nPaired comparisons by type:")
for seq_type in ['T1', 'T2', 'SWI']:
    count = len(df_paired[df_paired['sequence_type'] == seq_type])
    print(f"  {seq_type}: {count} pairs")

print(f"\nTotal paired comparisons: {len(df_paired)}")

print("\n" + "=" * 100)
print("✓ PROCESSING COMPLETE")
print("=" * 100)
print("\nFiles updated:")
print(f"  1. {MERGED_STATS}")
print(f"  2. {PAIRED_OUTPUT}")
print(f"\nBackups created:")
print(f"  1. {backup_file.name}")
print(f"  2. {paired_backup.name}")
