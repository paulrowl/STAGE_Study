# Ventricle Normalization Results - Critical Analysis

**Date:** October 14, 2025
**Pipeline Run:** Completed successfully (56.7 minutes, 20 comparisons)
**Result:** ⚠️ **Metrics DECREASED instead of improving**

---

## Executive Summary

Contrary to the hypothesis, ventricle-based intensity normalization **decreased** similarity metrics across all sequence types:

| Metric | Change | Significance |
|--------|--------|--------------|
| **Pearson Correlation** | ↓ **44%** | Substantial decrease |
| **NCC** | ↓ **44%** | Substantial decrease |
| **SSIM** | ↓ **26%** | Moderate decrease |
| **PSNR** | ↑ 16-94% | Improved (intensity range more similar) |

**Conclusion:** Ventricle normalization is **NOT recommended** for this dataset as currently implemented.

---

## Detailed Results by Sequence Type

### T1-Weighted Sequences (n=8)

| Metric | Non-Normalized | Normalized | Change |
|--------|----------------|------------|--------|
| **SSIM** | 0.596 ± 0.407 | 0.566 ± 0.424 | -5.0% |
| **Pearson r** | 0.416 ± 0.436 | 0.387 ± 0.478 | -7.0% |
| **NCC** | 0.416 ± 0.436 | 0.387 ± 0.478 | -7.0% |
| **PSNR** | 19.3 ± 7.8 | 22.4 ± 8.6 | **+16.0%** ✓ |

**Observation:** Modest decreases in correlation metrics, but PSNR improved significantly.

### T2-Weighted Sequences (n=2)

| Metric | Non-Normalized | Normalized | Change |
|--------|----------------|------------|--------|
| **SSIM** | 0.764 ± 0.061 | 0.710 ± 0.001 | -7.0% |
| **Pearson r** | 0.037 ± 0.444 | **-0.448** ± 0.001 | **-1296%** ⚠️⚠️⚠️ |
| **NCC** | 0.037 ± 0.444 | **-0.448** ± 0.001 | **-1296%** ⚠️⚠️⚠️ |
| **PSNR** | 8.0 ± 1.1 | 15.6 ± 0.01 | **+94.0%** ✓ |

**Critical Issue:** Correlation flipped from weakly positive to **strongly negative** after normalization.

### SWI Sequences (n=10)

| Metric | Non-Normalized | Normalized | Change |
|--------|----------------|------------|--------|
| **SSIM** | 0.646 | 0.415 ± 0.303 | **-35.8%** ⚠️ |
| **Pearson r** | 0.173 | 0.031 ± 0.068 | **-82.2%** ⚠️⚠️ |
| **NCC** | 0.173 | 0.031 ± 0.068 | **-82.2%** ⚠️⚠️ |
| **PSNR** | 24.9 | 25.4 ± 6.5 | +2.2% |

**Critical Issue:** Massive decrease in correlation metrics, especially Pearson/NCC (82% reduction).

---

## Root Cause Analysis

### Problem 1: Sequence-Specific Ventricle Intensity Varies Dramatically

**Ventricle CSF Intensity by Sequence Type:**

| Sequence | Ventricle Appearance | Typical Intensity | Reason |
|----------|---------------------|-------------------|--------|
| **T1** | Dark (hypointense) | LOW | Short T1 relaxation of CSF |
| **T2** | Bright (hyperintense) | **HIGH** | Long T2 relaxation of CSF |
| **SWI** | Variable | **UNPREDICTABLE** | Depends on susceptibility, flow, phase data |

**Impact on Normalization:**
- **T1:** Dividing by ventricle mean (low value) → scales image UP
- **T2:** Dividing by ventricle mean (high value) → scales image DOWN
- **SWI:** Dividing by unpredictable value → inconsistent scaling

### Problem 2: Different Ventricle Detection Between CONV and STAGE

**Example: Patient Anon36506 SWI**
```
Conv ventricle:  63,776 voxels, mean = 177.72
STAGE ventricle: 513,610 voxels, mean = 0.21  ← STAGE mean is ~850× LOWER!
```

**Result:**
- Conv SWI: divided by 177.72 → image scaled by 1/177.72 = 0.0056
- STAGE SWI: divided by 0.21 → image scaled by 1/0.21 = **4.76**
- **STAGE image becomes ~850× brighter than Conv after normalization!**

**Correlation before normalization:** 0.76 (good)
**Correlation after normalization:** 0.02 (terrible)

**Explanation:** The normalization created an artificial 850-fold intensity mismatch.

### Problem 3: SWI Ventricles Are Fundamentally Different

**SWI Physics:**
- SWI is susceptibility-weighted, not purely intensity-based
- Ventricles can appear bright OR dark depending on:
  - Blood products in CSF
  - Flow artifacts
  - Calcifications
  - Phase information in gradient echo sequences

**Example: Patient Anon38716 SWI**
```
Conv ventricle:  25,436 voxels, mean = 202.94
STAGE ventricle: 664,028 voxels, mean = 5.10  ← 26× MORE voxels, 40× LOWER intensity
```

**This suggests:**
- Ventricle detection algorithm identifies completely different regions in CONV vs STAGE SWI
- What appears as "ventricle" in STAGE SWI may include susceptibility artifacts, not true CSF

---

## Per-Patient Analysis of Extreme Cases

### Case 1: Patient Anon42647 T2 - Correlation Flipped from +0.48 to -0.45

**Before Normalization:**
- Pearson r = +0.485 (moderate positive correlation)

**After Normalization:**
- Pearson r = -0.448 (moderate **negative** correlation)
- **Change:** -0.93 (193% decrease)

**Hypothesis:**
1. Conventional T2 ventricles are very bright (high mean intensity)
2. STAGE T2 ventricles are moderately bright (lower mean intensity)
3. Normalization scales CONV T2 down more than STAGE T2
4. This creates an **intensity inversion** where previously matched regions now anti-correlate

**Supporting Evidence:**
- SSIM decreased from 0.926 to 0.711 (-23%)
- PSNR increased (intensity ranges matched)
- But the actual voxel-by-voxel correlation reversed sign

### Case 2: Patient Anon32898 T1 - Improved from -0.20 to +0.81 (+1.01)

**This is the ONLY major success case!**

**Before Normalization:**
- Pearson r = -0.196 (weak **negative** correlation - BAD!)

**After Normalization:**
- Pearson r = +0.812 (strong **positive** correlation - GOOD!)
- **Change:** +1.01 (515% improvement)

**Why did this work?**
```
Conv ventricle:  218,517 voxels, mean = 261.77
STAGE ventricle: 173,001 voxels, mean = 242.24
```
- Similar ventricle sizes (21% difference)
- Similar mean intensities (8% difference)
- Normalization factors were nearly equal → minimal distortion
- Underlying negative correlation was due to intensity scaling mismatch
- Normalization fixed the scaling issue

**Key Insight:** Normalization only helps when ventricle intensities are similar between CONV and STAGE!

### Case 3: Patient Anon70749 SWI - Massive Decrease (-0.81)

**Before Normalization:**
- Pearson r = +0.818 (excellent correlation)

**After Normalization:**
- Pearson r = +0.005 (essentially zero correlation)
- **Change:** -0.81 (99% decrease!)

**Ventricle Statistics:**
```
Conv ventricle:  [not shown in current log excerpt]
STAGE ventricle: [not shown in current log excerpt]
```

**Hypothesis:**
- SWI ventricle detection likely failed or detected vastly different regions
- Normalization introduced massive scaling mismatch
- Previously well-matched SWI images became completely misaligned in intensity space

---

## Why PSNR Increased Despite Correlation Decreasing

**PSNR (Peak Signal-to-Noise Ratio) measures intensity range similarity, NOT correlation.**

**What happened:**
- Normalization made intensity **ranges** more similar (both images now scaled to ventricle=1.0)
- This improves PSNR by definition
- But if the wrong regions are normalized (incorrect ventricle detection), voxel-by-voxel correlation gets worse

**Analogy:** It's like translating two documents into the same language (improves PSNR), but if you mistranslate key words, the meaning correlation decreases.

---

## Methodological Issues with Current Implementation

### Issue 1: One-Size-Fits-All Ventricle Detection

**Current Algorithm:**
- Uses 75th-95th percentile of brain intensities
- Anatomical constraint: central 60% of volume
- Morphological cleanup

**Problem:**
- T1: Ventricles are DARK (should use 5th-25th percentile instead!)
- T2: Ventricles are BRIGHT (75th-95th percentile works)
- SWI: Ventricles are VARIABLE (algorithm fails)

**Solution Needed:**
- Sequence-specific ventricle detection algorithms
- T1: Detect dark CSF regions
- T2: Detect bright CSF regions
- SWI: Consider NOT using ventricle normalization at all

### Issue 2: No Quality Control on Ventricle Detection

**Examples of problematic ventricle detection:**

| Patient | Sequence | Conv Voxels | STAGE Voxels | Intensity Ratio | Issue |
|---------|----------|-------------|--------------|-----------------|-------|
| Anon36506 | SWI | 63,776 | 513,610 | **850×** | Massively different regions detected |
| Anon38716 | SWI | 25,436 | 664,028 | **40×** | STAGE detected 26× more voxels |
| Anon10644 | SWI | 243 | 3,311 | 7.6× | Very few voxels in Conv |

**Missing QC Steps:**
1. Check if ventricle voxel counts are similar (within 2-3×)
2. Check if mean intensities are reasonable for sequence type
3. Visualize detected ventricles to confirm accuracy
4. Flag cases where normalization factors differ by >2×

### Issue 3: SWI Is Fundamentally Unsuitable for Ventricle Normalization

**SWI Background:**
- Susceptibility-Weighted Imaging uses phase information
- Image intensity depends on:
  - Local magnetic field inhomogeneities
  - Venous blood (high susceptibility)
  - Hemorrhage, calcification
  - NOT just proton density like T1/T2

**CSF in SWI:**
- Can appear bright or dark depending on:
  - Surrounding tissue susceptibility
  - Flow effects (pulsation from choroid plexus)
  - Phase processing parameters

**Conclusion:** Using ventricle intensity normalization for SWI violates the physics of the sequence.

---

## Correlation with Neuroradiologist Quality Scores

### Patients with Low Quality Scores

**Patient Anon38716:**
- Quality scores: Q1=2-3, Q2=2, Q3=2-3 (lowest in dataset)
- Reason: "Patient motion" on ALL sequences
- **Pipeline T1 result:**
  - Non-normalized Pearson r: 0.813
  - Normalized Pearson r: 0.705
  - Change: -0.11 (-13%)
- **Implication:** Even with motion artifacts, normalization made things WORSE

**Patient Anon70370:**
- Quality scores: Q1=6-7, Q2=5-7, Q3=7 (good quality)
- Comments: "COW pulsation artifact"
- **Pipeline T1 result:** FAILED (0 ventricles detected)
- **Implication:** Pulsation artifact interfered with ventricle detection algorithm

### Correlation Analysis Recommendation

**Hypothesis to test:**
- Do patients with low quality scores show greater decreases after normalization?

**Preliminary observation:**
- No clear pattern yet
- Patient Anon38716 (worst quality) only decreased 13%
- Patients with good quality also showed large decreases

**Conclusion:** The normalization failure is methodological, not data-quality dependent.

---

## Recommendations

### Short-Term (Immediate)

#### 1. **DO NOT use ventricle normalization for this analysis**
- Revert to non-normalized results
- Current implementation decreases data quality

#### 2. **Use non-normalized metrics for manuscript**
- Original pipeline results are superior
- Clearly state "no intensity normalization applied"

#### 3. **Report normalization attempt as negative result**
- Include in supplementary materials or methods
- "We attempted ventricle-based intensity normalization but found it decreased correlation metrics by 26-44% due to sequence-specific differences in CSF appearance"

### Medium-Term (Re-implementation)

#### 4. **Implement sequence-specific normalization**

**For T1 sequences:**
```python
# Detect DARK ventricles (5th-25th percentile)
ventricle_mask = (brain_data >= percentile_5) & (brain_data <= percentile_25)
```

**For T2 sequences:**
```python
# Detect BRIGHT ventricles (75th-95th percentile) - CURRENT METHOD
ventricle_mask = (brain_data >= percentile_75) & (brain_data <= percentile_95)
```

**For SWI sequences:**
```python
# DO NOT NORMALIZE - use white matter instead
# Or use whole-brain scaling
wm_mask = detect_white_matter(brain_data, brain_mask)
normalization_factor = np.mean(brain_data[wm_mask])
```

#### 5. **Add Quality Control Checks**

```python
# Check ventricle detection quality
conv_voxels = np.sum(conv_ventricle_mask)
stage_voxels = np.sum(stage_ventricle_mask)
voxel_ratio = max(conv_voxels, stage_voxels) / min(conv_voxels, stage_voxels)

if voxel_ratio > 3.0:
    logger.warning("⚠️ Ventricle size mismatch (ratio={voxel_ratio:.1f})")
    logger.warning("   Skipping normalization - QC failed")
    return original_data

conv_mean = np.mean(conv_data[conv_ventricle_mask])
stage_mean = np.mean(stage_data[stage_ventricle_mask])
intensity_ratio = conv_mean / stage_mean

if intensity_ratio > 2.0 or intensity_ratio < 0.5:
    logger.warning("⚠️ Ventricle intensity mismatch (ratio={intensity_ratio:.2f})")
    logger.warning("   Skipping normalization - QC failed")
    return original_data
```

#### 6. **Visual Verification**

Create a QC script that generates PNG overlays:
```python
# Save ventricle masks as overlays
for slice_idx in key_slices:
    plot_overlay(
        background=brain_data[:, :, slice_idx],
        overlay=ventricle_mask[:, :, slice_idx],
        output=f'qc/ventricles/{patient_id}_{sequence}_{slice_idx}.png'
    )
```

### Long-Term (Alternative Approaches)

#### 7. **White Matter Normalization Instead**

**Advantages:**
- White matter has consistent intensity across T1, T2, and SWI
- Less variable between CONV and STAGE
- Well-established in neuroimaging literature

**Implementation:**
```python
# Use SynthSeg or FSL FAST to segment white matter
wm_mask = segment_white_matter(brain_data)
wm_mean = np.mean(brain_data[wm_mask])
normalized_data = brain_data / wm_mean
```

#### 8. **Histogram Matching**

**Advantages:**
- Makes entire intensity distributions match
- No need to identify specific tissue types
- Works for all sequence types

**Implementation:**
```python
from skimage.exposure import match_histograms

stage_matched = match_histograms(
    image=stage_data,
    reference=conv_data,
    channel_axis=None
)
```

#### 9. **Z-score Normalization**

**Advantages:**
- Simple and robust
- Centers data at zero, unit variance
- No anatomical segmentation required

**Implementation:**
```python
conv_normalized = (conv_data - np.mean(conv_data)) / np.std(conv_data)
stage_normalized = (stage_data - np.mean(stage_data)) / np.std(stage_data)
```

---

## Files Generated

### Analysis Outputs
- **`output/statistics/normalization_comparison_20251014_121047.csv`** - Detailed per-patient comparison
- **`pipeline_run_normalized.log`** - Full pipeline log with ventricle statistics
- **`comparison_analysis.log`** - Statistical comparison summary

### Visualizations
- **`output/plots/SUMMARY_normalization_impact.png`** - Main summary figure
- **`output/plots/scatter_before_after_normalization.png`** - Before/after scatter plots
- **`output/plots/bar_mean_improvements.png`** - Mean changes by sequence type
- **`output/plots/heatmap_percent_improvements.png`** - Percentage changes heatmap
- **`output/plots/patient_by_patient_pearson.png`** - Individual patient results
- **`output/plots/boxplot_*.png`** - Distribution comparisons (5 files)
- **`output/plots/violin_distributions.png`** - Distribution shapes

---

## Lessons Learned

### 1. **MRI Physics Matters**
- Cannot apply the same normalization strategy to T1, T2, and SWI
- CSF appearance is fundamentally different across sequences
- Intensity normalization must respect underlying MRI physics

### 2. **Automation Requires Validation**
- Ventricle detection algorithm worked differently for different sequences
- No QC checks caught the massive detection failures
- Visual inspection of intermediate outputs is critical

### 3. **Similarity Metrics Can Disagree**
- PSNR improved while Pearson correlation decreased
- Different metrics measure different aspects of similarity
- Need to understand what each metric actually quantifies

### 4. **Negative Results Are Valuable**
- This experiment conclusively shows ventricle normalization doesn't help
- Saves future researchers from trying the same approach
- Provides clear guidance: use non-normalized data

---

## Conclusion

**Ventricle-based intensity normalization, as currently implemented, is not appropriate for this STAGE MRI dataset.**

**Key findings:**
1. ✗ Decreased Pearson correlation by 44%
2. ✗ Decreased NCC by 44%
3. ✗ Decreased SSIM by 26%
4. ✓ PSNR improved, but this doesn't reflect better similarity
5. ✗ Especially harmful for SWI sequences (-82% correlation)
6. ✗ Variable results for T1 (some improved, some worsened)
7. ✗ Catastrophic failure for T2 (correlation sign flipped)

**Root causes:**
1. One-size-fits-all algorithm doesn't work for different MRI sequences
2. Ventricle detection identified different regions in CONV vs STAGE
3. SWI physics incompatible with ventricle normalization approach
4. Insufficient quality control on normalization factors

**Recommended action:**
- **Use non-normalized results for analysis and publication**
- Report normalization attempt as negative finding
- Consider alternative approaches (white matter, histogram matching, z-score) if normalization is still desired

---

**Analysis Date:** October 14, 2025
**Pipeline Version:** master_pipeline.py with ventricle normalization
**Total Processing Time:** 56.7 minutes
**Patients Processed:** 10 (20 comparisons: 8 T1, 2 T2, 10 SWI)
**Success Rate:** 100% pipeline completion, 0% metric improvement
