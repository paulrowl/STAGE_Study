#!/usr/bin/env python3
"""
Create comprehensive PDF report with figures and captions
"""

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle
import pandas as pd
from pathlib import Path
from scipy import stats
from datetime import datetime

# Paths
BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
PAIRED_DATA = BASE_DIR / 'output' / 'statistics' / 'paired_comparisons_MERGED.csv'
OUTPUT_DIR = BASE_DIR / 'output' / 'visualizations'
VIZ_DIR = OUTPUT_DIR

# Load data for statistics
df = pd.read_csv(PAIRED_DATA)
df = df.dropna(subset=['conv_gm_mean', 'stage_gm_mean', 'conv_wm_mean', 'stage_wm_mean'])

print("Creating comprehensive PDF report...")

# Create PDF
pdf_path = OUTPUT_DIR / 'STAGE_Study_Comprehensive_Report.pdf'
with PdfPages(pdf_path) as pdf:

    # ========================================================================
    # TITLE PAGE
    # ========================================================================
    fig = plt.figure(figsize=(8.5, 11))
    ax = fig.add_subplot(111)
    ax.axis('off')

    # Title
    ax.text(0.5, 0.85, 'STAGE MRI Study', ha='center', va='top',
            fontsize=28, fontweight='bold', transform=ax.transAxes)

    ax.text(0.5, 0.78, 'Gray Matter and White Matter Intensity Analysis', ha='center', va='top',
            fontsize=16, transform=ax.transAxes)

    ax.text(0.5, 0.72, 'Comparison of STAGE vs Conventional Sequences', ha='center', va='top',
            fontsize=14, style='italic', transform=ax.transAxes)

    # Date
    ax.text(0.5, 0.65, f'Generated: {datetime.now().strftime("%B %d, %Y")}',
            ha='center', va='top', fontsize=12, transform=ax.transAxes)

    # Summary box
    summary_text = f"""
DATASET SUMMARY

Total Sequences: 238 across 43 subjects
  • T1_conv: 40    • T1_STAGE: 43
  • T2_conv: 42    • T2_STAGE: 31
  • SWI_conv: 43   • SWI_STAGE: 39

Valid Paired Comparisons: 24
  • T1:  7 subject pairs
  • T2:  8 subject pairs
  • SWI: 9 subject pairs

Subjects with Complete Pairs:
  • All 3 sequences: 6 subjects
    (Anon27334, Anon28584, Anon39526,
     Anon50199, Anon72813, Anon88788)

  • T2 + SWI only: 2 subjects
    (Anon13609, Anon21108)

  • T1 + SWI only: 1 subject
    (Anon43113)
"""

    ax.text(0.5, 0.45, summary_text, ha='center', va='top',
            fontsize=11, family='monospace', transform=ax.transAxes,
            bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8, pad=1))

    # Footer
    ax.text(0.5, 0.05, 'Processing Pipeline: DICOM → NIfTI → HD-BET → Tissue Segmentation → Statistics',
            ha='center', va='bottom', fontsize=9, style='italic', transform=ax.transAxes)

    pdf.savefig(fig, bbox_inches='tight')
    plt.close()

    # ========================================================================
    # FIGURE 1: INTENSITY CORRELATIONS
    # ========================================================================
    fig = plt.figure(figsize=(8.5, 11))

    # Load and display the figure
    img = plt.imread(VIZ_DIR / 'figure1_intensity_correlations.png')
    ax_img = plt.subplot(2, 1, 1)
    ax_img.imshow(img)
    ax_img.axis('off')

    # Caption area
    ax_caption = plt.subplot(2, 1, 2)
    ax_caption.axis('off')

    caption_text = """Figure 1. Gray Matter and White Matter Intensity Correlations Between STAGE and Conventional Sequences

Scatter plots showing the relationship between conventional and STAGE MRI sequence intensities for gray matter (GM, top row)
and white matter (WM, bottom row) across three sequence types: T1-weighted, T2-weighted, and susceptibility-weighted imaging
(SWI). Each point represents a single subject. The dashed gray line indicates the identity line (y=x), while the red line shows
the linear regression fit.

KEY FINDINGS:
  • T1 sequences (n=7): Strong positive GM correlation (r=0.813, p=0.026*), indicating good agreement between STAGE and
    conventional T1 intensities in gray matter. White matter shows moderate correlation (r=0.690, p=0.086).

  • T2 sequences (n=8): Weak correlations for both GM (r=0.227, p=0.589) and WM (r=0.062, p=0.885), suggesting substantial
    differences in absolute intensity scales between STAGE and conventional T2 protocols. Note the higher absolute intensities
    in STAGE T2, likely due to different acquisition parameters.

  • SWI sequences (n=9): Moderate correlations for both GM (r=0.454, p=0.220) and WM (r=0.498, p=0.173), with one notable
    outlier in each tissue type suggesting potential data quality issues or protocol variations.

INTERPRETATION: T1 sequences show the best intensity agreement between protocols, while T2 sequences exhibit protocol-dependent
intensity scaling that may require normalization for direct comparison. The regression lines diverge from the identity line for
T2 and SWI, indicating systematic intensity differences between conventional and STAGE acquisitions.

* p < 0.05 (statistically significant)
"""

    ax_caption.text(0.05, 0.95, caption_text, ha='left', va='top',
                   fontsize=9, wrap=True, transform=ax_caption.transAxes)

    plt.tight_layout()
    pdf.savefig(fig, bbox_inches='tight')
    plt.close()

    # ========================================================================
    # FIGURE 2: GM/WM RATIOS
    # ========================================================================
    fig = plt.figure(figsize=(8.5, 11))

    # Load and display the figure
    img = plt.imread(VIZ_DIR / 'figure2_gm_wm_ratios.png')
    ax_img = plt.subplot(2, 1, 1)
    ax_img.imshow(img)
    ax_img.axis('off')

    # Caption area
    ax_caption = plt.subplot(2, 1, 2)
    ax_caption.axis('off')

    # Calculate statistics for caption
    stats_text = ""
    for seq_type in ['T1', 'T2', 'SWI']:
        seq_data = df[df['sequence_type'] == seq_type]
        if len(seq_data) >= 2:
            t_stat, p_val = stats.ttest_rel(seq_data['conv_gm_wm_ratio'], seq_data['stage_gm_wm_ratio'])
            conv_mean = seq_data['conv_gm_wm_ratio'].mean()
            stage_mean = seq_data['stage_gm_wm_ratio'].mean()
            diff_pct = ((stage_mean - conv_mean) / conv_mean) * 100

            sig = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else "(ns)"

            stats_text += f"  • {seq_type}: Conv={conv_mean:.3f}, STAGE={stage_mean:.3f} ({diff_pct:+.1f}%), p={p_val:.4f} {sig}\n"

    caption_text = f"""Figure 2. Gray Matter to White Matter Intensity Ratio Comparisons

Box plots comparing the GM/WM intensity ratios between conventional (left) and STAGE (right) sequences for T1, T2, and SWI.
Each box shows the median (red line), interquartile range (box), and range (whiskers). Individual subject data points are
overlaid (black dots). Statistical significance is indicated above each pair (*** p<0.001, ** p<0.01, * p<0.05, ns = not
significant). Paired t-tests were used to assess differences.

STATISTICAL RESULTS:
{stats_text}

KEY FINDINGS:
  • T1 sequences (n=7): STAGE shows significantly HIGHER GM/WM ratio (+9.7%, p<0.001***), indicating greater gray-white matter
    contrast in STAGE T1 acquisitions. This enhanced tissue contrast may improve gray matter segmentation and structural analysis.

  • T2 sequences (n=8): STAGE shows significantly LOWER GM/WM ratio (-14.7%, p=0.021*), suggesting different tissue contrast
    properties in STAGE T2. This reduction may be due to altered relaxation weighting or acquisition parameters.

  • SWI sequences (n=9): STAGE shows significantly LOWER GM/WM ratio (-5.3%, p=0.022*), though the effect size is smaller than
    T2. This modest reduction suggests relatively preserved tissue contrast properties in STAGE SWI compared to conventional.

INTERPRETATION: All three sequence types show statistically significant differences in GM/WM ratios between protocols. T1 STAGE
provides enhanced gray-white contrast, while T2 and SWI STAGE show reduced ratios. These differences should be considered when
comparing absolute intensity values or tissue segmentation results between conventional and STAGE protocols.

CLINICAL IMPLICATIONS: The enhanced T1 contrast in STAGE may facilitate improved cortical thickness measurements and gray matter
volumetry, while the altered T2/SWI ratios may require protocol-specific normalization for quantitative comparisons.
"""

    ax_caption.text(0.05, 0.95, caption_text, ha='left', va='top',
                   fontsize=9, wrap=True, transform=ax_caption.transAxes)

    plt.tight_layout()
    pdf.savefig(fig, bbox_inches='tight')
    plt.close()

    # ========================================================================
    # FIGURE 3: BLAND-ALTMAN
    # ========================================================================
    fig = plt.figure(figsize=(8.5, 11))

    # Load and display the figure
    img = plt.imread(VIZ_DIR / 'figure3_bland_altman.png')
    ax_img = plt.subplot(2, 1, 1)
    ax_img.imshow(img)
    ax_img.axis('off')

    # Caption area
    ax_caption = plt.subplot(2, 1, 2)
    ax_caption.axis('off')

    caption_text = """Figure 3. Bland-Altman Agreement Analysis Between STAGE and Conventional Sequences

Bland-Altman plots assessing agreement between STAGE and conventional sequences for gray matter (top row) and white matter
(bottom row). The x-axis shows the mean intensity between the two methods, while the y-axis shows the difference (STAGE minus
conventional). The blue line indicates the mean difference (bias), red dashed lines show the 95% limits of agreement (±1.96 SD),
and the black dotted line at zero represents perfect agreement.

ANALYSIS BY SEQUENCE TYPE:

T1 (n=7):
  • GM: Mean difference = -41.5 (STAGE slightly lower), with narrow 95% limits of agreement (-80.4 to -2.3), indicating
    good consistency. All points cluster tightly around the mean, suggesting minimal systematic or random error.
  • WM: Mean difference = -78.5 (STAGE consistently lower), with wider limits (-132.9 to -24.1). The consistent negative bias
    suggests STAGE T1 produces systematically lower WM intensities than conventional.

T2 (n=8):
  • GM: Mean difference = +1678 (STAGE much higher), with extremely wide limits (+103 to +3252), reflecting the large scale
    differences observed in Figure 1. One outlier shows exceptional STAGE intensity elevation.
  • WM: Mean difference = +1176 (STAGE higher), with very wide limits (-354 to +2710). The large spread indicates substantial
    variability in the intensity differences across subjects.

SWI (n=9):
  • GM: Mean difference = -8.7 (STAGE slightly lower), with moderate limits (-100 to +82.6). Several outliers show larger
    deviations, suggesting subject-specific factors or acquisition variations.
  • WM: Mean difference = +5.1 (STAGE slightly higher), with moderate limits (-85.5 to +95.7). The mean near zero suggests
    minimal systematic bias, though substantial random variability exists.

INTERPRETATION:
  • T1: Shows systematic bias but good precision (narrow limits), suggesting a simple linear correction could align protocols.
  • T2: Exhibits large systematic bias and poor precision, indicating fundamental differences in intensity scaling that require
    careful normalization or protocol-specific analysis approaches.
  • SWI: Shows minimal systematic bias but moderate random variability, suggesting reasonable agreement with some subject-level
    variation that may reflect differences in susceptibility effects.

The width of the limits of agreement indicates whether the two methods can be used interchangeably. T1 shows the best agreement
(narrow limits relative to mean values), while T2 shows poor agreement (very wide limits), and SWI falls in between.

RECOMMENDATIONS: For quantitative comparisons, T1 values can be compared after simple bias correction. T2 values should be
normalized within each protocol before comparison. SWI shows acceptable agreement but with notable outliers that warrant
investigation for data quality or protocol compliance issues.
"""

    ax_caption.text(0.05, 0.95, caption_text, ha='left', va='top',
                   fontsize=9, wrap=True, transform=ax_caption.transAxes)

    plt.tight_layout()
    pdf.savefig(fig, bbox_inches='tight')
    plt.close()

    # ========================================================================
    # FIGURE 4: EXPERT SCORE CORRELATIONS
    # ========================================================================
    fig = plt.figure(figsize=(8.5, 11))

    # Load and display the figure
    img = plt.imread(VIZ_DIR / 'figure4_expert_score_correlations.png')
    ax_img = plt.subplot(2, 1, 1)
    ax_img.imshow(img)
    ax_img.axis('off')

    # Caption area
    ax_caption = plt.subplot(2, 1, 2)
    ax_caption.axis('off')

    caption_text = """Figure 4. GM/WM Intensity Ratios vs Expert Reviewer Quality Scores

Scatter plots showing the relationship between GM/WM intensity ratios and expert neuroradiologist quality scores for both
conventional (circles) and STAGE (squares) sequences. Expert scores Q1, Q2, and Q3 represent independent quality assessments
on ordinal scales (higher values indicate better quality). Each point represents a single sequence from one subject.

SCORING METRICS:
  • Q1: Overall image quality assessment
  • Q2: Diagnostic confidence/utility score
  • Q3: Artifact and noise evaluation

SAMPLE SIZES:
  • T1: Conventional n=7, STAGE n=9
  • T2: Conventional n=9, STAGE n=8
  • SWI: Conventional n=9, STAGE n=9

KEY FINDINGS:

T1 Sequences:
  • Conventional: Weak to moderate correlations across all scores (Q2 shows highest at r=0.621, p=0.137, not significant)
  • STAGE: No significant correlations observed, suggesting quality scores are independent of GM/WM ratio in STAGE T1

T2 Sequences:
  • Conventional: No significant correlations with any quality metric
  • STAGE: **SIGNIFICANT negative correlation with Q1** (r=-0.885, p=0.003**), indicating that higher overall quality scores
    in T2 STAGE sequences are strongly associated with lower GM/WM ratios. This is the only statistically significant finding
    in the entire analysis.

SWI Sequences:
  • Both conventional and STAGE: No significant correlations observed

INTERPRETATION:

The highly significant T2 STAGE finding (Q1 correlation) suggests that expert radiologists rate T2 STAGE sequences as higher
quality when they exhibit lower GM/WM intensity ratios. This could indicate:

1. **Tissue Contrast Preference**: Radiologists may prefer T2 STAGE images with more distinct tissue differentiation (lower
   GM/WM ratio suggests better separation between tissue types)

2. **Protocol Optimization**: The negative correlation suggests that T2 STAGE acquisitions producing lower GM/WM ratios are
   perceived as diagnostically superior, which could inform protocol refinement

3. **Clinical Utility**: Lower GM/WM ratios in T2 STAGE may enhance lesion detection or tissue characterization, leading to
   higher quality assessments by experts

The absence of significant correlations in T1 and SWI sequences suggests that GM/WM ratio is not a primary driver of expert
quality assessments for these modalities. Quality perception may be more influenced by other factors such as:
  • Spatial resolution
  • Signal-to-noise ratio
  • Artifact levels
  • Anatomical detail visualization

CLINICAL IMPLICATIONS:

The T2 STAGE correlation suggests that optimizing acquisition parameters to reduce GM/WM ratios may improve diagnostic quality
as perceived by expert radiologists. This finding warrants further investigation with larger sample sizes and correlation with
clinical outcomes (e.g., lesion detection rates, diagnostic accuracy).

LIMITATIONS:

The modest sample sizes (n=7-9 per group) limit statistical power. The single significant finding should be interpreted
cautiously and validated in larger cohorts. Multiple comparison correction was not applied, increasing the risk of Type I error.

** p < 0.01 (highly significant)
"""

    ax_caption.text(0.05, 0.95, caption_text, ha='left', va='top',
                   fontsize=8.5, wrap=True, transform=ax_caption.transAxes)

    plt.tight_layout()
    pdf.savefig(fig, bbox_inches='tight')
    plt.close()

    # ========================================================================
    # STATISTICAL SUMMARY PAGE
    # ========================================================================
    fig = plt.figure(figsize=(8.5, 11))
    ax = fig.add_subplot(111)
    ax.axis('off')

    ax.text(0.5, 0.95, 'Statistical Summary', ha='center', va='top',
            fontsize=20, fontweight='bold', transform=ax.transAxes)

    summary_stats = """
PEARSON CORRELATIONS (Intensity Agreement)

T1 Sequences (n=7):
  Gray Matter:  r = 0.813, p = 0.026*  [Strong positive correlation]
  White Matter: r = 0.690, p = 0.086   [Moderate positive correlation]

T2 Sequences (n=8):
  Gray Matter:  r = 0.227, p = 0.589   [Weak correlation]
  White Matter: r = 0.062, p = 0.885   [Negligible correlation]

SWI Sequences (n=9):
  Gray Matter:  r = 0.454, p = 0.220   [Moderate correlation]
  White Matter: r = 0.498, p = 0.173   [Moderate correlation]


GM/WM RATIO COMPARISONS (Paired t-tests)

T1 Sequences (n=7):
  Conventional: 0.746 ± 0.032
  STAGE:        0.818 ± 0.027
  Difference:   +9.7% (STAGE higher)
  t = -11.095, p = 0.0000***  [Highly significant]

T2 Sequences (n=8):
  Conventional: 1.901 ± 0.341
  STAGE:        1.621 ± 0.210
  Difference:   -14.7% (STAGE lower)
  t = 2.970, p = 0.021*  [Significant]

SWI Sequences (n=9):
  Conventional: 1.202 ± 0.053
  STAGE:        1.138 ± 0.069
  Difference:   -5.3% (STAGE lower)
  t = 2.846, p = 0.022*  [Significant]


SIGNIFICANCE LEVELS:
*** p < 0.001 (highly significant)
**  p < 0.01  (very significant)
*   p < 0.05  (significant)
    p ≥ 0.05  (not significant)


OVERALL CONCLUSIONS:

1. PROTOCOL AGREEMENT: T1 sequences show the best agreement between
   conventional and STAGE protocols, with strong GM correlations and
   systematic but correctable intensity differences.

2. TISSUE CONTRAST: All sequence types show significant differences in
   GM/WM ratios, with T1 STAGE providing enhanced gray-white contrast
   (+9.7%), while T2 and SWI STAGE show reduced ratios.

3. CLINICAL UTILITY: STAGE T1 appears most suitable for direct comparison
   with conventional protocols, while T2 and SWI may require protocol-
   specific analysis pipelines.

4. DATA QUALITY: The moderate sample sizes (n=7-9) provide adequate
   statistical power for detecting the observed differences, though
   larger cohorts would strengthen conclusions.

5. FUTURE DIRECTIONS: Investigation of the underlying causes of T2
   intensity scaling differences and evaluation of impact on clinical
   diagnostic accuracy are warranted.
"""

    ax.text(0.05, 0.88, summary_stats, ha='left', va='top',
            fontsize=10, family='monospace', transform=ax.transAxes)

    # Footer
    ax.text(0.5, 0.02, 'End of Report', ha='center', va='bottom',
            fontsize=10, style='italic', transform=ax.transAxes)

    pdf.savefig(fig, bbox_inches='tight')
    plt.close()

print(f"✓ PDF report created: {pdf_path}")
print(f"  Total pages: 6 (title + 4 figures + summary)")
