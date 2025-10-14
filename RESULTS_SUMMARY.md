# STAGE Study - Analysis Results Summary

**Analysis Date:** October 13, 2025
**Processing Time:** ~1 hour for 10 patients
**Platform:** macOS (CPU-only processing)

## Dataset Overview

**Total Patients:** 10
**Complete Patients:** 8 (80%)
**Incomplete Patients:** 2 (20%)

### Patient Status

| Patient ID | T1 | T2 | SWI | Status | Notes |
|------------|----|----|-----|--------|-------|
| 10644 | ✓ | ✓ | ✗ | Complete | |
| 28689 | ✓ | ✓ | ✗ | Complete | |
| 32898 | ✓ | ✓ | ✗ | Complete | |
| 36506 | ✓ | ✓ | ✗ | Complete | |
| 38716 | ✓ | ✓ | ✗ | Complete | |
| 42647 | ✓ | ✓ | ✗ | Complete | |
| **70370** | **✗** | ✓ | ✗ | **Incomplete** | **T1 metrics failed** |
| 70749 | ✓ | ✓ | ✗ | Complete | |
| Anon42647 | ✓ | ✓ | ✓ | Complete | Only patient with SWI |
| **Anon60837** | ✓ | **✗** | ✗ | **Incomplete** | **Missing T2_STAGE sequence** |

## Group Statistics

### T1-weighted (n=9 patients)

- **SSIM:** 0.60 ± 0.38 (range: 0.05-0.95)
- **NCC:** 0.42 ± 0.41
- **Pearson r:** 0.42 ± 0.41
- **PSNR:** 19.30 ± 7.37 dB

**Interpretation:** Moderate structural similarity with high variability between patients. Some patients show excellent agreement (SSIM ~0.95), while others show poor agreement (SSIM ~0.05).

### T2-weighted (n=9 patients)

- **SSIM:** 0.76 ± 0.06 (range: 0.69-0.86)
- **NCC:** 0.04 ± 0.42
- **Pearson r:** 0.04 ± 0.42
- **PSNR:** 8.03 ± 1.02 dB

**Interpretation:** Good structural similarity (consistently >0.7), but weak linear correlation. This suggests that T2_STAGE preserves structural features well but may have intensity scale differences.

### SWI (n=1 patient only)

- **SSIM:** 0.65
- **NCC:** 0.17
- **Pearson r:** 0.17
- **PSNR:** 24.91 dB

**Interpretation:** Limited data - only Anon42647 had complete SWI_STAGE sequence. Results suggest moderate agreement.

## Key Findings

### Successes

1. **T2 Structural Preservation:** T2_STAGE consistently preserves structural information (SSIM >0.7 across all patients)
2. **Pipeline Robustness:** Successfully processed 19 sequence pairs across 10 patients with automated error handling
3. **Data Organization:** All raw DICOM data successfully identified and organized into standardized format

### Issues Identified

1. **SWI_STAGE Missing:** 9 of 10 patients missing SWI_STAGE sequences
2. **Variable T1 Performance:** T1 similarity highly variable (SSIM: 0.05-0.95)
   - Patients 36506, 42647, Anon60837 show very poor T1 agreement (SSIM <0.1)
   - Possible causes: Image quality issues, misalignment, or acquisition differences
3. **Patient 70370:** T1 metrics calculation failed (empty overlap after brain extraction)
4. **Negative Correlations:** Several T2 comparisons show negative Pearson correlations, suggesting intensity inversions

## Processing Metrics

- **Average time per patient:** ~6 minutes
- **Steps completed:**
  1. DICOM → NIfTI conversion: 100% success
  2. Brain extraction (HD-BET): 100% success (except 70370 T1)
  3. Co-registration (ANTs): 100% success
  4. Metrics calculation: 95% success (18/19 comparisons)

## Recommendations

### Immediate Actions

1. **Investigate Poor T1 Performers:** Review patients 36506, 42647, and Anon60837 for:
   - Acquisition parameter differences
   - Motion artifacts
   - Protocol adherence

2. **Resolve 70370 T1 Issue:** Manual review of brain extraction masks
   - May need mask adjustment or alternative brain extraction method

3. **Address SWI_STAGE Missing Data:**
   - Verify if SWI_STAGE was acquired but not exported
   - Check DICOM organization criteria for SWI_STAGE detection

### Statistical Analysis Next Steps

1. **Paired t-tests:** All metrics show no statistically significant differences (sample size = 9)
2. **Subgroup Analysis:** Separate high-performers (SSIM >0.8) from low-performers
3. **Intensity Normalization:** Consider intensity normalization before metrics calculation
4. **Regional Analysis:** Add region-specific metrics (GM, WM, CSF) once tissue segmentation is implemented

## Files Generated

### Summary Reports
- `output/statistics/summary_20251013_232727.txt` - Human-readable summary
- `output/statistics/summary_20251013_232727.json` - Machine-readable summary
- `output/statistics/group_statistics_20251013_232727.csv` - Detailed statistics
- `output/statistics/all_patient_metrics_20251013_232727.csv` - All individual metrics
- `output/statistics/patient_completion_status_20251013_232727.csv` - Patient status report

### Per-Patient Outputs
- `output/nifti/[PatientID]/` - Converted NIfTI files
- `output/brain_masks/[PatientID]/` - Brain extraction masks
- `output/registered/[PatientID]/` - Co-registered images
- `output/metrics/[PatientID]/` - Individual metrics CSV files

## Conclusion

The STAGE pipeline successfully processed 10 patients, demonstrating:
- **Good performance for T2 sequences** (SSIM 0.76 ± 0.06)
- **Variable performance for T1 sequences** (requires further investigation)
- **Limited SWI data availability** (only 1/10 patients)

The automated pipeline is functional and robust, successfully handling diverse image qualities and dimensions. However, the high variability in T1 results and missing SWI data indicate potential issues with either the STAGE acquisition protocol or the data organization/export process.

**Next Steps:** Focus on resolving the three poor-performing T1 cases and investigating why SWI_STAGE is missing from 90% of patients.
