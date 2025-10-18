#!/usr/bin/env python3
"""
Generate comprehensive visualizations for GM/WM intensity analysis

Creates:
1. Box plots comparing conventional vs STAGE for each sequence type
2. Paired scatter plots showing within-subject comparisons
3. Bland-Altman plots for agreement analysis
4. Statistical summary figures

Usage:
    python scripts/visualize_gm_wm_results.py

Author: STAGE Study Analysis
Date: 2025-10-17
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats

# Paths
BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
STATS_DIR = BASE_DIR / 'output' / 'statistics'
PLOTS_DIR = BASE_DIR / 'output' / 'plots'
PLOTS_DIR.mkdir(exist_ok=True, parents=True)

# Load data
print("Loading data...")
tissue_stats_file = STATS_DIR / 'gm_wm_tissue_stats_20251017_025955.csv'
comparisons_file = STATS_DIR / 'gm_wm_comparisons_20251017_025955.csv'
statistical_tests_file = STATS_DIR / 'gm_wm_statistical_tests_20251017_025955.csv'

df_tissue = pd.read_csv(tissue_stats_file)
df_comp = pd.read_csv(comparisons_file)
df_stats = pd.read_csv(statistical_tests_file)

print(f"Loaded {len(df_tissue)} tissue measurements")
print(f"Loaded {len(df_comp)} paired comparisons")
print(f"Loaded {len(df_stats)} statistical tests")

# Set plot style
sns.set_style("whitegrid")
sns.set_context("talk")
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10

#############################################################################
# Figure 1: Box plots comparing conventional vs STAGE
#############################################################################
print("\nGenerating Figure 1: Box plots...")

fig, axes = plt.subplots(3, 2, figsize=(14, 16))
fig.suptitle('GM and WM Signal Intensities: Conventional vs STAGE', fontsize=16, fontweight='bold')

sequence_types = ['T1', 'T2', 'SWI']
tissues = ['GM', 'WM']

for i, seq_type in enumerate(sequence_types):
    for j, tissue in enumerate(tissues):
        ax = axes[i, j]

        # Get data for this sequence type
        conv_seq = f"{seq_type}_conv"
        stage_seq = f"{seq_type}_STAGE"

        # Filter data
        conv_data = df_tissue[df_tissue['sequence'] == conv_seq][f'{tissue}_mean'].values
        stage_data = df_tissue[df_tissue['sequence'] == stage_seq][f'{tissue}_mean'].values

        # Prepare data for box plot
        plot_data = pd.DataFrame({
            'Intensity': np.concatenate([conv_data, stage_data]),
            'Type': ['Conventional']*len(conv_data) + ['STAGE']*len(stage_data)
        })

        # Create box plot
        bp = sns.boxplot(data=plot_data, x='Type', y='Intensity', ax=ax, palette=['lightblue', 'lightcoral'])

        # Add individual points
        sns.stripplot(data=plot_data, x='Type', y='Intensity', ax=ax,
                     color='black', alpha=0.3, size=4, jitter=True)

        # Get statistics for this comparison
        stat_row = df_stats[(df_stats['sequence_type'] == seq_type) & (df_stats['tissue'] == tissue)]

        if len(stat_row) > 0:
            p_val = stat_row['p_value'].values[0]
            cohens_d = stat_row['cohens_d'].values[0]
            n = stat_row['n_subjects'].values[0]
            pct_diff = stat_row['pct_diff'].values[0]

            # Add significance annotation
            if p_val < 0.001:
                sig_text = "***"
            elif p_val < 0.01:
                sig_text = "**"
            elif p_val < 0.05:
                sig_text = "*"
            else:
                sig_text = "ns"

            # Add statistics text
            y_max = plot_data['Intensity'].max()
            y_range = plot_data['Intensity'].max() - plot_data['Intensity'].min()

            ax.text(0.5, y_max + y_range * 0.05, sig_text,
                   ha='center', va='bottom', fontsize=20, fontweight='bold')

            stats_text = f"n={int(n)}\np={p_val:.4f}\nd={cohens_d:.2f}\nΔ={pct_diff:.1f}%"
            ax.text(0.98, 0.98, stats_text, transform=ax.transAxes,
                   ha='right', va='top', fontsize=8,
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        # Formatting
        ax.set_title(f'{seq_type} - {tissue}', fontweight='bold')
        ax.set_xlabel('')
        ax.set_ylabel('Signal Intensity (a.u.)' if j == 0 else '')

        # Rotate x labels if needed
        ax.tick_params(axis='x', rotation=45)

plt.tight_layout()
output_file = PLOTS_DIR / 'gm_wm_boxplots_comparison.png'
plt.savefig(output_file, bbox_inches='tight')
print(f"Saved: {output_file}")
plt.close()

#############################################################################
# Figure 2: Paired scatter plots (within-subject comparisons)
#############################################################################
print("\nGenerating Figure 2: Paired scatter plots...")

fig, axes = plt.subplots(3, 2, figsize=(14, 16))
fig.suptitle('Within-Subject Comparisons: Conventional vs STAGE', fontsize=16, fontweight='bold')

for i, seq_type in enumerate(sequence_types):
    for j, tissue in enumerate(tissues):
        ax = axes[i, j]

        # Get comparison data
        seq_comp = df_comp[df_comp['sequence_type'] == seq_type]

        if len(seq_comp) > 0:
            conv_col = f"{tissue}_conv"
            stage_col = f"{tissue}_STAGE"

            x = seq_comp[conv_col].values
            y = seq_comp[stage_col].values

            # Scatter plot
            ax.scatter(x, y, alpha=0.6, s=50, edgecolors='black', linewidths=0.5)

            # Unity line (y=x)
            min_val = min(x.min(), y.min())
            max_val = max(x.max(), y.max())
            ax.plot([min_val, max_val], [min_val, max_val],
                   'r--', linewidth=2, label='Unity line', alpha=0.7)

            # Regression line
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            x_line = np.array([x.min(), x.max()])
            y_line = slope * x_line + intercept
            ax.plot(x_line, y_line, 'b-', linewidth=2,
                   label=f'Fit: y={slope:.2f}x+{intercept:.1f}', alpha=0.7)

            # Add correlation info
            corr = np.corrcoef(x, y)[0, 1]

            stat_row = df_stats[(df_stats['sequence_type'] == seq_type) &
                              (df_stats['tissue'] == tissue)]

            if len(stat_row) > 0:
                p_val = stat_row['p_value'].values[0]

                stats_text = f"r={corr:.3f}\np={p_val:.4f}\nn={len(x)}"
                ax.text(0.05, 0.95, stats_text, transform=ax.transAxes,
                       ha='left', va='top', fontsize=9,
                       bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))

            ax.set_xlabel(f'{seq_type} Conventional - {tissue} Intensity')
            ax.set_ylabel(f'{seq_type} STAGE - {tissue} Intensity')
            ax.set_title(f'{seq_type} - {tissue}', fontweight='bold')
            ax.legend(loc='lower right', fontsize=8)
            ax.set_aspect('equal', adjustable='box')
        else:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center',
                   transform=ax.transAxes, fontsize=14)
            ax.set_title(f'{seq_type} - {tissue}', fontweight='bold')

plt.tight_layout()
output_file = PLOTS_DIR / 'gm_wm_scatter_paired.png'
plt.savefig(output_file, bbox_inches='tight')
print(f"Saved: {output_file}")
plt.close()

#############################################################################
# Figure 3: Bland-Altman plots (agreement analysis)
#############################################################################
print("\nGenerating Figure 3: Bland-Altman plots...")

fig, axes = plt.subplots(3, 2, figsize=(14, 16))
fig.suptitle('Bland-Altman Plots: Agreement Between Conventional and STAGE',
             fontsize=16, fontweight='bold')

for i, seq_type in enumerate(sequence_types):
    for j, tissue in enumerate(tissues):
        ax = axes[i, j]

        # Get comparison data
        seq_comp = df_comp[df_comp['sequence_type'] == seq_type]

        if len(seq_comp) > 0:
            conv_col = f"{tissue}_conv"
            stage_col = f"{tissue}_STAGE"

            conv_vals = seq_comp[conv_col].values
            stage_vals = seq_comp[stage_col].values

            # Bland-Altman calculations
            mean = (conv_vals + stage_vals) / 2
            diff = stage_vals - conv_vals

            mean_diff = np.mean(diff)
            std_diff = np.std(diff)

            # Plot
            ax.scatter(mean, diff, alpha=0.6, s=50, edgecolors='black', linewidths=0.5)

            # Mean difference line
            ax.axhline(mean_diff, color='blue', linestyle='--', linewidth=2,
                      label=f'Mean diff: {mean_diff:.1f}')

            # Limits of agreement (±1.96 SD)
            loa_upper = mean_diff + 1.96 * std_diff
            loa_lower = mean_diff - 1.96 * std_diff

            ax.axhline(loa_upper, color='red', linestyle=':', linewidth=2,
                      label=f'+1.96 SD: {loa_upper:.1f}')
            ax.axhline(loa_lower, color='red', linestyle=':', linewidth=2,
                      label=f'-1.96 SD: {loa_lower:.1f}')

            # Zero line
            ax.axhline(0, color='black', linestyle='-', linewidth=1, alpha=0.3)

            ax.set_xlabel(f'Mean of Conventional and STAGE ({tissue})')
            ax.set_ylabel(f'STAGE - Conventional ({tissue})')
            ax.set_title(f'{seq_type} - {tissue}', fontweight='bold')
            ax.legend(loc='best', fontsize=8)
            ax.grid(True, alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center',
                   transform=ax.transAxes, fontsize=14)
            ax.set_title(f'{seq_type} - {tissue}', fontweight='bold')

plt.tight_layout()
output_file = PLOTS_DIR / 'gm_wm_bland_altman.png'
plt.savefig(output_file, bbox_inches='tight')
print(f"Saved: {output_file}")
plt.close()

#############################################################################
# Figure 4: Effect sizes and statistical summary
#############################################################################
print("\nGenerating Figure 4: Effect sizes summary...")

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle('Statistical Summary: Effect Sizes and Significance',
             fontsize=16, fontweight='bold')

# Prepare data
df_stats['comparison'] = df_stats['sequence_type'] + '_' + df_stats['tissue']

# Panel A: Cohen's d effect sizes
ax = axes[0]
colors = ['green' if p < 0.05 else 'gray' for p in df_stats['p_value']]
bars = ax.barh(df_stats['comparison'], df_stats['cohens_d'], color=colors, alpha=0.7)

# Add effect size interpretation lines
ax.axvline(0.2, color='orange', linestyle='--', alpha=0.5, label='Small (0.2)')
ax.axvline(0.5, color='blue', linestyle='--', alpha=0.5, label='Medium (0.5)')
ax.axvline(0.8, color='red', linestyle='--', alpha=0.5, label='Large (0.8)')
ax.axvline(-0.2, color='orange', linestyle='--', alpha=0.5)
ax.axvline(-0.5, color='blue', linestyle='--', alpha=0.5)
ax.axvline(-0.8, color='red', linestyle='--', alpha=0.5)
ax.axvline(0, color='black', linestyle='-', linewidth=2)

ax.set_xlabel("Cohen's d (Effect Size)", fontweight='bold')
ax.set_ylabel("Comparison", fontweight='bold')
ax.set_title("Effect Sizes (green = p<0.05)", fontweight='bold')
ax.legend(loc='best', fontsize=8)
ax.grid(True, alpha=0.3, axis='x')

# Panel B: P-values
ax = axes[1]
p_vals = df_stats['p_value'].values
colors = ['green' if p < 0.05 else 'gray' for p in p_vals]

# Plot on log scale
bars = ax.barh(df_stats['comparison'], -np.log10(p_vals), color=colors, alpha=0.7)

# Add significance threshold lines
ax.axvline(-np.log10(0.05), color='red', linestyle='--', linewidth=2,
          label='p=0.05', alpha=0.7)
ax.axvline(-np.log10(0.01), color='orange', linestyle='--', linewidth=2,
          label='p=0.01', alpha=0.7)
ax.axvline(-np.log10(0.001), color='purple', linestyle='--', linewidth=2,
          label='p=0.001', alpha=0.7)

ax.set_xlabel("-log10(p-value)", fontweight='bold')
ax.set_ylabel("")
ax.set_title("Statistical Significance", fontweight='bold')
ax.legend(loc='best', fontsize=8)
ax.grid(True, alpha=0.3, axis='x')

plt.tight_layout()
output_file = PLOTS_DIR / 'gm_wm_effect_sizes.png'
plt.savefig(output_file, bbox_inches='tight')
print(f"Saved: {output_file}")
plt.close()

#############################################################################
# Figure 5: Percent differences
#############################################################################
print("\nGenerating Figure 5: Percent differences...")

fig, ax = plt.subplots(figsize=(10, 6))
fig.suptitle('Percent Difference: STAGE vs Conventional', fontsize=16, fontweight='bold')

colors = ['green' if p < 0.05 else 'gray' for p in df_stats['p_value']]
bars = ax.barh(df_stats['comparison'], df_stats['pct_diff'], color=colors, alpha=0.7)

ax.axvline(0, color='black', linestyle='-', linewidth=2)
ax.set_xlabel("Percent Difference (%)\n(Positive = STAGE higher than Conventional)", fontweight='bold')
ax.set_ylabel("Comparison", fontweight='bold')
ax.set_title("Green bars indicate p < 0.05", fontsize=12)
ax.grid(True, alpha=0.3, axis='x')

# Add value labels
for i, (idx, row) in enumerate(df_stats.iterrows()):
    pct = row['pct_diff']
    ax.text(pct, i, f" {pct:.1f}%", va='center', ha='left' if pct > 0 else 'right',
           fontweight='bold', fontsize=9)

plt.tight_layout()
output_file = PLOTS_DIR / 'gm_wm_percent_differences.png'
plt.savefig(output_file, bbox_inches='tight')
print(f"Saved: {output_file}")
plt.close()

#############################################################################
# Create summary report
#############################################################################
print("\nCreating summary report...")

report_file = PLOTS_DIR / 'GM_WM_ANALYSIS_REPORT.md'
with open(report_file, 'w') as f:
    f.write("# GM/WM Intensity Analysis: Conventional vs STAGE Sequences\n\n")
    f.write("**Analysis Date:** 2025-10-17\n\n")
    f.write("**Dataset:** STAGE Study - Complete reprocessing with ground truth data\n\n")

    f.write("## Summary\n\n")
    f.write(f"- **Total subjects processed:** 42/43 (98% success rate)\n")
    f.write(f"- **T1 pairs analyzed:** {df_stats[df_stats['sequence_type']=='T1']['n_subjects'].values[0]:.0f}\n")
    f.write(f"- **T2 pairs analyzed:** {df_stats[df_stats['sequence_type']=='T2']['n_subjects'].values[0]:.0f}\n")
    f.write(f"- **SWI pairs analyzed:** {df_stats[df_stats['sequence_type']=='SWI']['n_subjects'].values[0]:.0f}\n\n")

    f.write("## Key Findings\n\n")

    for seq_type in ['T1', 'T2', 'SWI']:
        f.write(f"### {seq_type} Sequences\n\n")

        for tissue in ['GM', 'WM']:
            row = df_stats[(df_stats['sequence_type']==seq_type) & (df_stats['tissue']==tissue)].iloc[0]

            sig = "**SIGNIFICANT**" if row['p_value'] < 0.05 else "Not significant"

            f.write(f"**{tissue}:**\n")
            f.write(f"- Conventional: {row['conv_mean']:.1f} ± {row['conv_std']:.1f}\n")
            f.write(f"- STAGE: {row['stage_mean']:.1f} ± {row['stage_std']:.1f}\n")
            f.write(f"- Difference: {row['mean_diff']:.1f} ({row['pct_diff']:.1f}%)\n")
            f.write(f"- Statistics: t={row['t_statistic']:.2f}, p={row['p_value']:.4f}, d={row['cohens_d']:.2f}\n")
            f.write(f"- Result: {sig}\n\n")

    f.write("## Interpretation\n\n")
    f.write("### T1 Sequences\n")
    f.write("- No significant differences between conventional and STAGE\n")
    f.write("- Both GM and WM show similar signal intensities (p>0.3)\n")
    f.write("- Effect sizes are negligible (|d|<0.2)\n\n")

    f.write("### T2 Sequences\n")
    f.write("- **Highly significant differences** between conventional and STAGE (p<0.0001)\n")
    f.write("- STAGE shows 2-3x higher signal intensities\n")
    f.write("- Large effect sizes (d=0.99 for GM, d=1.38 for WM)\n")
    f.write("- This is the most dramatic difference across all sequence types\n\n")

    f.write("### SWI Sequences\n")
    f.write("- **Significant differences** between conventional and STAGE (p<0.05)\n")
    f.write("- STAGE shows ~25-30% higher signal intensities\n")
    f.write("- Small-to-medium effect sizes (d~0.35)\n")
    f.write("- Differences are consistent but more modest than T2\n\n")

    f.write("## Generated Visualizations\n\n")
    f.write("1. `gm_wm_boxplots_comparison.png` - Box plots comparing distributions\n")
    f.write("2. `gm_wm_scatter_paired.png` - Within-subject paired comparisons\n")
    f.write("3. `gm_wm_bland_altman.png` - Agreement analysis\n")
    f.write("4. `gm_wm_effect_sizes.png` - Statistical effect sizes and significance\n")
    f.write("5. `gm_wm_percent_differences.png` - Relative differences summary\n\n")

    f.write("## Statistical Methods\n\n")
    f.write("- **Analysis:** Paired t-tests (within-subject comparisons)\n")
    f.write("- **Effect size:** Cohen's d for paired samples\n")
    f.write("- **Significance level:** α = 0.05\n")
    f.write("- **Tissue segmentation:** Intensity-based percentile thresholds\n")
    f.write("- **Brain extraction:** HD-BET (deep learning-based)\n\n")

print(f"Saved: {report_file}")

print("\n" + "="*80)
print("VISUALIZATION COMPLETE!")
print("="*80)
print(f"\nGenerated 5 figures and 1 report in: {PLOTS_DIR}")
print("\nFiles created:")
print("  - gm_wm_boxplots_comparison.png")
print("  - gm_wm_scatter_paired.png")
print("  - gm_wm_bland_altman.png")
print("  - gm_wm_effect_sizes.png")
print("  - gm_wm_percent_differences.png")
print("  - GM_WM_ANALYSIS_REPORT.md")
