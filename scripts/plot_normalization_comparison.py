#!/usr/bin/env python3
"""
Generate comprehensive plots comparing normalized vs non-normalized results.
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

def load_metrics(metrics_dir):
    """Load all metrics files from a directory"""
    metrics_files = list(Path(metrics_dir).glob('**/*_metrics.csv'))

    if not metrics_files:
        return None

    all_metrics = []
    for file in metrics_files:
        try:
            df = pd.read_csv(file)
            all_metrics.append(df)
        except Exception as e:
            print(f"Warning: Could not load {file}: {e}")

    if not all_metrics:
        return None

    return pd.concat(all_metrics, ignore_index=True)

def extract_info(df):
    """Extract patient ID and sequence type from comparison name"""
    def get_patient_id(comparison):
        parts = comparison.split('_')
        return parts[0] if parts else 'Unknown'

    def get_sequence_type(comparison):
        if 'T1' in comparison:
            return 'T1'
        elif 'T2' in comparison:
            return 'T2'
        elif 'SWI' in comparison:
            return 'SWI'
        return 'Unknown'

    df['patient_id'] = df['comparison'].apply(get_patient_id)
    df['sequence_type'] = df['comparison'].apply(get_sequence_type)
    return df

def plot_metric_comparison(normalized_df, non_normalized_df, output_dir):
    """Create comprehensive comparison plots"""

    # Extract info
    normalized_df = extract_info(normalized_df)
    non_normalized_df = extract_info(non_normalized_df)

    # Add normalization labels
    normalized_df['normalization'] = 'With Ventricle Norm'
    non_normalized_df['normalization'] = 'Without Norm'

    # Combine for plotting
    combined = pd.concat([normalized_df, non_normalized_df], ignore_index=True)

    # Key metrics to plot
    metrics = ['ssim_mean', 'pearson_r', 'ncc', 'psnr', 'mutual_information']
    metric_labels = {
        'ssim_mean': 'SSIM',
        'pearson_r': 'Pearson Correlation',
        'ncc': 'Normalized Cross-Correlation',
        'psnr': 'PSNR (dB)',
        'mutual_information': 'Mutual Information'
    }

    # 1. Box plots by sequence type
    print("Creating box plots by sequence type...")
    for metric in metrics:
        if metric not in combined.columns:
            continue

        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        fig.suptitle(f'{metric_labels[metric]} Comparison by Sequence Type',
                     fontsize=14, fontweight='bold')

        for idx, seq_type in enumerate(['T1', 'T2', 'SWI']):
            ax = axes[idx]
            seq_data = combined[combined['sequence_type'] == seq_type]

            if len(seq_data) > 0:
                sns.boxplot(data=seq_data, x='normalization', y=metric, ax=ax)
                ax.set_title(f'{seq_type}-weighted (n={len(seq_data)//2})')
                ax.set_xlabel('')
                ax.set_ylabel(metric_labels[metric])
                ax.tick_params(axis='x', rotation=45)
            else:
                ax.text(0.5, 0.5, 'No data', ha='center', va='center')
                ax.set_title(f'{seq_type}-weighted')

        plt.tight_layout()
        plt.savefig(output_dir / f'boxplot_{metric}_by_sequence.png', dpi=300, bbox_inches='tight')
        plt.close()

    # 2. Scatter plots: Before vs After normalization
    print("Creating before/after scatter plots...")
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('Impact of Ventricle Normalization on Key Metrics',
                 fontsize=16, fontweight='bold')

    plot_metrics = ['ssim_mean', 'pearson_r', 'ncc', 'psnr', 'mutual_information']

    for idx, metric in enumerate(plot_metrics[:6]):
        if metric not in normalized_df.columns:
            continue

        ax = axes[idx // 3, idx % 3]

        # Match comparisons
        merged = pd.merge(
            non_normalized_df[['comparison', metric, 'sequence_type']],
            normalized_df[['comparison', metric]],
            on='comparison',
            suffixes=('_before', '_after')
        )

        # Plot by sequence type
        for seq_type, marker, color in [('T1', 'o', 'blue'), ('T2', 's', 'green'), ('SWI', '^', 'red')]:
            seq_data = merged[merged['sequence_type'] == seq_type]
            if len(seq_data) > 0:
                ax.scatter(seq_data[f'{metric}_before'], seq_data[f'{metric}_after'],
                          alpha=0.6, s=100, marker=marker, label=seq_type, color=color)

        # Add diagonal line (no change)
        lims = [
            np.min([ax.get_xlim(), ax.get_ylim()]),
            np.max([ax.get_xlim(), ax.get_ylim()]),
        ]
        ax.plot(lims, lims, 'k--', alpha=0.3, zorder=0, label='No change')

        ax.set_xlabel(f'{metric_labels[metric]} (Without Norm)')
        ax.set_ylabel(f'{metric_labels[metric]} (With Norm)')
        ax.set_title(metric_labels[metric])
        ax.legend()
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / 'scatter_before_after_normalization.png', dpi=300, bbox_inches='tight')
    plt.close()

    # 3. Bar plot: Mean improvement by sequence type
    print("Creating improvement bar plots...")
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle('Mean Metric Improvement After Ventricle Normalization',
                 fontsize=14, fontweight='bold')

    plot_metrics = ['ssim_mean', 'pearson_r', 'ncc']

    for idx, metric in enumerate(plot_metrics):
        if metric not in normalized_df.columns:
            continue

        ax = axes[idx]

        improvements = []
        seq_types = []

        for seq_type in ['T1', 'T2', 'SWI']:
            # Match comparisons
            merged = pd.merge(
                non_normalized_df[non_normalized_df['sequence_type'] == seq_type][['comparison', metric]],
                normalized_df[normalized_df['sequence_type'] == seq_type][['comparison', metric]],
                on='comparison',
                suffixes=('_before', '_after')
            )

            if len(merged) > 0:
                improvement = (merged[f'{metric}_after'] - merged[f'{metric}_before']).mean()
                improvements.append(improvement)
                seq_types.append(seq_type)

        if improvements:
            colors = ['blue' if x >= 0 else 'red' for x in improvements]
            bars = ax.bar(seq_types, improvements, color=colors, alpha=0.7)

            # Add value labels on bars
            for bar, val in zip(bars, improvements):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{val:+.4f}',
                       ha='center', va='bottom' if height > 0 else 'top')

            ax.axhline(y=0, color='k', linestyle='-', linewidth=0.5)
            ax.set_ylabel(f'Mean Δ{metric_labels[metric]}')
            ax.set_title(metric_labels[metric])
            ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(output_dir / 'bar_mean_improvements.png', dpi=300, bbox_inches='tight')
    plt.close()

    # 4. Violin plots: Distribution comparison
    print("Creating violin plots...")
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    fig.suptitle('Metric Distributions: With vs Without Ventricle Normalization',
                 fontsize=14, fontweight='bold')

    plot_metrics = ['ssim_mean', 'pearson_r', 'ncc', 'psnr']

    for idx, metric in enumerate(plot_metrics):
        if metric not in combined.columns:
            continue

        ax = axes[idx // 2, idx % 2]

        # Filter valid data
        valid_data = combined[combined[metric].notna()]

        if len(valid_data) > 0:
            sns.violinplot(data=valid_data, x='sequence_type', y=metric,
                          hue='normalization', split=True, ax=ax)
            ax.set_xlabel('Sequence Type')
            ax.set_ylabel(metric_labels[metric])
            ax.set_title(metric_labels[metric])
            ax.legend(title='', loc='best')
        else:
            ax.text(0.5, 0.5, 'No valid data', ha='center', va='center')
            ax.set_title(metric_labels[metric])

    plt.tight_layout()
    plt.savefig(output_dir / 'violin_distributions.png', dpi=300, bbox_inches='tight')
    plt.close()

    # 5. Patient-by-patient comparison for key metric
    print("Creating patient-by-patient comparison...")
    metric = 'pearson_r'

    if metric in normalized_df.columns:
        # Merge data
        merged = pd.merge(
            non_normalized_df[['comparison', 'patient_id', 'sequence_type', metric]],
            normalized_df[['comparison', metric]],
            on='comparison',
            suffixes=('_before', '_after')
        )

        if len(merged) > 0:
            fig, ax = plt.subplots(figsize=(14, 8))

            # Sort by patient and sequence
            merged = merged.sort_values(['patient_id', 'sequence_type'])

            x = np.arange(len(merged))
            width = 0.35

            bars1 = ax.bar(x - width/2, merged[f'{metric}_before'], width,
                          label='Without Normalization', alpha=0.7)
            bars2 = ax.bar(x + width/2, merged[f'{metric}_after'], width,
                          label='With Ventricle Normalization', alpha=0.7)

            ax.set_ylabel('Pearson Correlation', fontsize=12)
            ax.set_title('Patient-by-Patient Comparison: Pearson Correlation',
                        fontsize=14, fontweight='bold')
            ax.set_xticks(x)

            # Create labels with patient and sequence
            labels = [f"{row['patient_id']}\n{row['sequence_type']}"
                     for _, row in merged.iterrows()]
            ax.set_xticklabels(labels, rotation=45, ha='right')

            ax.legend()
            ax.grid(True, alpha=0.3, axis='y')
            ax.axhline(y=0, color='k', linestyle='-', linewidth=0.5)

            plt.tight_layout()
            plt.savefig(output_dir / 'patient_by_patient_pearson.png', dpi=300, bbox_inches='tight')
            plt.close()

    # 6. Heatmap: Percentage improvements
    print("Creating improvement heatmap...")

    metrics_to_compare = ['ssim_mean', 'pearson_r', 'ncc', 'psnr']
    sequence_types = ['T1', 'T2', 'SWI']

    improvement_matrix = []

    for seq_type in sequence_types:
        row = []
        for metric in metrics_to_compare:
            if metric not in normalized_df.columns:
                row.append(0)
                continue

            # Merge data
            merged = pd.merge(
                non_normalized_df[non_normalized_df['sequence_type'] == seq_type][['comparison', metric]],
                normalized_df[normalized_df['sequence_type'] == seq_type][['comparison', metric]],
                on='comparison',
                suffixes=('_before', '_after')
            )

            if len(merged) > 0 and merged[f'{metric}_before'].mean() != 0:
                before_mean = merged[f'{metric}_before'].mean()
                after_mean = merged[f'{metric}_after'].mean()
                pct_change = ((after_mean - before_mean) / abs(before_mean)) * 100
                row.append(pct_change)
            else:
                row.append(0)

        improvement_matrix.append(row)

    improvement_df = pd.DataFrame(
        improvement_matrix,
        index=sequence_types,
        columns=[metric_labels[m] for m in metrics_to_compare]
    )

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.heatmap(improvement_df, annot=True, fmt='.1f', cmap='RdYlGn', center=0,
                cbar_kws={'label': 'Percent Change (%)'}, ax=ax)
    ax.set_title('Percentage Change in Metrics After Ventricle Normalization',
                fontsize=14, fontweight='bold')
    ax.set_xlabel('Metric')
    ax.set_ylabel('Sequence Type')

    plt.tight_layout()
    plt.savefig(output_dir / 'heatmap_percent_improvements.png', dpi=300, bbox_inches='tight')
    plt.close()

    print(f"\n✓ All plots saved to {output_dir}/")

def create_summary_figure(normalized_df, non_normalized_df, output_dir):
    """Create a single summary figure with key results"""

    print("Creating summary figure...")

    # Extract info
    normalized_df = extract_info(normalized_df)
    non_normalized_df = extract_info(non_normalized_df)

    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

    # Main title
    fig.suptitle('Ventricle-Based Intensity Normalization: Impact Summary',
                 fontsize=16, fontweight='bold', y=0.98)

    # 1. Overall metric improvements (top row, spans 2 columns)
    ax1 = fig.add_subplot(gs[0, :2])

    metrics = ['ssim_mean', 'pearson_r', 'ncc']
    metric_names = ['SSIM', 'Pearson r', 'NCC']

    before_means = []
    after_means = []

    for metric in metrics:
        if metric in normalized_df.columns:
            # Match comparisons
            merged = pd.merge(
                non_normalized_df[['comparison', metric]],
                normalized_df[['comparison', metric]],
                on='comparison',
                suffixes=('_before', '_after')
            )

            before_means.append(merged[f'{metric}_before'].mean())
            after_means.append(merged[f'{metric}_after'].mean())
        else:
            before_means.append(0)
            after_means.append(0)

    x = np.arange(len(metric_names))
    width = 0.35

    bars1 = ax1.bar(x - width/2, before_means, width, label='Without Normalization', alpha=0.7)
    bars2 = ax1.bar(x + width/2, after_means, width, label='With Ventricle Normalization', alpha=0.7)

    ax1.set_ylabel('Mean Value', fontsize=11)
    ax1.set_title('Overall Metric Improvements', fontsize=12, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(metric_names)
    ax1.legend()
    ax1.grid(True, alpha=0.3, axis='y')

    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.3f}',
                    ha='center', va='bottom', fontsize=9)

    # 2. Sample counts (top right)
    ax2 = fig.add_subplot(gs[0, 2])

    seq_counts = normalized_df['sequence_type'].value_counts()
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']

    if len(seq_counts) > 0:
        wedges, texts, autotexts = ax2.pie(seq_counts.values, labels=seq_counts.index,
                                            autopct='%1.0f%%', colors=colors[:len(seq_counts)])
        ax2.set_title('Comparisons by\nSequence Type', fontsize=12, fontweight='bold')

    # 3-5. Scatter plots for each sequence type (middle row)
    for idx, seq_type in enumerate(['T1', 'T2', 'SWI']):
        ax = fig.add_subplot(gs[1, idx])

        metric = 'pearson_r'

        if metric in normalized_df.columns:
            # Merge data for this sequence type
            merged = pd.merge(
                non_normalized_df[non_normalized_df['sequence_type'] == seq_type][['comparison', metric]],
                normalized_df[normalized_df['sequence_type'] == seq_type][['comparison', metric]],
                on='comparison',
                suffixes=('_before', '_after')
            )

            if len(merged) > 0:
                ax.scatter(merged[f'{metric}_before'], merged[f'{metric}_after'],
                          alpha=0.6, s=100, color=colors[idx])

                # Add diagonal
                lims = [
                    np.min([ax.get_xlim(), ax.get_ylim()]),
                    np.max([ax.get_xlim(), ax.get_ylim()]),
                ]
                ax.plot(lims, lims, 'k--', alpha=0.3, zorder=0)

                ax.set_xlabel('Before Normalization', fontsize=10)
                ax.set_ylabel('After Normalization', fontsize=10)
                ax.set_title(f'{seq_type}: Pearson r (n={len(merged)})', fontsize=11, fontweight='bold')
                ax.grid(True, alpha=0.3)
            else:
                ax.text(0.5, 0.5, f'No {seq_type} data', ha='center', va='center', transform=ax.transAxes)
                ax.set_title(f'{seq_type}: Pearson r', fontsize=11, fontweight='bold')

    # 6-8. Box plots for key metrics (bottom row)
    for idx, metric in enumerate(['ssim_mean', 'pearson_r', 'ncc']):
        ax = fig.add_subplot(gs[2, idx])

        if metric in normalized_df.columns:
            # Combine data
            norm_data = normalized_df[[metric, 'sequence_type']].copy()
            norm_data['normalization'] = 'With'

            non_norm_data = non_normalized_df[[metric, 'sequence_type']].copy()
            non_norm_data['normalization'] = 'Without'

            combined = pd.concat([norm_data, non_norm_data], ignore_index=True)

            sns.boxplot(data=combined, x='normalization', y=metric, ax=ax)
            ax.set_xlabel('')
            ax.set_ylabel(metric_names[idx], fontsize=10)
            ax.set_title(f'{metric_names[idx]} Distribution', fontsize=11, fontweight='bold')
            ax.tick_params(axis='x', rotation=0)

    plt.savefig(output_dir / 'SUMMARY_normalization_impact.png', dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✓ Summary figure saved")

def main():
    print("=" * 80)
    print("VENTRICLE NORMALIZATION: PLOTTING COMPARISON")
    print("=" * 80)
    print("")

    # Load data
    print("Loading metrics...")
    normalized_metrics = load_metrics('output/metrics')
    non_normalized_metrics = load_metrics('output/metrics_without_normalization')

    if normalized_metrics is None:
        print("Error: Could not load normalized metrics")
        return 1

    if non_normalized_metrics is None:
        print("Error: Could not load non-normalized metrics")
        return 1

    print(f"  - Normalized: {len(normalized_metrics)} comparisons")
    print(f"  - Non-normalized: {len(non_normalized_metrics)} comparisons")
    print("")

    # Create output directory
    output_dir = Path('output/plots')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate plots
    plot_metric_comparison(normalized_metrics.copy(), non_normalized_metrics.copy(), output_dir)
    create_summary_figure(normalized_metrics.copy(), non_normalized_metrics.copy(), output_dir)

    print("")
    print("=" * 80)
    print("PLOTTING COMPLETE")
    print("=" * 80)
    print(f"\nAll plots saved to: {output_dir}/")
    print("\nKey files:")
    print("  - SUMMARY_normalization_impact.png - Main summary figure")
    print("  - scatter_before_after_normalization.png - Before/after comparison")
    print("  - bar_mean_improvements.png - Improvement by sequence type")
    print("  - heatmap_percent_improvements.png - Percentage changes")
    print("  - patient_by_patient_pearson.png - Individual patient results")
    print("")

    return 0

if __name__ == '__main__':
    sys.exit(main())
