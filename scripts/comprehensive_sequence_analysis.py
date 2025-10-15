#!/usr/bin/env python3
"""
Comprehensive Sequence Analysis: T1, T2, and SWI Conv vs STAGE
Analyzes all three sequences with expert score correlations and adequacy thresholds
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

def load_expert_scores(scores_file):
    """Load and process expert scores"""
    df = pd.read_csv(scores_file)

    # Average scores for patients with multiple ratings
    scores = df.groupby('rAccession').agg({
        'Q1': 'mean',  # T1 score
        'Q2': 'mean',  # T2 score
        'Q3': 'mean'   # SWI score
    }).reset_index()

    scores.columns = ['patient_id', 'T1_expert_score', 'T2_expert_score', 'SWI_expert_score']

    print(f"Loaded expert scores for {len(scores)} patients")
    print(f"  T1 score:  {scores['T1_expert_score'].mean():.2f} ± {scores['T1_expert_score'].std():.2f} (range: {scores['T1_expert_score'].min():.1f}-{scores['T1_expert_score'].max():.1f})")
    print(f"  T2 score:  {scores['T2_expert_score'].mean():.2f} ± {scores['T2_expert_score'].std():.2f} (range: {scores['T2_expert_score'].min():.1f}-{scores['T2_expert_score'].max():.1f})")
    print(f"  SWI score: {scores['SWI_expert_score'].mean():.2f} ± {scores['SWI_expert_score'].std():.2f} (range: {scores['SWI_expert_score'].min():.1f}-{scores['SWI_expert_score'].max():.1f})")

    return scores

def collect_sequence_metrics(metrics_dir, sequence_type):
    """Collect metrics for a specific sequence type"""
    metrics_dir = Path(metrics_dir)
    all_metrics = []

    for patient_dir in sorted(metrics_dir.glob('Anon*')):
        patient_id = patient_dir.name

        # Look for comparison file
        metrics_file = patient_dir / f"{patient_id}_{sequence_type}_conv_vs_{sequence_type}_STAGE_metrics.csv"

        if metrics_file.exists():
            try:
                df = pd.read_csv(metrics_file)
                df['patient_id'] = patient_id
                df['sequence_type'] = sequence_type
                all_metrics.append(df)
            except Exception as e:
                print(f"Warning: Could not read {metrics_file}: {e}")

    if not all_metrics:
        print(f"Warning: No {sequence_type} metrics files found!")
        return None

    combined = pd.concat(all_metrics, ignore_index=True)
    print(f"  {sequence_type}: {len(combined)} patients")

    return combined

def merge_with_expert_scores(metrics_df, scores_df, score_column):
    """Merge metrics with expert scores"""
    merged = metrics_df.merge(scores_df[['patient_id', score_column]], on='patient_id', how='left')
    merged.rename(columns={score_column: 'expert_score'}, inplace=True)

    has_scores = merged['expert_score'].notna().sum()
    no_scores = merged['expert_score'].isna().sum()

    return merged, has_scores, no_scores

def calculate_paired_statistics(df, sequence_type):
    """Calculate paired statistics for conv vs STAGE"""

    comparison_metrics = [
        ('conv_mean', 'stage_mean', 'Mean Intensity'),
        ('conv_std', 'stage_std', 'Std Dev'),
        ('conv_snr', 'stage_snr', 'SNR'),
        ('conv_cnr', 'stage_cnr', 'CNR'),
        ('conv_cv', 'stage_cv', 'Coefficient of Variation'),
    ]

    results = []

    print(f"\n{'='*80}")
    print(f"PAIRED STATISTICS: {sequence_type} Conventional vs STAGE")
    print(f"{'='*80}\n")
    print(f"Sample size: {len(df)} patients\n")

    for conv_col, stage_col, metric_name in comparison_metrics:
        if conv_col not in df.columns or stage_col not in df.columns:
            continue

        valid_idx = df[[conv_col, stage_col]].dropna().index
        if len(valid_idx) < 2:
            continue

        conv_paired = df.loc[valid_idx, conv_col]
        stage_paired = df.loc[valid_idx, stage_col]

        # Paired t-test
        t_stat, t_pval = stats.ttest_rel(conv_paired, stage_paired)

        # Wilcoxon signed-rank test
        w_stat, w_pval = stats.wilcoxon(conv_paired, stage_paired)

        # Effect size
        diff = conv_paired - stage_paired
        cohens_d = diff.mean() / diff.std() if diff.std() > 0 else 0

        # Determine significance
        if t_pval < 0.001:
            sig = "***"
        elif t_pval < 0.01:
            sig = "**"
        elif t_pval < 0.05:
            sig = "*"
        else:
            sig = "ns"

        print(f"{metric_name}:")
        print(f"  Conventional: {conv_paired.mean():.4f} ± {conv_paired.std():.4f}")
        print(f"  STAGE:        {stage_paired.mean():.4f} ± {stage_paired.std():.4f}")
        print(f"  Difference:   {diff.mean():.4f} ± {diff.std():.4f}")
        print(f"  Paired t-test: t={t_stat:.4f}, p={t_pval:.4e} {sig}")
        print(f"  Effect size (Cohen's d): {cohens_d:.4f}\n")

        results.append({
            'sequence': sequence_type,
            'metric': metric_name,
            'conv_mean': conv_paired.mean(),
            'conv_std': conv_paired.std(),
            'stage_mean': stage_paired.mean(),
            'stage_std': stage_paired.std(),
            'diff_mean': diff.mean(),
            'diff_std': diff.std(),
            't_statistic': t_stat,
            'p_value': t_pval,
            'cohens_d': cohens_d,
            'significance': sig,
            'n': len(valid_idx)
        })

    return pd.DataFrame(results)

def analyze_expert_score_thresholds(df, sequence_type):
    """Analyze metrics relative to expert scores"""

    df_scored = df[df['expert_score'].notna()].copy()

    if len(df_scored) == 0:
        print(f"\nWarning: No {sequence_type} patients with expert scores!")
        return None, None

    print(f"\n{'='*80}")
    print(f"EXPERT SCORE THRESHOLD ANALYSIS: {sequence_type}")
    print(f"{'='*80}\n")
    print(f"Analyzing {len(df_scored)} patients with expert scores\n")

    # Define quality categories
    df_scored['quality_category'] = pd.cut(
        df_scored['expert_score'],
        bins=[0, 4, 6, 10],
        labels=['Poor (<4)', 'Adequate (4-6)', 'Good (≥6)']
    )

    print(f"{sequence_type} Quality Distribution:")
    print(df_scored['quality_category'].value_counts().sort_index())
    print()

    # Key metrics to analyze
    key_metrics = [
        'ssim_mean', 'pearson_r', 'ncc', 'mae', 'psnr',
        'stage_snr', 'stage_cnr', 'stage_cv'
    ]

    threshold_results = []

    for metric in key_metrics:
        if metric not in df_scored.columns:
            continue

        valid_data = df_scored[[metric, 'expert_score']].dropna()
        if len(valid_data) < 3:
            continue

        pearson_r, pearson_p = stats.pearsonr(valid_data[metric], valid_data['expert_score'])
        spearman_r, spearman_p = stats.spearmanr(valid_data[metric], valid_data['expert_score'])

        # By quality category
        by_quality = df_scored.groupby('quality_category')[metric].agg(['mean', 'std', 'count'])

        # Threshold for adequate quality
        adequate_cases = df_scored[df_scored['expert_score'] >= 4]
        poor_cases = df_scored[df_scored['expert_score'] < 4]

        if len(adequate_cases) > 0 and len(poor_cases) > 0:
            adequate_mean = adequate_cases[metric].mean()
            adequate_std = adequate_cases[metric].std()
            adequate_sem = adequate_std / np.sqrt(len(adequate_cases))

            higher_better = metric in ['ssim_mean', 'pearson_r', 'ncc', 'psnr', 'stage_snr', 'stage_cnr']

            if higher_better:
                threshold = adequate_mean - 1.96 * adequate_sem
                direction = "≥"
            else:
                threshold = adequate_mean + 1.96 * adequate_sem
                direction = "≤"
        else:
            threshold = np.nan
            adequate_mean = adequate_cases[metric].mean() if len(adequate_cases) > 0 else np.nan
            adequate_std = adequate_cases[metric].std() if len(adequate_cases) > 0 else np.nan
            direction = "?"

        print(f"{metric}:")
        print(f"  Pearson r={pearson_r:.3f} (p={pearson_p:.4f}), Spearman r={spearman_r:.3f} (p={spearman_p:.4f})")

        if not np.isnan(threshold):
            print(f"  Adequacy threshold: {direction} {threshold:.4f}\n")
        else:
            print()

        threshold_results.append({
            'sequence': sequence_type,
            'metric': metric,
            'pearson_r': pearson_r,
            'pearson_p': pearson_p,
            'spearman_r': spearman_r,
            'spearman_p': spearman_p,
            'threshold': threshold,
            'threshold_direction': direction,
            'adequate_mean': adequate_mean,
            'adequate_std': adequate_std,
            'poor_mean': poor_cases[metric].mean() if len(poor_cases) > 0 else np.nan,
            'poor_std': poor_cases[metric].std() if len(poor_cases) > 0 else np.nan,
            'n_adequate': len(adequate_cases),
            'n_poor': len(poor_cases)
        })

    return pd.DataFrame(threshold_results), df_scored

def create_comparison_plots(all_sequences_data, output_dir):
    """Create comparison plots across all sequences"""

    output_dir = Path(output_dir)
    sns.set_style("whitegrid")

    # 1. Expert score distributions by sequence
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    for idx, (seq_type, df_scored) in enumerate(all_sequences_data.items()):
        if df_scored is None or len(df_scored) == 0:
            continue

        axes[idx].hist(df_scored['expert_score'], bins=np.arange(0.5, 10.5, 1),
                      edgecolor='black', alpha=0.7, color=['red', 'orange', 'green'][idx])
        axes[idx].set_xlabel('Expert Score')
        axes[idx].set_ylabel('Frequency')
        axes[idx].set_title(f'{seq_type} Quality Scores')
        axes[idx].axvline(4, color='red', linestyle='--', alpha=0.5, label='Adequate (≥4)')
        axes[idx].axvline(6, color='green', linestyle='--', alpha=0.5, label='Good (≥6)')
        axes[idx].legend()

    plt.tight_layout()
    plt.savefig(output_dir / 'expert_score_distributions_all_sequences.png', dpi=300, bbox_inches='tight')
    print(f"Saved: {output_dir / 'expert_score_distributions_all_sequences.png'}")

    # 2. SSIM vs Expert Score for all sequences
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    for idx, (seq_type, df_scored) in enumerate(all_sequences_data.items()):
        if df_scored is None or len(df_scored) == 0 or 'ssim_mean' not in df_scored.columns:
            continue

        axes[idx].scatter(df_scored['expert_score'], df_scored['ssim_mean'],
                         alpha=0.6, s=100, color=['red', 'orange', 'green'][idx])
        axes[idx].set_xlabel('Expert Score')
        axes[idx].set_ylabel('SSIM')
        axes[idx].set_title(f'{seq_type}: SSIM vs Expert Score')

        # Regression line
        valid = df_scored[['expert_score', 'ssim_mean']].dropna()
        if len(valid) > 2:
            z = np.polyfit(valid['expert_score'], valid['ssim_mean'], 1)
            p = np.poly1d(z)
            x_line = np.linspace(valid['expert_score'].min(), valid['expert_score'].max(), 100)
            axes[idx].plot(x_line, p(x_line), "k--", alpha=0.8, linewidth=2)

            # Calculate and display correlation
            r, p_val = stats.pearsonr(valid['expert_score'], valid['ssim_mean'])
            axes[idx].text(0.05, 0.95, f'r={r:.3f}\np={p_val:.3f}',
                          transform=axes[idx].transAxes, verticalalignment='top',
                          bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    plt.savefig(output_dir / 'ssim_vs_expert_score_all_sequences.png', dpi=300, bbox_inches='tight')
    print(f"Saved: {output_dir / 'ssim_vs_expert_score_all_sequences.png'}")

    plt.close('all')

def main():
    metrics_dir = Path('output/metrics')
    scores_file = Path('output/statistics/neurorad_scores_unified.csv')
    output_dir = Path('output/statistics')

    print("="*80)
    print("COMPREHENSIVE SEQUENCE ANALYSIS: T1, T2, and SWI")
    print("="*80 + "\n")

    # Load expert scores
    print("Loading expert scores...")
    scores_df = load_expert_scores(scores_file)

    # Collect metrics for all sequences
    print("\nCollecting metrics for all sequences...")
    sequence_types = ['T1', 'T2', 'SWI']
    all_metrics = {}
    all_scored_data = {}
    all_stats = []
    all_thresholds = []

    for seq_type in sequence_types:
        print(f"\n{'-'*80}")
        print(f"Processing {seq_type}...")
        print(f"{'-'*80}")

        # Collect metrics
        metrics_df = collect_sequence_metrics(metrics_dir, seq_type)

        if metrics_df is None:
            print(f"Skipping {seq_type} - no data found")
            continue

        all_metrics[seq_type] = metrics_df

        # Determine score column
        score_col = f'{seq_type}_expert_score'

        # Merge with expert scores
        merged_df, has_scores, no_scores = merge_with_expert_scores(metrics_df, scores_df, score_col)
        print(f"  Expert scores: {has_scores} with / {no_scores} without")

        # Save combined data
        combined_file = output_dir / f'{seq_type.lower()}_metrics_with_expert_scores.csv'
        merged_df.to_csv(combined_file, index=False)

        # Calculate paired statistics
        stats_df = calculate_paired_statistics(merged_df, seq_type)
        all_stats.append(stats_df)

        # Analyze thresholds
        threshold_df, scored_df = analyze_expert_score_thresholds(merged_df, seq_type)

        if threshold_df is not None:
            all_thresholds.append(threshold_df)
            all_scored_data[seq_type] = scored_df

    # Save combined results
    if all_stats:
        combined_stats = pd.concat(all_stats, ignore_index=True)
        combined_stats.to_csv(output_dir / 'all_sequences_statistics.csv', index=False)
        print(f"\nSaved: {output_dir / 'all_sequences_statistics.csv'}")

    if all_thresholds:
        combined_thresholds = pd.concat(all_thresholds, ignore_index=True)
        combined_thresholds.to_csv(output_dir / 'all_sequences_adequacy_thresholds.csv', index=False)
        print(f"Saved: {output_dir / 'all_sequences_adequacy_thresholds.csv'}")

    # Create visualizations
    if all_scored_data:
        print("\nCreating visualizations...")
        create_comparison_plots(all_scored_data, output_dir)

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)

    # Summary
    print("\nSummary by sequence:")
    for seq_type in sequence_types:
        if seq_type in all_metrics:
            total = len(all_metrics[seq_type])
            with_scores = all_scored_data[seq_type]['expert_score'].notna().sum() if seq_type in all_scored_data else 0
            print(f"  {seq_type}: {total} patients total, {with_scores} with expert scores")

if __name__ == '__main__':
    main()
