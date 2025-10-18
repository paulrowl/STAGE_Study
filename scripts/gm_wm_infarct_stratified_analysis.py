#!/usr/bin/env python3
"""
GM/WM Intensity Ratio Analysis Stratified by Infarct Status
Analyzes whether acute infarct presence affects tissue intensity differences
between STAGE and conventional protocols
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

# Subjects to EXCLUDE from T1 analysis (file processing errors identified in outlier analysis)
T1_EXCLUDED_SUBJECTS = ['Anon13609', 'Anon21108']

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
    """Load paired comparisons and merge with infarct status"""
    print("="*80)
    print("LOADING AND MERGING DATA")
    print("="*80)
    print()

    # Load infarct status
    print("Loading acute infarct status...")
    infarct_df = pd.read_excel('output/statistics/neurorad_scores_unified.xlsx')
    infarct_df['acute_infarct'] = infarct_df['Acute INFARCT?'].apply(standardize_infarct_status)

    # Map rAccession to patient_id (assuming they match or need mapping)
    infarct_df = infarct_df[['rAccession', 'acute_infarct']].copy()
    infarct_df.columns = ['subject_id', 'acute_infarct']

    print(f"✓ Loaded infarct status for {len(infarct_df)} subjects")
    print(f"  With acute infarct (Y): {(infarct_df['acute_infarct'] == 'Y').sum()}")
    print(f"  Without acute infarct (N): {(infarct_df['acute_infarct'] == 'N').sum()}")
    print(f"  Unknown: {(infarct_df['acute_infarct'] == 'Unknown').sum()}")
    print()

    # Load paired comparisons
    print("Loading paired comparisons data...")
    paired_df = pd.read_csv('output/statistics/paired_comparisons_MERGED.csv')
    print(f"✓ Loaded {len(paired_df)} paired comparisons")
    print(f"  T1: {(paired_df['sequence_type'] == 'T1').sum()}")
    print(f"  T2: {(paired_df['sequence_type'] == 'T2').sum()}")
    print(f"  SWI: {(paired_df['sequence_type'] == 'SWI').sum()}")
    print()

    # Apply T1 exclusions BEFORE merging
    print("Applying T1 exclusions...")
    n_before = len(paired_df)
    t1_mask = (paired_df['sequence_type'] == 'T1') & (paired_df['subject_id'].isin(T1_EXCLUDED_SUBJECTS))
    n_excluded = t1_mask.sum()
    paired_df = paired_df[~t1_mask].copy()
    print(f"✓ Excluded {n_excluded} T1 subjects with file processing errors: {T1_EXCLUDED_SUBJECTS}")
    print(f"  T1 sample size after exclusion: {(paired_df['sequence_type'] == 'T1').sum()}")
    print()

    # Merge with infarct status
    print("Merging with infarct status...")
    merged_df = paired_df.merge(infarct_df, on='subject_id', how='left')
    merged_df['acute_infarct'] = merged_df['acute_infarct'].fillna('Unknown')

    print(f"✓ Merged dataset: {len(merged_df)} observations")
    print()

    return merged_df

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

def analyze_by_sequence_and_infarct(df, sequence):
    """Analyze GM/WM ratios for one sequence stratified by infarct status"""

    print(f"\n{'='*80}")
    print(f"{sequence.upper()} ANALYSIS")
    print(f"{'='*80}\n")

    # Filter to this sequence and known infarct status
    seq_df = df[(df['sequence_type'] == sequence) &
                (df['acute_infarct'].isin(['Y', 'N']))].copy()

    if len(seq_df) == 0:
        print(f"⚠ No data for {sequence}")
        return None

    print(f"Sample sizes:")
    print(f"  With infarct (Y): {(seq_df['acute_infarct'] == 'Y').sum()}")
    print(f"  Without infarct (N): {(seq_df['acute_infarct'] == 'N').sum()}")
    print()

    results = []

    # Analyze each infarct group separately
    for infarct_status in ['Y', 'N']:
        group_df = seq_df[seq_df['acute_infarct'] == infarct_status].copy()

        if len(group_df) < 3:
            print(f"⚠ Insufficient data for infarct={infarct_status} (n={len(group_df)})")
            continue

        # Paired t-test: Conv vs STAGE within this infarct group
        conv_ratio = group_df['conv_gm_wm_ratio'].values
        stage_ratio = group_df['stage_gm_wm_ratio'].values
        ratio_diff = stage_ratio - conv_ratio

        # Remove NaN values
        valid_mask = ~(np.isnan(conv_ratio) | np.isnan(stage_ratio))
        conv_ratio = conv_ratio[valid_mask]
        stage_ratio = stage_ratio[valid_mask]
        ratio_diff = ratio_diff[valid_mask]

        if len(conv_ratio) < 3:
            print(f"⚠ Insufficient valid data for infarct={infarct_status}")
            continue

        t_stat, p_val = stats.ttest_rel(stage_ratio, conv_ratio)

        # Effect size (Cohen's d for paired samples)
        mean_diff = np.mean(ratio_diff)
        sd_diff = np.std(ratio_diff, ddof=1)
        cohens_d = mean_diff / sd_diff if sd_diff > 0 else 0

        # Correlation
        r_corr, r_p = stats.pearsonr(conv_ratio, stage_ratio)

        infarct_label = "With Infarct" if infarct_status == 'Y' else "Without Infarct"

        print(f"{infarct_label} (n={len(conv_ratio)}):")
        print(f"  Conv GM/WM ratio: {np.mean(conv_ratio):.3f} ± {np.std(conv_ratio):.3f}")
        print(f"  STAGE GM/WM ratio: {np.mean(stage_ratio):.3f} ± {np.std(stage_ratio):.3f}")
        print(f"  Mean difference: {mean_diff:.3f} ± {sd_diff:.3f}")
        print(f"  Paired t-test: t={t_stat:.3f}, p={p_val:.6f} {get_significance_stars(p_val)}")
        print(f"  Cohen's d: {cohens_d:.3f}")
        print(f"  Correlation: r={r_corr:.3f}, p={r_p:.6f}")
        print()

        results.append({
            'Sequence': sequence,
            'Infarct_Status': infarct_label,
            'N': len(conv_ratio),
            'Conv_Mean': np.mean(conv_ratio),
            'Conv_SD': np.std(conv_ratio),
            'STAGE_Mean': np.mean(stage_ratio),
            'STAGE_SD': np.std(stage_ratio),
            'Diff_Mean': mean_diff,
            'Diff_SD': sd_diff,
            'T_Statistic': t_stat,
            'P_Value': p_val,
            'Cohens_d': cohens_d,
            'Correlation_r': r_corr,
            'Correlation_p': r_p,
            'Significance': get_significance_stars(p_val)
        })

    # Test for interaction: Does infarct status modify the STAGE vs Conv difference?
    if len(seq_df[seq_df['acute_infarct'] == 'Y']) >= 3 and len(seq_df[seq_df['acute_infarct'] == 'N']) >= 3:

        infarct_y_diff = seq_df[seq_df['acute_infarct'] == 'Y']['gm_wm_ratio_diff'].dropna().values
        infarct_n_diff = seq_df[seq_df['acute_infarct'] == 'N']['gm_wm_ratio_diff'].dropna().values

        if len(infarct_y_diff) >= 3 and len(infarct_n_diff) >= 3:
            # Independent t-test comparing the differences between groups
            t_interaction, p_interaction = stats.ttest_ind(infarct_y_diff, infarct_n_diff)

            print(f"INTERACTION TEST:")
            print(f"  Does infarct status modify the STAGE vs Conv difference?")
            print(f"  With infarct difference: {np.mean(infarct_y_diff):.3f} ± {np.std(infarct_y_diff):.3f}")
            print(f"  Without infarct difference: {np.mean(infarct_n_diff):.3f} ± {np.std(infarct_n_diff):.3f}")
            print(f"  Independent t-test: t={t_interaction:.3f}, p={p_interaction:.6f} {get_significance_stars(p_interaction)}")
            print()

            results.append({
                'Sequence': sequence,
                'Infarct_Status': 'Interaction Test',
                'N': f"{len(infarct_y_diff)} vs {len(infarct_n_diff)}",
                'Conv_Mean': np.nan,
                'Conv_SD': np.nan,
                'STAGE_Mean': np.nan,
                'STAGE_SD': np.nan,
                'Diff_Mean': np.mean(infarct_y_diff) - np.mean(infarct_n_diff),
                'Diff_SD': np.nan,
                'T_Statistic': t_interaction,
                'P_Value': p_interaction,
                'Cohens_d': np.nan,
                'Correlation_r': np.nan,
                'Correlation_p': np.nan,
                'Significance': get_significance_stars(p_interaction)
            })

    return pd.DataFrame(results)

def create_visualization(df, output_dir):
    """Create comprehensive visualization of infarct-stratified GM/WM analysis"""

    print("\n" + "="*80)
    print("CREATING VISUALIZATIONS")
    print("="*80 + "\n")

    sequences = ['T1', 'T2', 'SWI']
    colors_seq = {'T1': '#2ecc71', 'T2': '#3498db', 'SWI': '#e74c3c'}

    # Figure 1: GM/WM Ratio Comparisons by Infarct Status
    fig = plt.figure(figsize=(20, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3)

    for seq_idx, seq in enumerate(sequences):
        seq_df = df[(df['sequence_type'] == seq) &
                    (df['acute_infarct'].isin(['Y', 'N']))].copy()

        if len(seq_df) == 0:
            continue

        # Panel 1: Conv GM/WM ratio by infarct status
        ax = fig.add_subplot(gs[seq_idx, 0])

        infarct_y = seq_df[seq_df['acute_infarct'] == 'Y']['conv_gm_wm_ratio'].dropna()
        infarct_n = seq_df[seq_df['acute_infarct'] == 'N']['conv_gm_wm_ratio'].dropna()

        data_to_plot = []
        labels_list = []
        colors_list = []

        if len(infarct_y) > 0:
            data_to_plot.append(infarct_y)
            labels_list.append(f'With Infarct\n(n={len(infarct_y)})')
            colors_list.append('#e74c3c')
        if len(infarct_n) > 0:
            data_to_plot.append(infarct_n)
            labels_list.append(f'Without Infarct\n(n={len(infarct_n)})')
            colors_list.append('#2ecc71')

        if data_to_plot:
            bp = ax.boxplot(data_to_plot, patch_artist=True, showmeans=True,
                           meanprops=dict(marker='D', markerfacecolor='red', markersize=8))
            for patch, color in zip(bp['boxes'], colors_list):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)

            ax.set_xticks(range(1, len(labels_list) + 1))
            ax.set_xticklabels(labels_list, fontsize=10)
            ax.set_ylabel('GM/WM Ratio', fontsize=12, fontweight='bold')
            ax.set_title(f'{seq}: Conventional GM/WM Ratio', fontsize=13, fontweight='bold', color=colors_seq[seq])
            ax.grid(axis='y', alpha=0.3)

            # Add significance test
            if len(infarct_y) > 2 and len(infarct_n) > 2:
                u_stat, p_val = stats.mannwhitneyu(infarct_y, infarct_n)
                stars = get_significance_stars(p_val)
                y_max = max(infarct_y.max(), infarct_n.max()) if len(data_to_plot) == 2 else max(data_to_plot[0].max(), 0)
                ax.text(1.5, y_max * 1.1, f'p={p_val:.4f} {stars}', ha='center', fontsize=10,
                       bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))

        # Panel 2: STAGE GM/WM ratio by infarct status
        ax = fig.add_subplot(gs[seq_idx, 1])

        infarct_y = seq_df[seq_df['acute_infarct'] == 'Y']['stage_gm_wm_ratio'].dropna()
        infarct_n = seq_df[seq_df['acute_infarct'] == 'N']['stage_gm_wm_ratio'].dropna()

        data_to_plot = []
        labels_list = []
        colors_list = []

        if len(infarct_y) > 0:
            data_to_plot.append(infarct_y)
            labels_list.append(f'With Infarct\n(n={len(infarct_y)})')
            colors_list.append('#e74c3c')
        if len(infarct_n) > 0:
            data_to_plot.append(infarct_n)
            labels_list.append(f'Without Infarct\n(n={len(infarct_n)})')
            colors_list.append('#2ecc71')

        if data_to_plot:
            bp = ax.boxplot(data_to_plot, patch_artist=True, showmeans=True,
                           meanprops=dict(marker='D', markerfacecolor='red', markersize=8))
            for patch, color in zip(bp['boxes'], colors_list):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)

            ax.set_xticks(range(1, len(labels_list) + 1))
            ax.set_xticklabels(labels_list, fontsize=10)
            ax.set_ylabel('GM/WM Ratio', fontsize=12, fontweight='bold')
            ax.set_title(f'{seq}: STAGE GM/WM Ratio', fontsize=13, fontweight='bold', color=colors_seq[seq])
            ax.grid(axis='y', alpha=0.3)

            # Add significance test
            if len(infarct_y) > 2 and len(infarct_n) > 2:
                u_stat, p_val = stats.mannwhitneyu(infarct_y, infarct_n)
                stars = get_significance_stars(p_val)
                y_max = max(infarct_y.max(), infarct_n.max()) if len(data_to_plot) == 2 else max(data_to_plot[0].max(), 0)
                ax.text(1.5, y_max * 1.1, f'p={p_val:.4f} {stars}', ha='center', fontsize=10,
                       bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))

        # Panel 3: STAGE - Conv difference by infarct status
        ax = fig.add_subplot(gs[seq_idx, 2])

        infarct_y = seq_df[seq_df['acute_infarct'] == 'Y']['gm_wm_ratio_diff'].dropna()
        infarct_n = seq_df[seq_df['acute_infarct'] == 'N']['gm_wm_ratio_diff'].dropna()

        data_to_plot = []
        labels_list = []
        colors_list = []

        if len(infarct_y) > 0:
            data_to_plot.append(infarct_y)
            labels_list.append(f'With Infarct\n(n={len(infarct_y)})')
            colors_list.append('#e74c3c')
        if len(infarct_n) > 0:
            data_to_plot.append(infarct_n)
            labels_list.append(f'Without Infarct\n(n={len(infarct_n)})')
            colors_list.append('#2ecc71')

        if data_to_plot:
            vp = ax.violinplot(data_to_plot, positions=range(1, len(data_to_plot) + 1),
                              showmeans=True, showmedians=True)

            for pc, color in zip(vp['bodies'], colors_list):
                pc.set_facecolor(color)
                pc.set_alpha(0.7)

            ax.axhline(y=0, color='black', linestyle='--', linewidth=2, alpha=0.5, label='No difference')

            ax.set_xticks(range(1, len(labels_list) + 1))
            ax.set_xticklabels(labels_list, fontsize=10)
            ax.set_ylabel('GM/WM Ratio Difference\n(STAGE - Conv)', fontsize=12, fontweight='bold')
            ax.set_title(f'{seq}: GM/WM Ratio Difference', fontsize=13, fontweight='bold', color=colors_seq[seq])
            ax.grid(axis='y', alpha=0.3)

            # Add interaction test
            if len(infarct_y) > 2 and len(infarct_n) > 2:
                t_stat, p_val = stats.ttest_ind(infarct_y, infarct_n)
                stars = get_significance_stars(p_val)
                y_range = ax.get_ylim()[1] - ax.get_ylim()[0]
                y_pos = ax.get_ylim()[1] - 0.1 * y_range
                ax.text(1.5, y_pos, f'Interaction: p={p_val:.4f} {stars}', ha='center', fontsize=10,
                       bbox=dict(boxstyle='round', facecolor='lightcyan', alpha=0.9))

    plt.suptitle('GM/WM Ratio Analysis Stratified by Acute Infarct Status',
                 fontsize=18, fontweight='bold', y=0.995)
    plt.savefig(output_dir / 'gm_wm_infarct_stratified_overview.png', dpi=300,
                bbox_inches='tight', facecolor='white', edgecolor='none')
    print("✓ Saved: gm_wm_infarct_stratified_overview.png")
    plt.close()

    # Figure 2: Paired comparisons within each infarct group
    create_paired_comparison_figure(df, output_dir)

def create_paired_comparison_figure(df, output_dir):
    """Create paired comparison scatter plots"""

    fig, axes = plt.subplots(3, 2, figsize=(16, 18))
    fig.suptitle('Paired Comparisons: Conv vs STAGE GM/WM Ratio by Infarct Status',
                 fontsize=18, fontweight='bold', y=0.995)

    sequences = ['T1', 'T2', 'SWI']
    colors_seq = {'T1': '#2ecc71', 'T2': '#3498db', 'SWI': '#e74c3c'}

    for seq_idx, seq in enumerate(sequences):
        seq_df = df[(df['sequence_type'] == seq) &
                    (df['acute_infarct'].isin(['Y', 'N']))].copy()

        for col_idx, infarct_status in enumerate(['Y', 'N']):
            ax = axes[seq_idx, col_idx]

            group_df = seq_df[seq_df['acute_infarct'] == infarct_status].copy()

            if len(group_df) == 0:
                ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
                continue

            conv = group_df['conv_gm_wm_ratio'].values
            stage = group_df['stage_gm_wm_ratio'].values

            # Remove NaN
            valid_mask = ~(np.isnan(conv) | np.isnan(stage))
            conv = conv[valid_mask]
            stage = stage[valid_mask]

            if len(conv) == 0:
                ax.text(0.5, 0.5, 'No valid data', ha='center', va='center', transform=ax.transAxes)
                continue

            # Scatter plot
            ax.scatter(conv, stage, alpha=0.6, s=100, color=colors_seq[seq], edgecolor='black', linewidth=1.5)

            # Identity line
            min_val = min(conv.min(), stage.min())
            max_val = max(conv.max(), stage.max())
            ax.plot([min_val, max_val], [min_val, max_val], 'k--', linewidth=2, alpha=0.5, label='Identity')

            # Regression line
            if len(conv) > 2:
                slope, intercept, r_value, p_value, std_err = stats.linregress(conv, stage)
                x_line = np.linspace(min_val, max_val, 100)
                y_line = slope * x_line + intercept
                ax.plot(x_line, y_line, 'r-', linewidth=2, alpha=0.7, label=f'Fit: r={r_value:.3f}')

            ax.set_xlabel('Conventional GM/WM Ratio', fontsize=12, fontweight='bold')
            ax.set_ylabel('STAGE GM/WM Ratio', fontsize=12, fontweight='bold')

            infarct_label = "With Acute Infarct" if infarct_status == 'Y' else "Without Acute Infarct"
            ax.set_title(f'{seq}: {infarct_label} (n={len(conv)})',
                        fontsize=13, fontweight='bold', color=colors_seq[seq])
            ax.grid(alpha=0.3)
            ax.legend(fontsize=10, loc='upper left')

            # Add statistics
            if len(conv) > 2:
                t_stat, p_val = stats.ttest_rel(stage, conv)
                diff_mean = np.mean(stage - conv)
                diff_sd = np.std(stage - conv, ddof=1)

                stats_text = f'Paired t-test:\np={p_val:.6f}\nΔ={diff_mean:.3f}±{diff_sd:.3f}'
                ax.text(0.98, 0.02, stats_text, transform=ax.transAxes,
                       fontsize=9, verticalalignment='bottom', horizontalalignment='right',
                       bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))

    plt.tight_layout()
    plt.savefig(output_dir / 'gm_wm_infarct_paired_comparisons.png', dpi=300,
                bbox_inches='tight', facecolor='white', edgecolor='none')
    print("✓ Saved: gm_wm_infarct_paired_comparisons.png")
    plt.close()

def generate_writeup(all_results, output_dir):
    """Generate manuscript-ready writeup"""

    print("\n" + "="*80)
    print("GENERATING WRITEUP")
    print("="*80 + "\n")

    writeup = []
    writeup.append("# GM/WM Intensity Ratio Analysis Stratified by Acute Infarct Status")
    writeup.append("=" * 80)
    writeup.append("")
    writeup.append("**Date:** " + pd.Timestamp.now().strftime('%Y-%m-%d'))
    writeup.append("**Analysis:** Tissue contrast analysis stratified by acute infarct presence")
    writeup.append("")
    writeup.append("## OVERVIEW")
    writeup.append("")
    writeup.append("This analysis examines whether the presence of acute infarct affects:")
    writeup.append("1. Absolute GM/WM intensity ratios in conventional and STAGE protocols")
    writeup.append("2. Differences between STAGE and conventional tissue contrast")
    writeup.append("3. Correlation between conventional and STAGE measurements")
    writeup.append("")
    writeup.append("**Key Question:** Does acute infarct status modify the relationship between")
    writeup.append("STAGE and conventional tissue contrast?")
    writeup.append("")
    writeup.append("## IMPORTANT EXCLUSIONS")
    writeup.append("")
    writeup.append("**T1 Analysis:** Two subjects excluded due to file processing errors identified")
    writeup.append("in outlier analysis:")
    writeup.append(f"- {T1_EXCLUDED_SUBJECTS[0]}: T1_conv.nii.gz is binary mask (max=1.0), not T1 image")
    writeup.append(f"- {T1_EXCLUDED_SUBJECTS[1]}: T1_conv.nii.gz is binary mask (max=1.0), not T1 image")
    writeup.append("")
    writeup.append("T1 sample size: n=39 (after exclusion from original n=41)")
    writeup.append("")

    writeup.append("## RESULTS BY SEQUENCE")
    writeup.append("")

    for seq in ['T1', 'T2', 'SWI']:
        seq_results = all_results[all_results['Sequence'] == seq].copy()

        if len(seq_results) == 0:
            continue

        writeup.append(f"### {seq}")
        writeup.append("")

        # Within-group comparisons (Conv vs STAGE)
        within_group = seq_results[seq_results['Infarct_Status'] != 'Interaction Test']

        for _, row in within_group.iterrows():
            writeup.append(f"#### {row['Infarct_Status']} (n={row['N']})")
            writeup.append("")
            writeup.append(f"**Conventional GM/WM ratio:** {row['Conv_Mean']:.3f} ± {row['Conv_SD']:.3f}")
            writeup.append(f"**STAGE GM/WM ratio:** {row['STAGE_Mean']:.3f} ± {row['STAGE_SD']:.3f}")
            writeup.append(f"**Difference (STAGE - Conv):** {row['Diff_Mean']:.3f} ± {row['Diff_SD']:.3f}")
            writeup.append(f"**Paired t-test:** t={row['T_Statistic']:.3f}, p={row['P_Value']:.6f} {row['Significance']}")
            writeup.append(f"**Effect size (Cohen's d):** {row['Cohens_d']:.3f}")
            writeup.append(f"**Correlation (Conv vs STAGE):** r={row['Correlation_r']:.3f}, p={row['Correlation_p']:.6f}")
            writeup.append("")

        # Interaction test
        interaction = seq_results[seq_results['Infarct_Status'] == 'Interaction Test']
        if len(interaction) > 0:
            row = interaction.iloc[0]
            writeup.append(f"#### Interaction Test: Does infarct status modify STAGE vs Conv difference?")
            writeup.append("")
            writeup.append(f"**Sample sizes:** {row['N']}")
            writeup.append(f"**Between-group difference:** {row['Diff_Mean']:.3f}")
            writeup.append(f"**Independent t-test:** t={row['T_Statistic']:.3f}, p={row['P_Value']:.6f} {row['Significance']}")

            if row['P_Value'] < 0.05:
                writeup.append("")
                writeup.append("⚠ **SIGNIFICANT INTERACTION:** Acute infarct presence significantly modifies")
                writeup.append("   the relationship between STAGE and conventional tissue contrast.")
            else:
                writeup.append("")
                writeup.append("✓ **NO SIGNIFICANT INTERACTION:** Acute infarct presence does not significantly")
                writeup.append("   modify the relationship between STAGE and conventional tissue contrast.")
            writeup.append("")

        writeup.append("")

    writeup.append("## INTERPRETATION")
    writeup.append("")
    writeup.append("### Key Findings:")
    writeup.append("")

    # Check for significant interactions
    interactions = all_results[all_results['Infarct_Status'] == 'Interaction Test']
    significant_interactions = interactions[interactions['P_Value'] < 0.05]

    if len(significant_interactions) > 0:
        writeup.append("**SIGNIFICANT INTERACTIONS DETECTED:**")
        writeup.append("")
        for _, row in significant_interactions.iterrows():
            writeup.append(f"- **{row['Sequence']}:** Acute infarct status significantly modifies the")
            writeup.append(f"  STAGE vs conventional difference (p={row['P_Value']:.6f})")
        writeup.append("")
        writeup.append("**Clinical Implication:** STAGE protocol tissue contrast characteristics may")
        writeup.append("depend on the presence of acute pathology. Separate validation may be needed")
        writeup.append("for patients with and without acute infarcts.")
    else:
        writeup.append("**NO SIGNIFICANT INTERACTIONS DETECTED:**")
        writeup.append("")
        writeup.append("Acute infarct status does not significantly modify the relationship between")
        writeup.append("STAGE and conventional tissue contrast across all three sequence types.")
        writeup.append("")
        writeup.append("**Clinical Implication:** STAGE protocol tissue contrast characteristics appear")
        writeup.append("robust to the presence of acute infarcts. Findings from the overall analysis")
        writeup.append("apply to both patient subgroups.")

    writeup.append("")
    writeup.append("---")
    writeup.append("")
    writeup.append("## METHODS")
    writeup.append("")
    writeup.append("**Statistical Approach:**")
    writeup.append("1. Paired t-tests within each infarct group (Conv vs STAGE)")
    writeup.append("2. Independent t-tests for interaction (comparing differences between infarct groups)")
    writeup.append("3. Pearson correlation between Conv and STAGE ratios")
    writeup.append("4. Effect sizes reported as Cohen's d")
    writeup.append("")
    writeup.append("**Significance Levels:**")
    writeup.append("- ***: p < 0.001 (highly significant)")
    writeup.append("- **: p < 0.01 (very significant)")
    writeup.append("- *: p < 0.05 (significant)")
    writeup.append("- ns: p ≥ 0.05 (not significant)")
    writeup.append("")
    writeup.append("**Effect Size Interpretation (Cohen's d):**")
    writeup.append("- |d| < 0.3: Negligible")
    writeup.append("- 0.3 ≤ |d| < 0.5: Small")
    writeup.append("- 0.5 ≤ |d| < 0.8: Medium")
    writeup.append("- |d| ≥ 0.8: Large")

    # Write to file
    output_file = output_dir / 'GM_WM_INFARCT_STRATIFIED_RESULTS.md'
    with open(output_file, 'w') as f:
        f.write('\n'.join(writeup))

    print(f"✓ Saved: {output_file.name}")

def main():
    print("\n" + "="*80)
    print("GM/WM INTENSITY RATIO ANALYSIS STRATIFIED BY ACUTE INFARCT STATUS")
    print("="*80)
    print()

    # Create output directory
    output_dir = Path('output/statistics/gm_wm_infarct_analysis')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load and merge data
    df = load_and_merge_data()

    # Analyze each sequence
    all_results = []

    for sequence in ['T1', 'T2', 'SWI']:
        results = analyze_by_sequence_and_infarct(df, sequence)
        if results is not None:
            all_results.append(results)

    # Combine all results
    if all_results:
        all_results_df = pd.concat(all_results, ignore_index=True)

        # Save results
        results_file = output_dir / 'gm_wm_infarct_stratified_statistics.csv'
        all_results_df.to_csv(results_file, index=False)
        print(f"\n✓ Saved statistical results: {results_file}")

        # Create visualizations
        create_visualization(df, output_dir)

        # Generate writeup
        generate_writeup(all_results_df, output_dir)
    else:
        print("\n⚠ No results generated")

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print(f"Results saved to: {output_dir}/")
    print("="*80)
    print()

if __name__ == '__main__':
    main()
