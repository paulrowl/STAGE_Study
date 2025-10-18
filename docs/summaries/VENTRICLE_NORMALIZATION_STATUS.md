# Ventricle-Based Intensity Normalization - Status

**Date:** October 14, 2025
**Status:** Pipeline Running (50% Complete)

## Implementation Summary

### What Was Done

1. **Added Ventricle Identification Function** to `scripts/master_pipeline.py`:
   - Uses intensity-based approach (75th-95th percentile)
   - Applies anatomical constraints (central brain region)
   - Performs morphological operations for clean masks
   - Minimum 50 voxels required for reliable normalization

2. **Modified Metrics Calculation**:
   - Identifies ventricles in both conventional and STAGE images
   - Calculates mean ventricle intensity for each image
   - Normalizes by dividing entire image by ventricle mean intensity
   - Computes all similarity metrics on normalized data

3. **Backup System**:
   - Old results saved to `output/metrics_without_normalization/`
   - Old statistics saved to `output/statistics_without_normalization/`
   - Old log saved to `pipeline_run_without_normalization.log`

## Current Progress

**Pipeline Started:** 10:43 AM
**Current Time:** 11:14 AM (~31 minutes elapsed)
**Patients Processed:** 5 / 10 (50%)
**Metrics Calculated:** 8 comparisons

### Patients Completed:
1. ✓ **10644** - SWI_conv vs SWI_STAGE
2. ✓ **28689** - T1_conv vs T1_STAGE, SWI_conv vs SWI_STAGE
3. ✓ **32898** - T1_conv vs T1_STAGE, SWI_conv vs SWI_STAGE
4. ✓ **36506** - T1_conv vs T1_STAGE (in progress)
5. ⏳ **38716** - Starting...

### Patients Remaining:
- 42647
- 70370
- 70749
- Anon42647
- Anon60837

## Ventricle Detection Examples

| Patient | Sequence | Ventricle Voxels | Mean Intensity |
|---------|----------|------------------|----------------|
| 28689   | T1_conv  | 208,258          | 293.56         |
| 28689   | T1_STAGE | 169,252          | 259.07         |
| 32898   | T1_conv  | 218,517          | 261.77         |
| 32898   | T1_STAGE | 173,001          | 242.24         |

## Preliminary Results

### Latest T1 Comparison (Patient 36506):
- **SSIM:** 0.8274 (structural similarity)
- **NCC:** 0.7048 (normalized cross-correlation)
- **Pearson r:** 0.7048 (correlation)

### Expected Benefits:
- ✓ Consistent intensity scaling across patients
- ✓ Fair comparison between conventional and STAGE sequences
- ✓ Improved correlation metrics (intensity-dependent)
- ✓ Physiologically meaningful normalization

## Automated Analysis

**Scripts Running in Background:**
1. `master_pipeline.py` - Processing all 10 patients with ventricle normalization
2. `wait_and_compare.py` - Monitoring completion and will auto-generate comparison statistics

**Estimated Completion:** ~40 minutes from now (12:00 PM)

## Next Steps (Automated)

Once pipeline completes, the comparison script will automatically:
1. Load normalized and non-normalized metrics
2. Compare statistics by sequence type (T1, T2, SWI)
3. Calculate improvement percentages
4. Generate detailed comparison CSV
5. Display summary statistics

## Files Being Generated

### During Pipeline:
- `output/metrics/[PatientID]/*_metrics.csv` - Individual patient metrics
- `output/nifti/[PatientID]/*.nii.gz` - Converted NIfTI files
- `output/brain_masks/[PatientID]/*.nii.gz` - Brain extraction masks
- `output/registered/[PatientID]/*.nii.gz` - Co-registered images

### After Completion:
- `output/statistics/normalization_comparison_*.csv` - Detailed comparison
- `comparison_analysis.log` - Analysis log with summary statistics

## Monitoring

**Check progress anytime:**
```bash
# Quick check
find output/metrics -name "*_metrics.csv" | wc -l

# Detailed log view
tail -20 pipeline_run_normalized.log

# Comparison script status
tail comparison_analysis.log
```

## Technical Notes

### Ventricle Identification Algorithm:
1. Extract brain voxels using brain mask
2. Calculate intensity percentiles (75th-95th)
3. Create central region mask (middle 60% of volume)
4. Combine intensity and spatial constraints
5. Apply morphological operations (erosion → dilation)
6. Keep connected components ≥100 voxels

### Normalization Formula:
```
normalized_intensity = raw_intensity / mean_ventricle_intensity
```

This makes ventricle intensity = 1.0 in all normalized images, providing a common reference point across acquisitions.

---

**Last Updated:** October 14, 2025 11:14 AM
