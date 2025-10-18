#!/usr/bin/env python3
"""
Generate 5 high-quality figures for ISMRM Abstract submission.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats
from sklearn.metrics import roc_curve, auc

# Configuration
sns.set_style("whitegrid")
sns.set_context("talk", font_scale=1.1)

# Paths
BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
STATS_DIR = BASE_DIR / 'output' / 'statistics'
FIG_DIR = BASE_DIR / 'docs' / 'ISMRM' / 'figures'
FIG_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("GENERATING ISMRM FIGURES (ADULT PATIENTS ONLY, AGE ≥18)")
print("=" * 80)

# Load patient master list with demographics
df_master = pd.read_csv(STATS_DIR / 'PATIENT_MASTER_LIST.csv')

# Filter for adult patients only (age >= 18)
adult_patients = df_master[df_master['age'] >= 18]['subject_id'].tolist()
print(f"\nFiltering for adult patients (age ≥18): {len(adult_patients)} patients")
print(f"Excluded pediatric patients: {df_master[df_master['age'] < 18]['subject_id'].tolist()}")

# Load data
df_stats = pd.read_csv(STATS_DIR / 'comprehensive_statistical_results_CORRECTED.csv')
df_similarity = pd.read_csv(STATS_DIR / 'similarity_metrics_vs_expert_scores.csv')
df_paired = pd.read_csv(STATS_DIR / 'paired_comparisons_MERGED.csv')

# Filter all dataframes for adult patients only
df_similarity = df_similarity[df_similarity['subject_id'].isin(adult_patients)].copy()
df_paired = df_paired[df_paired['subject_id'].isin(adult_patients)].copy()

print(f"\nFiltered data:")
print(f"  - Similarity metrics: {len(df_similarity)} records")
print(f"  - Paired comparisons: {len(df_paired)} records")

# Define sequence types and colors
sequence_types = ['T1', 'T2', 'SWI']
colors_conv = ['#90EE90', '#87CEEB', '#FFB6C1']
colors_stage = ['#2ecc71', '#3498db', '#e74c3c']

# ============================================================================
# FIGURE 1: Intensity Correlations (Conventional vs STAGE)
# ============================================================================

print("\nGenerating Figure 1: Intensity Correlations...")

fig, axes = plt.subplots(2, 3, figsize=(15, 10))
fig.suptitle('Figure 1: Conventional vs STAGE Intensity Correlations',
             fontsize=16, fontweight='bold', y=0.995)

for idx, seq_type in enumerate(sequence_types):
    seq_data = df_paired[df_paired['sequence_type'] == seq_type].copy()
    row = df_stats[df_stats['sequence'] == seq_type].iloc[0]

    # GM intensities
    ax = axes[0, idx]
    ax.scatter(seq_data['conv_gm_mean'], seq_data['stage_gm_mean'],
              alpha=0.6, s=100, color=colors_stage[idx],
              edgecolors='black', linewidth=1.5)

    # Add diagonal reference line
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    min_val = min(xlim[0], ylim[0])
    max_val = max(xlim[1], ylim[1])
    ax.plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.3, linewidth=2)

    r_gm = row['gm_r']
    p_gm = row['gm_p']
    sig = "***" if p_gm < 0.001 else ("**" if p_gm < 0.01 else ("*" if p_gm < 0.05 else "NS"))
    ax.text(0.05, 0.95, f'r={r_gm:.3f} {sig}\np={p_gm:.4f}',
           transform=ax.transAxes, va='top', fontsize=10,
           bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    ax.set_xlabel('Conventional GM Intensity', fontsize=11, fontweight='bold')
    ax.set_ylabel('STAGE GM Intensity', fontsize=11, fontweight='bold')
    ax.set_title(f'{seq_type}: Gray Matter', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)

    # WM intensities
    ax = axes[1, idx]
    ax.scatter(seq_data['conv_wm_mean'], seq_data['stage_wm_mean'],
              alpha=0.6, s=100, color=colors_stage[idx],
              edgecolors='black', linewidth=1.5)

    # Add diagonal reference line
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    min_val = min(xlim[0], ylim[0])
    max_val = max(xlim[1], ylim[1])
    ax.plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.3, linewidth=2)

    r_wm = row['wm_r']
    p_wm = row['wm_p']
    sig = "***" if p_wm < 0.001 else ("**" if p_wm < 0.01 else ("*" if p_wm < 0.05 else "NS"))
    ax.text(0.05, 0.95, f'r={r_wm:.3f} {sig}\np={p_wm:.4f}',
           transform=ax.transAxes, va='top', fontsize=10,
           bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    ax.set_xlabel('Conventional WM Intensity', fontsize=11, fontweight='bold')
    ax.set_ylabel('STAGE WM Intensity', fontsize=11, fontweight='bold')
    ax.set_title(f'{seq_type}: White Matter', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)

plt.tight_layout()
fig1_path = FIG_DIR / 'Figure1_Intensity_Correlations.png'
plt.savefig(fig1_path, dpi=300, bbox_inches='tight')
print(f"✓ Saved: {fig1_path}")
plt.close()

# ============================================================================
# FIGURE 2: Similarity Metrics and Clinical Adequacy
# ============================================================================

print("\nGenerating Figure 2: Similarity Metrics and Clinical Adequacy...")

fig = plt.figure(figsize=(16, 10))
gs = fig.add_gridspec(3, 3, hspace=0.4, wspace=0.4)
fig.suptitle('Figure 2: Image Similarity Metrics and Clinical Quality Assessment',
             fontsize=16, fontweight='bold', y=0.98)

colors_seq = {'T1': '#2ecc71', 'T2': '#3498db', 'SWI': '#e74c3c'}

# Panel A: Heatmap of correlations between metrics and expert scores
ax1 = fig.add_subplot(gs[0, :])
metrics_list = ['SSIM', 'NCC', 'DICE', 'MSE', 'PSNR']
sequences = ['T1', 'T2', 'SWI']
corr_matrix = np.zeros((len(sequences), len(metrics_list)))

for i, seq in enumerate(sequences):
    seq_data = df_similarity[df_similarity['sequence_type'] == seq]
    for j, metric in enumerate(metrics_list):
        valid_data = seq_data.dropna(subset=[metric, 'expert_score'])
        if len(valid_data) >= 3:
            r, _ = stats.pearsonr(valid_data['expert_score'], valid_data[metric])
            corr_matrix[i, j] = r
        else:
            corr_matrix[i, j] = 0

# Create heatmap
im = ax1.imshow(corr_matrix, cmap='RdBu_r', aspect='auto', vmin=-0.6, vmax=0.6)
ax1.set_xticks(np.arange(len(metrics_list)))
ax1.set_yticks(np.arange(len(sequences)))
ax1.set_xticklabels(metrics_list, fontsize=12, fontweight='bold')
ax1.set_yticklabels(sequences, fontsize=12, fontweight='bold')

# Add correlation values
for i in range(len(sequences)):
    for j in range(len(metrics_list)):
        text = ax1.text(j, i, f'{corr_matrix[i, j]:.2f}',
                       ha="center", va="center", color="black", fontsize=11, fontweight='bold')

ax1.set_title('A. Correlation Matrix: Similarity Metrics vs Expert Scores',
              fontsize=13, fontweight='bold', pad=10)
cbar = plt.colorbar(im, ax=ax1, orientation='horizontal', pad=0.1, fraction=0.046)
cbar.set_label('Pearson Correlation', fontsize=11, fontweight='bold')

# Panel B: Best performing metric by sequence (NCC)
ax2 = fig.add_subplot(gs[1, 0])
for seq_type in sequences:
    seq_data = df_similarity[df_similarity['sequence_type'] == seq_type].copy()
    valid_data = seq_data.dropna(subset=['NCC', 'expert_score'])

    if len(valid_data) >= 3:
        ax2.scatter(valid_data['expert_score'], valid_data['NCC'],
                   alpha=0.7, s=120, color=colors_seq[seq_type],
                   label=seq_type, edgecolors='black', linewidth=2)

        r, p = stats.pearsonr(valid_data['expert_score'], valid_data['NCC'])
        if p < 0.1:
            z = np.polyfit(valid_data['expert_score'], valid_data['NCC'], 1)
            p_line = np.poly1d(z)
            x_line = np.linspace(valid_data['expert_score'].min(),
                                valid_data['expert_score'].max(), 100)
            ax2.plot(x_line, p_line(x_line),
                    color=colors_seq[seq_type], linestyle='--', alpha=0.6, linewidth=3)

ax2.set_xlabel('Expert Quality Score', fontsize=11, fontweight='bold')
ax2.set_ylabel('NCC (Normalized Cross-Correlation)', fontsize=11, fontweight='bold')
ax2.set_title('B. NCC vs Expert Scores', fontsize=12, fontweight='bold')
ax2.legend(fontsize=10, loc='lower right')
ax2.grid(True, alpha=0.3)

# Panel C: SSIM performance
ax3 = fig.add_subplot(gs[1, 1])
for seq_type in sequences:
    seq_data = df_similarity[df_similarity['sequence_type'] == seq_type].copy()
    valid_data = seq_data.dropna(subset=['SSIM', 'expert_score'])

    if len(valid_data) >= 3:
        ax3.scatter(valid_data['expert_score'], valid_data['SSIM'],
                   alpha=0.7, s=120, color=colors_seq[seq_type],
                   label=seq_type, edgecolors='black', linewidth=2)

        r, p = stats.pearsonr(valid_data['expert_score'], valid_data['SSIM'])
        if p < 0.1:
            z = np.polyfit(valid_data['expert_score'], valid_data['SSIM'], 1)
            p_line = np.poly1d(z)
            x_line = np.linspace(valid_data['expert_score'].min(),
                                valid_data['expert_score'].max(), 100)
            ax3.plot(x_line, p_line(x_line),
                    color=colors_seq[seq_type], linestyle='--', alpha=0.6, linewidth=3)

ax3.set_xlabel('Expert Quality Score', fontsize=11, fontweight='bold')
ax3.set_ylabel('SSIM (Structural Similarity)', fontsize=11, fontweight='bold')
ax3.set_title('C. SSIM vs Expert Scores', fontsize=12, fontweight='bold')
ax3.legend(fontsize=10, loc='lower right')
ax3.grid(True, alpha=0.3)

# Panel D: DICE performance (significant overall correlation)
ax4 = fig.add_subplot(gs[1, 2])
for seq_type in sequences:
    seq_data = df_similarity[df_similarity['sequence_type'] == seq_type].copy()
    valid_data = seq_data.dropna(subset=['DICE', 'expert_score'])

    if len(valid_data) >= 3:
        ax4.scatter(valid_data['expert_score'], valid_data['DICE'],
                   alpha=0.7, s=120, color=colors_seq[seq_type],
                   label=seq_type, edgecolors='black', linewidth=2)

        r, p = stats.pearsonr(valid_data['expert_score'], valid_data['DICE'])
        if p < 0.1:
            z = np.polyfit(valid_data['expert_score'], valid_data['DICE'], 1)
            p_line = np.poly1d(z)
            x_line = np.linspace(valid_data['expert_score'].min(),
                                valid_data['expert_score'].max(), 100)
            ax4.plot(x_line, p_line(x_line),
                    color=colors_seq[seq_type], linestyle='--', alpha=0.6, linewidth=3)

# Overall correlation for DICE
valid_all = df_similarity.dropna(subset=['DICE', 'expert_score'])
r_overall, p_overall = stats.pearsonr(valid_all['expert_score'], valid_all['DICE'])
sig = "**" if p_overall < 0.01 else ("*" if p_overall < 0.05 else "")
ax4.text(0.05, 0.95, f'Overall: r={r_overall:.3f}{sig}\np={p_overall:.3f}',
        transform=ax4.transAxes, va='top', fontsize=10, fontweight='bold',
        bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))

ax4.set_xlabel('Expert Quality Score', fontsize=11, fontweight='bold')
ax4.set_ylabel('DICE (Overlap Coefficient)', fontsize=11, fontweight='bold')
ax4.set_title('D. DICE vs Expert Scores (Significant Overall)', fontsize=12, fontweight='bold')
ax4.legend(fontsize=10, loc='lower right')
ax4.grid(True, alpha=0.3)

# Panel E: Metric performance summary - bar chart
ax5 = fig.add_subplot(gs[2, :2])
x_pos = np.arange(len(metrics_list))
width = 0.25

for i, seq_type in enumerate(sequences):
    correlations = corr_matrix[i, :]
    ax5.bar(x_pos + i*width, correlations, width, label=seq_type,
           color=colors_seq[seq_type], alpha=0.8, edgecolor='black', linewidth=1.5)

    # Add value labels on bars
    for j, (pos, val) in enumerate(zip(x_pos + i*width, correlations)):
        if abs(val) > 0.1:
            ax5.text(pos, val + 0.02 if val > 0 else val - 0.02, f'{val:.2f}',
                    ha='center', va='bottom' if val > 0 else 'top', fontsize=9, fontweight='bold')

ax5.axhline(y=0, color='black', linestyle='-', linewidth=1)
ax5.axhline(y=0.5, color='green', linestyle='--', linewidth=1.5, alpha=0.5, label='Moderate corr')
ax5.axhline(y=-0.5, color='green', linestyle='--', linewidth=1.5, alpha=0.5)
ax5.set_ylabel('Correlation with Expert Score', fontsize=12, fontweight='bold')
ax5.set_title('E. Summary: Metric Performance by Sequence Type', fontsize=13, fontweight='bold')
ax5.set_xticks(x_pos + width)
ax5.set_xticklabels(metrics_list, fontsize=11)
ax5.legend(fontsize=10, loc='upper right')
ax5.grid(True, alpha=0.3, axis='y')
ax5.set_ylim([-0.6, 0.6])

# Panel F: Key findings text
ax6 = fig.add_subplot(gs[2, 2])
ax6.axis('off')

findings_text = """
KEY CORRELATION FINDINGS:

Overall:
• DICE: r=0.42* (p=0.041)
  Only significant metric

By Sequence:
• SWI: NCC r=0.49, SSIM r=0.23
  Moderate positive trends

• T2: All metrics r<0.30
  Weak correlations suggest
  artifact-driven quality issues

• T1: Mixed, small sample
  (all rated adequate)

*p<0.05 **p<0.01 ***p<0.001
"""

ax6.text(0.05, 0.95, findings_text, transform=ax6.transAxes,
        verticalalignment='top', fontsize=10, family='monospace',
        bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7, pad=1))

fig2_path = FIG_DIR / 'Figure2_Similarity_Metrics.png'
plt.savefig(fig2_path, dpi=300, bbox_inches='tight')
print(f"✓ Saved: {fig2_path}")
plt.close()

# ============================================================================
# FIGURE 3: ROC Curves for Clinical Adequacy
# ============================================================================

print("\nGenerating Figure 3: ROC Curves...")

fig, axes = plt.subplots(1, 2, figsize=(12, 5))
fig.suptitle('Figure 3: ROC Curves for Predicting Clinical Adequacy (Score ≥ 5)',
             fontsize=16, fontweight='bold', y=1.02)

adequacy_threshold = 5

# Panel A: SWI sequences (best results)
ax = axes[0]
swi_data = df_similarity[df_similarity['sequence_type'] == 'SWI'].copy()
swi_data['adequate'] = (swi_data['expert_score'] >= adequacy_threshold).astype(int)

for metric, color in [('SSIM', '#e74c3c'), ('NCC', '#c0392b'), ('DICE', '#e67e22')]:
    valid_data = swi_data.dropna(subset=[metric, 'adequate'])
    if len(valid_data) >= 3 and valid_data['adequate'].nunique() == 2:
        fpr, tpr, _ = roc_curve(valid_data['adequate'], valid_data[metric])
        roc_auc = auc(fpr, tpr)
        ax.plot(fpr, tpr, linewidth=3, label=f'{metric} (AUC={roc_auc:.2f})', color=color)

ax.plot([0, 1], [0, 1], 'k--', linewidth=2, alpha=0.3, label='Chance')
ax.set_xlabel('False Positive Rate', fontsize=12, fontweight='bold')
ax.set_ylabel('True Positive Rate', fontsize=12, fontweight='bold')
ax.set_title('SWI Sequences', fontsize=13, fontweight='bold')
ax.legend(loc='lower right', fontsize=10)
ax.grid(True, alpha=0.3)

# Panel B: T2 sequences (poor results)
ax = axes[1]
t2_data = df_similarity[df_similarity['sequence_type'] == 'T2'].copy()
t2_data['adequate'] = (t2_data['expert_score'] >= adequacy_threshold).astype(int)

for metric, color in [('SSIM', '#3498db'), ('NCC', '#2980b9'), ('DICE', '#5dade2')]:
    valid_data = t2_data.dropna(subset=[metric, 'adequate'])
    if len(valid_data) >= 3 and valid_data['adequate'].nunique() == 2:
        try:
            fpr, tpr, _ = roc_curve(valid_data['adequate'], valid_data[metric])
            roc_auc = auc(fpr, tpr)
            ax.plot(fpr, tpr, linewidth=3, label=f'{metric} (AUC={roc_auc:.2f})', color=color)
        except:
            pass

ax.plot([0, 1], [0, 1], 'k--', linewidth=2, alpha=0.3, label='Chance')
ax.set_xlabel('False Positive Rate', fontsize=12, fontweight='bold')
ax.set_ylabel('True Positive Rate', fontsize=12, fontweight='bold')
ax.set_title('T2 Sequences', fontsize=13, fontweight='bold')
ax.legend(loc='lower right', fontsize=10)
ax.grid(True, alpha=0.3)

plt.tight_layout()
fig3_path = FIG_DIR / 'Figure3_ROC_Curves.png'
plt.savefig(fig3_path, dpi=300, bbox_inches='tight')
print(f"✓ Saved: {fig3_path}")
plt.close()

# ============================================================================
# FIGURE 4: Comprehensive Summary Figure
# ============================================================================

print("\nGenerating Figure 4: Comprehensive Summary...")

fig = plt.figure(figsize=(16, 10))
gs = fig.add_gridspec(3, 4, hspace=0.35, wspace=0.4)

fig.suptitle('Figure 4: Comprehensive Summary of STAGE Protocol Analysis',
             fontsize=18, fontweight='bold', y=0.98)

# Panel A: GM/WM Ratio Effect Sizes
ax1 = fig.add_subplot(gs[0, :2])
sequences = ['T1', 'T2', 'SWI']
effect_sizes = []
p_values = []
ns = []

for seq in sequences:
    row = df_stats[df_stats['sequence'] == seq].iloc[0]
    effect_sizes.append(row['ratio_d'])
    p_values.append(row['ratio_p'])
    ns.append(int(row['n']))

colors_bar = ['#2ecc71' if p > 0.05 else ('#f39c12' if abs(d) < 0.5 else '#e74c3c')
              for p, d in zip(p_values, effect_sizes)]

bars = ax1.bar(sequences, effect_sizes, color=colors_bar, alpha=0.8,
               edgecolor='black', linewidth=2)

# Add significance markers
for i, (p, d, n) in enumerate(zip(p_values, effect_sizes, ns)):
    sig = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "NS"))
    ax1.text(i, d + 0.1 if d > 0 else d - 0.1, f'{sig}\nn={n}',
            ha='center', va='bottom' if d > 0 else 'top', fontsize=11, fontweight='bold')

ax1.axhline(y=0, color='black', linestyle='-', linewidth=1)
ax1.axhline(y=0.5, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='Medium effect')
ax1.axhline(y=-0.5, color='gray', linestyle='--', linewidth=1, alpha=0.5)
ax1.set_ylabel('Cohen\'s d (Effect Size)', fontsize=12, fontweight='bold')
ax1.set_title('A. Tissue Contrast Effect Sizes (GM/WM Ratio)', fontsize=13, fontweight='bold')
ax1.legend(fontsize=9)
ax1.grid(True, alpha=0.3, axis='y')

# Panel B: Intensity Correlations Summary
ax2 = fig.add_subplot(gs[0, 2:])
x_pos = np.arange(len(sequences))
width = 0.35

gm_corrs = []
wm_corrs = []
for seq in sequences:
    row = df_stats[df_stats['sequence'] == seq].iloc[0]
    gm_corrs.append(row['gm_r'])
    wm_corrs.append(row['wm_r'])

ax2.bar(x_pos - width/2, gm_corrs, width, label='Gray Matter',
        color='#95a5a6', alpha=0.8, edgecolor='black', linewidth=1.5)
ax2.bar(x_pos + width/2, wm_corrs, width, label='White Matter',
        color='#34495e', alpha=0.8, edgecolor='black', linewidth=1.5)

ax2.set_ylabel('Pearson Correlation', fontsize=12, fontweight='bold')
ax2.set_title('B. Conventional vs STAGE Intensity Correlations', fontsize=13, fontweight='bold')
ax2.set_xticks(x_pos)
ax2.set_xticklabels(sequences)
ax2.legend(fontsize=10)
ax2.grid(True, alpha=0.3, axis='y')
ax2.set_ylim([-0.5, 1.0])

# Panel C: Sample Sizes
ax3 = fig.add_subplot(gs[1, :2])
bars = ax3.bar(sequences, ns, color=['#2ecc71', '#3498db', '#e74c3c'],
               alpha=0.8, edgecolor='black', linewidth=2)

for i, n in enumerate(ns):
    ax3.text(i, n + 1, str(n), ha='center', va='bottom',
            fontsize=14, fontweight='bold')

ax3.set_ylabel('Number of Paired Subjects', fontsize=12, fontweight='bold')
ax3.set_title('C. Sample Sizes by Sequence Type', fontsize=13, fontweight='bold')
ax3.grid(True, alpha=0.3, axis='y')

# Panel D: Similarity Metric Performance
ax4 = fig.add_subplot(gs[1, 2:])

# Get best AUC values for each sequence-metric combination
auc_data = []
for seq in ['T2', 'SWI']:  # T1 all adequate, so skip
    seq_data = df_similarity[df_similarity['sequence_type'] == seq].copy()
    seq_data['adequate'] = (seq_data['expert_score'] >= 5).astype(int)

    for metric in ['SSIM', 'NCC', 'DICE']:
        valid_data = seq_data.dropna(subset=[metric, 'adequate'])
        if len(valid_data) >= 3 and valid_data['adequate'].nunique() == 2:
            try:
                fpr, tpr, _ = roc_curve(valid_data['adequate'], valid_data[metric])
                auc_val = auc(fpr, tpr)
                auc_data.append({'Sequence': seq, 'Metric': metric, 'AUC': auc_val})
            except:
                pass

if auc_data:
    df_auc = pd.DataFrame(auc_data)
    pivot = df_auc.pivot(index='Metric', columns='Sequence', values='AUC')

    x_pos = np.arange(len(pivot.index))
    width = 0.35

    if 'T2' in pivot.columns:
        ax4.bar(x_pos - width/2, pivot['T2'], width, label='T2',
               color='#3498db', alpha=0.8, edgecolor='black', linewidth=1.5)
    if 'SWI' in pivot.columns:
        ax4.bar(x_pos + width/2, pivot['SWI'], width, label='SWI',
               color='#e74c3c', alpha=0.8, edgecolor='black', linewidth=1.5)

    ax4.axhline(y=0.7, color='green', linestyle='--', linewidth=2,
               alpha=0.5, label='Good Discrimination')
    ax4.set_ylabel('AUC', fontsize=12, fontweight='bold')
    ax4.set_title('D. Clinical Adequacy Prediction (ROC AUC)', fontsize=13, fontweight='bold')
    ax4.set_xticks(x_pos)
    ax4.set_xticklabels(pivot.index)
    ax4.legend(fontsize=10)
    ax4.grid(True, alpha=0.3, axis='y')
    ax4.set_ylim([0, 1.0])

# Panel E: Mean Intensity Differences
ax5 = fig.add_subplot(gs[2, :2])

gm_diffs = []
wm_diffs = []
for seq in sequences:
    row = df_stats[df_stats['sequence'] == seq].iloc[0]
    # Calculate percent difference
    gm_diff_pct = (row['gm_stage_mean'] - row['gm_conv_mean']) / row['gm_conv_mean'] * 100
    wm_diff_pct = (row['wm_stage_mean'] - row['wm_conv_mean']) / row['wm_conv_mean'] * 100
    gm_diffs.append(gm_diff_pct)
    wm_diffs.append(wm_diff_pct)

x_pos = np.arange(len(sequences))
width = 0.35

ax5.bar(x_pos - width/2, gm_diffs, width, label='Gray Matter',
       color='#95a5a6', alpha=0.8, edgecolor='black', linewidth=1.5)
ax5.bar(x_pos + width/2, wm_diffs, width, label='White Matter',
       color='#34495e', alpha=0.8, edgecolor='black', linewidth=1.5)

ax5.axhline(y=0, color='black', linestyle='-', linewidth=1)
ax5.set_ylabel('% Difference (STAGE vs Conv)', fontsize=12, fontweight='bold')
ax5.set_title('E. Absolute Intensity Scaling', fontsize=13, fontweight='bold')
ax5.set_xticks(x_pos)
ax5.set_xticklabels(sequences)
ax5.legend(fontsize=10)
ax5.grid(True, alpha=0.3, axis='y')

# Panel F: Key Findings Text Summary
ax6 = fig.add_subplot(gs[2, 2:])
ax6.axis('off')

summary_text = """
KEY FINDINGS:

T1-weighted STAGE:
• Statistical equivalence (p>0.05, |d|<0.3)
• Strong correlations (r>0.86, p<0.001)
• All sequences clinically adequate

T2-weighted STAGE:
• 17.6% contrast reduction (p<0.001, d=-1.01)
• Weak similarity-quality correlation (AUC<0.5)
• Artifact-driven quality concerns

SWI STAGE:
• Preserved contrast (p=0.679, d=-0.07)
• Good adequacy prediction:
  - NCC ≥ 0.814 (AUC=0.786)
  - SSIM ≥ 0.470 (AUC=0.643)
"""

ax6.text(0.05, 0.95, summary_text, transform=ax6.transAxes,
        verticalalignment='top', fontsize=11, family='monospace',
        bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8, pad=1))

fig4_path = FIG_DIR / 'Figure4_Comprehensive_Summary.png'
plt.savefig(fig4_path, dpi=300, bbox_inches='tight')
print(f"✓ Saved: {fig4_path}")
plt.close()

print("\n" + "=" * 80)
print("✓ ALL FIGURES GENERATED")
print("=" * 80)
print(f"\nFigures saved to: {FIG_DIR}/")
print("  - Figure1_Intensity_Correlations.png")
print("  - Figure2_Similarity_Metrics.png")
print("  - Figure3_ROC_Curves.png")
print("  - Figure4_Comprehensive_Summary.png")
