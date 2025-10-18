#!/usr/bin/env python3
"""
Compute image similarity metrics between conventional and STAGE MRI sequences
and correlate them with expert quality scores to determine clinical adequacy thresholds.
"""

import pandas as pd
import numpy as np
import nibabel as nib
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats
from scipy.ndimage import zoom
from skimage.metrics import structural_similarity as ssim
from sklearn.metrics import roc_curve, auc
import warnings
warnings.filterwarnings('ignore')

# Configuration
sns.set_style("whitegrid")
sns.set_context("paper", font_scale=1.2)

# Paths
BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
NIFTI_DIR = BASE_DIR / 'output' / 'nifti'
STATS_DIR = BASE_DIR / 'output' / 'statistics'
OUTPUT_DIR = BASE_DIR / 'output' / 'visualizations'
OUTPUT_DIR.mkdir(exist_ok=True)

print("=" * 80)
print("IMAGE SIMILARITY METRICS vs EXPERT QUALITY SCORES")
print("=" * 80)

# Load expert scores
print("\nLoading expert quality scores...")
expert_scores_file = STATS_DIR / 'intensity_with_expert_scores.csv'
df_scores = pd.read_csv(expert_scores_file)

# Extract unique subjects
subjects = df_scores['subject_id'].unique()
print(f"Found {len(subjects)} subjects with expert scores: {list(subjects)}")

# ============================================================================
# SIMILARITY METRIC FUNCTIONS
# ============================================================================

def normalize_intensities(img):
    """Normalize image intensities to 0-1 range"""
    img_min = img.min()
    img_max = img.max()
    if img_max > img_min:
        return (img - img_min) / (img_max - img_min)
    return img

def resize_to_match(img1, img2):
    """Resize img2 to match img1's shape using trilinear interpolation"""
    if img1.shape == img2.shape:
        return img1, img2

    # Calculate zoom factors
    zoom_factors = np.array(img1.shape) / np.array(img2.shape)

    # Resize img2 to match img1
    img2_resized = zoom(img2, zoom_factors, order=1)  # order=1 for trilinear

    return img1, img2_resized

def compute_ssim(img1, img2):
    """Compute Structural Similarity Index (SSIM)"""
    try:
        # Normalize intensities
        img1_norm = normalize_intensities(img1)
        img2_norm = normalize_intensities(img2)

        # Resize if needed
        img1_norm, img2_norm = resize_to_match(img1_norm, img2_norm)

        # Compute SSIM with appropriate data range
        ssim_value = ssim(img1_norm, img2_norm, data_range=1.0)
        return ssim_value
    except Exception as e:
        print(f"    SSIM computation failed: {e}")
        return np.nan

def compute_ncc(img1, img2):
    """Compute Normalized Cross-Correlation (Pearson correlation)"""
    try:
        # Resize if needed
        img1, img2 = resize_to_match(img1, img2)

        # Flatten and compute correlation
        img1_flat = img1.flatten()
        img2_flat = img2.flatten()

        correlation = np.corrcoef(img1_flat, img2_flat)[0, 1]
        return correlation
    except Exception as e:
        print(f"    NCC computation failed: {e}")
        return np.nan

def compute_mse(img1, img2):
    """Compute Mean Squared Error"""
    try:
        # Normalize intensities first
        img1_norm = normalize_intensities(img1)
        img2_norm = normalize_intensities(img2)

        # Resize if needed
        img1_norm, img2_norm = resize_to_match(img1_norm, img2_norm)

        mse = np.mean((img1_norm - img2_norm) ** 2)
        return mse
    except Exception as e:
        print(f"    MSE computation failed: {e}")
        return np.nan

def compute_psnr(img1, img2):
    """Compute Peak Signal-to-Noise Ratio"""
    try:
        mse = compute_mse(img1, img2)
        if mse == 0 or np.isnan(mse):
            return np.nan

        # PSNR = 10 * log10(MAX^2 / MSE)
        # For normalized data, MAX = 1
        psnr = 10 * np.log10(1.0 / mse)
        return psnr
    except Exception as e:
        print(f"    PSNR computation failed: {e}")
        return np.nan

def compute_dice(mask1, mask2):
    """Compute DICE coefficient for binary masks"""
    try:
        # Resize if needed
        mask1, mask2 = resize_to_match(mask1, mask2)

        # Binarize masks
        mask1_bin = mask1 > 0
        mask2_bin = mask2 > 0

        intersection = np.sum(mask1_bin & mask2_bin)
        union = np.sum(mask1_bin) + np.sum(mask2_bin)

        if union == 0:
            return np.nan

        dice = 2.0 * intersection / union
        return dice
    except Exception as e:
        print(f"    DICE computation failed: {e}")
        return np.nan

# ============================================================================
# COMPUTE METRICS FOR ALL PAIRED SEQUENCES
# ============================================================================

results = []
sequence_types = ['T1', 'T2', 'SWI']

print("\n" + "=" * 80)
print("COMPUTING SIMILARITY METRICS")
print("=" * 80)

for subject in subjects:
    print(f"\nProcessing {subject}...")
    subject_dir = NIFTI_DIR / subject

    if not subject_dir.exists():
        print(f"  ✗ NIfTI directory not found")
        continue

    for seq_type in sequence_types:
        conv_file = subject_dir / f"{seq_type}_conv.nii.gz"
        stage_file = subject_dir / f"{seq_type}_STAGE.nii.gz"

        if not conv_file.exists() or not stage_file.exists():
            print(f"  ✗ {seq_type}: Missing files")
            continue

        print(f"  ✓ {seq_type}: Computing metrics...")

        try:
            # Load NIfTI images
            conv_img = nib.load(str(conv_file)).get_fdata()
            stage_img = nib.load(str(stage_file)).get_fdata()

            # Compute similarity metrics
            ssim_val = compute_ssim(conv_img, stage_img)
            ncc_val = compute_ncc(conv_img, stage_img)
            mse_val = compute_mse(conv_img, stage_img)
            psnr_val = compute_psnr(conv_img, stage_img)

            # For DICE, create simple brain masks (non-zero voxels)
            dice_val = compute_dice(conv_img, stage_img)

            # Get expert score for this sequence
            q_col = f'Q{sequence_types.index(seq_type) + 1}'  # Q1 for T1, Q2 for T2, Q3 for SWI
            expert_row = df_scores[(df_scores['subject_id'] == subject) &
                                   (df_scores['sequence'] == f'{seq_type}_conv')].iloc[0]
            expert_score = expert_row[q_col]

            results.append({
                'subject_id': subject,
                'sequence_type': seq_type,
                'SSIM': ssim_val,
                'NCC': ncc_val,
                'MSE': mse_val,
                'PSNR': psnr_val,
                'DICE': dice_val,
                'expert_score': expert_score,
                'Q_column': q_col
            })

            print(f"    SSIM={ssim_val:.3f}, NCC={ncc_val:.3f}, MSE={mse_val:.4f}, "
                  f"PSNR={psnr_val:.1f}, DICE={dice_val:.3f}, Expert={expert_score}")

        except Exception as e:
            print(f"    ✗ Error: {e}")
            continue

# Create results dataframe
df_results = pd.DataFrame(results)

print(f"\n✓ Computed metrics for {len(df_results)} sequence pairs")

# Save results
output_csv = STATS_DIR / 'similarity_metrics_vs_expert_scores.csv'
df_results.to_csv(output_csv, index=False)
print(f"✓ Saved: {output_csv}")

# ============================================================================
# STATISTICAL CORRELATION ANALYSIS
# ============================================================================

print("\n" + "=" * 80)
print("CORRELATION ANALYSIS: SIMILARITY METRICS vs EXPERT SCORES")
print("=" * 80)

metrics = ['SSIM', 'NCC', 'MSE', 'PSNR', 'DICE']

# Overall correlations
print("\n### OVERALL (All Sequences) ###")
for metric in metrics:
    valid_data = df_results.dropna(subset=[metric, 'expert_score'])
    if len(valid_data) >= 3:
        r, p = stats.pearsonr(valid_data[metric], valid_data['expert_score'])
        rho, p_spearman = stats.spearmanr(valid_data[metric], valid_data['expert_score'])
        sig = "*" if p < 0.05 else ""
        print(f"  {metric:8s}: Pearson r={r:6.3f} (p={p:.4f}){sig}, "
              f"Spearman ρ={rho:6.3f} (p={p_spearman:.4f})")

# By sequence type
for seq_type in sequence_types:
    print(f"\n### {seq_type} SEQUENCES ###")
    seq_data = df_results[df_results['sequence_type'] == seq_type]

    for metric in metrics:
        valid_data = seq_data.dropna(subset=[metric, 'expert_score'])
        if len(valid_data) >= 3:
            r, p = stats.pearsonr(valid_data[metric], valid_data['expert_score'])
            rho, p_spearman = stats.spearmanr(valid_data[metric], valid_data['expert_score'])
            sig = "*" if p < 0.05 else ""
            print(f"  {metric:8s}: Pearson r={r:6.3f} (p={p:.4f}){sig}, "
                  f"Spearman ρ={rho:6.3f} (p={p_spearman:.4f})")

# ============================================================================
# THRESHOLD ANALYSIS: ROC CURVES
# ============================================================================

print("\n" + "=" * 80)
print("THRESHOLD ANALYSIS: OPTIMAL CUTOFFS FOR CLINICAL ADEQUACY")
print("=" * 80)

# Define clinical adequacy threshold (e.g., expert score >= 5 = "adequate")
adequacy_threshold = 5

threshold_results = []

for seq_type in sequence_types:
    print(f"\n### {seq_type} SEQUENCES ###")
    seq_data = df_results[df_results['sequence_type'] == seq_type].copy()

    # Create binary clinical adequacy label
    seq_data['adequate'] = (seq_data['expert_score'] >= adequacy_threshold).astype(int)

    n_adequate = seq_data['adequate'].sum()
    n_inadequate = len(seq_data) - n_adequate

    print(f"  Adequate (score≥{adequacy_threshold}): n={n_adequate}")
    print(f"  Inadequate (score<{adequacy_threshold}): n={n_inadequate}")

    if n_adequate == 0 or n_inadequate == 0:
        print(f"  ✗ Cannot compute ROC (need both adequate and inadequate samples)")
        continue

    for metric in metrics:
        valid_data = seq_data.dropna(subset=[metric, 'adequate'])

        if len(valid_data) < 3:
            continue

        try:
            # Compute ROC curve
            # For metrics where higher=better (SSIM, NCC, PSNR, DICE), use as-is
            # For metrics where lower=better (MSE), invert
            if metric == 'MSE':
                y_score = -valid_data[metric]  # Invert so higher is better
            else:
                y_score = valid_data[metric]

            fpr, tpr, thresholds = roc_curve(valid_data['adequate'], y_score)
            roc_auc = auc(fpr, tpr)

            # Find optimal threshold (Youden's J statistic)
            j_scores = tpr - fpr
            optimal_idx = np.argmax(j_scores)
            optimal_threshold = thresholds[optimal_idx]

            # Undo MSE inversion
            if metric == 'MSE':
                optimal_threshold = -optimal_threshold

            optimal_sensitivity = tpr[optimal_idx]
            optimal_specificity = 1 - fpr[optimal_idx]

            print(f"  {metric:8s}: AUC={roc_auc:.3f}, "
                  f"Optimal threshold={optimal_threshold:.3f} "
                  f"(Sens={optimal_sensitivity:.2f}, Spec={optimal_specificity:.2f})")

            threshold_results.append({
                'sequence_type': seq_type,
                'metric': metric,
                'AUC': roc_auc,
                'optimal_threshold': optimal_threshold,
                'sensitivity': optimal_sensitivity,
                'specificity': optimal_specificity,
                'n_samples': len(valid_data)
            })

        except Exception as e:
            print(f"  {metric:8s}: ROC computation failed - {e}")

# Save threshold analysis results
df_thresholds = pd.DataFrame(threshold_results)
threshold_csv = STATS_DIR / 'similarity_metric_thresholds.csv'
df_thresholds.to_csv(threshold_csv, index=False)
print(f"\n✓ Saved threshold analysis: {threshold_csv}")

# ============================================================================
# VISUALIZATION: SCATTER PLOTS
# ============================================================================

print("\n" + "=" * 80)
print("GENERATING VISUALIZATIONS")
print("=" * 80)

# Figure 1: Scatter plots - Metrics vs Expert Scores
print("\nGenerating scatter plots...")

fig, axes = plt.subplots(3, 5, figsize=(20, 12))
fig.suptitle('Image Similarity Metrics vs Expert Quality Scores',
             fontsize=18, fontweight='bold', y=0.995)

colors = {'T1': '#2ecc71', 'T2': '#3498db', 'SWI': '#e74c3c'}

for row, seq_type in enumerate(sequence_types):
    seq_data = df_results[df_results['sequence_type'] == seq_type]

    for col, metric in enumerate(metrics):
        ax = axes[row, col]

        valid_data = seq_data.dropna(subset=[metric, 'expert_score'])

        if len(valid_data) >= 3:
            # Scatter plot
            ax.scatter(valid_data['expert_score'], valid_data[metric],
                      alpha=0.7, s=100, color=colors[seq_type],
                      edgecolors='black', linewidth=1.5)

            # Correlation
            r, p = stats.pearsonr(valid_data['expert_score'], valid_data[metric])

            # Add trend line if significant
            if p < 0.1:
                z = np.polyfit(valid_data['expert_score'], valid_data[metric], 1)
                p_line = np.poly1d(z)
                x_line = np.linspace(valid_data['expert_score'].min(),
                                    valid_data['expert_score'].max(), 100)
                ax.plot(x_line, p_line(x_line), "r--", alpha=0.5, linewidth=2)

            # Statistics text
            sig = "**" if p < 0.01 else ("*" if p < 0.05 else "")
            ax.text(0.05, 0.95, f'r={r:.3f}{sig}\np={p:.3f}\nn={len(valid_data)}',
                   transform=ax.transAxes, va='top', fontsize=9,
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        ax.set_xlabel('Expert Score', fontsize=10, fontweight='bold')
        ax.set_ylabel(metric, fontsize=10, fontweight='bold')
        ax.set_title(f'{seq_type}: {metric}', fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.3)

plt.tight_layout()
scatter_file = OUTPUT_DIR / 'similarity_metrics_vs_expert_scores.png'
plt.savefig(scatter_file, dpi=300, bbox_inches='tight')
print(f"✓ Saved: {scatter_file}")
plt.close()

# Figure 2: ROC Curves
print("Generating ROC curves...")

if len(threshold_results) > 0:
    # Group by sequence type
    n_seq = len([s for s in sequence_types if any(r['sequence_type'] == s for r in threshold_results)])

    if n_seq > 0:
        fig, axes = plt.subplots(1, n_seq, figsize=(6*n_seq, 5))
        if n_seq == 1:
            axes = [axes]

        fig.suptitle(f'ROC Curves: Predicting Clinical Adequacy (Score ≥ {adequacy_threshold})',
                     fontsize=16, fontweight='bold')

        ax_idx = 0
        for seq_type in sequence_types:
            seq_data = df_results[df_results['sequence_type'] == seq_type].copy()
            seq_data['adequate'] = (seq_data['expert_score'] >= adequacy_threshold).astype(int)

            if seq_data['adequate'].nunique() < 2:
                continue

            ax = axes[ax_idx]

            for metric in metrics:
                valid_data = seq_data.dropna(subset=[metric, 'adequate'])

                if len(valid_data) < 3:
                    continue

                try:
                    if metric == 'MSE':
                        y_score = -valid_data[metric]
                    else:
                        y_score = valid_data[metric]

                    fpr, tpr, _ = roc_curve(valid_data['adequate'], y_score)
                    roc_auc = auc(fpr, tpr)

                    ax.plot(fpr, tpr, linewidth=2, label=f'{metric} (AUC={roc_auc:.2f})')
                except:
                    continue

            # Diagonal reference line
            ax.plot([0, 1], [0, 1], 'k--', linewidth=1, alpha=0.3)

            ax.set_xlabel('False Positive Rate', fontsize=12, fontweight='bold')
            ax.set_ylabel('True Positive Rate', fontsize=12, fontweight='bold')
            ax.set_title(f'{seq_type} Sequences', fontsize=14, fontweight='bold')
            ax.legend(loc='lower right', fontsize=9)
            ax.grid(True, alpha=0.3)

            ax_idx += 1

        plt.tight_layout()
        roc_file = OUTPUT_DIR / 'similarity_metrics_roc_curves.png'
        plt.savefig(roc_file, dpi=300, bbox_inches='tight')
        print(f"✓ Saved: {roc_file}")
        plt.close()

# ============================================================================
# SUMMARY REPORT
# ============================================================================

print("\n" + "=" * 80)
print("GENERATING SUMMARY REPORT")
print("=" * 80)

report_lines = []
report_lines.append("# Image Similarity Metrics vs Expert Quality Scores")
report_lines.append("=" * 80)
report_lines.append(f"\n**Analysis Date:** {pd.Timestamp.now().strftime('%Y-%m-%d')}")
report_lines.append(f"**Subjects Analyzed:** {len(subjects)}")
report_lines.append(f"**Total Sequence Pairs:** {len(df_results)}")
report_lines.append(f"**Clinical Adequacy Threshold:** Expert Score ≥ {adequacy_threshold}")

report_lines.append("\n## Summary Statistics\n")
for metric in metrics:
    mean_val = df_results[metric].mean()
    std_val = df_results[metric].std()
    report_lines.append(f"- **{metric}**: {mean_val:.3f} ± {std_val:.3f}")

report_lines.append("\n## Correlation with Expert Scores (Overall)\n")
report_lines.append("| Metric | Pearson r | p-value | Spearman ρ | Significance |")
report_lines.append("|--------|-----------|---------|------------|--------------|")
for metric in metrics:
    valid_data = df_results.dropna(subset=[metric, 'expert_score'])
    if len(valid_data) >= 3:
        r, p = stats.pearsonr(valid_data[metric], valid_data['expert_score'])
        rho, p_s = stats.spearmanr(valid_data[metric], valid_data['expert_score'])
        sig = "**" if p < 0.01 else ("*" if p < 0.05 else "NS")
        report_lines.append(f"| {metric} | {r:.3f} | {p:.4f} | {rho:.3f} | {sig} |")

if len(threshold_results) > 0:
    report_lines.append("\n## Optimal Thresholds for Clinical Adequacy\n")
    report_lines.append("| Sequence | Metric | AUC | Threshold | Sensitivity | Specificity |")
    report_lines.append("|----------|--------|-----|-----------|-------------|-------------|")
    for _, row in df_thresholds.sort_values(['sequence_type', 'AUC'], ascending=[True, False]).iterrows():
        report_lines.append(f"| {row['sequence_type']} | {row['metric']} | {row['AUC']:.3f} | "
                           f"{row['optimal_threshold']:.3f} | {row['sensitivity']:.2f} | "
                           f"{row['specificity']:.2f} |")

report_lines.append("\n## Interpretation\n")
report_lines.append("**Metrics:**")
report_lines.append("- **SSIM** (Structural Similarity): Range [0,1], higher = better similarity")
report_lines.append("- **NCC** (Normalized Cross-Correlation): Range [-1,1], higher = better correlation")
report_lines.append("- **MSE** (Mean Squared Error): Range [0,∞], lower = better similarity")
report_lines.append("- **PSNR** (Peak Signal-to-Noise Ratio): Range [0,∞] dB, higher = better quality")
report_lines.append("- **DICE** (Overlap Coefficient): Range [0,1], higher = better overlap")

report_lines.append("\n**Clinical Adequacy:**")
report_lines.append(f"- Images with expert score ≥ {adequacy_threshold} are considered clinically adequate")
report_lines.append("- AUC > 0.7 indicates good discriminative ability")
report_lines.append("- Optimal thresholds balance sensitivity and specificity (Youden's J statistic)")

report_lines.append("\n## Files Generated\n")
report_lines.append(f"- **Metrics CSV:** `{output_csv.name}`")
report_lines.append(f"- **Thresholds CSV:** `{threshold_csv.name}`")
report_lines.append(f"- **Scatter plots:** `{scatter_file.name}`")
if len(threshold_results) > 0:
    report_lines.append(f"- **ROC curves:** `{roc_file.name}`")

# Save report
report_file = STATS_DIR / 'similarity_metrics_analysis_report.md'
with open(report_file, 'w') as f:
    f.write('\n'.join(report_lines))

print(f"✓ Saved report: {report_file}")

print("\n" + "=" * 80)
print("✓ ANALYSIS COMPLETE")
print("=" * 80)
print(f"\nResults saved to:")
print(f"  - {output_csv}")
print(f"  - {threshold_csv}")
print(f"  - {report_file}")
print(f"  - {scatter_file}")
if len(threshold_results) > 0:
    print(f"  - {roc_file}")
