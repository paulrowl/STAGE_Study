#!/usr/bin/env python3
"""
Print comprehensive updated statistics after recovery
"""
import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats

BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
PAIRED_DATA = BASE_DIR / 'output' / 'statistics' / 'paired_comparisons_MERGED.csv'
MERGED_STATS = BASE_DIR / 'output' / 'statistics' / 'gm_wm_tissue_stats_MERGED.csv'
EXPERT_SCORES = BASE_DIR / 'output' / 'statistics' / 'intensity_with_expert_scores.csv'

print("=" * 100)
print("UPDATED STATISTICAL ANALYSIS - STAGE STUDY")
print("After Recovery of 2 Missing T1_conv Sequences")
print("=" * 100)

# Load data
df_paired = pd.read_csv(PAIRED_DATA)
df_stats = pd.read_csv(MERGED_STATS)
df_expert = pd.read_csv(EXPERT_SCORES)

print(f"\n{'='*100}")
print("DATASET OVERVIEW")
print(f"{'='*100}")
print(f"\nTotal Sequences: {len(df_stats)}")
print(f"Total Subjects: {df_stats['subject_id'].nunique()}")
print(f"Total Paired Comparisons: {len(df_paired)}")

print("\nSequences by Type:")
for seq_type in ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']:
    count = len(df_stats[df_stats['sequence'] == seq_type])
    print(f"  {seq_type:12s}: {count:3d} sequences")

print("\nPaired Comparisons by Sequence:")
for seq_type in ['T1', 'T2', 'SWI']:
    count = len(df_paired[df_paired['sequence_type'] == seq_type])
    print(f"  {seq_type:12s}: {count:3d} pairs")

# Paired t-tests
print(f"\n{'='*100}")
print("PAIRED T-TEST RESULTS: Conventional vs STAGE")
print(f"{'='*100}")

for seq_type in ['T1', 'T2', 'SWI']:
    data = df_paired[df_paired['sequence_type'] == seq_type]
    
    if len(data) < 3:
        continue
    
    print(f"\n{seq_type} Sequences (n={len(data)} pairs):")
    print(f"{'-'*100}")
    
    # Gray Matter
    gm_conv = data['conv_gm_mean'].values
    gm_stage = data['stage_gm_mean'].values
    t_stat, p_val = stats.ttest_rel(gm_conv, gm_stage)
    mean_diff = np.mean(gm_stage - gm_conv)
    pct_change = (mean_diff / np.mean(gm_conv)) * 100
    
    print(f"\n  Gray Matter Intensity:")
    print(f"    Conventional:  {np.mean(gm_conv):8.2f} ± {np.std(gm_conv):6.2f}")
    print(f"    STAGE:         {np.mean(gm_stage):8.2f} ± {np.std(gm_stage):6.2f}")
    print(f"    Mean Diff:     {mean_diff:8.2f} ({pct_change:+.1f}%)")
    print(f"    t-statistic:   {t_stat:8.3f}")
    print(f"    p-value:       {p_val:.6f} {'***' if p_val < 0.001 else '**' if p_val < 0.01 else '*' if p_val < 0.05 else 'ns'}")
    
    # White Matter
    wm_conv = data['conv_wm_mean'].values
    wm_stage = data['stage_wm_mean'].values
    t_stat, p_val = stats.ttest_rel(wm_conv, wm_stage)
    mean_diff = np.mean(wm_stage - wm_conv)
    pct_change = (mean_diff / np.mean(wm_conv)) * 100
    
    print(f"\n  White Matter Intensity:")
    print(f"    Conventional:  {np.mean(wm_conv):8.2f} ± {np.std(wm_conv):6.2f}")
    print(f"    STAGE:         {np.mean(wm_stage):8.2f} ± {np.std(wm_stage):6.2f}")
    print(f"    Mean Diff:     {mean_diff:8.2f} ({pct_change:+.1f}%)")
    print(f"    t-statistic:   {t_stat:8.3f}")
    print(f"    p-value:       {p_val:.6f} {'***' if p_val < 0.001 else '**' if p_val < 0.01 else '*' if p_val < 0.05 else 'ns'}")
    
    # GM/WM Ratio
    ratio_conv = data['conv_gm_wm_ratio'].values
    ratio_stage = data['stage_gm_wm_ratio'].values
    t_stat, p_val = stats.ttest_rel(ratio_conv, ratio_stage)
    mean_diff = np.mean(ratio_stage - ratio_conv)
    pct_change = (mean_diff / np.mean(ratio_conv)) * 100
    
    print(f"\n  GM/WM Ratio (Tissue Contrast):")
    print(f"    Conventional:  {np.mean(ratio_conv):8.4f} ± {np.std(ratio_conv):6.4f}")
    print(f"    STAGE:         {np.mean(ratio_stage):8.4f} ± {np.std(ratio_stage):6.4f}")
    print(f"    Mean Diff:     {mean_diff:8.4f} ({pct_change:+.1f}%)")
    print(f"    t-statistic:   {t_stat:8.3f}")
    print(f"    p-value:       {p_val:.6f} {'***' if p_val < 0.001 else '**' if p_val < 0.01 else '*' if p_val < 0.05 else 'ns'}")

# Pearson correlations
print(f"\n{'='*100}")
print("PEARSON CORRELATIONS: Conventional vs STAGE")
print(f"{'='*100}")

for seq_type in ['T1', 'T2', 'SWI']:
    data = df_paired[df_paired['sequence_type'] == seq_type]
    
    if len(data) < 3:
        continue
    
    print(f"\n{seq_type} (n={len(data)}):")
    print(f"{'-'*100}")
    
    # GM correlation
    r, p = stats.pearsonr(data['conv_gm_mean'], data['stage_gm_mean'])
    print(f"  Gray Matter:   r = {r:.4f}, p = {p:.6f} {'***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else 'ns'}")
    
    # WM correlation
    r, p = stats.pearsonr(data['conv_wm_mean'], data['stage_wm_mean'])
    print(f"  White Matter:  r = {r:.4f}, p = {p:.6f} {'***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else 'ns'}")
    
    # Ratio correlation
    r, p = stats.pearsonr(data['conv_gm_wm_ratio'], data['stage_gm_wm_ratio'])
    print(f"  GM/WM Ratio:   r = {r:.4f}, p = {p:.6f} {'***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else 'ns'}")

# Expert score correlations
print(f"\n{'='*100}")
print("EXPERT REVIEWER SCORE CORRELATIONS")
print(f"{'='*100}")

print(f"\nSequences with expert scores: {len(df_expert)}")
print(f"Subjects with expert scores: {df_expert['subject_id'].nunique()}")

for seq_type in ['T1', 'T2', 'SWI']:
    print(f"\n{seq_type} Sequences:")
    print(f"{'-'*100}")
    
    for protocol in ['conv', 'STAGE']:
        data = df_expert[df_expert['sequence'] == f'{seq_type}_{protocol}']
        
        if len(data) < 3:
            continue
        
        print(f"\n  {protocol.upper()} (n={len(data)}):")
        
        # Only calculate if we have valid data
        valid_data = data.dropna(subset=['gm_wm_ratio', 'Q1', 'Q2', 'Q3'])
        
        if len(valid_data) >= 3:
            for q in ['Q1', 'Q2', 'Q3']:
                r, p = stats.pearsonr(valid_data[q], valid_data['gm_wm_ratio'])
                sig = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else 'ns'
                print(f"    {q} vs GM/WM ratio: r = {r:7.3f}, p = {p:.4f} {sig}")
        else:
            print(f"    Insufficient data for correlation (n={len(valid_data)})")

print(f"\n{'='*100}")
print("RECOVERY IMPACT")
print(f"{'='*100}")

print("\nBefore Recovery:")
print("  Total sequences: 238")
print("  T1 pairs: 40")
print("  T2 pairs: 31")
print("  SWI pairs: 39")
print("  Total pairs: 110")

print("\nAfter Recovery:")
print(f"  Total sequences: {len(df_stats)} (+2)")
print(f"  T1 pairs: {len(df_paired[df_paired['sequence_type'] == 'T1'])} (+2, +5.0%)")
print(f"  T2 pairs: {len(df_paired[df_paired['sequence_type'] == 'T2'])}")
print(f"  SWI pairs: {len(df_paired[df_paired['sequence_type'] == 'SWI'])}")
print(f"  Total pairs: {len(df_paired)} (+2, +1.8%)")

print("\nRecovered Subjects:")
print("  Anon13609 - T1_conv (Series: 1000C9D0)")
print("  Anon21108 - T1_conv (Series: 19)")

print(f"\n{'='*100}")
print("✓ Analysis Complete")
print(f"{'='*100}")
print(f"\nUpdated PDF Report: {BASE_DIR}/output/visualizations/STAGE_Study_Comprehensive_Report.pdf")
print(f"Updated Data Files:")
print(f"  - {BASE_DIR}/output/statistics/gm_wm_tissue_stats_MERGED.csv")
print(f"  - {BASE_DIR}/output/statistics/paired_comparisons_MERGED.csv")
