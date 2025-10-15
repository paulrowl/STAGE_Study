#!/usr/bin/env python3
"""
SWI STAGE vs Conventional Analysis with Expert Score Thresholds
Collects metrics from all patients, compares sequences, and determines adequacy thresholds
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

    # Extract patient ID and Q3 (SWI) scores
    # Keep both rows for patients with multiple ratings and average them
    scores = df.groupby('rAccession').agg({
        'Q1': 'mean',  # T1 score
        'Q2': 'mean',  # T2 score
        'Q3': 'mean'   # SWI score
    }).reset_index()

    scores.columns = ['patient_id', 'T1_expert_score', 'T2_expert_score', 'SWI_expert_score']

    print(f"Loaded expert scores for {len(scores)} patients")
    print(f"SWI score range: {scores['SWI_expert_score'].min():.1f} - {scores['SWI_expert_score'].max():.1f}")
    print(f"SWI score mean: {scores['SWI_expert_score'].mean():.2f} ± {scores['SWI_expert_score'].std():.2f}")

    return scores

def collect_swi_metrics(metrics_dir):
    """Collect all SWI metrics from patient folders"""
    metrics_dir = Path(metrics_dir)
    all_metrics = []

    for patient_dir in sorted(metrics_dir.glob('Anon*')):
        patient_id = patient_dir.name

        # Look for SWI comparison file
        swi_file = patient_dir / f"{patient_id}_SWI_conv_vs_SWI_STAGE_metrics.csv"

        if swi_file.exists():
            try:
                df = pd.read_csv(swi_file)
                df['patient_id'] = patient_id
                all_metrics.append(df)
            except Exception as e:
                print(f"Warning: Could not read {swi_file}: {e}")

    if not all_metrics:
        raise ValueError("No SWI metrics files found!")

    combined = pd.concat(all_metrics, ignore_index=True)
    print(f"\nCollected SWI metrics from {len(combined)} patients")

    return combined

def merge_with_expert_scores(metrics_df, scores_df):
    """Merge metrics with expert scores"""
    merged = metrics_df.merge(scores_df, on='patient_id', how='left')

    # Report merge results
    has_scores = merged['SWI_expert_score'].notna().sum()
    no_scores = merged['SWI_expert_score'].isna().sum()

    print(f"\nMerge results:")
    print(f"  Patients with expert scores: {has_scores}")
    print(f"  Patients without scores: {no_scores}")

    return merged

def calculate_paired_statistics(df):
    """Calculate paired statistics for conv vs STAGE"""

    # Metrics to compare
    comparison_metrics = [
        ('conv_mean', 'stage_mean', 'Mean Intensity'),
        ('conv_std', 'stage_std', 'Std Dev'),
        ('conv_snr', 'stage_snr', 'SNR'),
        ('conv_cnr', 'stage_cnr', 'CNR'),
        ('conv_cv', 'stage_cv', 'Coefficient of Variation'),
    ]

    results = []

    print("\n" + "="*80)
    print("PAIRED STATISTICAL COMPARISON: SWI Conventional vs STAGE")
    print("="*80 + "\n")

    for conv_col, stage_col, metric_name in comparison_metrics:
        conv_vals = df[conv_col].dropna()
        stage_vals = df[stage_col].dropna()

        # Ensure paired
        valid_idx = df[[conv_col, stage_col]].dropna().index
        conv_paired = df.loc[valid_idx, conv_col]
        stage_paired = df.loc[valid_idx, stage_col]

        # Paired t-test
        t_stat, t_pval = stats.ttest_rel(conv_paired, stage_paired)

        # Wilcoxon signed-rank test (non-parametric)
        w_stat, w_pval = stats.wilcoxon(conv_paired, stage_paired)

        # Effect size (Cohen's d)
        diff = conv_paired - stage_paired
        cohens_d = diff.mean() / diff.std()

        print(f"{metric_name}:")
        print(f"  Conventional: {conv_paired.mean():.4f} ± {conv_paired.std():.4f}")
        print(f"  STAGE:        {stage_paired.mean():.4f} ± {stage_paired.std():.4f}")
        print(f"  Difference:   {diff.mean():.4f} ± {diff.std():.4f}")
        print(f"  Paired t-test: t={t_stat:.4f}, p={t_pval:.4e}")
        print(f"  Wilcoxon test: W={w_stat:.1f}, p={w_pval:.4e}")
        print(f"  Effect size (Cohen's d): {cohens_d:.4f}")

        if t_pval < 0.001:
            sig = "***"
        elif t_pval < 0.01:
            sig = "**"
        elif t_pval < 0.05:
            sig = "*"
        else:
            sig = "ns"
        print(f"  Significance: {sig}\n")

        results.append({
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
            'significance': sig
        })

    return pd.DataFrame(results)

def analyze_expert_score_thresholds(df):
    """Analyze metrics relative to expert scores to determine adequacy thresholds"""

    # Filter to patients with expert scores
    df_scored = df[df['SWI_expert_score'].notna()].copy()

    if len(df_scored) == 0:
        print("\nWarning: No patients with expert scores found!")
        return None

    print("\n" + "="*80)
    print("EXPERT SCORE THRESHOLD ANALYSIS")
    print("="*80 + "\n")

    print(f"Analyzing {len(df_scored)} patients with expert SWI scores\n")

    # Define adequacy levels
    # Based on radiologist feedback:
    # - Score >= 6: Good/Excellent quality
    # - Score >= 4: Adequate for diagnosis
    # - Score < 4: Poor quality

    df_scored['quality_category'] = pd.cut(
        df_scored['SWI_expert_score'],
        bins=[0, 4, 6, 10],
        labels=['Poor (<4)', 'Adequate (4-6)', 'Good (≥6)']
    )

    print("Quality Distribution:")
    print(df_scored['quality_category'].value_counts().sort_index())
    print()

    # Key metrics to analyze
    key_metrics = [
        'ssim_mean',
        'pearson_r',
        'ncc',
        'mae',
        'psnr',
        'stage_snr',
        'stage_cnr',
        'stage_cv'
    ]

    threshold_results = []

    for metric in key_metrics:
        if metric not in df_scored.columns:
            continue

        # Calculate correlation with expert score
        valid_data = df_scored[[metric, 'SWI_expert_score']].dropna()

        if len(valid_data) < 3:
            continue

        pearson_r, pearson_p = stats.pearsonr(valid_data[metric], valid_data['SWI_expert_score'])
        spearman_r, spearman_p = stats.spearmanr(valid_data[metric], valid_data['SWI_expert_score'])

        # Calculate mean values by quality category
        by_quality = df_scored.groupby('quality_category')[metric].agg(['mean', 'std', 'count'])

        # Determine threshold for "adequate" quality (score >= 4)
        adequate_cases = df_scored[df_scored['SWI_expert_score'] >= 4]
        poor_cases = df_scored[df_scored['SWI_expert_score'] < 4]

        if len(adequate_cases) > 0 and len(poor_cases) > 0:
            # Use lower 95% CI bound of adequate cases as threshold
            adequate_mean = adequate_cases[metric].mean()
            adequate_std = adequate_cases[metric].std()
            adequate_sem = adequate_std / np.sqrt(len(adequate_cases))

            # For metrics where higher is better (SSIM, PSNR, SNR, CNR, correlations)
            higher_better = metric in ['ssim_mean', 'pearson_r', 'ncc', 'psnr', 'stage_snr', 'stage_cnr']

            if higher_better:
                threshold = adequate_mean - 1.96 * adequate_sem  # Lower 95% CI
                direction = "≥"
            else:  # Lower is better (MAE, CV)
                threshold = adequate_mean + 1.96 * adequate_sem  # Upper 95% CI
                direction = "≤"
        else:
            threshold = np.nan
            direction = "?"

        print(f"\n{metric}:")
        print(f"  Correlation with expert score:")
        print(f"    Pearson r={pearson_r:.3f}, p={pearson_p:.4f}")
        print(f"    Spearman r={spearman_r:.3f}, p={spearman_p:.4f}")
        print(f"  By quality category:")
        for cat in by_quality.index:
            print(f"    {cat}: {by_quality.loc[cat, 'mean']:.4f} ± {by_quality.loc[cat, 'std']:.4f} (n={by_quality.loc[cat, 'count']:.0f})")
        if not np.isnan(threshold):
            print(f"  Suggested adequacy threshold: {direction} {threshold:.4f}")

        threshold_results.append({
            'metric': metric,
            'pearson_r': pearson_r,
            'pearson_p': pearson_p,
            'spearman_r': spearman_r,
            'spearman_p': spearman_p,
            'threshold': threshold,
            'threshold_direction': direction,
            'adequate_mean': adequate_mean if len(adequate_cases) > 0 else np.nan,
            'adequate_std': adequate_std if len(adequate_cases) > 0 else np.nan,
            'poor_mean': poor_cases[metric].mean() if len(poor_cases) > 0 else np.nan,
            'poor_std': poor_cases[metric].std() if len(poor_cases) > 0 else np.nan
        })

    return pd.DataFrame(threshold_results), df_scored

def create_visualizations(df_scored, output_dir):
    """Create comprehensive visualization plots"""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Set style
    sns.set_style("whitegrid")
    plt.rcParams['figure.figsize'] = (15, 10)

    # 1. Expert Score Distribution
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))

    # Score histogram
    axes[0, 0].hist(df_scored['SWI_expert_score'], bins=np.arange(0.5, 10.5, 1),
                    edgecolor='black', alpha=0.7)
    axes[0, 0].set_xlabel('Expert SWI Score')
    axes[0, 0].set_ylabel('Frequency')
    axes[0, 0].set_title('Distribution of Expert SWI Scores')
    axes[0, 0].axvline(4, color='red', linestyle='--', label='Adequate threshold (4)')
    axes[0, 0].axvline(6, color='green', linestyle='--', label='Good threshold (6)')
    axes[0, 0].legend()

    # SSIM vs Expert Score
    if 'ssim_mean' in df_scored.columns:
        axes[0, 1].scatter(df_scored['SWI_expert_score'], df_scored['ssim_mean'],
                          alpha=0.6, s=100)
        axes[0, 1].set_xlabel('Expert SWI Score')
        axes[0, 1].set_ylabel('SSIM')
        axes[0, 1].set_title('SSIM vs Expert Score')

        # Add regression line
        valid = df_scored[['SWI_expert_score', 'ssim_mean']].dropna()
        if len(valid) > 2:
            z = np.polyfit(valid['SWI_expert_score'], valid['ssim_mean'], 1)
            p = np.poly1d(z)
            x_line = np.linspace(valid['SWI_expert_score'].min(),
                                valid['SWI_expert_score'].max(), 100)
            axes[0, 1].plot(x_line, p(x_line), "r--", alpha=0.8, linewidth=2)

    # SNR vs Expert Score
    if 'stage_snr' in df_scored.columns:
        axes[1, 0].scatter(df_scored['SWI_expert_score'], df_scored['stage_snr'],
                          alpha=0.6, s=100, color='green')
        axes[1, 0].set_xlabel('Expert SWI Score')
        axes[1, 0].set_ylabel('STAGE SNR')
        axes[1, 0].set_title('STAGE SNR vs Expert Score')

        valid = df_scored[['SWI_expert_score', 'stage_snr']].dropna()
        if len(valid) > 2:
            z = np.polyfit(valid['SWI_expert_score'], valid['stage_snr'], 1)
            p = np.poly1d(z)
            x_line = np.linspace(valid['SWI_expert_score'].min(),
                                valid['SWI_expert_score'].max(), 100)
            axes[1, 0].plot(x_line, p(x_line), "r--", alpha=0.8, linewidth=2)

    # MAE vs Expert Score
    if 'mae' in df_scored.columns:
        axes[1, 1].scatter(df_scored['SWI_expert_score'], df_scored['mae'],
                          alpha=0.6, s=100, color='orange')
        axes[1, 1].set_xlabel('Expert SWI Score')
        axes[1, 1].set_ylabel('MAE (Lower is Better)')
        axes[1, 1].set_title('MAE vs Expert Score')

        valid = df_scored[['SWI_expert_score', 'mae']].dropna()
        if len(valid) > 2:
            z = np.polyfit(valid['SWI_expert_score'], valid['mae'], 1)
            p = np.poly1d(z)
            x_line = np.linspace(valid['SWI_expert_score'].min(),
                                valid['SWI_expert_score'].max(), 100)
            axes[1, 1].plot(x_line, p(x_line), "r--", alpha=0.8, linewidth=2)

    plt.tight_layout()
    plt.savefig(output_dir / 'swi_expert_score_correlations.png', dpi=300, bbox_inches='tight')
    print(f"\nSaved: {output_dir / 'swi_expert_score_correlations.png'}")

    # 2. Box plots by quality category
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    axes = axes.flatten()

    metrics_to_plot = ['ssim_mean', 'pearson_r', 'stage_snr', 'stage_cnr', 'mae', 'psnr']

    for idx, metric in enumerate(metrics_to_plot):
        if metric in df_scored.columns and idx < len(axes):
            df_scored.boxplot(column=metric, by='quality_category', ax=axes[idx])
            axes[idx].set_xlabel('Quality Category')
            axes[idx].set_ylabel(metric)
            axes[idx].set_title(f'{metric} by Quality Category')
            plt.sca(axes[idx])
            plt.xticks(rotation=45)

    # Remove empty subplots
    for idx in range(len(metrics_to_plot), len(axes)):
        fig.delaxes(axes[idx])

    plt.suptitle('Image Quality Metrics by Expert Score Category', fontsize=16, y=1.02)
    plt.tight_layout()
    plt.savefig(output_dir / 'swi_metrics_by_quality_category.png', dpi=300, bbox_inches='tight')
    print(f"Saved: {output_dir / 'swi_metrics_by_quality_category.png'}")

    plt.close('all')

def main():
    # Paths
    metrics_dir = Path('output/metrics')
    scores_file = Path('output/statistics/neurorad_scores_unified.csv')
    output_dir = Path('output/statistics')

    print("="*80)
    print("SWI STAGE vs CONVENTIONAL ANALYSIS WITH EXPERT SCORE THRESHOLDS")
    print("="*80 + "\n")

    # 1. Load expert scores
    print("Step 1: Loading expert scores...")
    scores_df = load_expert_scores(scores_file)

    # 2. Collect SWI metrics
    print("\nStep 2: Collecting SWI metrics from all patients...")
    metrics_df = collect_swi_metrics(metrics_dir)

    # 3. Merge with expert scores
    print("\nStep 3: Merging metrics with expert scores...")
    merged_df = merge_with_expert_scores(metrics_df, scores_df)

    # Save combined data
    combined_file = output_dir / 'swi_metrics_with_expert_scores.csv'
    merged_df.to_csv(combined_file, index=False)
    print(f"\nSaved combined data: {combined_file}")

    # 4. Calculate paired statistics
    print("\nStep 4: Calculating paired statistics...")
    stats_df = calculate_paired_statistics(merged_df)

    stats_file = output_dir / 'swi_conv_vs_stage_statistics.csv'
    stats_df.to_csv(stats_file, index=False)
    print(f"\nSaved statistics: {stats_file}")

    # 5. Analyze expert score thresholds
    print("\nStep 5: Analyzing expert score thresholds...")
    threshold_df, scored_df = analyze_expert_score_thresholds(merged_df)

    if threshold_df is not None:
        threshold_file = output_dir / 'swi_adequacy_thresholds.csv'
        threshold_df.to_csv(threshold_file, index=False)
        print(f"\nSaved thresholds: {threshold_file}")

        # 6. Create visualizations
        print("\nStep 6: Creating visualizations...")
        create_visualizations(scored_df, output_dir)

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)

    # Summary
    print(f"\nSummary:")
    print(f"  Total patients analyzed: {len(merged_df)}")
    print(f"  Patients with expert scores: {merged_df['SWI_expert_score'].notna().sum()}")
    print(f"  Output files saved to: {output_dir}")

if __name__ == '__main__':
    main()
