#!/usr/bin/env python3
"""
Generate 5 comprehensive summary figures for STAGE MRI analysis
Including special analysis of very good vs very bad performers
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (16, 10)
plt.rcParams['font.size'] = 10

def load_all_metrics():
    """Load T1, T2, and SWI metrics with expert scores"""
    stats_dir = Path('output/statistics')

    metrics = {}
    for seq in ['t1', 't2', 'swi']:
        file_path = stats_dir / f'{seq}_metrics_with_expert_scores.csv'
        if file_path.exists():
            df = pd.read_csv(file_path)
            metrics[seq.upper()] = df
            print(f"Loaded {seq.upper()}: {len(df)} patients")
        else:
            print(f"Warning: {file_path} not found")

    return metrics

def figure1_expert_score_distributions(metrics, output_dir):
    """Figure 1: Distribution of expert scores across all sequences"""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    colors = {'T1': '#2ecc71', 'T2': '#3498db', 'SWI': '#e74c3c'}

    for idx, (seq, df) in enumerate(metrics.items()):
        ax = axes[idx]

        expert_col = f'Q{idx+1}_Expert_Score'
        if expert_col in df.columns:
            scores = df[expert_col].dropna()

            # Histogram
            ax.hist(scores, bins=np.arange(0.5, 10.5, 1),
                   color=colors[seq], alpha=0.7, edgecolor='black')

            # Add statistics
            mean_score = scores.mean()
            median_score = scores.median()
            adequate = (scores >= 4).sum()
            total = len(scores)

            ax.axvline(mean_score, color='red', linestyle='--', linewidth=2,
                      label=f'Mean: {mean_score:.2f}')
            ax.axvline(median_score, color='orange', linestyle='--', linewidth=2,
                      label=f'Median: {median_score:.1f}')
            ax.axvline(4, color='black', linestyle=':', linewidth=2,
                      label='Adequacy threshold')

            ax.set_xlabel(f'{seq} Expert Quality Score', fontsize=12, fontweight='bold')
            ax.set_ylabel('Number of Patients', fontsize=12, fontweight='bold')
            ax.set_title(f'{seq} Quality Distribution\n{adequate}/{total} ({adequate/total*100:.1f}%) Adequate (≥4)',
                        fontsize=13, fontweight='bold')
            ax.legend(loc='upper left')
            ax.set_xlim(0, 10)
            ax.grid(axis='y', alpha=0.3)

    plt.suptitle('Expert Quality Score Distributions Across Sequences',
                 fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output_dir / 'figure1_expert_score_distributions.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved: figure1_expert_score_distributions.png")
    plt.close()

def figure2_ssim_correlations(metrics, output_dir):
    """Figure 2: SSIM vs Expert Score with correlations"""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    colors = {'T1': '#2ecc71', 'T2': '#3498db', 'SWI': '#e74c3c'}

    for idx, (seq, df) in enumerate(metrics.items()):
        ax = axes[idx]

        expert_col = f'Q{idx+1}_Expert_Score'
        if expert_col in df.columns and 'ssim_mean' in df.columns:
            # Remove NaN values
            data = df[[expert_col, 'ssim_mean']].dropna()
            x = data[expert_col]
            y = data['ssim_mean']

            # Scatter plot
            ax.scatter(x, y, alpha=0.6, s=100, color=colors[seq], edgecolors='black', linewidth=0.5)

            # Calculate correlations
            pearson_r, pearson_p = stats.pearsonr(x, y)
            spearman_r, spearman_p = stats.spearmanr(x, y)

            # Fit line
            z = np.polyfit(x, y, 1)
            p = np.poly1d(z)
            x_line = np.linspace(x.min(), x.max(), 100)
            ax.plot(x_line, p(x_line), "r--", alpha=0.8, linewidth=2)

            # Add correlation text
            corr_text = f'Pearson r = {pearson_r:.3f} (p={pearson_p:.4f})\n'
            corr_text += f'Spearman ρ = {spearman_r:.3f} (p={spearman_p:.4f})\n'
            corr_text += f'n = {len(data)}'

            ax.text(0.05, 0.95, corr_text, transform=ax.transAxes,
                   fontsize=10, verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

            ax.set_xlabel(f'{seq} Expert Quality Score', fontsize=12, fontweight='bold')
            ax.set_ylabel('SSIM (Structural Similarity)', fontsize=12, fontweight='bold')
            ax.set_title(f'{seq}: SSIM vs Expert Score', fontsize=13, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.set_xlim(0, 10)

    plt.suptitle('SSIM Correlations with Expert Scores',
                 fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output_dir / 'figure2_ssim_correlations.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved: figure2_ssim_correlations.png")
    plt.close()

def figure3_good_vs_bad_performers(metrics, output_dir):
    """Figure 3: Very Good vs Very Bad Performers with detailed correlations"""
    fig = plt.figure(figsize=(20, 12))
    gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.3)

    colors = {'T1': '#2ecc71', 'T2': '#3498db', 'SWI': '#e74c3c'}
    quality_metrics = ['ssim_mean', 'pearson_r', 'ncc', 'stage_snr', 'stage_cnr']
    metric_labels = ['SSIM', 'Pearson r', 'NCC', 'SNR', 'CNR']

    for seq_idx, (seq, df) in enumerate(metrics.items()):
        expert_col = f'Q{seq_idx+1}_Expert_Score'
        if expert_col not in df.columns:
            continue

        # Define very good (≥7) and very bad (≤3)
        very_good = df[df[expert_col] >= 7].copy()
        very_bad = df[df[expert_col] <= 3].copy()

        n_good = len(very_good)
        n_bad = len(very_bad)

        # Row for this sequence
        row = seq_idx

        # Column 0: Distribution comparison
        ax0 = fig.add_subplot(gs[row, 0])

        if n_good > 0:
            ax0.hist(very_good[expert_col], bins=np.arange(6.5, 10.5, 1),
                    color='green', alpha=0.7, label=f'Very Good (n={n_good})')
        if n_bad > 0:
            ax0.hist(very_bad[expert_col], bins=np.arange(0.5, 4.5, 1),
                    color='red', alpha=0.7, label=f'Very Bad (n={n_bad})')

        ax0.set_xlabel('Expert Score', fontsize=10, fontweight='bold')
        ax0.set_ylabel('Count', fontsize=10, fontweight='bold')
        ax0.set_title(f'{seq}: Score Distribution', fontsize=11, fontweight='bold')
        ax0.legend()
        ax0.grid(axis='y', alpha=0.3)

        # Columns 1-3: Metric comparisons with correlations
        for metric_idx in range(3):
            ax = fig.add_subplot(gs[row, metric_idx + 1])

            if metric_idx < len(quality_metrics):
                metric = quality_metrics[metric_idx]
                label = metric_labels[metric_idx]

                # Prepare data
                good_data = very_good[[expert_col, metric]].dropna()
                bad_data = very_bad[[expert_col, metric]].dropna()

                # Scatter plots
                if len(good_data) > 0:
                    ax.scatter(good_data[expert_col], good_data[metric],
                             color='green', s=80, alpha=0.7, label=f'Very Good (n={len(good_data)})',
                             edgecolors='black', linewidth=0.5)

                if len(bad_data) > 0:
                    ax.scatter(bad_data[expert_col], bad_data[metric],
                             color='red', s=80, alpha=0.7, label=f'Very Bad (n={len(bad_data)})',
                             edgecolors='black', linewidth=0.5)

                # Calculate correlations for each group
                corr_text = ""
                if len(good_data) > 2:
                    r_good, p_good = stats.pearsonr(good_data[expert_col], good_data[metric])
                    corr_text += f'Good: r={r_good:.3f}\n'
                if len(bad_data) > 2:
                    r_bad, p_bad = stats.pearsonr(bad_data[expert_col], bad_data[metric])
                    corr_text += f'Bad: r={r_bad:.3f}\n'

                # Overall correlation
                all_data = pd.concat([good_data, bad_data])
                if len(all_data) > 2:
                    r_all, p_all = stats.pearsonr(all_data[expert_col], all_data[metric])
                    corr_text += f'All: r={r_all:.3f}'

                if corr_text:
                    ax.text(0.05, 0.95, corr_text, transform=ax.transAxes,
                           fontsize=9, verticalalignment='top',
                           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))

                ax.set_xlabel('Expert Score', fontsize=10, fontweight='bold')
                ax.set_ylabel(label, fontsize=10, fontweight='bold')
                ax.set_title(f'{seq}: {label}', fontsize=11, fontweight='bold')
                ax.legend(fontsize=8)
                ax.grid(True, alpha=0.3)

    plt.suptitle('Very Good (≥7) vs Very Bad (≤3) Performers: Quality Metrics Analysis',
                 fontsize=16, fontweight='bold', y=0.995)
    plt.savefig(output_dir / 'figure3_good_vs_bad_performers.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved: figure3_good_vs_bad_performers.png")
    plt.close()

def figure4_adequacy_thresholds(metrics, output_dir):
    """Figure 4: Adequacy threshold performance"""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    colors = {'T1': '#2ecc71', 'T2': '#3498db', 'SWI': '#e74c3c'}

    # Load threshold data
    threshold_file = Path('output/statistics/all_sequences_adequacy_thresholds.csv')
    thresholds_dict = {}
    if threshold_file.exists():
        thresh_df = pd.read_csv(threshold_file)
        # Create dict mapping (sequence, metric) -> threshold value
        for _, row in thresh_df.iterrows():
            key = (row['sequence'], row['metric'])
            thresholds_dict[key] = row['threshold']

    for idx, (seq, df) in enumerate(metrics.items()):
        ax = axes[idx]

        expert_col = f'Q{idx+1}_Expert_Score'
        if expert_col not in df.columns or 'ssim_mean' not in df.columns:
            continue

        data = df[[expert_col, 'ssim_mean']].dropna()

        # Categorize as adequate (≥4) or inadequate (<4)
        adequate = data[data[expert_col] >= 4]
        inadequate = data[data[expert_col] < 4]

        # Scatter plot
        if len(adequate) > 0:
            ax.scatter(adequate[expert_col], adequate['ssim_mean'],
                      color='green', s=100, alpha=0.7, label=f'Adequate (n={len(adequate)})',
                      edgecolors='black', linewidth=0.5)
        if len(inadequate) > 0:
            ax.scatter(inadequate[expert_col], inadequate['ssim_mean'],
                      color='red', s=100, alpha=0.7, label=f'Inadequate (n={len(inadequate)})',
                      edgecolors='black', linewidth=0.5)

        # Add threshold line if available
        threshold_key = (seq, 'ssim_mean')
        if threshold_key in thresholds_dict:
            ssim_threshold = thresholds_dict[threshold_key]
            ax.axhline(ssim_threshold, color='purple', linestyle='--', linewidth=2,
                      label=f'SSIM threshold: {ssim_threshold:.3f}')

        # Add adequacy line
        ax.axvline(4, color='black', linestyle=':', linewidth=2, label='Adequacy cutoff')

        # Calculate accuracy
        if threshold_key in thresholds_dict:
            ssim_threshold = thresholds_dict[threshold_key]
            true_pos = len(adequate[adequate['ssim_mean'] >= ssim_threshold])
            true_neg = len(inadequate[inadequate['ssim_mean'] < ssim_threshold])
            accuracy = (true_pos + true_neg) / len(data) * 100

            ax.text(0.05, 0.95, f'Classification Accuracy: {accuracy:.1f}%',
                   transform=ax.transAxes, fontsize=10, verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))

        ax.set_xlabel(f'{seq} Expert Quality Score', fontsize=12, fontweight='bold')
        ax.set_ylabel('SSIM', fontsize=12, fontweight='bold')
        ax.set_title(f'{seq}: Adequacy Threshold Performance', fontsize=13, fontweight='bold')
        ax.legend(loc='lower right', fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, 10)

    plt.suptitle('Quality Adequacy Assessment Using SSIM Thresholds',
                 fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output_dir / 'figure4_adequacy_thresholds.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved: figure4_adequacy_thresholds.png")
    plt.close()

def figure5_comprehensive_metrics_heatmap(metrics, output_dir):
    """Figure 5: Comprehensive metrics heatmap"""
    fig, axes = plt.subplots(1, 3, figsize=(20, 6))

    quality_metrics = ['ssim_mean', 'pearson_r', 'ncc', 'mae', 'psnr',
                      'stage_snr', 'stage_cnr', 'stage_cv']
    metric_labels = ['SSIM', 'Pearson r', 'NCC', 'MAE', 'PSNR',
                    'SNR', 'CNR', 'CV']

    for idx, (seq, df) in enumerate(metrics.items()):
        ax = axes[idx]

        expert_col = f'Q{idx+1}_Expert_Score'
        if expert_col not in df.columns:
            continue

        # Select relevant columns
        available_metrics = [m for m in quality_metrics if m in df.columns]
        data_cols = [expert_col] + available_metrics

        # Create correlation matrix
        corr_data = df[data_cols].dropna()
        if len(corr_data) < 3:
            continue

        corr_matrix = corr_data.corr()

        # Plot heatmap
        im = ax.imshow(corr_matrix, cmap='RdYlGn', aspect='auto', vmin=-1, vmax=1)

        # Set ticks
        labels = ['Expert\nScore'] + [metric_labels[quality_metrics.index(m)]
                                      for m in available_metrics]
        ax.set_xticks(np.arange(len(labels)))
        ax.set_yticks(np.arange(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=9)
        ax.set_yticklabels(labels, fontsize=9)

        # Add correlation values
        for i in range(len(labels)):
            for j in range(len(labels)):
                text = ax.text(j, i, f'{corr_matrix.iloc[i, j]:.2f}',
                             ha="center", va="center", color="black", fontsize=8)

        ax.set_title(f'{seq}: Metric Correlations\n(n={len(corr_data)} patients)',
                    fontsize=12, fontweight='bold')

        # Add colorbar
        cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('Correlation Coefficient', fontsize=10)

    plt.suptitle('Comprehensive Quality Metrics Correlation Matrix',
                 fontsize=16, fontweight='bold', y=0.98)
    plt.tight_layout()
    plt.savefig(output_dir / 'figure5_comprehensive_metrics_heatmap.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved: figure5_comprehensive_metrics_heatmap.png")
    plt.close()

def main():
    print("="*80)
    print("GENERATING 5 COMPREHENSIVE SUMMARY FIGURES")
    print("="*80)

    output_dir = Path('output/statistics')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load all metrics
    print("\nLoading metrics data...")
    metrics = load_all_metrics()

    if not metrics:
        print("Error: No metrics data found!")
        return

    print(f"\nLoaded data for {len(metrics)} sequences")
    print("\nGenerating figures...")
    print("-"*80)

    # Generate each figure
    figure1_expert_score_distributions(metrics, output_dir)
    figure2_ssim_correlations(metrics, output_dir)
    figure3_good_vs_bad_performers(metrics, output_dir)
    figure4_adequacy_thresholds(metrics, output_dir)
    figure5_comprehensive_metrics_heatmap(metrics, output_dir)

    print("-"*80)
    print("\n✅ ALL 5 FIGURES GENERATED SUCCESSFULLY!")
    print(f"\nSaved to: {output_dir}/")
    print("\nFigures:")
    print("  1. figure1_expert_score_distributions.png")
    print("  2. figure2_ssim_correlations.png")
    print("  3. figure3_good_vs_bad_performers.png ⭐ (Very Good vs Bad)")
    print("  4. figure4_adequacy_thresholds.png")
    print("  5. figure5_comprehensive_metrics_heatmap.png")
    print("\n" + "="*80)

if __name__ == '__main__':
    main()
