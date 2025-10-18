#!/usr/bin/env python3
"""
Create visualizations for merged data
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 10)

# File paths
BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
PAIRED_DATA = BASE_DIR / 'output' / 'statistics' / 'paired_comparisons_MERGED.csv'
OUTPUT_DIR = BASE_DIR / 'output' / 'visualizations'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("Loading paired comparisons...")
df = pd.read_csv(PAIRED_DATA)

# Drop rows with any NaN values in the numeric columns
print(f"Loaded {len(df)} rows")
df = df.dropna(subset=['conv_gm_mean', 'stage_gm_mean', 'conv_wm_mean', 'stage_wm_mean'])
print(f"After removing empty rows: {len(df)} valid paired comparisons")

print(f"  T1: {len(df[df['sequence_type'] == 'T1'])}")
print(f"  T2: {len(df[df['sequence_type'] == 'T2'])}")
print(f"  SWI: {len(df[df['sequence_type'] == 'SWI'])}")

# Create comprehensive visualization
fig, axes = plt.subplots(3, 3, figsize=(18, 16))
fig.suptitle('STAGE vs Conventional Sequences: GM/WM Intensity Comparison (MERGED DATA)',
             fontsize=16, fontweight='bold', y=0.995)

sequence_types = ['T1', 'T2', 'SWI']
colors = {'T1': '#2ecc71', 'T2': '#3498db', 'SWI': '#e74c3c'}

for idx, seq_type in enumerate(sequence_types):
    seq_data = df[df['sequence_type'] == seq_type]

    # Skip if insufficient data
    if len(seq_data) < 2:
        print(f"⚠️  Skipping {seq_type} - insufficient data (n={len(seq_data)})")
        for col in range(3):
            axes[idx, col].text(0.5, 0.5, f'Insufficient data\n(n={len(seq_data)})',
                              transform=axes[idx, col].transAxes, ha='center', va='center',
                              fontsize=14, color='gray')
            axes[idx, col].set_title(f'{seq_type}: No data available')
        continue

    # 1. GM Means Scatter Plot
    ax = axes[idx, 0]
    ax.scatter(seq_data['conv_gm_mean'], seq_data['stage_gm_mean'],
              alpha=0.6, s=100, color=colors[seq_type], edgecolors='black', linewidth=1)

    # Add identity line
    min_val = min(seq_data['conv_gm_mean'].min(), seq_data['stage_gm_mean'].min())
    max_val = max(seq_data['conv_gm_mean'].max(), seq_data['stage_gm_mean'].max())
    ax.plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.3, label='Identity')

    # Regression line
    z = np.polyfit(seq_data['conv_gm_mean'], seq_data['stage_gm_mean'], 1)
    p = np.poly1d(z)
    x_line = np.linspace(min_val, max_val, 100)
    ax.plot(x_line, p(x_line), 'r-', alpha=0.5, label=f'Fit: y={z[0]:.2f}x+{z[1]:.1f}')

    # Correlation
    r, p_val = stats.pearsonr(seq_data['conv_gm_mean'], seq_data['stage_gm_mean'])
    ax.text(0.05, 0.95, f'r={r:.3f}\np={p_val:.4f}',
           transform=ax.transAxes, verticalalignment='top',
           bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    ax.set_xlabel(f'{seq_type} Conventional GM Mean')
    ax.set_ylabel(f'{seq_type} STAGE GM Mean')
    ax.set_title(f'{seq_type}: GM Mean Correlation (n={len(seq_data)})')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 2. WM Means Scatter Plot
    ax = axes[idx, 1]
    ax.scatter(seq_data['conv_wm_mean'], seq_data['stage_wm_mean'],
              alpha=0.6, s=100, color=colors[seq_type], edgecolors='black', linewidth=1)

    # Add identity line
    min_val = min(seq_data['conv_wm_mean'].min(), seq_data['stage_wm_mean'].min())
    max_val = max(seq_data['conv_wm_mean'].max(), seq_data['stage_wm_mean'].max())
    ax.plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.3, label='Identity')

    # Regression line
    z = np.polyfit(seq_data['conv_wm_mean'], seq_data['stage_wm_mean'], 1)
    p = np.poly1d(z)
    x_line = np.linspace(min_val, max_val, 100)
    ax.plot(x_line, p(x_line), 'r-', alpha=0.5, label=f'Fit: y={z[0]:.2f}x+{z[1]:.1f}')

    # Correlation
    r, p_val = stats.pearsonr(seq_data['conv_wm_mean'], seq_data['stage_wm_mean'])
    ax.text(0.05, 0.95, f'r={r:.3f}\np={p_val:.4f}',
           transform=ax.transAxes, verticalalignment='top',
           bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    ax.set_xlabel(f'{seq_type} Conventional WM Mean')
    ax.set_ylabel(f'{seq_type} STAGE WM Mean')
    ax.set_title(f'{seq_type}: WM Mean Correlation (n={len(seq_data)})')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 3. GM/WM Ratio Comparison
    ax = axes[idx, 2]

    # Prepare data for box plot
    conv_ratios = seq_data['conv_gm_wm_ratio'].values
    stage_ratios = seq_data['stage_gm_wm_ratio'].values

    positions = [1, 2]
    bp = ax.boxplot([conv_ratios, stage_ratios], positions=positions,
                     widths=0.6, patch_artist=True,
                     boxprops=dict(facecolor=colors[seq_type], alpha=0.6),
                     medianprops=dict(color='red', linewidth=2))

    # Add individual points
    for i, data in enumerate([conv_ratios, stage_ratios]):
        y = data
        x = np.random.normal(positions[i], 0.04, size=len(y))
        ax.scatter(x, y, alpha=0.3, s=30, color='black')

    # Paired t-test
    t_stat, p_val = stats.ttest_rel(conv_ratios, stage_ratios)

    ax.text(0.5, 0.95, f't={t_stat:.3f}\np={p_val:.4f}',
           transform=ax.transAxes, verticalalignment='top', horizontalalignment='center',
           bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    ax.set_xticks([1, 2])
    ax.set_xticklabels(['Conventional', 'STAGE'])
    ax.set_ylabel('GM/WM Intensity Ratio')
    ax.set_title(f'{seq_type}: GM/WM Ratio Comparison (n={len(seq_data)})')
    ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
output_file = OUTPUT_DIR / 'stage_vs_conv_MERGED.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"\n✓ Saved visualization: {output_file}")

# Create summary statistics table
print("\n" + "=" * 100)
print("STATISTICAL SUMMARY")
print("=" * 100)

for seq_type in sequence_types:
    seq_data = df[df['sequence_type'] == seq_type]

    print(f"\n{seq_type} Sequences (n={len(seq_data)}):")
    print("-" * 100)

    if len(seq_data) < 2:
        print(f"  ⚠️  Insufficient data for statistical analysis (n={len(seq_data)})")
        continue

    # GM correlation
    r_gm, p_gm = stats.pearsonr(seq_data['conv_gm_mean'], seq_data['stage_gm_mean'])
    print(f"  GM Mean Correlation: r={r_gm:.3f}, p={p_gm:.4f}")

    # WM correlation
    r_wm, p_wm = stats.pearsonr(seq_data['conv_wm_mean'], seq_data['stage_wm_mean'])
    print(f"  WM Mean Correlation: r={r_wm:.3f}, p={p_wm:.4f}")

    # GM/WM ratio comparison
    t_stat, p_val = stats.ttest_rel(seq_data['conv_gm_wm_ratio'], seq_data['stage_gm_wm_ratio'])
    conv_mean = seq_data['conv_gm_wm_ratio'].mean()
    stage_mean = seq_data['stage_gm_wm_ratio'].mean()
    print(f"  GM/WM Ratio (Conv): {conv_mean:.3f} ± {seq_data['conv_gm_wm_ratio'].std():.3f}")
    print(f"  GM/WM Ratio (STAGE): {stage_mean:.3f} ± {seq_data['stage_gm_wm_ratio'].std():.3f}")
    print(f"  Paired t-test: t={t_stat:.3f}, p={p_val:.4f}")

    if p_val < 0.05:
        print(f"  ⚠️  Significant difference detected!")

print("\n" + "=" * 100)
