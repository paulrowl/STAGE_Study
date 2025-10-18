#!/usr/bin/env python3
"""
Generate 5 most important and interesting figures for STAGE MRI analysis
Publication-ready visualizations highlighting key findings
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for compatibility
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Set publication-quality style with white backgrounds
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (16, 10)
plt.rcParams['font.size'] = 11
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.labelweight'] = 'bold'
plt.rcParams['axes.titleweight'] = 'bold'
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = 'white'
plt.rcParams['savefig.facecolor'] = 'white'
plt.rcParams['savefig.edgecolor'] = 'none'

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

    return metrics

def get_significance_stars(p_value):
    """Convert p-value to significance stars"""
    if p_value < 0.001:
        return '***'
    elif p_value < 0.01:
        return '**'
    elif p_value < 0.05:
        return '*'
    else:
        return 'ns'

def figure1_main_findings_comparison(metrics, output_dir):
    """Figure 1: Key Metrics Comparison - Conventional vs STAGE"""
    fig, axes = plt.subplots(2, 3, figsize=(20, 12))

    sequences = ['T1', 'T2', 'SWI']
    colors = {'T1': '#2ecc71', 'T2': '#3498db', 'SWI': '#e74c3c'}

    # Metrics to compare: SNR, CNR, SSIM
    metrics_to_plot = ['snr', 'cnr', 'ssim_mean']
    metric_labels = ['SNR', 'CNR', 'SSIM']

    for col_idx, (metric, label) in enumerate(zip(metrics_to_plot, metric_labels)):
        ax = axes[0, col_idx]

        # Collect data for all sequences
        conv_data = []
        stage_data = []
        positions = []
        seq_labels = []

        for seq_idx, seq in enumerate(sequences):
            if seq not in metrics:
                continue

            df = metrics[seq]

            if metric == 'snr':
                conv_col = 'conv_snr'
                stage_col = 'stage_snr'
            elif metric == 'cnr':
                conv_col = 'conv_cnr'
                stage_col = 'stage_cnr'
            else:
                conv_col = metric
                stage_col = metric

            if conv_col in df.columns and stage_col in df.columns:
                conv_vals = df[conv_col].dropna()
                stage_vals = df[stage_col].dropna()

                # For SSIM, we just have one value (comparison metric)
                if metric == 'ssim_mean':
                    stage_vals = df[metric].dropna()
                    # Plot as single box
                    bp = ax.boxplot([stage_vals], positions=[seq_idx], widths=0.6,
                                   patch_artist=True, showmeans=True,
                                   meanprops=dict(marker='D', markerfacecolor='red', markersize=8))
                    bp['boxes'][0].set_facecolor(colors[seq])
                    bp['boxes'][0].set_alpha(0.7)
                else:
                    # Plot paired boxes
                    positions_pair = [seq_idx*3, seq_idx*3 + 1]
                    bp = ax.boxplot([conv_vals, stage_vals], positions=positions_pair, widths=0.6,
                                   patch_artist=True, showmeans=True,
                                   meanprops=dict(marker='D', markerfacecolor='red', markersize=8))

                    bp['boxes'][0].set_facecolor('lightgray')
                    bp['boxes'][0].set_alpha(0.7)
                    bp['boxes'][1].set_facecolor(colors[seq])
                    bp['boxes'][1].set_alpha(0.7)

                    # Add significance test
                    if metric in ['snr', 'cnr']:
                        # Paired t-test for same patients
                        common_idx = df[[conv_col, stage_col]].dropna().index
                        if len(common_idx) > 2:
                            t_stat, p_val = stats.ttest_rel(
                                df.loc[common_idx, conv_col],
                                df.loc[common_idx, stage_col]
                            )
                            stars = get_significance_stars(p_val)

                            # Add significance annotation
                            y_max = max(conv_vals.max(), stage_vals.max())
                            ax.text(seq_idx*3 + 0.5, y_max * 1.1, stars,
                                   ha='center', fontsize=16, fontweight='bold')

        if metric == 'ssim_mean':
            ax.set_xticks(range(len(sequences)))
            ax.set_xticklabels(sequences, fontsize=12, fontweight='bold')
            ax.set_title(f'{label} (Conventional vs STAGE Agreement)', fontsize=14, fontweight='bold')
        else:
            ax.set_xticks([i*3 + 0.5 for i in range(len(sequences))])
            ax.set_xticklabels(sequences, fontsize=12, fontweight='bold')
            ax.set_title(f'{label}: Conventional vs STAGE', fontsize=14, fontweight='bold')

        ax.set_ylabel(label, fontsize=12, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)

        # Add legend for non-SSIM plots
        if metric != 'ssim_mean':
            from matplotlib.patches import Patch
            legend_elements = [
                Patch(facecolor='lightgray', alpha=0.7, label='Conventional'),
                Patch(facecolor='gray', alpha=0.7, label='STAGE')
            ]
            ax.legend(handles=legend_elements, loc='upper right', fontsize=10)

    # Bottom row: Paired differences
    for col_idx, (metric, label) in enumerate(zip(['snr', 'cnr', 'ssim_mean'], metric_labels)):
        ax = axes[1, col_idx]

        differences = []
        labels_list = []
        colors_list = []

        for seq in sequences:
            if seq not in metrics:
                continue

            df = metrics[seq]

            if metric == 'ssim_mean':
                # For SSIM, show distribution directly
                if metric in df.columns:
                    vals = df[metric].dropna()
                    differences.append(vals)
                    labels_list.append(seq)
                    colors_list.append(colors[seq])
            else:
                conv_col = f'conv_{metric}'
                stage_col = f'stage_{metric}'

                if conv_col in df.columns and stage_col in df.columns:
                    common_idx = df[[conv_col, stage_col]].dropna().index
                    if len(common_idx) > 0:
                        diff = df.loc[common_idx, stage_col] - df.loc[common_idx, conv_col]
                        differences.append(diff)
                        labels_list.append(seq)
                        colors_list.append(colors[seq])

        if differences:
            vp = ax.violinplot(differences, positions=range(len(differences)),
                              showmeans=True, showmedians=True)

            # Color the violins
            for pc, color in zip(vp['bodies'], colors_list):
                pc.set_facecolor(color)
                pc.set_alpha(0.7)

            # Add zero line for difference plots
            if metric != 'ssim_mean':
                ax.axhline(0, color='red', linestyle='--', linewidth=2, alpha=0.5)
                ax.set_ylabel(f'{label} Difference\n(STAGE - Conventional)', fontsize=12, fontweight='bold')
            else:
                ax.set_ylabel(f'{label} Distribution', fontsize=12, fontweight='bold')

            ax.set_xticks(range(len(labels_list)))
            ax.set_xticklabels(labels_list, fontsize=12, fontweight='bold')
            ax.grid(axis='y', alpha=0.3)

    plt.suptitle('Key Metrics Comparison: Conventional vs STAGE MRI',
                 fontsize=18, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig(output_dir / 'key_figure1_main_findings.png', dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    print(f"✓ Saved: key_figure1_main_findings.png")
    plt.close()

def figure2_ssim_expert_correlation(metrics, output_dir):
    """Figure 2: SSIM vs Expert Score - The Gold Standard Comparison"""
    fig, axes = plt.subplots(1, 3, figsize=(20, 6))

    colors = {'T1': '#2ecc71', 'T2': '#3498db', 'SWI': '#e74c3c'}

    for idx, (seq, df) in enumerate(metrics.items()):
        ax = axes[idx]

        expert_col = 'expert_score'  # Fixed: use actual column name
        if expert_col not in df.columns or 'ssim_mean' not in df.columns:
            continue

        data = df[[expert_col, 'ssim_mean']].dropna()
        x = data[expert_col]
        y = data['ssim_mean']

        # Create scatter with size proportional to adequacy
        sizes = [150 if score >= 4 else 80 for score in x]
        scatter_colors = ['green' if score >= 4 else 'red' for score in x]

        ax.scatter(x, y, s=sizes, c=scatter_colors, alpha=0.6, edgecolors='black', linewidth=1.5)

        # Fit line
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        x_line = np.linspace(x.min(), x.max(), 100)
        ax.plot(x_line, p(x_line), "b--", alpha=0.8, linewidth=3, label='Linear fit')

        # Calculate correlations
        pearson_r, pearson_p = stats.pearsonr(x, y)
        spearman_r, spearman_p = stats.spearmanr(x, y)

        # Add detailed statistics box
        stats_text = f'Pearson r = {pearson_r:.3f}\n'
        stats_text += f'p = {pearson_p:.4f} {get_significance_stars(pearson_p)}\n\n'
        stats_text += f'Spearman ρ = {spearman_r:.3f}\n'
        stats_text += f'p = {spearman_p:.4f} {get_significance_stars(spearman_p)}\n\n'
        stats_text += f'n = {len(data)} patients\n'
        stats_text += f'Adequate (≥4): {(x >= 4).sum()}'

        ax.text(0.05, 0.95, stats_text, transform=ax.transAxes,
               fontsize=11, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.9, edgecolor='black', linewidth=2))

        # Add adequacy threshold line
        ax.axvline(4, color='black', linestyle=':', linewidth=2.5, label='Adequacy threshold', alpha=0.7)

        ax.set_xlabel(f'{seq} Expert Quality Score (1-9)', fontsize=13, fontweight='bold')
        ax.set_ylabel('SSIM (Structural Similarity Index)', fontsize=13, fontweight='bold')
        ax.set_title(f'{seq}: Image Quality Correlation', fontsize=15, fontweight='bold',
                    color=colors[seq], pad=10)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, 9.5)
        ax.legend(loc='lower right', fontsize=10)

    plt.suptitle('Expert Score vs SSIM: Validation of Automated Quality Metrics',
                 fontsize=18, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output_dir / 'key_figure2_ssim_validation.png', dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    print(f"✓ Saved: key_figure2_ssim_validation.png")
    plt.close()

def figure3_performance_extremes(metrics, output_dir):
    """Figure 3: Good vs Poor Quality Performers - Detailed Analysis"""
    fig = plt.figure(figsize=(22, 13))
    gs = fig.add_gridspec(3, 5, hspace=0.35, wspace=0.3)

    colors = {'T1': '#2ecc71', 'T2': '#3498db', 'SWI': '#e74c3c'}
    quality_metrics = ['ssim_mean', 'pearson_r', 'ncc', 'stage_snr']
    metric_labels = ['SSIM', 'Pearson r', 'NCC', 'SNR']

    for seq_idx, (seq, df) in enumerate(metrics.items()):
        expert_col = 'expert_score'  # Fixed: use actual column name
        if expert_col not in df.columns:
            continue

        # Define groups - using Good (≥6) vs Poor (<4) for better sample sizes
        very_good = df[df[expert_col] >= 6].copy()
        very_bad = df[df[expert_col] < 4].copy()

        n_good = len(very_good)
        n_bad = len(very_bad)

        row = seq_idx

        # Column 0: Score distribution
        ax0 = fig.add_subplot(gs[row, 0])

        all_scores = df[expert_col].dropna()
        bins = np.arange(0.5, 10.5, 1)

        ax0.hist(all_scores, bins=bins, color=colors[seq], alpha=0.3, edgecolor='black', label='All patients')

        if n_good > 0:
            ax0.hist(very_good[expert_col], bins=bins, color='green', alpha=0.7,
                    edgecolor='black', linewidth=1.5, label=f'Good (≥6): n={n_good}')
        if n_bad > 0:
            ax0.hist(very_bad[expert_col], bins=bins, color='red', alpha=0.7,
                    edgecolor='black', linewidth=1.5, label=f'Poor (<4): n={n_bad}')

        ax0.axvline(4, color='black', linestyle='--', linewidth=2, label='Adequacy', alpha=0.7)
        ax0.set_xlabel('Expert Score', fontsize=11, fontweight='bold')
        ax0.set_ylabel('Count', fontsize=11, fontweight='bold')
        ax0.set_title(f'{seq}: Quality Distribution', fontsize=12, fontweight='bold', color=colors[seq])
        ax0.legend(fontsize=9, loc='upper right')
        ax0.grid(axis='y', alpha=0.3)

        # Columns 1-4: Metric comparisons
        for metric_idx, (metric, label) in enumerate(zip(quality_metrics, metric_labels)):
            ax = fig.add_subplot(gs[row, metric_idx + 1])

            good_data = very_good[[expert_col, metric]].dropna()
            bad_data = very_bad[[expert_col, metric]].dropna()

            # Scatter plots with jitter
            if len(good_data) > 0:
                x_jitter = good_data[expert_col] + np.random.normal(0, 0.05, len(good_data))
                ax.scatter(x_jitter, good_data[metric],
                         color='green', s=120, alpha=0.7, label=f'Very Good (n={len(good_data)})',
                         edgecolors='black', linewidth=1.5, marker='o')

            if len(bad_data) > 0:
                x_jitter = bad_data[expert_col] + np.random.normal(0, 0.05, len(bad_data))
                ax.scatter(x_jitter, bad_data[metric],
                         color='red', s=120, alpha=0.7, label=f'Very Bad (n={len(bad_data)})',
                         edgecolors='black', linewidth=1.5, marker='s')

            # Statistical comparison
            if len(good_data) > 2 and len(bad_data) > 2:
                # Mann-Whitney U test (non-parametric)
                u_stat, p_val = stats.mannwhitneyu(good_data[metric], bad_data[metric], alternative='two-sided')
                stars = get_significance_stars(p_val)

                # Effect size (Cohen's d)
                mean_diff = good_data[metric].mean() - bad_data[metric].mean()
                pooled_std = np.sqrt((good_data[metric].std()**2 + bad_data[metric].std()**2) / 2)
                cohens_d = mean_diff / pooled_std if pooled_std > 0 else 0

                stats_text = f'p = {p_val:.4f} {stars}\n'
                stats_text += f"Cohen's d = {cohens_d:.2f}\n"
                stats_text += f'Good: {good_data[metric].mean():.2f}±{good_data[metric].std():.2f}\n'
                stats_text += f'Bad: {bad_data[metric].mean():.2f}±{bad_data[metric].std():.2f}'

                ax.text(0.05, 0.95, stats_text, transform=ax.transAxes,
                       fontsize=9, verticalalignment='top',
                       bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9, edgecolor='black'))

            ax.set_xlabel('Expert Score', fontsize=11, fontweight='bold')
            ax.set_ylabel(label, fontsize=11, fontweight='bold')
            ax.set_title(f'{seq}: {label}', fontsize=12, fontweight='bold')
            ax.legend(fontsize=8, loc='lower right')
            ax.grid(True, alpha=0.3)
            ax.set_xlim(0, 10)

    plt.suptitle('Quality Comparison: Good (≥6) vs Poor (<4) Performance Analysis',
                 fontsize=18, fontweight='bold', y=0.997)
    plt.savefig(output_dir / 'key_figure3_performance_extremes.png', dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    print(f"✓ Saved: key_figure3_performance_extremes.png")
    plt.close()

def figure4_statistical_significance_summary(metrics, output_dir):
    """Figure 4: Statistical Significance Summary - Effect Sizes and P-values"""
    fig, axes = plt.subplots(1, 3, figsize=(20, 8))

    sequences = ['T1', 'T2', 'SWI']
    colors = {'T1': '#2ecc71', 'T2': '#3498db', 'SWI': '#e74c3c'}

    # Metrics to test
    test_metrics = [
        ('mean_intensity', 'Mean Intensity'),
        ('std_dev', 'Std Dev'),
        ('snr', 'SNR'),
        ('cnr', 'CNR'),
        ('coefficient_variation', 'CV')
    ]

    for seq_idx, seq in enumerate(sequences):
        if seq not in metrics:
            continue

        ax = axes[seq_idx]
        df = metrics[seq]

        effect_sizes = []
        p_values = []
        labels = []
        significance = []

        for metric, label in test_metrics:
            conv_col = f'conv_{metric}'
            stage_col = f'stage_{metric}'

            if conv_col in df.columns and stage_col in df.columns:
                common_idx = df[[conv_col, stage_col]].dropna().index

                if len(common_idx) > 2:
                    conv_vals = df.loc[common_idx, conv_col]
                    stage_vals = df.loc[common_idx, stage_col]

                    # Paired t-test
                    t_stat, p_val = stats.ttest_rel(conv_vals, stage_vals)

                    # Cohen's d for paired samples
                    diff = stage_vals - conv_vals
                    cohens_d = diff.mean() / diff.std()

                    effect_sizes.append(cohens_d)
                    p_values.append(p_val)
                    labels.append(label)
                    significance.append(get_significance_stars(p_val))

        if effect_sizes:
            y_pos = np.arange(len(labels))

            # Color by significance
            bar_colors = ['green' if p < 0.05 else 'gray' for p in p_values]

            bars = ax.barh(y_pos, effect_sizes, color=bar_colors, alpha=0.7, edgecolor='black', linewidth=1.5)

            # Add vertical line at 0
            ax.axvline(0, color='red', linestyle='--', linewidth=2, alpha=0.7)

            # Add significance stars
            for i, (es, sig) in enumerate(zip(effect_sizes, significance)):
                x_pos = es + 0.05 if es > 0 else es - 0.05
                ax.text(x_pos, i, sig, va='center', fontsize=12, fontweight='bold')

            ax.set_yticks(y_pos)
            ax.set_yticklabels(labels, fontsize=11, fontweight='bold')
            ax.set_xlabel("Effect Size (Cohen's d)", fontsize=12, fontweight='bold')
            ax.set_title(f'{seq}: STAGE vs Conventional\nEffect Sizes',
                        fontsize=13, fontweight='bold', color=colors[seq])
            ax.grid(axis='x', alpha=0.3)

            # Add legend
            from matplotlib.patches import Patch
            legend_elements = [
                Patch(facecolor='green', alpha=0.7, label='Significant (p<0.05)'),
                Patch(facecolor='gray', alpha=0.7, label='Not Significant')
            ]
            ax.legend(handles=legend_elements, loc='lower right', fontsize=10)

    plt.suptitle('Statistical Significance Summary: STAGE vs Conventional MRI',
                 fontsize=18, fontweight='bold', y=0.98)
    plt.tight_layout()
    plt.savefig(output_dir / 'key_figure4_statistical_summary.png', dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    print(f"✓ Saved: key_figure4_statistical_summary.png")
    plt.close()

def figure5_comprehensive_overview(metrics, output_dir):
    """Figure 5: Comprehensive Overview - Sample Sizes, Quality Distribution, and Key Findings"""
    fig = plt.figure(figsize=(22, 10))
    gs = fig.add_gridspec(2, 4, hspace=0.3, wspace=0.3)

    sequences = ['T1', 'T2', 'SWI']
    colors = {'T1': '#2ecc71', 'T2': '#3498db', 'SWI': '#e74c3c'}

    # Panel 1: Sample sizes
    ax1 = fig.add_subplot(gs[0, 0])

    sample_sizes = []
    with_expert = []
    for seq in sequences:
        if seq in metrics:
            df = metrics[seq]
            sample_sizes.append(len(df))
            expert_col = 'expert_score'  # Fixed: use actual column name
            if expert_col in df.columns:
                with_expert.append(df[expert_col].notna().sum())
            else:
                with_expert.append(0)

    x = np.arange(len(sequences))
    width = 0.35

    ax1.bar(x - width/2, sample_sizes, width, label='Total Patients', color='lightblue', edgecolor='black', linewidth=1.5)
    ax1.bar(x + width/2, with_expert, width, label='With Expert Scores', color='orange', edgecolor='black', linewidth=1.5)

    ax1.set_ylabel('Number of Patients', fontsize=12, fontweight='bold')
    ax1.set_title('Sample Sizes by Sequence', fontsize=13, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(sequences, fontsize=11, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(axis='y', alpha=0.3)

    # Add values on bars
    for i, (total, expert) in enumerate(zip(sample_sizes, with_expert)):
        ax1.text(i - width/2, total + 0.5, str(total), ha='center', fontsize=10, fontweight='bold')
        ax1.text(i + width/2, expert + 0.5, str(expert), ha='center', fontsize=10, fontweight='bold')

    # Panel 2-4: Quality distribution by sequence
    for seq_idx, seq in enumerate(sequences):
        ax = fig.add_subplot(gs[0, seq_idx + 1])

        if seq in metrics:
            df = metrics[seq]
            expert_col = 'expert_score'  # Fixed: use actual column name

            if expert_col in df.columns:
                scores = df[expert_col].dropna()

                # Categorize
                poor = (scores < 4).sum()
                adequate = ((scores >= 4) & (scores < 6)).sum()
                good = (scores >= 6).sum()

                categories = ['Poor\n(<4)', 'Adequate\n(4-6)', 'Good\n(≥6)']
                counts = [poor, adequate, good]
                colors_bars = ['#e74c3c', '#f39c12', '#2ecc71']

                bars = ax.bar(categories, counts, color=colors_bars, alpha=0.7, edgecolor='black', linewidth=1.5)

                # Add percentages
                total = len(scores)
                for i, (cat, count) in enumerate(zip(categories, counts)):
                    pct = count / total * 100
                    ax.text(i, count + 0.5, f'{count}\n({pct:.1f}%)', ha='center', fontsize=10, fontweight='bold')

                ax.set_ylabel('Number of Patients', fontsize=11, fontweight='bold')
                ax.set_title(f'{seq} Quality Categories', fontsize=12, fontweight='bold', color=colors[seq])
                ax.grid(axis='y', alpha=0.3)

    # Bottom row: Key correlations heatmap
    for seq_idx, seq in enumerate(sequences):
        ax = fig.add_subplot(gs[1, seq_idx])

        if seq not in metrics:
            continue

        df = metrics[seq]
        expert_col = 'expert_score'  # Fixed: use actual column name

        if expert_col not in df.columns:
            continue

        # Select metrics for correlation
        corr_metrics = [expert_col, 'ssim_mean', 'pearson_r', 'stage_snr', 'stage_cnr']
        available = [m for m in corr_metrics if m in df.columns]

        if len(available) > 1:
            corr_data = df[available].dropna()

            if len(corr_data) > 2:
                corr_matrix = corr_data.corr()

                # Plot heatmap
                im = ax.imshow(corr_matrix, cmap='RdYlGn', aspect='auto', vmin=-1, vmax=1)

                # Labels
                labels = ['Expert', 'SSIM', 'Pearson', 'SNR', 'CNR'][:len(available)]
                ax.set_xticks(np.arange(len(labels)))
                ax.set_yticks(np.arange(len(labels)))
                ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=10)
                ax.set_yticklabels(labels, fontsize=10)

                # Add correlation values
                for i in range(len(labels)):
                    for j in range(len(labels)):
                        text = ax.text(j, i, f'{corr_matrix.iloc[i, j]:.2f}',
                                     ha="center", va="center", color="black", fontsize=9, fontweight='bold')

                ax.set_title(f'{seq}: Metric Correlations (n={len(corr_data)})',
                            fontsize=11, fontweight='bold', color=colors[seq])

                # Colorbar
                cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
                cbar.set_label('Correlation', fontsize=10)

    # Bottom right: Key findings text summary
    ax_summary = fig.add_subplot(gs[1, 3])
    ax_summary.axis('off')

    summary_text = "KEY FINDINGS\n" + "="*40 + "\n\n"

    for seq_idx, seq in enumerate(sequences):
        if seq not in metrics:
            continue

        df = metrics[seq]
        expert_col = 'expert_score'  # Fixed: use actual column name

        summary_text += f"{seq}:\n"
        summary_text += f"  • Patients: {len(df)}\n"

        if expert_col in df.columns:
            scores = df[expert_col].dropna()
            summary_text += f"  • Mean Score: {scores.mean():.2f}±{scores.std():.2f}\n"
            summary_text += f"  • Adequate: {(scores >= 4).sum()}/{len(scores)} ({(scores >= 4).sum()/len(scores)*100:.1f}%)\n"

            if 'ssim_mean' in df.columns:
                corr_data = df[[expert_col, 'ssim_mean']].dropna()
                if len(corr_data) > 2:
                    r, p = stats.pearsonr(corr_data[expert_col], corr_data['ssim_mean'])
                    summary_text += f"  • SSIM Correlation: r={r:.3f}"
                    summary_text += f" {get_significance_stars(p)}\n"

        summary_text += "\n"

    ax_summary.text(0.1, 0.9, summary_text, transform=ax_summary.transAxes,
                   fontsize=11, verticalalignment='top', fontfamily='monospace',
                   bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3, edgecolor='black', linewidth=2))

    plt.suptitle('Comprehensive Study Overview: STAGE MRI Quality Assessment',
                 fontsize=18, fontweight='bold', y=0.98)
    plt.savefig(output_dir / 'key_figure5_comprehensive_overview.png', dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    print(f"✓ Saved: key_figure5_comprehensive_overview.png")
    plt.close()

def main():
    print("="*80)
    print("GENERATING 5 KEY FINDINGS FIGURES")
    print("Publication-quality visualizations of most important results")
    print("="*80)

    output_dir = Path('output/figures')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load all metrics
    print("\nLoading metrics data...")
    metrics = load_all_metrics()

    if not metrics:
        print("Error: No metrics data found!")
        return

    print(f"\nLoaded data for {len(metrics)} sequences")
    print("\nGenerating key figures...")
    print("-"*80)

    # Generate each figure
    figure1_main_findings_comparison(metrics, output_dir)
    figure2_ssim_expert_correlation(metrics, output_dir)
    figure3_performance_extremes(metrics, output_dir)
    figure4_statistical_significance_summary(metrics, output_dir)
    figure5_comprehensive_overview(metrics, output_dir)

    print("-"*80)
    print("\n✅ ALL 5 KEY FIGURES GENERATED SUCCESSFULLY!")
    print(f"\nSaved to: {output_dir}/")
    print("\nFigures:")
    print("  1. key_figure1_main_findings.png - SNR/CNR/SSIM comparisons with significance")
    print("  2. key_figure2_ssim_validation.png - Expert vs SSIM correlation analysis")
    print("  3. key_figure3_performance_extremes.png - Good (≥6) vs Poor (<4) detailed analysis")
    print("  4. key_figure4_statistical_summary.png - Effect sizes and p-values")
    print("  5. key_figure5_comprehensive_overview.png - Study overview and key findings")
    print("\n" + "="*80)

if __name__ == '__main__':
    main()
