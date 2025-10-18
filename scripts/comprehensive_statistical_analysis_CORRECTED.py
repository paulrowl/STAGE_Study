#!/usr/bin/env python3
"""
Comprehensive Statistical Analysis - CORRECTED
Analyzes the corrected paired comparisons data with n=30 subjects
"""

import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path

def calculate_cohens_d(diff, std_diff):
    """Calculate Cohen's d effect size"""
    return diff / std_diff

def main():
    print("=" * 80)
    print("COMPREHENSIVE STATISTICAL ANALYSIS - CORRECTED DATA")
    print("=" * 80)

    # Load corrected paired comparisons
    df_paired = pd.read_csv('output/statistics/paired_comparisons_MERGED.csv')

    print(f"\nTotal paired comparisons: {len(df_paired)}")
    print(f"Unique subjects: {len(df_paired['subject_id'].unique())}")

    # Subjects with all 3 modalities
    subjects_all_3 = []
    for subject in df_paired['subject_id'].unique():
        subject_data = df_paired[df_paired['subject_id'] == subject]
        if len(subject_data) == 3:
            subjects_all_3.append(subject)

    print(f"Subjects with all 3 modalities: {len(subjects_all_3)}")

    results = []

    # Analyze each sequence type
    for sequence in ['T1', 'T2', 'SWI']:
        print("\n" + "=" * 80)
        print(f"{sequence} ANALYSIS")
        print("=" * 80)

        df_seq = df_paired[df_paired['sequence_type'] == sequence]
        n = len(df_seq)

        print(f"\nSample size: n={n}")

        # GM Mean
        conv_gm = df_seq['conv_gm_mean'].values
        stage_gm = df_seq['stage_gm_mean'].values
        gm_diff = stage_gm - conv_gm

        t_stat_gm, p_val_gm = stats.ttest_rel(stage_gm, conv_gm)
        cohens_d_gm = calculate_cohens_d(np.mean(gm_diff), np.std(gm_diff, ddof=1))

        print(f"\nGray Matter Mean Intensity:")
        print(f"  Conventional: {np.mean(conv_gm):.2f} ± {np.std(conv_gm, ddof=1):.2f}")
        print(f"  STAGE:        {np.mean(stage_gm):.2f} ± {np.std(stage_gm, ddof=1):.2f}")
        print(f"  Mean diff:    {np.mean(gm_diff):.2f} ± {np.std(gm_diff, ddof=1):.2f}")
        print(f"  t-statistic:  {t_stat_gm:.4f}")
        print(f"  p-value:      {p_val_gm:.6f}")
        print(f"  Cohen's d:    {cohens_d_gm:.4f}")

        # WM Mean
        conv_wm = df_seq['conv_wm_mean'].values
        stage_wm = df_seq['stage_wm_mean'].values
        wm_diff = stage_wm - conv_wm

        t_stat_wm, p_val_wm = stats.ttest_rel(stage_wm, conv_wm)
        cohens_d_wm = calculate_cohens_d(np.mean(wm_diff), np.std(wm_diff, ddof=1))

        print(f"\nWhite Matter Mean Intensity:")
        print(f"  Conventional: {np.mean(conv_wm):.2f} ± {np.std(conv_wm, ddof=1):.2f}")
        print(f"  STAGE:        {np.mean(stage_wm):.2f} ± {np.std(stage_wm, ddof=1):.2f}")
        print(f"  Mean diff:    {np.mean(wm_diff):.2f} ± {np.std(wm_diff, ddof=1):.2f}")
        print(f"  t-statistic:  {t_stat_wm:.4f}")
        print(f"  p-value:      {p_val_wm:.6f}")
        print(f"  Cohen's d:    {cohens_d_wm:.4f}")

        # GM/WM Ratio
        conv_ratio = df_seq['conv_gm_wm_ratio'].values
        stage_ratio = df_seq['stage_gm_wm_ratio'].values
        ratio_diff = stage_ratio - conv_ratio

        t_stat_ratio, p_val_ratio = stats.ttest_rel(stage_ratio, conv_ratio)
        cohens_d_ratio = calculate_cohens_d(np.mean(ratio_diff), np.std(ratio_diff, ddof=1))

        print(f"\nGM/WM Ratio:")
        print(f"  Conventional: {np.mean(conv_ratio):.4f} ± {np.std(conv_ratio, ddof=1):.4f}")
        print(f"  STAGE:        {np.mean(stage_ratio):.4f} ± {np.std(stage_ratio, ddof=1):.4f}")
        print(f"  Mean diff:    {np.mean(ratio_diff):.4f} ± {np.std(ratio_diff, ddof=1):.4f}")
        print(f"  t-statistic:  {t_stat_ratio:.4f}")
        print(f"  p-value:      {p_val_ratio:.6f}")
        print(f"  Cohen's d:    {cohens_d_ratio:.4f}")

        # Pearson correlations
        r_gm, p_gm = stats.pearsonr(conv_gm, stage_gm)
        r_wm, p_wm = stats.pearsonr(conv_wm, stage_wm)
        r_ratio, p_ratio = stats.pearsonr(conv_ratio, stage_ratio)

        print(f"\nPearson Correlations (conv vs STAGE):")
        print(f"  GM mean:   r={r_gm:.4f}, p={p_gm:.6f}")
        print(f"  WM mean:   r={r_wm:.4f}, p={p_wm:.6f}")
        print(f"  GM/WM ratio: r={r_ratio:.4f}, p={p_ratio:.6f}")

        # Store results
        results.append({
            'sequence': sequence,
            'n': n,
            'gm_conv_mean': np.mean(conv_gm),
            'gm_conv_std': np.std(conv_gm, ddof=1),
            'gm_stage_mean': np.mean(stage_gm),
            'gm_stage_std': np.std(stage_gm, ddof=1),
            'gm_diff_mean': np.mean(gm_diff),
            'gm_diff_std': np.std(gm_diff, ddof=1),
            'gm_t': t_stat_gm,
            'gm_p': p_val_gm,
            'gm_d': cohens_d_gm,
            'gm_r': r_gm,
            'wm_conv_mean': np.mean(conv_wm),
            'wm_conv_std': np.std(conv_wm, ddof=1),
            'wm_stage_mean': np.mean(stage_wm),
            'wm_stage_std': np.std(stage_wm, ddof=1),
            'wm_diff_mean': np.mean(wm_diff),
            'wm_diff_std': np.std(wm_diff, ddof=1),
            'wm_t': t_stat_wm,
            'wm_p': p_val_wm,
            'wm_d': cohens_d_wm,
            'wm_r': r_wm,
            'ratio_conv_mean': np.mean(conv_ratio),
            'ratio_conv_std': np.std(conv_ratio, ddof=1),
            'ratio_stage_mean': np.mean(stage_ratio),
            'ratio_stage_std': np.std(stage_ratio, ddof=1),
            'ratio_diff_mean': np.mean(ratio_diff),
            'ratio_diff_std': np.std(ratio_diff, ddof=1),
            'ratio_t': t_stat_ratio,
            'ratio_p': p_val_ratio,
            'ratio_d': cohens_d_ratio,
            'ratio_r': r_ratio
        })

    # Save results
    df_results = pd.DataFrame(results)
    output_file = Path('output/statistics/comprehensive_statistical_results_CORRECTED.csv')
    df_results.to_csv(output_file, index=False)

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\nSignificant findings (p < 0.05):")

    for result in results:
        seq = result['sequence']
        print(f"\n{seq}:")

        if result['gm_p'] < 0.05:
            direction = "increased" if result['gm_diff_mean'] > 0 else "decreased"
            print(f"  ✓ GM mean {direction} (p={result['gm_p']:.4f}, d={result['gm_d']:.2f})")
        else:
            print(f"    GM mean: no significant difference (p={result['gm_p']:.4f})")

        if result['wm_p'] < 0.05:
            direction = "increased" if result['wm_diff_mean'] > 0 else "decreased"
            print(f"  ✓ WM mean {direction} (p={result['wm_p']:.4f}, d={result['wm_d']:.2f})")
        else:
            print(f"    WM mean: no significant difference (p={result['wm_p']:.4f})")

        if result['ratio_p'] < 0.05:
            direction = "increased" if result['ratio_diff_mean'] > 0 else "decreased"
            print(f"  ✓ GM/WM ratio {direction} (p={result['ratio_p']:.4f}, d={result['ratio_d']:.2f})")
        else:
            print(f"    GM/WM ratio: no significant difference (p={result['ratio_p']:.4f})")

    print(f"\n✓ Results saved to: {output_file}")
    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
