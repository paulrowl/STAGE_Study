#!/usr/bin/env python3
"""
Create publication-quality visualizations from merged STAGE study data
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats

# Configuration
sns.set_style("whitegrid")
sns.set_context("paper", font_scale=1.3)
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['savefig.bbox'] = 'tight'

# Paths
BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
PAIRED_DATA = BASE_DIR / 'output' / 'statistics' / 'paired_comparisons_MERGED.csv'
OUTPUT_DIR = BASE_DIR / 'output' / 'visualizations'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("STAGE MRI Study - Visualization Generation")
print("=" * 80)

# Load data
print("\nLoading paired comparisons data...")
df = pd.read_csv(PAIRED_DATA)

# Remove empty rows
df = df.dropna(subset=['conv_gm_mean', 'stage_gm_mean', 'conv_wm_mean', 'stage_wm_mean'])
print(f"Valid paired comparisons: {len(df)}")

sequence_types = ['T1', 'T2', 'SWI']
colors = {'T1': '#2ecc71', 'T2': '#3498db', 'SWI': '#e74c3c'}

# Count samples per sequence
for seq_type in sequence_types:
    n = len(df[df['sequence_type'] == seq_type])
    print(f"  {seq_type}: n={n}")

print("\n" + "=" * 80)

# ============================================================================
# FIGURE 1: Intensity Correlations (GM and WM)
# ============================================================================
print("\nGenerating Figure 1: Intensity Correlations...")

fig, axes = plt.subplots(2, 3, figsize=(15, 10))
fig.suptitle('STAGE vs Conventional: Gray Matter and White Matter Intensity Correlations',
             fontsize=16, fontweight='bold', y=0.98)

for idx, seq_type in enumerate(sequence_types):
    seq_data = df[df['sequence_type'] == seq_type]

    if len(seq_data) < 2:
        continue

    # GM correlation (top row)
    ax = axes[0, idx]
    ax.scatter(seq_data['conv_gm_mean'], seq_data['stage_gm_mean'],
              alpha=0.7, s=120, color=colors[seq_type], edgecolors='black', linewidth=1.5)

    # Add identity line
    min_val = min(seq_data['conv_gm_mean'].min(), seq_data['stage_gm_mean'].min())
    max_val = max(seq_data['conv_gm_mean'].max(), seq_data['stage_gm_mean'].max())
    ax.plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.3, linewidth=2, label='Identity')

    # Regression line
    z = np.polyfit(seq_data['conv_gm_mean'], seq_data['stage_gm_mean'], 1)
    p = np.poly1d(z)
    x_line = np.linspace(min_val, max_val, 100)
    ax.plot(x_line, p(x_line), 'r-', alpha=0.6, linewidth=2,
           label=f'Fit: y={z[0]:.2f}x+{z[1]:.0f}')

    # Statistics
    r, p_val = stats.pearsonr(seq_data['conv_gm_mean'], seq_data['stage_gm_mean'])
    ax.text(0.05, 0.95, f'r = {r:.3f}\np = {p_val:.4f}',
           transform=ax.transAxes, verticalalignment='top',
           bbox=dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='black'),
           fontsize=11, fontweight='bold')

    ax.set_xlabel(f'{seq_type} Conventional GM Mean Intensity', fontsize=12, fontweight='bold')
    ax.set_ylabel(f'{seq_type} STAGE GM Mean Intensity', fontsize=12, fontweight='bold')
    ax.set_title(f'{seq_type}: Gray Matter (n={len(seq_data)})', fontsize=13, fontweight='bold')
    ax.legend(fontsize=10, loc='lower right')
    ax.grid(True, alpha=0.3)

    # WM correlation (bottom row)
    ax = axes[1, idx]
    ax.scatter(seq_data['conv_wm_mean'], seq_data['stage_wm_mean'],
              alpha=0.7, s=120, color=colors[seq_type], edgecolors='black', linewidth=1.5)

    # Add identity line
    min_val = min(seq_data['conv_wm_mean'].min(), seq_data['stage_wm_mean'].min())
    max_val = max(seq_data['conv_wm_mean'].max(), seq_data['stage_wm_mean'].max())
    ax.plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.3, linewidth=2, label='Identity')

    # Regression line
    z = np.polyfit(seq_data['conv_wm_mean'], seq_data['stage_wm_mean'], 1)
    p = np.poly1d(z)
    x_line = np.linspace(min_val, max_val, 100)
    ax.plot(x_line, p(x_line), 'r-', alpha=0.6, linewidth=2,
           label=f'Fit: y={z[0]:.2f}x+{z[1]:.0f}')

    # Statistics
    r, p_val = stats.pearsonr(seq_data['conv_wm_mean'], seq_data['stage_wm_mean'])
    ax.text(0.05, 0.95, f'r = {r:.3f}\np = {p_val:.4f}',
           transform=ax.transAxes, verticalalignment='top',
           bbox=dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='black'),
           fontsize=11, fontweight='bold')

    ax.set_xlabel(f'{seq_type} Conventional WM Mean Intensity', fontsize=12, fontweight='bold')
    ax.set_ylabel(f'{seq_type} STAGE WM Mean Intensity', fontsize=12, fontweight='bold')
    ax.set_title(f'{seq_type}: White Matter (n={len(seq_data)})', fontsize=13, fontweight='bold')
    ax.legend(fontsize=10, loc='lower right')
    ax.grid(True, alpha=0.3)

plt.tight_layout()
output_file = OUTPUT_DIR / 'figure1_intensity_correlations.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"✓ Saved: {output_file}")
plt.close()

# ============================================================================
# FIGURE 2: GM/WM Ratio Comparisons
# ============================================================================
print("\nGenerating Figure 2: GM/WM Ratio Comparisons...")

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle('STAGE vs Conventional: Gray Matter / White Matter Intensity Ratios',
             fontsize=16, fontweight='bold', y=1.02)

for idx, seq_type in enumerate(sequence_types):
    seq_data = df[df['sequence_type'] == seq_type]

    if len(seq_data) < 2:
        continue

    ax = axes[idx]

    # Prepare data
    conv_ratios = seq_data['conv_gm_wm_ratio'].values
    stage_ratios = seq_data['stage_gm_wm_ratio'].values

    positions = [1, 2]
    bp = ax.boxplot([conv_ratios, stage_ratios], positions=positions,
                     widths=0.5, patch_artist=True,
                     boxprops=dict(facecolor=colors[seq_type], alpha=0.6, linewidth=2),
                     medianprops=dict(color='red', linewidth=3),
                     whiskerprops=dict(linewidth=2),
                     capprops=dict(linewidth=2))

    # Add individual points with jitter
    for i, data in enumerate([conv_ratios, stage_ratios]):
        y = data
        x = np.random.normal(positions[i], 0.04, size=len(y))
        ax.scatter(x, y, alpha=0.5, s=60, color='black', zorder=3)

    # Statistical test
    t_stat, p_val = stats.ttest_rel(conv_ratios, stage_ratios)

    # Add significance annotation
    y_max = max(conv_ratios.max(), stage_ratios.max())
    y_line = y_max * 1.05
    ax.plot([1, 2], [y_line, y_line], 'k-', linewidth=2)

    if p_val < 0.001:
        sig_text = '***'
    elif p_val < 0.01:
        sig_text = '**'
    elif p_val < 0.05:
        sig_text = '*'
    else:
        sig_text = 'ns'

    ax.text(1.5, y_line * 1.02, sig_text, ha='center', va='bottom',
           fontsize=16, fontweight='bold')

    # Add statistics box
    ax.text(0.98, 0.98, f't = {t_stat:.3f}\np = {p_val:.4f}\nn = {len(seq_data)}',
           transform=ax.transAxes, verticalalignment='top', horizontalalignment='right',
           bbox=dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='black'),
           fontsize=11, fontweight='bold')

    ax.set_xticks([1, 2])
    ax.set_xticklabels(['Conventional', 'STAGE'], fontsize=12, fontweight='bold')
    ax.set_ylabel('GM/WM Intensity Ratio', fontsize=12, fontweight='bold')
    ax.set_title(f'{seq_type} (n={len(seq_data)})', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
output_file = OUTPUT_DIR / 'figure2_gm_wm_ratios.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"✓ Saved: {output_file}")
plt.close()

# ============================================================================
# FIGURE 3: Paired Differences (Bland-Altman style)
# ============================================================================
print("\nGenerating Figure 3: Bland-Altman Plots...")

fig, axes = plt.subplots(2, 3, figsize=(15, 10))
fig.suptitle('STAGE vs Conventional: Bland-Altman Analysis',
             fontsize=16, fontweight='bold', y=0.98)

for idx, seq_type in enumerate(sequence_types):
    seq_data = df[df['sequence_type'] == seq_type]

    if len(seq_data) < 2:
        continue

    # GM differences (top row)
    ax = axes[0, idx]
    mean_gm = (seq_data['conv_gm_mean'] + seq_data['stage_gm_mean']) / 2
    diff_gm = seq_data['stage_gm_mean'] - seq_data['conv_gm_mean']

    ax.scatter(mean_gm, diff_gm, alpha=0.7, s=120, color=colors[seq_type],
              edgecolors='black', linewidth=1.5)

    # Mean difference line
    mean_diff = diff_gm.mean()
    ax.axhline(mean_diff, color='blue', linestyle='-', linewidth=2, label=f'Mean: {mean_diff:.1f}')

    # Limits of agreement
    std_diff = diff_gm.std()
    ax.axhline(mean_diff + 1.96*std_diff, color='red', linestyle='--', linewidth=2,
              label=f'+1.96 SD: {mean_diff + 1.96*std_diff:.1f}')
    ax.axhline(mean_diff - 1.96*std_diff, color='red', linestyle='--', linewidth=2,
              label=f'-1.96 SD: {mean_diff - 1.96*std_diff:.1f}')
    ax.axhline(0, color='black', linestyle=':', linewidth=1, alpha=0.5)

    ax.set_xlabel('Mean GM Intensity', fontsize=12, fontweight='bold')
    ax.set_ylabel('Difference (STAGE - Conv)', fontsize=12, fontweight='bold')
    ax.set_title(f'{seq_type}: Gray Matter (n={len(seq_data)})', fontsize=13, fontweight='bold')
    ax.legend(fontsize=9, loc='best')
    ax.grid(True, alpha=0.3)

    # WM differences (bottom row)
    ax = axes[1, idx]
    mean_wm = (seq_data['conv_wm_mean'] + seq_data['stage_wm_mean']) / 2
    diff_wm = seq_data['stage_wm_mean'] - seq_data['conv_wm_mean']

    ax.scatter(mean_wm, diff_wm, alpha=0.7, s=120, color=colors[seq_type],
              edgecolors='black', linewidth=1.5)

    # Mean difference line
    mean_diff = diff_wm.mean()
    ax.axhline(mean_diff, color='blue', linestyle='-', linewidth=2, label=f'Mean: {mean_diff:.1f}')

    # Limits of agreement
    std_diff = diff_wm.std()
    ax.axhline(mean_diff + 1.96*std_diff, color='red', linestyle='--', linewidth=2,
              label=f'+1.96 SD: {mean_diff + 1.96*std_diff:.1f}')
    ax.axhline(mean_diff - 1.96*std_diff, color='red', linestyle='--', linewidth=2,
              label=f'-1.96 SD: {mean_diff - 1.96*std_diff:.1f}')
    ax.axhline(0, color='black', linestyle=':', linewidth=1, alpha=0.5)

    ax.set_xlabel('Mean WM Intensity', fontsize=12, fontweight='bold')
    ax.set_ylabel('Difference (STAGE - Conv)', fontsize=12, fontweight='bold')
    ax.set_title(f'{seq_type}: White Matter (n={len(seq_data)})', fontsize=13, fontweight='bold')
    ax.legend(fontsize=9, loc='best')
    ax.grid(True, alpha=0.3)

plt.tight_layout()
output_file = OUTPUT_DIR / 'figure3_bland_altman.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"✓ Saved: {output_file}")
plt.close()

# ============================================================================
# Print Statistical Summary
# ============================================================================
print("\n" + "=" * 80)
print("STATISTICAL SUMMARY")
print("=" * 80)

for seq_type in sequence_types:
    seq_data = df[df['sequence_type'] == seq_type]

    if len(seq_data) < 2:
        continue

    print(f"\n{seq_type} Sequences (n={len(seq_data)}):")
    print("-" * 80)

    # GM correlation
    r_gm, p_gm = stats.pearsonr(seq_data['conv_gm_mean'], seq_data['stage_gm_mean'])
    print(f"  GM Intensity Correlation: r = {r_gm:.3f}, p = {p_gm:.4f}")

    # WM correlation
    r_wm, p_wm = stats.pearsonr(seq_data['conv_wm_mean'], seq_data['stage_wm_mean'])
    print(f"  WM Intensity Correlation: r = {r_wm:.3f}, p = {p_wm:.4f}")

    # GM/WM ratio comparison
    t_stat, p_val = stats.ttest_rel(seq_data['conv_gm_wm_ratio'], seq_data['stage_gm_wm_ratio'])
    conv_mean = seq_data['conv_gm_wm_ratio'].mean()
    stage_mean = seq_data['stage_gm_wm_ratio'].mean()
    print(f"  GM/WM Ratio Conventional: {conv_mean:.3f} ± {seq_data['conv_gm_wm_ratio'].std():.3f}")
    print(f"  GM/WM Ratio STAGE:        {stage_mean:.3f} ± {seq_data['stage_gm_wm_ratio'].std():.3f}")
    print(f"  Paired t-test: t = {t_stat:.3f}, p = {p_val:.4f}", end="")

    if p_val < 0.001:
        print(" ***")
    elif p_val < 0.01:
        print(" **")
    elif p_val < 0.05:
        print(" *")
    else:
        print(" (ns)")

print("\n" + "=" * 80)
print("✓ All visualizations generated successfully")
print("=" * 80)
