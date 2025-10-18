#!/usr/bin/env python3
"""
GM/WM Analysis: Visualization and Reporting

Generate comprehensive visualizations and summary report for the GM/WM tissue
intensity analysis comparing conventional and STAGE MRI sequences.

Usage:
    python scripts/gm_wm_visualizations_and_report.py

Author: Analysis Pipeline
Date: 2025-10-16
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

# Project paths
BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
STATS_DIR = BASE_DIR / 'output' / 'statistics'
PLOTS_DIR = BASE_DIR / 'output' / 'plots'

# Set plotting style
sns.set_style("whitegrid")
sns.set_palette("husl")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10

# Find the most recent analysis files
def find_latest_files():
    """Find the most recent GM/WM analysis files."""
    tissue_files = list(STATS_DIR.glob('gm_wm_tissue_stats_*.csv'))
    comp_files = list(STATS_DIR.glob('gm_wm_comparisons_*.csv'))
    stat_files = list(STATS_DIR.glob('gm_wm_statistical_tests_*.csv'))

    if not tissue_files or not comp_files or not stat_files:
        print("Error: Could not find GM/WM analysis files!")
        sys.exit(1)

    # Get most recent files
    tissue_file = sorted(tissue_files, key=lambda x: x.stat().st_mtime)[-1]
    comp_file = sorted(comp_files, key=lambda x: x.stat().st_mtime)[-1]
    stat_file = sorted(stat_files, key=lambda x: x.stat().st_mtime)[-1]

    return tissue_file, comp_file, stat_file


def plot_gm_wm_comparisons(df_comp, df_tissue):
    """Create comprehensive comparison plots."""
    print("\nGenerating GM/WM comparison visualizations...")

    # Figure 1: GM and WM Mean Intensities (Conv vs STAGE) by Sequence Type
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('GM and WM Signal Intensities: Conventional vs STAGE MRI Sequences',
                 fontsize=16, fontweight='bold')

    seq_types = ['T1', 'T2', 'SWI']
    tissues = ['GM', 'WM']

    for seq_idx, seq_type in enumerate(seq_types):
        df_seq = df_comp[df_comp['sequence_type'] == seq_type]

        if len(df_seq) == 0:
            for tissue_idx in range(2):
                axes[tissue_idx, seq_idx].text(0.5, 0.5, f'No {seq_type} data',
                                               ha='center', va='center', fontsize=14)
                axes[tissue_idx, seq_idx].set_title(f'{seq_type} - No Data')
                axes[tissue_idx, seq_idx].axis('off')
            continue

        # GM plot
        ax_gm = axes[0, seq_idx]
        subjects = df_seq['subject_id'].values
        gm_conv = df_seq['gm_conv_mean'].values
        gm_stage = df_seq['gm_stage_mean'].values

        x = np.arange(len(subjects))
        width = 0.35

        ax_gm.bar(x - width/2, gm_conv, width, label='Conventional', alpha=0.8, color='#3498db')
        ax_gm.bar(x + width/2, gm_stage, width, label='STAGE', alpha=0.8, color='#e74c3c')
        ax_gm.set_xlabel('Subject ID', fontweight='bold')
        ax_gm.set_ylabel('Mean Gray Matter Intensity', fontweight='bold')
        ax_gm.set_title(f'{seq_type}: Gray Matter (n={len(df_seq)})', fontweight='bold')
        ax_gm.set_xticks(x)
        ax_gm.set_xticklabels(subjects, rotation=45, ha='right')
        ax_gm.legend()
        ax_gm.grid(True, alpha=0.3)

        # WM plot
        ax_wm = axes[1, seq_idx]
        wm_conv = df_seq['wm_conv_mean'].values
        wm_stage = df_seq['wm_stage_mean'].values

        ax_wm.bar(x - width/2, wm_conv, width, label='Conventional', alpha=0.8, color='#3498db')
        ax_wm.bar(x + width/2, wm_stage, width, label='STAGE', alpha=0.8, color='#e74c3c')
        ax_wm.set_xlabel('Subject ID', fontweight='bold')
        ax_wm.set_ylabel('Mean White Matter Intensity', fontweight='bold')
        ax_wm.set_title(f'{seq_type}: White Matter (n={len(df_seq)})', fontweight='bold')
        ax_wm.set_xticks(x)
        ax_wm.set_xticklabels(subjects, rotation=45, ha='right')
        ax_wm.legend()
        ax_wm.grid(True, alpha=0.3)

    plt.tight_layout()
    output_file = PLOTS_DIR / 'gm_wm_conv_vs_stage_by_sequence.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  ✓ Saved: {output_file.name}")
    plt.close()

    # Figure 2: Percent Differences
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle('Signal Intensity Differences: STAGE vs Conventional (%)',
                 fontsize=16, fontweight='bold')

    # GM percent differences
    ax_gm = axes[0]
    for seq_type in seq_types:
        df_seq = df_comp[df_comp['sequence_type'] == seq_type]
        if len(df_seq) > 0:
            x = range(len(df_seq))
            y = df_seq['gm_percent_diff'].values
            ax_gm.scatter(x, y, s=100, alpha=0.7, label=seq_type)
            ax_gm.plot(x, y, alpha=0.5)

    ax_gm.axhline(y=0, color='black', linestyle='--', alpha=0.5)
    ax_gm.set_xlabel('Subject Index', fontweight='bold')
    ax_gm.set_ylabel('Percent Difference (%)', fontweight='bold')
    ax_gm.set_title('Gray Matter: STAGE vs Conventional', fontweight='bold')
    ax_gm.legend()
    ax_gm.grid(True, alpha=0.3)

    # WM percent differences
    ax_wm = axes[1]
    for seq_type in seq_types:
        df_seq = df_comp[df_comp['sequence_type'] == seq_type]
        if len(df_seq) > 0:
            x = range(len(df_seq))
            y = df_seq['wm_percent_diff'].values
            ax_wm.scatter(x, y, s=100, alpha=0.7, label=seq_type)
            ax_wm.plot(x, y, alpha=0.5)

    ax_wm.axhline(y=0, color='black', linestyle='--', alpha=0.5)
    ax_wm.set_xlabel('Subject Index', fontweight='bold')
    ax_wm.set_ylabel('Percent Difference (%)', fontweight='bold')
    ax_wm.set_title('White Matter: STAGE vs Conventional', fontweight='bold')
    ax_wm.legend()
    ax_wm.grid(True, alpha=0.3)

    plt.tight_layout()
    output_file = PLOTS_DIR / 'gm_wm_percent_differences.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  ✓ Saved: {output_file.name}")
    plt.close()

    # Figure 3: GM/WM Ratios
    fig, ax = plt.subplots(figsize=(12, 8))
    for seq_type in seq_types:
        df_seq = df_comp[df_comp['sequence_type'] == seq_type]
        if len(df_seq) > 0:
            x = np.arange(len(df_seq))
            width = 0.25
            offset = (seq_types.index(seq_type) - 1) * width

            conv_ratios = df_seq['gm_wm_ratio_conv'].values
            stage_ratios = df_seq['gm_wm_ratio_stage'].values

            ax.bar(x + offset, conv_ratios, width, label=f'{seq_type} Conv', alpha=0.7)
            ax.bar(x + offset, stage_ratios, width, label=f'{seq_type} STAGE',
                   alpha=0.7, bottom=0, hatch='//')

    ax.set_xlabel('Subject Index', fontweight='bold')
    ax.set_ylabel('GM/WM Intensity Ratio', fontweight='bold')
    ax.set_title('GM/WM Intensity Ratios: Conventional vs STAGE', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    output_file = PLOTS_DIR / 'gm_wm_ratios.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  ✓ Saved: {output_file.name}")
    plt.close()


def plot_tissue_distributions(df_tissue):
    """Plot tissue intensity distributions."""
    print("\nGenerating tissue intensity distribution plots...")

    # Separate by sequence type
    fig, axes = plt.subplots(3, 2, figsize=(16, 18))
    fig.suptitle('Tissue Intensity Distributions by Sequence Type',
                 fontsize=16, fontweight='bold')

    seq_types = ['T1', 'T2', 'SWI']
    tissues = ['GM', 'WM']

    for seq_idx, seq_type in enumerate(seq_types):
        # Get conv and STAGE sequences
        conv_seq = f'{seq_type}_conv'
        stage_seq = f'{seq_type}_STAGE'

        df_conv = df_tissue[df_tissue['sequence'] == conv_seq]
        df_stage = df_tissue[df_tissue['sequence'] == stage_seq]

        # GM distributions
        ax_gm = axes[seq_idx, 0]
        if len(df_conv) > 0:
            ax_gm.hist(df_conv['gm_mean'].dropna(), bins=20, alpha=0.6, label='Conv', color='#3498db')
        if len(df_stage) > 0:
            ax_gm.hist(df_stage['gm_mean'].dropna(), bins=20, alpha=0.6, label='STAGE', color='#e74c3c')
        ax_gm.set_xlabel('Mean GM Intensity', fontweight='bold')
        ax_gm.set_ylabel('Frequency', fontweight='bold')
        ax_gm.set_title(f'{seq_type}: Gray Matter (Conv n={len(df_conv)}, STAGE n={len(df_stage)})',
                       fontweight='bold')
        ax_gm.legend()
        ax_gm.grid(True, alpha=0.3)

        # WM distributions
        ax_wm = axes[seq_idx, 1]
        if len(df_conv) > 0:
            ax_wm.hist(df_conv['wm_mean'].dropna(), bins=20, alpha=0.6, label='Conv', color='#3498db')
        if len(df_stage) > 0:
            ax_wm.hist(df_stage['wm_mean'].dropna(), bins=20, alpha=0.6, label='STAGE', color='#e74c3c')
        ax_wm.set_xlabel('Mean WM Intensity', fontweight='bold')
        ax_wm.set_ylabel('Frequency', fontweight='bold')
        ax_wm.set_title(f'{seq_type}: White Matter (Conv n={len(df_conv)}, STAGE n={len(df_stage)})',
                       fontweight='bold')
        ax_wm.legend()
        ax_wm.grid(True, alpha=0.3)

    plt.tight_layout()
    output_file = PLOTS_DIR / 'tissue_intensity_distributions.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  ✓ Saved: {output_file.name}")
    plt.close()


def generate_summary_report(df_tissue, df_comp, df_stats):
    """Generate comprehensive summary report in Markdown format."""
    print("\nGenerating summary report...")

    report = []
    report.append("# GM and WM Tissue Intensity Analysis: Validated STAGE Study Subjects")
    report.append("")
    report.append(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**Subjects Analyzed:** 13 validated subjects")
    report.append("")
    report.append("---")
    report.append("")
    report.append("## Executive Summary")
    report.append("")
    report.append("This analysis compares gray matter (GM) and white matter (WM) signal intensities")
    report.append("between conventional and STAGE MRI sequences across 13 validated subjects.")
    report.append("Intensity-based tissue segmentation was used to identify GM and WM regions,")
    report.append("and mean signal intensities were extracted for comparison.")
    report.append("")
    report.append("---")
    report.append("")
    report.append("## Data Availability")
    report.append("")

    # Count sequences processed
    seq_counts = df_tissue.groupby('sequence').size().to_dict()
    report.append("### Sequences Processed")
    report.append("")
    report.append("| Sequence | Count |")
    report.append("|----------|-------|")
    for seq in ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']:
        count = seq_counts.get(seq, 0)
        report.append(f"| {seq} | {count} |")
    report.append("")

    # Count comparisons
    comp_counts = df_comp.groupby('sequence_type').size().to_dict()
    report.append("### Comparisons Available (Conv vs STAGE)")
    report.append("")
    report.append("| Sequence Type | Subjects |")
    report.append("|--------------|----------|")
    for seq_type in ['T1', 'T2', 'SWI']:
        count = comp_counts.get(seq_type, 0)
        report.append(f"| {seq_type} | {count} |")
    report.append("")
    report.append("---")
    report.append("")
    report.append("## Statistical Analysis Results")
    report.append("")

    for _, row in df_stats.iterrows():
        seq_type = row['sequence_type']
        n = int(row['n_subjects'])

        report.append(f"### {seq_type} Sequences (n={n} subjects)")
        report.append("")

        report.append("#### Gray Matter")
        report.append("")
        report.append("| Metric | Conventional | STAGE | Difference | Statistics |")
        report.append("|--------|-------------|-------|------------|------------|")

        gm_conv_mean = row['gm_conv_mean']
        gm_conv_std = row['gm_conv_std']
        gm_stage_mean = row['gm_stage_mean']
        gm_stage_std = row['gm_stage_std']
        gm_diff = gm_stage_mean - gm_conv_mean
        gm_pct = (gm_diff / gm_conv_mean * 100) if gm_conv_mean != 0 else 0

        gm_t = row['gm_t_stat']
        gm_p = row['gm_p_value']
        gm_d = row['gm_effect_size']

        sig = ""
        if gm_p < 0.001:
            sig = "✓✓✓"
        elif gm_p < 0.01:
            sig = "✓✓"
        elif gm_p < 0.05:
            sig = "✓"

        report.append(f"| Mean ± SD | {gm_conv_mean:.1f} ± {gm_conv_std:.1f} | "
                     f"{gm_stage_mean:.1f} ± {gm_stage_std:.1f} | "
                     f"{gm_diff:+.1f} ({gm_pct:+.1f}%) | "
                     f"t={gm_t:.2f}, p={gm_p:.4f} {sig}, d={gm_d:.2f} |")
        report.append("")

        report.append("#### White Matter")
        report.append("")
        report.append("| Metric | Conventional | STAGE | Difference | Statistics |")
        report.append("|--------|-------------|-------|------------|------------|")

        wm_conv_mean = row['wm_conv_mean']
        wm_conv_std = row['wm_conv_std']
        wm_stage_mean = row['wm_stage_mean']
        wm_stage_std = row['wm_stage_std']
        wm_diff = wm_stage_mean - wm_conv_mean
        wm_pct = (wm_diff / wm_conv_mean * 100) if wm_conv_mean != 0 else 0

        wm_t = row['wm_t_stat']
        wm_p = row['wm_p_value']
        wm_d = row['wm_effect_size']

        sig = ""
        if wm_p < 0.001:
            sig = "✓✓✓"
        elif wm_p < 0.01:
            sig = "✓✓"
        elif wm_p < 0.05:
            sig = "✓"

        report.append(f"| Mean ± SD | {wm_conv_mean:.1f} ± {wm_conv_std:.1f} | "
                     f"{wm_stage_mean:.1f} ± {wm_stage_std:.1f} | "
                     f"{wm_diff:+.1f} ({wm_pct:+.1f}%) | "
                     f"t={wm_t:.2f}, p={wm_p:.4f} {sig}, d={wm_d:.2f} |")
        report.append("")

        # Interpretation
        report.append("**Interpretation:**")
        report.append("")

        if gm_p < 0.05:
            direction = "higher" if gm_diff > 0 else "lower"
            report.append(f"- STAGE sequences show **significantly {direction}** GM intensity "
                         f"({gm_pct:+.1f}%, p={gm_p:.4f})")
        else:
            report.append(f"- No significant difference in GM intensity (p={gm_p:.4f})")

        if wm_p < 0.05:
            direction = "higher" if wm_diff > 0 else "lower"
            report.append(f"- STAGE sequences show **significantly {direction}** WM intensity "
                         f"({wm_pct:+.1f}%, p={wm_p:.4f})")
        else:
            report.append(f"- No significant difference in WM intensity (p={wm_p:.4f})")

        if abs(gm_d) > 0.8:
            report.append(f"- **Large effect size** for GM (d={gm_d:.2f})")
        elif abs(gm_d) > 0.5:
            report.append(f"- **Medium effect size** for GM (d={gm_d:.2f})")

        if abs(wm_d) > 0.8:
            report.append(f"- **Large effect size** for WM (d={wm_d:.2f})")
        elif abs(wm_d) > 0.5:
            report.append(f"- **Medium effect size** for WM (d={wm_d:.2f})")

        report.append("")
        report.append("---")
        report.append("")

    report.append("## Key Findings")
    report.append("")
    report.append("1. **T2 Sequences:** Showed significant differences between conventional and STAGE")
    report.append("   - Both GM and WM intensities were markedly higher in STAGE sequences")
    report.append("   - Large effect sizes indicate substantial practical differences")
    report.append("")
    report.append("2. **T1 and SWI Sequences:** Limited comparisons available (n=1 each)")
    report.append("   - Additional data needed for robust statistical analysis")
    report.append("")
    report.append("3. **Tissue Segmentation:** Successfully identified GM and WM regions")
    report.append("   - Intensity-based segmentation provided reasonable tissue separation")
    report.append("   - QC tissue masks saved for visual inspection")
    report.append("")
    report.append("---")
    report.append("")
    report.append("## Generated Files")
    report.append("")
    report.append("### Data Files")
    report.append("- `gm_wm_tissue_stats_*.csv` - Tissue intensity statistics for all sequences")
    report.append("- `gm_wm_comparisons_*.csv` - Conv vs STAGE comparisons")
    report.append("- `gm_wm_statistical_tests_*.csv` - Statistical test results")
    report.append("")
    report.append("### Visualizations")
    report.append("- `gm_wm_conv_vs_stage_by_sequence.png` - Bar plots comparing intensities")
    report.append("- `gm_wm_percent_differences.png` - Percent difference plots")
    report.append("- `gm_wm_ratios.png` - GM/WM ratio comparisons")
    report.append("- `tissue_intensity_distributions.png` - Intensity histograms")
    report.append("")
    report.append("### Tissue Segmentation Masks")
    report.append("- `output/tissue_segmentations/{subject_id}/{sequence}_GM_mask.nii.gz`")
    report.append("- `output/tissue_segmentations/{subject_id}/{sequence}_WM_mask.nii.gz`")
    report.append("")
    report.append("---")
    report.append("")
    report.append(f"**Report Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")

    # Save report
    report_file = STATS_DIR / 'GM_WM_ANALYSIS_SUMMARY_REPORT.md'
    with open(report_file, 'w') as f:
        f.write('\n'.join(report))

    print(f"  ✓ Saved: {report_file.name}")

    return report_file


def main():
    """Main execution function."""
    print("=" * 100)
    print("GM/WM Tissue Intensity Analysis: Visualization and Reporting")
    print("=" * 100)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)

    # Find latest analysis files
    tissue_file, comp_file, stat_file = find_latest_files()
    print(f"\nLoading analysis files:")
    print(f"  - Tissue stats: {tissue_file.name}")
    print(f"  - Comparisons: {comp_file.name}")
    print(f"  - Statistical tests: {stat_file.name}")

    # Load data
    df_tissue = pd.read_csv(tissue_file)
    df_comp = pd.read_csv(comp_file)
    df_stats = pd.read_csv(stat_file)

    # Generate visualizations
    plot_gm_wm_comparisons(df_comp, df_tissue)
    plot_tissue_distributions(df_tissue)

    # Generate summary report
    report_file = generate_summary_report(df_tissue, df_comp, df_stats)

    print("\n" + "=" * 100)
    print("Analysis Complete!")
    print("=" * 100)
    print(f"\nVisualization Files:")
    print(f"  - {PLOTS_DIR}/gm_wm_conv_vs_stage_by_sequence.png")
    print(f"  - {PLOTS_DIR}/gm_wm_percent_differences.png")
    print(f"  - {PLOTS_DIR}/gm_wm_ratios.png")
    print(f"  - {PLOTS_DIR}/tissue_intensity_distributions.png")
    print(f"\nSummary Report:")
    print(f"  - {report_file}")
    print("=" * 100)


if __name__ == '__main__':
    main()
