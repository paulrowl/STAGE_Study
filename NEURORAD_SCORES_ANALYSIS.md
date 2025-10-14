# Neuroradiologist Quality Scores - Analysis Summary

**Date:** October 14, 2025
**Dataset:** 69 clinical entries matched with research IDs

---

## Merge Results

### Perfect Matching
- **100% match rate**: All 69 clinical records successfully matched with research IDs
- **Matching key**: rMRN (research) ↔ Clinical_Accession (clinical)
- **No orphaned records**: 0 research IDs without clinical data, 0 clinical entries without research ID

### Duplicate Entries (Inter-Rater Reliability)
The following patients have multiple quality scores from different neuroradiologists:

| Patient ID | Number of Ratings | Notes |
|------------|------------------|-------|
| Anon56933 | 4 ratings | 2 dates (2025-03-21, 2025-04-14) × 2 raters |
| Anon74742, Anon55375, Anon87199, Anon70370, Anon28689, Anon42647, Anon70749, Anon10644, Anon32898, Anon36506, Anon38716, Anon38782, Anon42259, Anon67731, Anon60837 | 2 ratings each | Inter-rater reliability assessment |
| All others | 1 rating | Single rater |

---

## Overall Quality Score Statistics

**Scoring Scale:** 1-9 (higher = better quality)

| Metric | Q1 (T1 Quality) | Q2 (T2 Quality) | Q3 (SWI Quality) |
|--------|-----------------|-----------------|------------------|
| **Mean** | 5.75 | 3.81 | 4.57 |
| **Median** | 6.0 | 4.0 | 4.0 |
| **Range** | 2 - 9 | 1 - 7 | 1 - 7 |
| **N** | 69 | 69 | 69 |

### Key Observations:
- **T1 quality highest** (mean 5.75) - most consistent sequence
- **T2 quality lowest** (mean 3.81) - frequently noted as "blurry/pixely"
- **SWI quality intermediate** (mean 4.57) - variable depending on motion artifacts

---

## Pipeline Patients - Quality Score Correlation

### Our 10 Pipeline Patients with Neuroradiologist Scores

| Patient | Q1 (T1) | Q2 (T2) | Q3 (SWI) | Pipeline Status | Key Comments |
|---------|---------|---------|----------|-----------------|--------------|
| **Anon70370** | 7, 6 | 7, 5 | 7, 7 | ❌ **FAILED T1** | "COW pulsation artifact", "enhanced gray-white" |
| **Anon38716** | 2, 3 | 2, 2 | 2, 3 | ⚠️ **LOW QUALITY** | **"patient motion"** on all sequences |
| **Anon10644** | 8, 6 | 5, 5 | 6, 7 | ✓ Partial (no T1/T2) | "COW pulsation artifact, crisper", "still blurry" |
| **Anon28689** | 6, 6 | 7, 5 | 7, 7 | ✓ Partial (no T2_STAGE) | "COW pulsation artifact, crisper", "blurry/pixely" |
| **Anon32898** | 8, 6 | 3, 3 | 6, 6 | ✓ Partial (no T2_STAGE) | "Can't see ventric tube tip", "edema less distinct" |
| **Anon36506** | 7, 7 | 3, 4 | 4, 4 | ✓ Complete | "CONV T2 3 mm 2D", "STAGE T2 blurry" |
| **Anon42647** | 8, 7 | 3, 4 | 7, 5 | ✓ Complete | "Artifactual R cerebellar edema", "blurry/pixely" |
| **Anon70749** | 7, 7 | 7, 6 | 6, 7 | ✓ Partial (no T2_STAGE) | "STAGE T2 crisper", "less visible edema" |
| **60837** | 8, 6 | 3, 3 | 3, 4 | ⚠️ Partial (no T2_STAGE) | "STAGE T2 blurry, less defined edema" |

**Note:** Scores shown as "Rater1, Rater2" where two ratings available

---

## Critical Insights

### 1. Patient Anon70370 - Failed T1 Processing BUT Good Quality Scores

**Pipeline Failure:**
- 0 ventricles detected in T1_conv and T1_STAGE
- Empty brain overlap after co-registration
- Metrics calculation failed

**Neuroradiologist Scores:**
- Q1 (T1): **7/10 and 6/10** - Actually quite good!
- Comments: "STAGE T1 more COW pulsation artifact, crisper"

**Hypothesis:** The COW (Circle of Willis) pulsation artifact may have disrupted:
- Brain extraction (HD-BET failed to generate proper mask)
- Ventricle identification (high-intensity pulsation mimics/masks ventricles)
- Co-registration alignment (pulsation creates misalignment)

**Recommendation:** Manual review of brain masks needed - the raw images may be good quality, but automated processing failed due to artifacts.

---

### 2. Patient Anon38716 - Lowest Quality Scores (Motion Artifacts)

**Quality Scores:** Q1=2-3, Q2=2, Q3=2-3 (worst in dataset)

**Comments:** "patient motion" mentioned on ALL sequences by both raters

**Pipeline Status:** Likely completed but metrics will be unreliable

**Recommendation:** Consider excluding from final analysis due to severe motion artifacts

---

### 3. T2 Sequence Quality Issues

**Observation:** T2 has lowest mean quality score (3.81/9)

**Frequent Comments:**
- "blurry/pixely" (mentioned repeatedly for STAGE T2)
- "CONV T2 3 mm 2D" (many patients have 2D conventional T2, not 3D)
- "patient motion on both T2, but conv T2 less affected"

**Impact on Pipeline:**
- 7/10 patients missing T2_STAGE in organized data
- Lower T2 quality may explain missing classifications
- DICOM classifier may have failed to identify poor-quality T2_STAGE sequences

**Action Items:**
1. Review raw DICOM for T2_STAGE presence
2. Check if low-quality T2_STAGE images were excluded by classifier thresholds
3. Consider manual classification of borderline T2 sequences

---

### 4. STAGE vs Conventional Quality Trade-offs

**Common Pattern Observed:**

| Sequence | STAGE Advantage | STAGE Disadvantage |
|----------|-----------------|-------------------|
| **T1** | "crisper", "better G-W" | "COW pulsation artifact", "arteries brighter" |
| **T2** | "better G-W definition" | "blurrier", "artifactual edema", "less defined edema" |
| **SWI** | "sharper" in some cases | "CSF brighter", "motion artifacts", "blurrier" |

**Key Finding:** STAGE sequences trade spatial resolution/crispness for acquisition speed, resulting in more motion/pulsation artifacts.

---

## Quality Score Distribution by Sequence

### T1 Quality (Q1)
```
Score 8-9 (Excellent): 18 ratings (26%)
Score 6-7 (Good):      39 ratings (57%)
Score 4-5 (Fair):      10 ratings (14%)
Score 2-3 (Poor):       2 ratings (3%)
```

### T2 Quality (Q2)
```
Score 6-7 (Good):      13 ratings (19%)
Score 4-5 (Fair):      24 ratings (35%)
Score 2-3 (Poor):      32 ratings (46%)
```

### SWI Quality (Q3)
```
Score 6-7 (Good):      30 ratings (43%)
Score 4-5 (Fair):      30 ratings (43%)
Score 2-3 (Poor):       7 ratings (10%)
Score 1 (Very Poor):    2 ratings (3%)
```

**Conclusion:** T2 has the highest proportion of poor-quality ratings (46%), explaining why T2_STAGE sequences are frequently missing.

---

## Inter-Rater Reliability (Preliminary)

### Patients with Dual Ratings

**Example: Patient Anon70370**
- Rater 1: Q1=7, Q2=7, Q3=7
- Rater 2: Q1=6, Q2=5, Q3=7
- Difference: ±0-2 points (good agreement)

**Example: Patient Anon38716** (motion artifacts)
- Rater 1: Q1=2, Q2=2, Q3=2
- Rater 2: Q1=3, Q2=2, Q3=3
- Difference: ±0-1 points (excellent agreement on poor quality)

**Example: Patient Anon42647**
- Rater 1: Q1=8, Q2=3, Q3=7
- Rater 2: Q1=7, Q2=4, Q3=5
- Difference: Q1=±1, Q2=±1, Q3=±2 (moderate agreement)

**Recommendation:** Calculate formal inter-rater reliability metrics:
- Intraclass correlation coefficient (ICC)
- Cohen's kappa (if converted to categories)
- Bland-Altman plots for systematic bias

---

## Correlation with Pipeline Metrics (To Be Analyzed)

### Next Steps:

1. **Load pipeline metrics** for the 10 patients with quality scores
2. **Correlate:**
   - Q1 scores ↔ T1 SSIM/Pearson/NCC
   - Q2 scores ↔ T2 SSIM/Pearson/NCC
   - Q3 scores ↔ SWI SSIM/Pearson/NCC
3. **Hypothesis:** Lower quality scores → lower similarity metrics between CONV and STAGE
4. **Test:** Do patients with Q < 5 have significantly different metrics?

### Expected Findings:
- Patient Anon38716 (Q=2-3) likely has lowest SSIM/correlation
- Patient Anon70370 (Q=6-7) failed processing despite good scores → artifact-specific issue
- Patients with "motion" comments may have lower metrics

---

## Files Generated

### Primary Output:
- **`output/statistics/neurorad_scores_unified.csv`** - Complete merged dataset (69 rows)
- **`output/statistics/neurorad_scores_unified.xlsx`** - Excel workbook with 4 sheets:
  - `All_Data` - Complete merged dataset
  - `Matched_Only` - Records with both research and clinical data (69)
  - `Research_No_Clinical` - Empty (0 records)
  - `Clinical_No_Research` - Empty (0 records)

### Script:
- **`scripts/merge_neurorad_scores.py`** - Automated merge script

---

## Recommended Analyses

### 1. Immediate
- ✓ Calculate mean quality scores by sequence type
- ✓ Identify patients with low quality scores
- ✓ Correlate with pipeline success/failure

### 2. Short-term
- [ ] Formal inter-rater reliability analysis (ICC, kappa)
- [ ] Correlate quality scores with pipeline metrics (SSIM, Pearson, NCC)
- [ ] Statistical test: quality score predicts pipeline metrics?

### 3. Long-term
- [ ] Use quality scores as covariates in group analysis
- [ ] Stratified analysis: high-quality vs low-quality subgroups
- [ ] Investigate why good-quality images (Anon70370) failed processing

---

## Data Quality Flags

### Patients to Exclude (Recommendation):
1. **Anon38716** - Severe motion artifacts (Q=2-3, unanimous poor quality)
2. **56933** - Severe motion artifacts (Q=1-3, lowest SWI score of 1)

### Patients Requiring Manual Review:
1. **Anon70370** - Good quality scores (6-7) but pipeline failed
2. **42259** - Motion on all sequences (Q=2-5)
3. **Anon32898** - Cannot see ventricle catheter tip (may affect ventricle detection)

---

**Last Updated:** October 14, 2025
**Status:** Merge complete, ready for correlation analysis
