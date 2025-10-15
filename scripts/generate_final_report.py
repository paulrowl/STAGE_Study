#!/usr/bin/env python3
"""
Generate Final Analysis Report
Comprehensive statistics and visualizations for STAGE MRI study
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 100
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10

# Load data
df = pd.read_csv('output/statistics/all_patients_metrics.csv')

# Extract sequence type and patient ID
df['sequence_type'] = df['comparison'].str.extract(r'_(T1|T2|SWI)_')[0]
df['patient_id'] = df['comparison'].str.extract(r'^(Anon\d+)_')[0]

# Output directories
plot_dir = Path('output/plots')
plot_dir.mkdir(exist_ok=True)

print("=" * 70)
print("STAGE MRI ANALYSIS - FINAL REPORT")
print("=" * 70)
print(f"\nTotal comparisons: {len(df)}")
print(f"Total patients: {df['patient_id'].nunique()}")
print(f"\nSequence breakdown:")
print(df['sequence_type'].value_counts().sort_index())

# Summary statistics by sequence type
print("\n" + "=" * 70)
print("SUMMARY STATISTICS BY SEQUENCE TYPE")
print("=" * 70)

metrics = ['ssim_mean', 'ncc', 'pearson_r', 'psnr', 'mutual_information', 'mae', 'rmse']
summary_stats = df.groupby('sequence_type')[metrics].agg(['mean', 'std', 'min', 'max', 'median'])

# Save summary statistics
summary_stats.to_csv('output/statistics/summary_statistics_by_sequence.csv')
print("\n✓ Saved: output/statistics/summary_statistics_by_sequence.csv")

# Print key metrics
for seq in ['T1', 'T2', 'SWI']:
    print(f"\n{seq} Sequences (n={len(df[df['sequence_type']==seq])}):")
    seq_data = df[df['sequence_type'] == seq]
    print(f"  SSIM:      {seq_data['ssim_mean'].mean():.4f} ± {seq_data['ssim_mean'].std():.4f}")
    print(f"  NCC:       {seq_data['ncc'].mean():.4f} ± {seq_data['ncc'].std():.4f}")
    print(f"  Pearson r: {seq_data['pearson_r'].mean():.4f} ± {seq_data['pearson_r'].std():.4f}")
    print(f"  PSNR:      {seq_data['psnr'].mean():.2f} ± {seq_data['psnr'].std():.2f} dB")

# ============================================================================
# VISUALIZATION 1: Overview Dashboard
# ============================================================================
print("\n" + "=" * 70)
print("GENERATING VISUALIZATIONS")
print("=" * 70)

fig, axes = plt.subplots(2, 3, figsize=(18, 12))
fig.suptitle('STAGE MRI Analysis: Overview Dashboard', fontsize=16, fontweight='bold')

# 1. SSIM by Sequence
ax = axes[0, 0]
sns.boxplot(data=df, x='sequence_type', y='ssim_mean', ax=ax, palette='Set2')
ax.set_title('Structural Similarity Index (SSIM)', fontweight='bold')
ax.set_xlabel('Sequence Type')
ax.set_ylabel('SSIM')
ax.set_ylim(0, 1)
for i, seq in enumerate(['T1', 'T2', 'SWI']):
    data = df[df['sequence_type'] == seq]['ssim_mean']
    ax.text(i, ax.get_ylim()[1] * 0.95, f'n={len(data)}',
            ha='center', fontsize=9, fontweight='bold')

# 2. NCC by Sequence
ax = axes[0, 1]
sns.boxplot(data=df, x='sequence_type', y='ncc', ax=ax, palette='Set2')
ax.set_title('Normalized Cross-Correlation (NCC)', fontweight='bold')
ax.set_xlabel('Sequence Type')
ax.set_ylabel('NCC')
ax.axhline(y=0, color='red', linestyle='--', alpha=0.3)

# 3. Pearson r by Sequence
ax = axes[0, 2]
sns.boxplot(data=df, x='sequence_type', y='pearson_r', ax=ax, palette='Set2')
ax.set_title('Pearson Correlation', fontweight='bold')
ax.set_xlabel('Sequence Type')
ax.set_ylabel('Pearson r')
ax.axhline(y=0, color='red', linestyle='--', alpha=0.3)

# 4. PSNR by Sequence
ax = axes[1, 0]
sns.boxplot(data=df, x='sequence_type', y='psnr', ax=ax, palette='Set2')
ax.set_title('Peak Signal-to-Noise Ratio (PSNR)', fontweight='bold')
ax.set_xlabel('Sequence Type')
ax.set_ylabel('PSNR (dB)')

# 5. MAE by Sequence
ax = axes[1, 1]
sns.boxplot(data=df, x='sequence_type', y='mae', ax=ax, palette='Set2')
ax.set_title('Mean Absolute Error (MAE)', fontweight='bold')
ax.set_xlabel('Sequence Type')
ax.set_ylabel('MAE')

# 6. Sample sizes
ax = axes[1, 2]
seq_counts = df['sequence_type'].value_counts().sort_index()
bars = ax.bar(seq_counts.index, seq_counts.values, color=sns.color_palette('Set2'))
ax.set_title('Comparisons per Sequence Type', fontweight='bold')
ax.set_xlabel('Sequence Type')
ax.set_ylabel('Number of Comparisons')
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{int(height)}', ha='center', va='bottom', fontweight='bold')

plt.tight_layout()
plt.savefig('output/plots/OVERVIEW_dashboard.png', bbox_inches='tight')
print("✓ Saved: output/plots/OVERVIEW_dashboard.png")
plt.close()

# ============================================================================
# VISUALIZATION 2: Correlation Matrix
# ============================================================================
fig, axes = plt.subplots(1, 3, figsize=(18, 5))
fig.suptitle('Metric Correlations by Sequence Type', fontsize=14, fontweight='bold')

for idx, seq in enumerate(['T1', 'T2', 'SWI']):
    seq_data = df[df['sequence_type'] == seq][metrics]
    corr = seq_data.corr()

    ax = axes[idx]
    sns.heatmap(corr, annot=True, fmt='.2f', cmap='RdBu_r', center=0,
                vmin=-1, vmax=1, square=True, ax=ax, cbar_kws={'label': 'Correlation'})
    ax.set_title(f'{seq} (n={len(seq_data)})', fontweight='bold')

plt.tight_layout()
plt.savefig('output/plots/correlation_matrix.png', bbox_inches='tight')
print("✓ Saved: output/plots/correlation_matrix.png")
plt.close()

# ============================================================================
# VISUALIZATION 3: Patient-wise Performance
# ============================================================================
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle('Patient-Level Metrics', fontsize=14, fontweight='bold')

# SSIM by patient and sequence
ax = axes[0, 0]
for seq in ['T1', 'T2', 'SWI']:
    seq_data = df[df['sequence_type'] == seq].sort_values('patient_id')
    ax.plot(range(len(seq_data)), seq_data['ssim_mean'], 'o-', label=seq, alpha=0.7)
ax.set_title('SSIM across Patients', fontweight='bold')
ax.set_xlabel('Patient Index')
ax.set_ylabel('SSIM')
ax.legend()
ax.grid(True, alpha=0.3)

# NCC by patient and sequence
ax = axes[0, 1]
for seq in ['T1', 'T2', 'SWI']:
    seq_data = df[df['sequence_type'] == seq].sort_values('patient_id')
    ax.plot(range(len(seq_data)), seq_data['ncc'], 'o-', label=seq, alpha=0.7)
ax.set_title('NCC across Patients', fontweight='bold')
ax.set_xlabel('Patient Index')
ax.set_ylabel('NCC')
ax.axhline(y=0, color='red', linestyle='--', alpha=0.3)
ax.legend()
ax.grid(True, alpha=0.3)

# Pearson correlation distribution
ax = axes[1, 0]
for seq in ['T1', 'T2', 'SWI']:
    seq_data = df[df['sequence_type'] == seq]['pearson_r']
    ax.hist(seq_data, bins=20, alpha=0.5, label=f'{seq} (n={len(seq_data)})')
ax.set_title('Pearson Correlation Distribution', fontweight='bold')
ax.set_xlabel('Pearson r')
ax.set_ylabel('Frequency')
ax.axvline(x=0, color='red', linestyle='--', alpha=0.3)
ax.legend()

# PSNR distribution
ax = axes[1, 1]
for seq in ['T1', 'T2', 'SWI']:
    seq_data = df[df['sequence_type'] == seq]['psnr']
    ax.hist(seq_data, bins=20, alpha=0.5, label=f'{seq} (n={len(seq_data)})')
ax.set_title('PSNR Distribution', fontweight='bold')
ax.set_xlabel('PSNR (dB)')
ax.set_ylabel('Frequency')
ax.legend()

plt.tight_layout()
plt.savefig('output/plots/patient_level_metrics.png', bbox_inches='tight')
print("✓ Saved: output/plots/patient_level_metrics.png")
plt.close()

# ============================================================================
# VISUALIZATION 4: Detailed Violin Plots
# ============================================================================
fig, axes = plt.subplots(2, 3, figsize=(18, 12))
fig.suptitle('Detailed Metric Distributions', fontsize=14, fontweight='bold')

plot_metrics = ['ssim_mean', 'ncc', 'pearson_r', 'psnr', 'mae', 'mutual_information']
titles = ['SSIM', 'NCC', 'Pearson r', 'PSNR (dB)', 'MAE', 'Mutual Information']

for idx, (metric, title) in enumerate(zip(plot_metrics, titles)):
    ax = axes[idx // 3, idx % 3]
    sns.violinplot(data=df, x='sequence_type', y=metric, ax=ax, palette='Set2')
    ax.set_title(title, fontweight='bold')
    ax.set_xlabel('Sequence Type')
    ax.set_ylabel(title)

    # Add mean markers
    for i, seq in enumerate(['T1', 'T2', 'SWI']):
        data = df[df['sequence_type'] == seq][metric]
        if len(data) > 0:
            mean_val = data.mean()
            ax.plot(i, mean_val, 'D', color='red', markersize=8,
                   markeredgecolor='white', markeredgewidth=1.5, zorder=10)

plt.tight_layout()
plt.savefig('output/plots/violin_distributions.png', bbox_inches='tight')
print("✓ Saved: output/plots/violin_distributions.png")
plt.close()

# ============================================================================
# Statistical Tests with Benjamini-Hochberg FDR Correction
# ============================================================================
print("\n" + "=" * 70)
print("STATISTICAL TESTS (with Benjamini-Hochberg FDR correction)")
print("=" * 70)

# Test differences between sequence types
from scipy.stats import kruskal, mannwhitneyu
from statsmodels.stats.multitest import multipletests

# Collect all test results
test_results = []

for metric in ['ssim_mean', 'ncc', 'pearson_r']:
    t1_data = df[df['sequence_type'] == 'T1'][metric].dropna()
    t2_data = df[df['sequence_type'] == 'T2'][metric].dropna()
    swi_data = df[df['sequence_type'] == 'SWI'][metric].dropna()

    # Kruskal-Wallis test (non-parametric ANOVA)
    h_stat, p_val = kruskal(t1_data, t2_data, swi_data)
    test_results.append({
        'metric': metric,
        'test': 'Kruskal-Wallis',
        'comparison': 'T1 vs T2 vs SWI',
        'statistic': h_stat,
        'p_value': p_val
    })

    # Pairwise Mann-Whitney U tests
    pairs = [('T1', 'T2', t1_data, t2_data),
             ('T1', 'SWI', t1_data, swi_data),
             ('T2', 'SWI', t2_data, swi_data)]

    for name1, name2, data1, data2 in pairs:
        if len(data1) > 0 and len(data2) > 0:
            u_stat, p_val = mannwhitneyu(data1, data2, alternative='two-sided')
            test_results.append({
                'metric': metric,
                'test': 'Mann-Whitney U',
                'comparison': f'{name1} vs {name2}',
                'statistic': u_stat,
                'p_value': p_val
            })

# Create DataFrame and apply FDR correction
results_df = pd.DataFrame(test_results)
p_values = results_df['p_value'].values

# Benjamini-Hochberg FDR correction
reject, p_corrected, alphacSidak, alphacBonf = multipletests(
    p_values, alpha=0.05, method='fdr_bh'
)

results_df['p_fdr_corrected'] = p_corrected
results_df['significant_fdr'] = reject

# Save detailed results to CSV
results_df.to_csv('output/statistics/statistical_tests_fdr_corrected.csv', index=False)
print("\n✓ Saved: output/statistics/statistical_tests_fdr_corrected.csv")

# Print results with both uncorrected and FDR-corrected p-values
print(f"\nTotal tests: {len(test_results)}")
print(f"FDR threshold: α = 0.05")
print(f"Significant after FDR correction: {reject.sum()}/{len(test_results)}")

for metric in ['ssim_mean', 'ncc', 'pearson_r']:
    print(f"\n{metric.upper()}:")

    metric_results = results_df[results_df['metric'] == metric]

    for _, row in metric_results.iterrows():
        sig_marker = "***" if row['significant_fdr'] else ""
        print(f"  {row['comparison']:20s}: ", end='')

        if row['test'] == 'Kruskal-Wallis':
            print(f"H={row['statistic']:.4f}, p={row['p_value']:.6f}, ", end='')
        else:
            print(f"U={row['statistic']:.2f}, p={row['p_value']:.6f}, ", end='')

        print(f"p_FDR={row['p_fdr_corrected']:.6f} {sig_marker}")

# Print summary of significant results
print("\n" + "=" * 70)
print("SUMMARY: Significant Results After FDR Correction (α = 0.05)")
print("=" * 70)
sig_results = results_df[results_df['significant_fdr']]
if len(sig_results) > 0:
    for _, row in sig_results.iterrows():
        print(f"  {row['metric']:12s} | {row['comparison']:20s} | p_FDR = {row['p_fdr_corrected']:.6f}")
else:
    print("  No tests remained significant after FDR correction.")

print("\n" + "=" * 70)
print("ANALYSIS COMPLETE!")
print("=" * 70)
print(f"\n✓ All visualizations saved to: output/plots/")
print(f"✓ Summary statistics saved to: output/statistics/")
print(f"✓ Statistical tests (FDR corrected) saved to: output/statistics/statistical_tests_fdr_corrected.csv")
