#!/usr/bin/env python3
"""
Comprehensive Outlier Analysis for STAGE Study

Performs multi-method outlier detection to ensure statistical findings
aren't driven by extreme values.

Methods:
1. Z-score (|z| > 3)
2. IQR method (1.5*IQR rule)
3. Leverage and Cook's distance
4. Visual inspection via boxplots and scatter plots
5. Influence analysis (statistics with/without each subject)

Author: Analysis Pipeline
Date: 2025-10-17
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# Paths
BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
STATS_DIR = BASE_DIR / 'output' / 'statistics'
OUTPUT_DIR = STATS_DIR / 'outlier_analysis'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("COMPREHENSIVE OUTLIER ANALYSIS")
print("=" * 80)

# Load data
print("\nLoading data...")
df_paired = pd.read_csv(STATS_DIR / 'paired_comparisons_MERGED.csv')
print(f"✓ Loaded {len(df_paired)} paired observations")

# Initialize results storage
outlier_results = []
influence_results = []

# ============================================================================
# OUTLIER DETECTION FUNCTIONS
# ============================================================================

def detect_outliers_zscore(data: np.ndarray, threshold: float = 3.0) -> np.ndarray:
    """Detect outliers using z-score method."""
    z_scores = np.abs(stats.zscore(data, nan_policy='omit'))
    return z_scores > threshold

def detect_outliers_iqr(data: np.ndarray, multiplier: float = 1.5) -> np.ndarray:
    """Detect outliers using IQR method."""
    q1 = np.nanpercentile(data, 25)
    q3 = np.nanpercentile(data, 75)
    iqr = q3 - q1
    lower_bound = q1 - (multiplier * iqr)
    upper_bound = q3 + (multiplier * iqr)
    return (data < lower_bound) | (data > upper_bound)

def detect_outliers_modified_zscore(data: np.ndarray, threshold: float = 3.5) -> np.ndarray:
    """Detect outliers using modified z-score (based on median)."""
    median = np.nanmedian(data)
    mad = np.nanmedian(np.abs(data - median))
    modified_z_scores = 0.6745 * (data - median) / mad if mad != 0 else np.zeros_like(data)
    return np.abs(modified_z_scores) > threshold

def calculate_cooks_distance(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Calculate Cook's distance for regression influence."""
    from sklearn.linear_model import LinearRegression

    # Fit full model
    X = x.reshape(-1, 1)
    model = LinearRegression()
    model.fit(X, y)

    # Calculate residuals and leverage
    predictions = model.predict(X)
    residuals = y - predictions

    # Hat matrix diagonal (leverage)
    X_mean = np.mean(X)
    h = (X - X_mean)**2 / np.sum((X - X_mean)**2) + 1/len(X)

    # MSE
    mse = np.sum(residuals**2) / (len(y) - 2)

    # Cook's distance
    cooks_d = (residuals**2 / (2 * mse)) * (h / (1 - h)**2)

    return cooks_d

# ============================================================================
# ANALYSIS BY SEQUENCE TYPE
# ============================================================================

for seq_type in ['T1', 'T2', 'SWI']:
    print(f"\n{'='*80}")
    print(f"{seq_type} OUTLIER ANALYSIS")
    print(f"{'='*80}")

    df_seq = df_paired[df_paired['sequence_type'] == seq_type].copy()
    n = len(df_seq)

    if n < 3:
        print(f"Insufficient data (n={n}), skipping...")
        continue

    print(f"Sample size: n={n}")

    # Variables to check
    variables = {
        'GM Conv': 'conv_gm_mean',
        'GM STAGE': 'stage_gm_mean',
        'WM Conv': 'conv_wm_mean',
        'WM STAGE': 'stage_wm_mean',
        'GM/WM Ratio Conv': 'conv_gm_wm_ratio',
        'GM/WM Ratio STAGE': 'stage_gm_wm_ratio'
    }

    # Check each variable
    for var_name, var_col in variables.items():
        data = df_seq[var_col].values

        # Skip if too many NaNs
        if np.sum(~np.isnan(data)) < 3:
            continue

        # Detect outliers
        outliers_z = detect_outliers_zscore(data, threshold=3.0)
        outliers_iqr = detect_outliers_iqr(data, multiplier=1.5)
        outliers_mod_z = detect_outliers_modified_zscore(data, threshold=3.5)

        # Count outliers
        n_z = np.sum(outliers_z)
        n_iqr = np.sum(outliers_iqr)
        n_mod_z = np.sum(outliers_mod_z)

        # Consensus outliers (flagged by multiple methods)
        consensus = outliers_z & outliers_iqr
        n_consensus = np.sum(consensus)

        if n_z > 0 or n_iqr > 0 or n_mod_z > 0:
            print(f"\n  {var_name}:")
            print(f"    Z-score (|z|>3):        {n_z} outliers")
            print(f"    IQR (1.5×IQR):          {n_iqr} outliers")
            print(f"    Modified Z-score:       {n_mod_z} outliers")
            print(f"    Consensus (Z & IQR):    {n_consensus} outliers")

            if n_consensus > 0:
                outlier_subjects = df_seq[consensus]['subject_id'].values
                outlier_values = data[consensus]
                print(f"    Flagged subjects: {', '.join(outlier_subjects)}")
                print(f"    Values: {outlier_values}")

        # Store results
        outlier_results.append({
            'sequence': seq_type,
            'variable': var_name,
            'n_total': n,
            'n_z_outliers': n_z,
            'n_iqr_outliers': n_iqr,
            'n_modified_z_outliers': n_mod_z,
            'n_consensus_outliers': n_consensus,
            'pct_consensus_outliers': (n_consensus / n * 100) if n > 0 else 0
        })

    # ========================================================================
    # GM/WM RATIO: Key outcome variable - detailed analysis
    # ========================================================================
    print(f"\n  {'─'*76}")
    print(f"  DETAILED ANALYSIS: GM/WM Ratio (Primary Outcome)")
    print(f"  {'─'*76}")

    ratio_conv = df_seq['conv_gm_wm_ratio'].values
    ratio_stage = df_seq['stage_gm_wm_ratio'].values
    ratio_diff = ratio_stage - ratio_conv

    # Outliers in the DIFFERENCE (most important)
    outliers_diff_z = detect_outliers_zscore(ratio_diff, threshold=3.0)
    outliers_diff_iqr = detect_outliers_iqr(ratio_diff, multiplier=1.5)

    print(f"\n  Difference (STAGE - Conv):")
    print(f"    Mean: {np.nanmean(ratio_diff):.4f}")
    print(f"    Median: {np.nanmedian(ratio_diff):.4f}")
    print(f"    Std: {np.nanstd(ratio_diff):.4f}")
    print(f"    Range: [{np.nanmin(ratio_diff):.4f}, {np.nanmax(ratio_diff):.4f}]")
    print(f"    Z-score outliers: {np.sum(outliers_diff_z)}")
    print(f"    IQR outliers: {np.sum(outliers_diff_iqr)}")

    if np.sum(outliers_diff_z | outliers_diff_iqr) > 0:
        flagged = outliers_diff_z | outliers_diff_iqr
        flagged_subjects = df_seq[flagged]['subject_id'].values
        flagged_diffs = ratio_diff[flagged]
        print(f"\n    Flagged subjects with extreme differences:")
        for subj, diff in zip(flagged_subjects, flagged_diffs):
            print(f"      {subj}: {diff:+.4f}")

    # ========================================================================
    # COOK'S DISTANCE for correlation analysis
    # ========================================================================
    print(f"\n  Cook's Distance (Influence on Correlation):")

    # GM correlation influence
    gm_conv = df_seq['conv_gm_mean'].values
    gm_stage = df_seq['stage_gm_mean'].values
    valid_mask = ~np.isnan(gm_conv) & ~np.isnan(gm_stage)

    if np.sum(valid_mask) >= 3:
        cooks_gm = calculate_cooks_distance(gm_conv[valid_mask], gm_stage[valid_mask])
        influential_gm = cooks_gm > 4/len(cooks_gm)  # Common threshold

        print(f"    GM correlation: {np.sum(influential_gm)} influential points")
        if np.sum(influential_gm) > 0:
            influential_subjects = df_seq[valid_mask]['subject_id'].values[influential_gm]
            print(f"      Influential subjects: {', '.join(influential_subjects)}")

    # WM correlation influence
    wm_conv = df_seq['conv_wm_mean'].values
    wm_stage = df_seq['stage_wm_mean'].values
    valid_mask = ~np.isnan(wm_conv) & ~np.isnan(wm_stage)

    if np.sum(valid_mask) >= 3:
        cooks_wm = calculate_cooks_distance(wm_conv[valid_mask], wm_stage[valid_mask])
        influential_wm = cooks_wm > 4/len(cooks_wm)

        print(f"    WM correlation: {np.sum(influential_wm)} influential points")
        if np.sum(influential_wm) > 0:
            influential_subjects = df_seq[valid_mask]['subject_id'].values[influential_wm]
            print(f"      Influential subjects: {', '.join(influential_subjects)}")

    # ========================================================================
    # INFLUENCE ANALYSIS: Statistics with/without each subject
    # ========================================================================
    print(f"\n  Leave-One-Out Influence Analysis:")
    print(f"  (Testing if removing any single subject changes conclusions)")

    # Full dataset statistics
    ratio_conv_full = df_seq['conv_gm_wm_ratio'].dropna().values
    ratio_stage_full = df_seq['stage_gm_wm_ratio'].dropna().values

    if len(ratio_conv_full) >= 3 and len(ratio_stage_full) >= 3:
        t_full, p_full = stats.ttest_rel(ratio_conv_full, ratio_stage_full)
        r_full, r_p_full = stats.pearsonr(ratio_conv_full, ratio_stage_full)
        d_full = (np.mean(ratio_stage_full) - np.mean(ratio_conv_full)) / np.std(ratio_stage_full - ratio_conv_full)

        print(f"    Full dataset: t={t_full:.3f}, p={p_full:.4f}, d={d_full:.3f}, r={r_full:.3f}")

        # Leave-one-out
        max_p_change = 0
        max_d_change = 0
        most_influential_subj = None

        for i in range(len(df_seq)):
            mask = np.ones(len(df_seq), dtype=bool)
            mask[i] = False

            df_loo = df_seq[mask]
            ratio_conv_loo = df_loo['conv_gm_wm_ratio'].dropna().values
            ratio_stage_loo = df_loo['stage_gm_wm_ratio'].dropna().values

            if len(ratio_conv_loo) >= 2:
                t_loo, p_loo = stats.ttest_rel(ratio_conv_loo, ratio_stage_loo)
                d_loo = (np.mean(ratio_stage_loo) - np.mean(ratio_conv_loo)) / np.std(ratio_stage_loo - ratio_conv_loo)

                p_change = abs(p_loo - p_full)
                d_change = abs(d_loo - d_full)

                if p_change > max_p_change:
                    max_p_change = p_change
                    most_influential_subj = df_seq.iloc[i]['subject_id']
                    most_influential_p = p_loo
                    most_influential_d = d_loo

                if d_change > max_d_change:
                    max_d_change = d_change

        print(f"    Max p-value change: {max_p_change:.4f}")
        print(f"    Max effect size change: {max_d_change:.3f}")

        if most_influential_subj:
            print(f"    Most influential subject: {most_influential_subj}")
            print(f"      Without: t=?, p={most_influential_p:.4f}, d={most_influential_d:.3f}")

            # Check if significance changes
            sig_changes = (p_full < 0.05 and most_influential_p >= 0.05) or (p_full >= 0.05 and most_influential_p < 0.05)
            if sig_changes:
                print(f"      ⚠️ WARNING: Significance changes when this subject removed!")

        influence_results.append({
            'sequence': seq_type,
            'n': len(df_seq),
            'full_p': p_full,
            'full_d': d_full,
            'full_r': r_full,
            'max_p_change': max_p_change,
            'max_d_change': max_d_change,
            'most_influential': most_influential_subj,
            'significance_stable': not sig_changes if most_influential_subj else True
        })

# ============================================================================
# CREATE DIAGNOSTIC VISUALIZATIONS
# ============================================================================

print(f"\n{'='*80}")
print("CREATING DIAGNOSTIC VISUALIZATIONS")
print(f"{'='*80}")

fig, axes = plt.subplots(3, 4, figsize=(20, 15))
fig.suptitle('Outlier Diagnostic Plots', fontsize=16, fontweight='bold')

for idx, seq_type in enumerate(['T1', 'T2', 'SWI']):
    df_seq = df_paired[df_paired['sequence_type'] == seq_type].copy()

    if len(df_seq) < 2:
        continue

    # Boxplot: GM/WM ratios
    ax = axes[idx, 0]
    data_to_plot = [
        df_seq['conv_gm_wm_ratio'].dropna().values,
        df_seq['stage_gm_wm_ratio'].dropna().values
    ]
    bp = ax.boxplot(data_to_plot, labels=['Conv', 'STAGE'], showfliers=True)
    ax.set_title(f'{seq_type}: GM/WM Ratio', fontweight='bold')
    ax.set_ylabel('GM/WM Ratio')
    ax.grid(True, alpha=0.3)

    # Scatter: Conv vs STAGE GM
    ax = axes[idx, 1]
    gm_conv = df_seq['conv_gm_mean'].values
    gm_stage = df_seq['stage_gm_mean'].values
    ax.scatter(gm_conv, gm_stage, s=100, alpha=0.6, edgecolors='black', linewidth=1.5)

    # Mark potential outliers
    outliers = detect_outliers_zscore(gm_conv) | detect_outliers_zscore(gm_stage)
    if np.any(outliers):
        ax.scatter(gm_conv[outliers], gm_stage[outliers], s=150,
                  facecolors='none', edgecolors='red', linewidth=3, label='Potential outlier')
        ax.legend()

    ax.set_xlabel('Conventional GM')
    ax.set_ylabel('STAGE GM')
    ax.set_title(f'{seq_type}: GM Intensities', fontweight='bold')
    ax.grid(True, alpha=0.3)

    # Scatter: Conv vs STAGE WM
    ax = axes[idx, 2]
    wm_conv = df_seq['conv_wm_mean'].values
    wm_stage = df_seq['stage_wm_mean'].values
    ax.scatter(wm_conv, wm_stage, s=100, alpha=0.6, edgecolors='black', linewidth=1.5)

    outliers = detect_outliers_zscore(wm_conv) | detect_outliers_zscore(wm_stage)
    if np.any(outliers):
        ax.scatter(wm_conv[outliers], wm_stage[outliers], s=150,
                  facecolors='none', edgecolors='red', linewidth=3, label='Potential outlier')
        ax.legend()

    ax.set_xlabel('Conventional WM')
    ax.set_ylabel('STAGE WM')
    ax.set_title(f'{seq_type}: WM Intensities', fontweight='bold')
    ax.grid(True, alpha=0.3)

    # Histogram: Ratio differences
    ax = axes[idx, 3]
    ratio_diff = df_seq['stage_gm_wm_ratio'].values - df_seq['conv_gm_wm_ratio'].values
    ax.hist(ratio_diff[~np.isnan(ratio_diff)], bins=10, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax.axvline(np.nanmean(ratio_diff), color='red', linestyle='--', linewidth=2, label='Mean')
    ax.axvline(np.nanmedian(ratio_diff), color='blue', linestyle='--', linewidth=2, label='Median')
    ax.set_xlabel('GM/WM Ratio Difference (STAGE - Conv)')
    ax.set_ylabel('Count')
    ax.set_title(f'{seq_type}: Difference Distribution', fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
fig_path = OUTPUT_DIR / 'outlier_diagnostic_plots.png'
plt.savefig(fig_path, dpi=300, bbox_inches='tight')
print(f"✓ Saved: {fig_path}")
plt.close()

# ============================================================================
# SAVE RESULTS
# ============================================================================

print(f"\n{'='*80}")
print("SAVING RESULTS")
print(f"{'='*80}")

# Outlier summary
df_outliers = pd.DataFrame(outlier_results)
outlier_file = OUTPUT_DIR / 'outlier_detection_summary.csv'
df_outliers.to_csv(outlier_file, index=False)
print(f"✓ Outlier summary: {outlier_file}")

# Influence analysis
if influence_results:
    df_influence = pd.DataFrame(influence_results)
    influence_file = OUTPUT_DIR / 'influence_analysis.csv'
    df_influence.to_csv(influence_file, index=False)
    print(f"✓ Influence analysis: {influence_file}")

# Create detailed report
report_path = OUTPUT_DIR / 'outlier_analysis_report.md'
with open(report_path, 'w') as f:
    f.write("# Outlier Analysis Report\n\n")
    f.write("## Summary\n\n")
    f.write("This analysis checks whether the statistical findings are driven by outliers.\n\n")
    f.write("### Methods Used\n\n")
    f.write("1. **Z-score method**: Flags values with |z| > 3\n")
    f.write("2. **IQR method**: Flags values outside Q1-1.5×IQR to Q3+1.5×IQR\n")
    f.write("3. **Modified Z-score**: Median-based robust outlier detection\n")
    f.write("4. **Cook's distance**: Identifies influential points in correlations\n")
    f.write("5. **Leave-one-out influence**: Tests if removing any subject changes conclusions\n\n")

    f.write("## Key Findings\n\n")

    for seq in ['T1', 'T2', 'SWI']:
        f.write(f"### {seq}\n\n")

        seq_outliers = df_outliers[df_outliers['sequence'] == seq]
        if len(seq_outliers) > 0:
            max_consensus = seq_outliers['n_consensus_outliers'].max()
            f.write(f"- Maximum consensus outliers in any variable: {max_consensus}\n")

            if max_consensus > 0:
                problematic_vars = seq_outliers[seq_outliers['n_consensus_outliers'] > 0]['variable'].tolist()
                f.write(f"- Variables with consensus outliers: {', '.join(problematic_vars)}\n")

        if influence_results:
            seq_influence = [r for r in influence_results if r['sequence'] == seq]
            if seq_influence:
                r = seq_influence[0]
                f.write(f"- Leave-one-out max p-value change: {r['max_p_change']:.4f}\n")
                f.write(f"- Leave-one-out max effect size change: {r['max_d_change']:.3f}\n")
                f.write(f"- Significance stable: {r['significance_stable']}\n")
                if r['most_influential']:
                    f.write(f"- Most influential subject: {r['most_influential']}\n")

        f.write("\n")

    f.write("## Recommendations\n\n")
    f.write("Based on this analysis:\n\n")
    f.write("1. If consensus outliers < 5% of sample: Results likely robust\n")
    f.write("2. If leave-one-out changes p-value by > 0.01: Consider sensitivity analysis\n")
    f.write("3. If significance changes with any single subject removal: Report as exploratory\n")
    f.write("4. Consider reporting both with and without outliers removed\n")

print(f"✓ Detailed report: {report_path}")

print(f"\n{'='*80}")
print("OUTLIER ANALYSIS COMPLETE")
print(f"{'='*80}")
print(f"Results saved to: {OUTPUT_DIR}")
print(f"{'='*80}")
