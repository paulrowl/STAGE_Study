#!/usr/bin/env python3
"""
Infarct-Stratified Analysis of STAGE MRI Quality Assessment
Bifurcate analysis by acute infarct status
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Set publication-quality style
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

def standardize_infarct_status(value):
    """Standardize acute infarct status to Y/N"""
    if pd.isna(value):
        return 'Unknown'
    value_str = str(value).strip().upper()
    if value_str.startswith('Y') or value_str == 'YES':
        return 'Y'
    elif value_str.startswith('N') or value_str == 'NO':
        return 'N'
    else:
        return 'Unknown'

def load_and_merge_data():
    """Load metrics data and merge with acute infarct status"""
    print("Loading data...")

    # Load acute infarct data
    infarct_df = pd.read_excel('output/statistics/neurorad_scores_unified.xlsx')
    infarct_df['acute_infarct'] = infarct_df['Acute INFARCT?'].apply(standardize_infarct_status)
    infarct_df = infarct_df[['rAccession', 'acute_infarct']]
    infarct_df.columns = ['patient_id', 'acute_infarct']

    print(f"Loaded infarct status for {len(infarct_df)} patients")
    print(f"  With acute infarct (Y): {(infarct_df['acute_infarct'] == 'Y').sum()}")
    print(f"  Without acute infarct (N): {(infarct_df['acute_infarct'] == 'N').sum()}")
    print(f"  Unknown: {(infarct_df['acute_infarct'] == 'Unknown').sum()}")

    # Load metrics for each sequence
    metrics = {}
    for seq in ['t1', 't2', 'swi']:
        file_path = Path(f'output/statistics/{seq}_metrics_with_expert_scores.csv')
        if file_path.exists():
            df = pd.read_csv(file_path)
            # Merge with infarct status
            df = df.merge(infarct_df, on='patient_id', how='left')
            # Fill unknown
            df['acute_infarct'] = df['acute_infarct'].fillna('Unknown')
            metrics[seq.upper()] = df
            print(f"Loaded {seq.upper()}: {len(df)} patients")
            print(f"  With infarct: {(df['acute_infarct'] == 'Y').sum()}")
            print(f"  Without infarct: {(df['acute_infarct'] == 'N').sum()}")

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

def compare_groups_statistical_tests(metrics):
    """Perform statistical tests comparing infarct vs non-infarct groups"""
    results = []

    test_metrics = ['ssim_mean', 'pearson_r', 'ncc', 'stage_snr', 'stage_cnr',
                    'conv_snr', 'conv_cnr', 'expert_score']

    for seq, df in metrics.items():
        # Only include patients with known infarct status
        df_known = df[df['acute_infarct'].isin(['Y', 'N'])].copy()

        for metric in test_metrics:
            if metric not in df_known.columns:
                continue

            infarct_yes = df_known[df_known['acute_infarct'] == 'Y'][metric].dropna()
            infarct_no = df_known[df_known['acute_infarct'] == 'N'][metric].dropna()

            if len(infarct_yes) > 2 and len(infarct_no) > 2:
                # Mann-Whitney U test (non-parametric)
                u_stat, p_val = stats.mannwhitneyu(infarct_yes, infarct_no, alternative='two-sided')

                # Effect size (Cohen's d)
                mean_diff = infarct_yes.mean() - infarct_no.mean()
                pooled_std = np.sqrt((infarct_yes.std()**2 + infarct_no.std()**2) / 2)
                cohens_d = mean_diff / pooled_std if pooled_std > 0 else 0

                results.append({
                    'Sequence': seq,
                    'Metric': metric,
                    'Infarct_Y_Mean': infarct_yes.mean(),
                    'Infarct_Y_SD': infarct_yes.std(),
                    'Infarct_Y_N': len(infarct_yes),
                    'Infarct_N_Mean': infarct_no.mean(),
                    'Infarct_N_SD': infarct_no.std(),
                    'Infarct_N_N': len(infarct_no),
                    'U_Statistic': u_stat,
                    'P_Value': p_val,
                    'Cohens_d': cohens_d,
                    'Significance': get_significance_stars(p_val)
                })

    results_df = pd.DataFrame(results)
    return results_df

def create_comparison_figures(metrics, output_dir):
    """Create comprehensive comparison figures"""

    # Figure 1: Sample sizes and quality distribution by infarct status
    fig = plt.figure(figsize=(20, 12))
    gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.3)

    sequences = ['T1', 'T2', 'SWI']
    colors_seq = {'T1': '#2ecc71', 'T2': '#3498db', 'SWI': '#e74c3c'}

    for seq_idx, seq in enumerate(sequences):
        if seq not in metrics:
            continue

        df = metrics[seq]
        df_known = df[df['acute_infarct'].isin(['Y', 'N'])].copy()

        # Sample sizes
        ax = fig.add_subplot(gs[0, seq_idx])
        infarct_counts = df_known['acute_infarct'].value_counts()
        ax.bar(['With Infarct', 'Without Infarct'],
               [infarct_counts.get('Y', 0), infarct_counts.get('N', 0)],
               color=['#e74c3c', '#2ecc71'], alpha=0.7, edgecolor='black', linewidth=2)
        ax.set_ylabel('Number of Patients', fontsize=12, fontweight='bold')
        ax.set_title(f'{seq}: Sample Sizes', fontsize=13, fontweight='bold', color=colors_seq[seq])
        ax.grid(axis='y', alpha=0.3)

        # Add counts on bars
        for i, count in enumerate([infarct_counts.get('Y', 0), infarct_counts.get('N', 0)]):
            ax.text(i, count + 0.5, str(count), ha='center', fontsize=11, fontweight='bold')

        # Quality score distributions
        ax = fig.add_subplot(gs[1, seq_idx])
        if 'expert_score' in df_known.columns:
            infarct_y_scores = df_known[df_known['acute_infarct'] == 'Y']['expert_score'].dropna()
            infarct_n_scores = df_known[df_known['acute_infarct'] == 'N']['expert_score'].dropna()

            if len(infarct_y_scores) > 0 and len(infarct_n_scores) > 0:
                positions = [1, 2]
                bp = ax.boxplot([infarct_y_scores, infarct_n_scores], positions=positions,
                               widths=0.6, patch_artist=True, showmeans=True,
                               meanprops=dict(marker='D', markerfacecolor='red', markersize=8))
                bp['boxes'][0].set_facecolor('#e74c3c')
                bp['boxes'][0].set_alpha(0.7)
                bp['boxes'][1].set_facecolor('#2ecc71')
                bp['boxes'][1].set_alpha(0.7)

                ax.set_xticks(positions)
                ax.set_xticklabels(['With Infarct', 'Without Infarct'], fontsize=10)
                ax.set_ylabel('Expert Quality Score', fontsize=12, fontweight='bold')
                ax.set_title(f'{seq}: Quality Scores by Infarct Status', fontsize=13, fontweight='bold')
                ax.grid(axis='y', alpha=0.3)

                # Add significance test
                if len(infarct_y_scores) > 2 and len(infarct_n_scores) > 2:
                    u_stat, p_val = stats.mannwhitneyu(infarct_y_scores, infarct_n_scores)
                    stars = get_significance_stars(p_val)
                    y_max = max(infarct_y_scores.max(), infarct_n_scores.max())
                    ax.text(1.5, y_max + 0.5, stars, ha='center', fontsize=16, fontweight='bold')

        # SSIM comparison
        ax = fig.add_subplot(gs[2, seq_idx])
        if 'ssim_mean' in df_known.columns:
            infarct_y_ssim = df_known[df_known['acute_infarct'] == 'Y']['ssim_mean'].dropna()
            infarct_n_ssim = df_known[df_known['acute_infarct'] == 'N']['ssim_mean'].dropna()

            if len(infarct_y_ssim) > 0 and len(infarct_n_ssim) > 0:
                vp = ax.violinplot([infarct_y_ssim, infarct_n_ssim], positions=[1, 2],
                                  showmeans=True, showmedians=True)
                vp['bodies'][0].set_facecolor('#e74c3c')
                vp['bodies'][0].set_alpha(0.7)
                vp['bodies'][1].set_facecolor('#2ecc71')
                vp['bodies'][1].set_alpha(0.7)

                ax.set_xticks([1, 2])
                ax.set_xticklabels(['With Infarct', 'Without Infarct'], fontsize=10)
                ax.set_ylabel('SSIM', fontsize=12, fontweight='bold')
                ax.set_title(f'{seq}: SSIM by Infarct Status', fontsize=13, fontweight='bold')
                ax.grid(axis='y', alpha=0.3)

                # Add significance test
                if len(infarct_y_ssim) > 2 and len(infarct_n_ssim) > 2:
                    u_stat, p_val = stats.mannwhitneyu(infarct_y_ssim, infarct_n_ssim)
                    stars = get_significance_stars(p_val)
                    y_max = max(infarct_y_ssim.max(), infarct_n_ssim.max())
                    ax.text(1.5, y_max + 0.02, stars, ha='center', fontsize=16, fontweight='bold')

    # Summary statistics text box
    ax_summary = fig.add_subplot(gs[:, 3])
    ax_summary.axis('off')

    summary_text = "INFARCT-STRATIFIED ANALYSIS\n" + "="*50 + "\n\n"

    for seq in sequences:
        if seq not in metrics:
            continue

        df = metrics[seq]
        df_known = df[df['acute_infarct'].isin(['Y', 'N'])].copy()

        summary_text += f"{seq}:\n"
        infarct_y = df_known[df_known['acute_infarct'] == 'Y']
        infarct_n = df_known[df_known['acute_infarct'] == 'N']

        summary_text += f"  With Infarct: n={len(infarct_y)}\n"
        summary_text += f"  Without Infarct: n={len(infarct_n)}\n"

        if 'expert_score' in df_known.columns:
            y_scores = infarct_y['expert_score'].dropna()
            n_scores = infarct_n['expert_score'].dropna()
            if len(y_scores) > 0 and len(n_scores) > 0:
                summary_text += f"  Quality (Y): {y_scores.mean():.2f}±{y_scores.std():.2f}\n"
                summary_text += f"  Quality (N): {n_scores.mean():.2f}±{n_scores.std():.2f}\n"

                if len(y_scores) > 2 and len(n_scores) > 2:
                    u_stat, p_val = stats.mannwhitneyu(y_scores, n_scores)
                    summary_text += f"  p-value: {p_val:.4f} {get_significance_stars(p_val)}\n"

        summary_text += "\n"

    ax_summary.text(0.1, 0.9, summary_text, transform=ax_summary.transAxes,
                   fontsize=11, verticalalignment='top', fontfamily='monospace',
                   bbox=dict(boxstyle='round', facecolor='lightcyan', alpha=0.3,
                            edgecolor='black', linewidth=2))

    plt.suptitle('Infarct-Stratified Analysis: Quality Comparison',
                 fontsize=18, fontweight='bold', y=0.98)
    plt.savefig(output_dir / 'infarct_comparison_overview.png', dpi=300,
                bbox_inches='tight', facecolor='white', edgecolor='none')
    print(f"✓ Saved: infarct_comparison_overview.png")
    plt.close()

    # Figure 2: Metric-by-metric comparison
    create_detailed_metric_comparison(metrics, output_dir)

def create_detailed_metric_comparison(metrics, output_dir):
    """Create detailed metric comparison figures"""

    fig, axes = plt.subplots(3, 3, figsize=(20, 15))
    fig.suptitle('Detailed Metric Comparison: Infarct vs Non-Infarct',
                 fontsize=18, fontweight='bold', y=0.995)

    sequences = ['T1', 'T2', 'SWI']
    metrics_to_plot = ['ssim_mean', 'stage_snr', 'stage_cnr']
    metric_labels = ['SSIM', 'STAGE SNR', 'STAGE CNR']

    for row_idx, seq in enumerate(sequences):
        if seq not in metrics:
            continue

        df = metrics[seq]
        df_known = df[df['acute_infarct'].isin(['Y', 'N'])].copy()

        for col_idx, (metric, label) in enumerate(zip(metrics_to_plot, metric_labels)):
            ax = axes[row_idx, col_idx]

            if metric not in df_known.columns:
                ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
                continue

            infarct_y = df_known[df_known['acute_infarct'] == 'Y'][metric].dropna()
            infarct_n = df_known[df_known['acute_infarct'] == 'N'][metric].dropna()

            if len(infarct_y) == 0 and len(infarct_n) == 0:
                ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
                continue

            # Create violin plot
            data_to_plot = []
            labels_list = []
            colors_list = []

            if len(infarct_y) > 0:
                data_to_plot.append(infarct_y)
                labels_list.append('With Infarct')
                colors_list.append('#e74c3c')
            if len(infarct_n) > 0:
                data_to_plot.append(infarct_n)
                labels_list.append('Without Infarct')
                colors_list.append('#2ecc71')

            if data_to_plot:
                vp = ax.violinplot(data_to_plot, positions=range(len(data_to_plot)),
                                  showmeans=True, showmedians=True)

                for pc, color in zip(vp['bodies'], colors_list):
                    pc.set_facecolor(color)
                    pc.set_alpha(0.7)

                ax.set_xticks(range(len(labels_list)))
                ax.set_xticklabels(labels_list, fontsize=10)
                ax.set_ylabel(label, fontsize=11, fontweight='bold')
                ax.set_title(f'{seq}: {label}', fontsize=12, fontweight='bold')
                ax.grid(axis='y', alpha=0.3)

                # Add statistics
                if len(infarct_y) > 2 and len(infarct_n) > 2:
                    u_stat, p_val = stats.mannwhitneyu(infarct_y, infarct_n)
                    stars = get_significance_stars(p_val)
                    cohens_d = (infarct_y.mean() - infarct_n.mean()) / np.sqrt((infarct_y.std()**2 + infarct_n.std()**2) / 2)

                    stats_text = f'p={p_val:.4f} {stars}\nd={cohens_d:.2f}'
                    ax.text(0.98, 0.98, stats_text, transform=ax.transAxes,
                           fontsize=9, verticalalignment='top', horizontalalignment='right',
                           bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))

    plt.tight_layout()
    plt.savefig(output_dir / 'infarct_detailed_metric_comparison.png', dpi=300,
                bbox_inches='tight', facecolor='white', edgecolor='none')
    print(f"✓ Saved: infarct_detailed_metric_comparison.png")
    plt.close()

def generate_statistical_writeup(metrics, stats_results, output_dir):
    """Generate manuscript-ready statistical writeup"""

    writeup = []
    writeup.append("# INFARCT-STRATIFIED ANALYSIS: STAGE MRI Quality Assessment")
    writeup.append("=" * 80)
    writeup.append("")
    writeup.append("## OVERVIEW")
    writeup.append("")
    writeup.append("This analysis stratifies the STAGE MRI quality assessment by acute infarct status.")
    writeup.append("Patients were classified as having acute infarct (Y) or no acute infarct (N) based on")
    writeup.append("expert neuroradiologist review. Statistical comparisons were performed using")
    writeup.append("Mann-Whitney U tests (non-parametric) with effect sizes reported as Cohen's d.")
    writeup.append("")

    # Sample characteristics
    writeup.append("## SAMPLE CHARACTERISTICS")
    writeup.append("")

    for seq, df in metrics.items():
        df_known = df[df['acute_infarct'].isin(['Y', 'N'])].copy()
        infarct_y = df_known[df_known['acute_infarct'] == 'Y']
        infarct_n = df_known[df_known['acute_infarct'] == 'N']

        writeup.append(f"### {seq}")
        writeup.append(f"- Total patients with known infarct status: {len(df_known)}")
        writeup.append(f"- With acute infarct: {len(infarct_y)} ({len(infarct_y)/len(df_known)*100:.1f}%)")
        writeup.append(f"- Without acute infarct: {len(infarct_n)} ({len(infarct_n)/len(df_known)*100:.1f}%)")
        writeup.append("")

    # Quality score comparisons
    writeup.append("## QUALITY SCORE COMPARISONS")
    writeup.append("")

    for seq, df in metrics.items():
        df_known = df[df['acute_infarct'].isin(['Y', 'N'])].copy()

        if 'expert_score' in df_known.columns:
            infarct_y_scores = df_known[df_known['acute_infarct'] == 'Y']['expert_score'].dropna()
            infarct_n_scores = df_known[df_known['acute_infarct'] == 'N']['expert_score'].dropna()

            if len(infarct_y_scores) > 0 and len(infarct_n_scores) > 0:
                writeup.append(f"### {seq}")
                writeup.append(f"- With infarct: {infarct_y_scores.mean():.2f} ± {infarct_y_scores.std():.2f} (n={len(infarct_y_scores)})")
                writeup.append(f"- Without infarct: {infarct_n_scores.mean():.2f} ± {infarct_n_scores.std():.2f} (n={len(infarct_n_scores)})")

                if len(infarct_y_scores) > 2 and len(infarct_n_scores) > 2:
                    u_stat, p_val = stats.mannwhitneyu(infarct_y_scores, infarct_n_scores)
                    cohens_d = (infarct_y_scores.mean() - infarct_n_scores.mean()) / np.sqrt((infarct_y_scores.std()**2 + infarct_n_scores.std()**2) / 2)
                    writeup.append(f"- Mann-Whitney U = {u_stat:.2f}, p = {p_val:.4f} {get_significance_stars(p_val)}")
                    writeup.append(f"- Cohen's d = {cohens_d:.3f}")
                writeup.append("")

    # Detailed metric comparisons
    writeup.append("## DETAILED METRIC COMPARISONS")
    writeup.append("")
    writeup.append("Statistically significant differences (p < 0.05) between infarct and non-infarct groups:")
    writeup.append("")

    significant_results = stats_results[stats_results['P_Value'] < 0.05].sort_values('P_Value')

    if len(significant_results) > 0:
        for _, row in significant_results.iterrows():
            writeup.append(f"### {row['Sequence']} - {row['Metric']}")
            writeup.append(f"- With infarct: {row['Infarct_Y_Mean']:.3f} ± {row['Infarct_Y_SD']:.3f} (n={row['Infarct_Y_N']})")
            writeup.append(f"- Without infarct: {row['Infarct_N_Mean']:.3f} ± {row['Infarct_N_SD']:.3f} (n={row['Infarct_N_N']})")
            writeup.append(f"- p = {row['P_Value']:.4f} {row['Significance']}, Cohen's d = {row['Cohens_d']:.3f}")
            writeup.append("")
    else:
        writeup.append("No statistically significant differences were found between groups.")
        writeup.append("")

    writeup.append("## INTERPRETATION")
    writeup.append("")
    writeup.append("This stratified analysis examined whether the presence of acute infarct affects")
    writeup.append("image quality metrics and radiologist quality scores. ")

    if len(significant_results) > 0:
        writeup.append("Several significant differences were identified, suggesting that acute")
        writeup.append("pathology may impact certain quality metrics. These findings should be")
        writeup.append("considered when interpreting overall quality assessments.")
    else:
        writeup.append("No significant differences in quality metrics were found between patients")
        writeup.append("with and without acute infarcts, suggesting that image quality assessment")
        writeup.append("is robust to the presence of acute pathology.")

    writeup.append("")
    writeup.append("---")
    writeup.append(f"**Analysis Date:** {pd.Timestamp.now().strftime('%Y-%m-%d')}")
    writeup.append("**Statistical Method:** Mann-Whitney U test (non-parametric)")
    writeup.append("**Effect Size:** Cohen's d")

    # Write to file
    with open(output_dir / 'INFARCT_STRATIFIED_RESULTS.md', 'w') as f:
        f.write('\n'.join(writeup))

    print(f"✓ Saved: INFARCT_STRATIFIED_RESULTS.md")

def main():
    print("="*80)
    print("INFARCT-STRATIFIED ANALYSIS")
    print("Bifurcating STAGE MRI quality assessment by acute infarct status")
    print("="*80)
    print()

    output_dir = Path('output/figures/infarct_stratified_analysis')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load and merge data
    metrics = load_and_merge_data()
    print()

    # Perform statistical tests
    print("Performing statistical comparisons...")
    stats_results = compare_groups_statistical_tests(metrics)
    stats_results.to_csv(output_dir / 'infarct_stratified_statistics.csv', index=False)
    print(f"✓ Saved statistical results: {len(stats_results)} comparisons")
    print()

    # Create figures
    print("Generating figures...")
    create_comparison_figures(metrics, output_dir)
    print()

    # Generate writeup
    print("Generating statistical writeup...")
    generate_statistical_writeup(metrics, stats_results, output_dir)
    print()

    print("="*80)
    print("INFARCT-STRATIFIED ANALYSIS COMPLETE")
    print(f"Results saved to: {output_dir}/")
    print("="*80)

if __name__ == '__main__':
    main()
