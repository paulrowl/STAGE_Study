#!/usr/bin/env python3
"""
Analyze correlations between intensity metrics and expert reviewer scores
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats

# Configuration
sns.set_style("whitegrid")
sns.set_context("paper", font_scale=1.2)

# Paths
BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
MERGED_STATS = BASE_DIR / 'output' / 'statistics' / 'gm_wm_tissue_stats_MERGED.csv'
EXPERT_SCORES = BASE_DIR / 'output' / 'statistics' / 'neurorad_scores_unified.xlsx'
OUTPUT_DIR = BASE_DIR / 'output' / 'visualizations'

print("=" * 80)
print("EXPERT SCORE CORRELATION ANALYSIS")
print("=" * 80)

# Load data
print("\nLoading data...")
df_intensity = pd.read_csv(MERGED_STATS)
df_scores = pd.read_excel(EXPERT_SCORES)

# Rename columns
df_scores = df_scores.rename(columns={'rAccession': 'subject_id'})

print(f"Intensity data: {len(df_intensity)} sequences from {df_intensity['subject_id'].nunique()} subjects")
print(f"Expert scores: {len(df_scores)} evaluations from {df_scores['subject_id'].nunique()} subjects")

# Merge data
df_merged = df_intensity.merge(df_scores[['subject_id', 'Q1', 'Q2', 'Q3']],
                                on='subject_id', how='inner')

# Remove rows with missing GM/WM ratios
df_merged = df_merged.dropna(subset=['gm_wm_ratio', 'Q1', 'Q2', 'Q3'])

print(f"\nMerged data: {len(df_merged)} sequences with both intensity and scores")

# Count by sequence type
print("\nSequences with expert scores:")
for seq in ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']:
    count = len(df_merged[df_merged['sequence'] == seq])
    print(f"  {seq}: {count}")

# ============================================================================
# FIGURE 4: GM/WM Ratios vs Expert Scores
# ============================================================================
print("\nGenerating Figure 4: GM/WM Ratios vs Expert Scores...")

fig, axes = plt.subplots(3, 3, figsize=(16, 14))
fig.suptitle('GM/WM Intensity Ratios vs Expert Reviewer Scores',
             fontsize=18, fontweight='bold', y=0.995)

sequence_types = ['T1', 'T2', 'SWI']
colors = {'T1_conv': '#90EE90', 'T1_STAGE': '#2ecc71',
          'T2_conv': '#87CEEB', 'T2_STAGE': '#3498db',
          'SWI_conv': '#FFB6C1', 'SWI_STAGE': '#e74c3c'}

for row, seq_type in enumerate(sequence_types):
    # Filter data for this sequence type
    conv_data = df_merged[df_merged['sequence'] == f'{seq_type}_conv'].copy()
    stage_data = df_merged[df_merged['sequence'] == f'{seq_type}_STAGE'].copy()

    # Q1 Score
    ax = axes[row, 0]
    if len(conv_data) >= 3:
        ax.scatter(conv_data['Q1'], conv_data['gm_wm_ratio'],
                  alpha=0.6, s=100, color=colors[f'{seq_type}_conv'],
                  edgecolors='black', linewidth=1, label='Conventional')
        r_conv, p_conv = stats.pearsonr(conv_data['Q1'], conv_data['gm_wm_ratio'])
        show_conv = True
    else:
        show_conv = False

    if len(stage_data) >= 3:
        ax.scatter(stage_data['Q1'], stage_data['gm_wm_ratio'],
                  alpha=0.6, s=100, color=colors[f'{seq_type}_STAGE'],
                  edgecolors='black', linewidth=1, label='STAGE', marker='s')
        r_stage, p_stage = stats.pearsonr(stage_data['Q1'], stage_data['gm_wm_ratio'])
        show_stage = True
    else:
        show_stage = False

    # Add statistics
    if show_conv:
        ax.text(0.05, 0.95, f'Conv: r={r_conv:.3f}, p={p_conv:.3f}',
               transform=ax.transAxes, va='top', fontsize=9,
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    if show_stage:
        ax.text(0.05, 0.85, f'STAGE: r={r_stage:.3f}, p={p_stage:.3f}',
               transform=ax.transAxes, va='top', fontsize=9,
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    ax.set_xlabel('Q1 Score', fontsize=11, fontweight='bold')
    ax.set_ylabel('GM/WM Ratio', fontsize=11, fontweight='bold')
    ax.set_title(f'{seq_type}: Q1 (n_conv={len(conv_data)}, n_stage={len(stage_data)})',
                fontsize=12, fontweight='bold')
    ax.legend(loc='lower right', fontsize=9)
    ax.grid(True, alpha=0.3)

    # Q2 Score
    ax = axes[row, 1]
    if len(conv_data) > 0:
        ax.scatter(conv_data['Q2'], conv_data['gm_wm_ratio'],
                  alpha=0.6, s=100, color=colors[f'{seq_type}_conv'],
                  edgecolors='black', linewidth=1, label='Conventional')
        r_conv, p_conv = stats.pearsonr(conv_data['Q2'], conv_data['gm_wm_ratio'])

    if len(stage_data) > 0:
        ax.scatter(stage_data['Q2'], stage_data['gm_wm_ratio'],
                  alpha=0.6, s=100, color=colors[f'{seq_type}_STAGE'],
                  edgecolors='black', linewidth=1, label='STAGE', marker='s')
        r_stage, p_stage = stats.pearsonr(stage_data['Q2'], stage_data['gm_wm_ratio'])

    if len(conv_data) > 0:
        ax.text(0.05, 0.95, f'Conv: r={r_conv:.3f}, p={p_conv:.3f}',
               transform=ax.transAxes, va='top', fontsize=9,
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    if len(stage_data) > 0:
        ax.text(0.05, 0.85, f'STAGE: r={r_stage:.3f}, p={p_stage:.3f}',
               transform=ax.transAxes, va='top', fontsize=9,
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    ax.set_xlabel('Q2 Score', fontsize=11, fontweight='bold')
    ax.set_ylabel('GM/WM Ratio', fontsize=11, fontweight='bold')
    ax.set_title(f'{seq_type}: Q2 (n_conv={len(conv_data)}, n_stage={len(stage_data)})',
                fontsize=12, fontweight='bold')
    ax.legend(loc='lower right', fontsize=9)
    ax.grid(True, alpha=0.3)

    # Q3 Score
    ax = axes[row, 2]
    if len(conv_data) > 0:
        ax.scatter(conv_data['Q3'], conv_data['gm_wm_ratio'],
                  alpha=0.6, s=100, color=colors[f'{seq_type}_conv'],
                  edgecolors='black', linewidth=1, label='Conventional')
        r_conv, p_conv = stats.pearsonr(conv_data['Q3'], conv_data['gm_wm_ratio'])

    if len(stage_data) > 0:
        ax.scatter(stage_data['Q3'], stage_data['gm_wm_ratio'],
                  alpha=0.6, s=100, color=colors[f'{seq_type}_STAGE'],
                  edgecolors='black', linewidth=1, label='STAGE', marker='s')
        r_stage, p_stage = stats.pearsonr(stage_data['Q3'], stage_data['gm_wm_ratio'])

    if len(conv_data) > 0:
        ax.text(0.05, 0.95, f'Conv: r={r_conv:.3f}, p={p_conv:.3f}',
               transform=ax.transAxes, va='top', fontsize=9,
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    if len(stage_data) > 0:
        ax.text(0.05, 0.85, f'STAGE: r={r_stage:.3f}, p={p_stage:.3f}',
               transform=ax.transAxes, va='top', fontsize=9,
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    ax.set_xlabel('Q3 Score', fontsize=11, fontweight='bold')
    ax.set_ylabel('GM/WM Ratio', fontsize=11, fontweight='bold')
    ax.set_title(f'{seq_type}: Q3 (n_conv={len(conv_data)}, n_stage={len(stage_data)})',
                fontsize=12, fontweight='bold')
    ax.legend(loc='lower right', fontsize=9)
    ax.grid(True, alpha=0.3)

plt.tight_layout()
output_file = OUTPUT_DIR / 'figure4_expert_score_correlations.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"✓ Saved: {output_file}")
plt.close()

# ============================================================================
# Print Statistical Summary
# ============================================================================
print("\n" + "=" * 80)
print("CORRELATION STATISTICS")
print("=" * 80)

for seq_type in sequence_types:
    print(f"\n{seq_type} Sequences:")
    print("-" * 80)

    conv_data = df_merged[df_merged['sequence'] == f'{seq_type}_conv']
    stage_data = df_merged[df_merged['sequence'] == f'{seq_type}_STAGE']

    print(f"  Conventional (n={len(conv_data)}):")
    if len(conv_data) >= 3:
        for q in ['Q1', 'Q2', 'Q3']:
            r, p = stats.pearsonr(conv_data[q], conv_data['gm_wm_ratio'])
            sig = "*" if p < 0.05 else ""
            print(f"    {q} vs GM/WM ratio: r={r:.3f}, p={p:.4f}{sig}")
    else:
        print("    Insufficient data")

    print(f"  STAGE (n={len(stage_data)}):")
    if len(stage_data) >= 3:
        for q in ['Q1', 'Q2', 'Q3']:
            r, p = stats.pearsonr(stage_data[q], stage_data['gm_wm_ratio'])
            sig = "*" if p < 0.05 else ""
            print(f"    {q} vs GM/WM ratio: r={r:.3f}, p={p:.4f}{sig}")
    else:
        print("    Insufficient data")

print("\n" + "=" * 80)
print("✓ Expert score correlation analysis complete")
print("=" * 80)

# Save merged data for reference
output_csv = BASE_DIR / 'output' / 'statistics' / 'intensity_with_expert_scores.csv'
df_merged.to_csv(output_csv, index=False)
print(f"\n✓ Saved merged data: {output_csv}")
