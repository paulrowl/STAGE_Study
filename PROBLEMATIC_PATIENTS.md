# Problematic Patients - Data Quality Issues

**Analysis Date:** October 14, 2025
**Pipeline:** Ventricle-based intensity normalization

---

## Summary

During the automated pipeline processing with ventricle normalization, several patients exhibited data quality issues resulting in incomplete processing.

---

## Patient Anon70370 ❌

**Status:** FAILED - T1 sequence metrics calculation

### Issue Details

**Sequence Affected:** T1_conv vs T1_STAGE

**Error Type:** Empty brain overlap after co-registration

**Log Evidence:**
```
2025-10-14 11:30:54,698 - WARNING - ⚠ Insufficient ventricle voxels detected (conv=0, stage=0)
2025-10-14 11:30:54,698 - WARNING - Proceeding without ventricle normalization
2025-10-14 11:30:54,710 - ERROR - ✗ Error calculating metrics: x and y must have length at least 2.
2025-10-14 11:30:54,723 - WARNING - ⚠ Metrics calculation failed
```

**Root Cause:**
- Both conventional and STAGE T1 images had **0 ventricle voxels detected**
- After brain extraction and co-registration, the overlap region was empty or had <2 voxels
- Cannot calculate correlation metrics on empty or single-voxel data

**Sequences Completed:**
- ❌ T1_conv vs T1_STAGE (FAILED)
- ✗ T2_conv vs T2_STAGE (MISSING - no T2_STAGE data)
- ✓ SWI_conv vs SWI_STAGE (SUCCESS - Conv: 51,786 voxels, STAGE: 788,131 voxels)

**Recommendation:**
- **Manual Review Required:** Check T1 brain extraction masks
- Possible Issues:
  1. Poor image quality preventing brain extraction
  2. Unusual head positioning
  3. Severe motion artifacts
  4. Incomplete acquisition
- **Action:** Review `output/brain_masks/Anon70370/T1_*_mask.nii.gz` manually

---

## Patient Anon60837 ⚠️

**Status:** INCOMPLETE - Missing T2_STAGE sequence

### Issue Details

**From Previous Analysis (RESULTS_SUMMARY.md):**
- Missing T2_STAGE sequence entirely
- Only T1 sequences present
- Likely incomplete data export from scanner

**Sequences Expected:**
- ✓ T1_conv vs T1_STAGE (SUCCESS)
- ❌ T2_conv vs T2_STAGE (MISSING DATA)
- Status: SWI sequences (to be determined in current run)

**Recommendation:**
- **Verify DICOM export:** Check if T2_STAGE was acquired but not exported
- **Scanner logs:** Review acquisition protocol for this patient
- **Action:** Contact imaging site to verify complete data acquisition

---

## Additional Notes from Previous Run

### Patient Anon70370 (Previous Analysis)
**From RESULTS_SUMMARY.md:**
- Previous run also had T1 metrics calculation failed
- Error: "empty overlap after brain extraction"
- **Consistent failure across multiple pipeline runs**
- This is a reproducible data quality issue, not a transient error

---

## Data Completeness Statistics

### Current Run (With Ventricle Normalization)

| Patient | T1 | T2 | SWI | Status | Issues |
|---------|----|----|-----|--------|--------|
| Anon10644 | ✗ | ✗ | ✓ | Partial | Missing T1/T2 from organized data |
| Anon28689 | ✓ | ✗ | ✓ | Partial | Missing T2_STAGE |
| Anon32898 | ✓ | ✗ | ✓ | Partial | Missing T2_STAGE |
| Anon36506 | ✓ | ✓ | ✓ | Complete | All sequences present |
| Anon38716 | ✓ | ✓ | ✓ | Complete | All sequences present |
| Anon42647 | ✓ | ✓ | ✓ | Complete | All sequences present |
| **Anon70370** | **❌** | **✗** | **✓** | **Failed** | **T1 metrics failed, T2 missing** |
| Anon70749 | ✓ | ✗ | ✓ | Partial | Missing T2_STAGE |
| Anon42647 | ✓ | ✓ | ✓ | Complete | All sequences present |
| Anon60837 | ✓ | ✗ | ? | Partial | Missing T2_STAGE |

### Summary Statistics

**Total Patients:** 10

**Complete (All 3 Sequences):** 3 patients (30%)
- Anon36506, Anon38716, Anon42647

**Partial (Some Sequences):** 6 patients (60%)
- Various T2_STAGE missing

**Failed Processing:** 1 patient (10%)
- Anon70370 (T1 metrics calculation failed)

---

## Common Issues Identified

### 1. Missing T2_STAGE Sequences (7/10 patients)

**Affected:** Anon10644, Anon28689, Anon32898, Anon70370, Anon70749, Anon60837, and potentially others

**Possible Causes:**
- Data export incomplete from scanner
- Different acquisition protocol for some patients
- T2_STAGE not acquired (protocol change mid-study?)
- File organization issue (misclassified by DICOM classifier?)

**Investigation Required:**
- Review raw DICOM data for presence of T2_STAGE
- Check DICOM headers for T2_STAGE classification criteria
- Verify acquisition protocol consistency

### 2. Brain Extraction Failure (Patient Anon70370, T1)

**Specific Issue:** No brain tissue detected after HD-BET

**Possible Causes:**
- Severe motion artifacts
- Incomplete FOV (field of view)
- Very low SNR preventing brain detection
- Unusual intensity distribution

**Action Items:**
- Visual inspection of T1_conv.nii.gz and T1_STAGE.nii.gz
- Check raw DICOM quality
- Consider manual brain mask creation
- Potentially exclude from analysis

### 3. Ventricle Detection Variability

**Observation:** Wide range of ventricle voxel counts across patients

**Examples:**
- Patient Anon70370 SWI_STAGE: 788,131 voxels (very high)
- Patient Anon70749 SWI_STAGE: 1,052 voxels (very low)
- Patient Anon70370 T1: 0 voxels (failed)

**Implication:** Some patients may have:
- Enlarged ventricles (expected in older patients)
- Small ventricles (younger patients)
- Poor image quality affecting detection

---

## Recommendations

### Immediate Actions

1. **Patient Anon70370 - Manual Review**
   - Inspect T1 images visually
   - Check brain extraction masks
   - Determine if data is salvageable
   - Consider exclusion if data quality is poor

2. **T2_STAGE Missing Data Investigation**
   - Review raw DICOM directories
   - Check if sequences were acquired but not classified
   - Update DICOM classifier if needed
   - Contact imaging site if truly missing

3. **Quality Control Protocol**
   - Add automated QC checks for brain extraction
   - Flag cases with <50 voxels brain overlap
   - Visual review of failed cases before exclusion

### Analysis Adjustments

1. **Document Incomplete Data**
   - Clearly note which patients have incomplete data
   - Adjust sample sizes in statistical analysis
   - Stratify results by data completeness

2. **Sensitivity Analysis**
   - Compare results with/without problematic patients
   - Check if excluding Anon70370 changes overall conclusions
   - Report both complete-case and available-case analyses

3. **Per-Sequence Analysis**
   - T1: n=8 patients (excluding Anon70370)
   - T2: n=3 patients (only complete data)
   - SWI: n=10 patients (full coverage expected)

---

## Expected Impact on Results

### Statistical Power

**Original Design:** 10 patients × 3 sequences = 30 comparisons

**Actual Available:**
- T1 comparisons: 8 (excluding Anon70370 failure)
- T2 comparisons: 3 (limited by missing T2_STAGE)
- SWI comparisons: ~10 (nearly complete)

**Power Loss:** T2 analysis severely underpowered (n=3)

### Recommendations for Publication

1. **Primary Analysis:** Focus on T1 and SWI (better coverage)
2. **Secondary Analysis:** T2 as preliminary/exploratory (n=3)
3. **Transparency:** Report all missing data in methods
4. **Future Work:** Emphasize need for complete T2_STAGE acquisition

---

## Files for Manual Review

### Patient Anon70370
```
output/nifti/Anon70370/T1_conv.nii.gz
output/nifti/Anon70370/T1_STAGE.nii.gz
output/brain_masks/Anon70370/T1_conv_mask.nii.gz
output/brain_masks/Anon70370/T1_STAGE_mask.nii.gz
output/brain_masks/Anon70370/T1_conv_brain.nii.gz
output/brain_masks/Anon70370/T1_STAGE_brain.nii.gz
```

**Use a viewer to inspect:**
```bash
# Using FSLeyes (if installed)
fsleyes output/nifti/Anon70370/T1_conv.nii.gz output/brain_masks/Anon70370/T1_conv_mask.nii.gz

# Or any NIfTI viewer
```

---

## Update Log

**2025-10-14 11:30:** Patient Anon70370 T1 metrics calculation failed
- 0 ventricles detected in both conventional and STAGE
- Empty brain overlap after co-registration
- Error: "x and y must have length at least 2"
- Pipeline continued with SWI sequences

**2025-10-14 11:45:** Pipeline continuing with remaining patients
- Anon42647 processing successfully (T1 complete with good ventricle detection)
- T2 processing started for Anon42647

---

**Last Updated:** October 14, 2025 11:47 AM
**Status:** Pipeline in progress (9/10 patients)
