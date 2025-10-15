# STAGE Study Data Structure Audit

**Date**: October 15, 2025
**Status**: Analysis complete, awaiting pipeline completion for cleanup

## Current Structure

```
/Users/paul/Projects/STAGE_Study/
├── data/
│   ├── organized/          [7.4 GB]  ← REDUNDANT - Outdated
│   │   └── 43 patients (missing T1_STAGE, has PD_STAGE)
│   └── raw/
│       ├── Anon*/          [Unknown size] ← Original unorganized DICOMs
│       │   (43 patient folders)
│       └── organized/      [14 GB]   ← CANONICAL organized DICOMs
│           └── 43 patients (complete, properly classified)
│
└── output/
    ├── nifti/              [9.8 GB]  ← Converted NIfTI files (1,255 files)
    ├── brain_masks/        [629 MB]  ← HD-BET masks
    ├── registered/         [568 MB]  ← Co-registered images
    ├── metrics/            [~5 MB]   ← Analysis metrics (113+ CSV files)
    ├── statistics/         [~1 MB]   ← Statistical summaries
    ├── segmentations/      [empty]
    ├── logs/               [minimal]
    └── report/             [empty]
```

## Redundancies Identified

### 1. Duplicate Organized Directories ⚠️ CRITICAL
- **data/organized/** (7.4 GB): Outdated version from earlier organization
  - Missing T1_STAGE folders
  - Has PD_STAGE data (should be filtered)
  - Inconsistent structure
- **data/raw/organized/** (14 GB): Current canonical version
  - Complete sequence classification
  - Proper DICOM organization
  - Used by current pipeline

**Impact**: 7.4 GB wasted space with outdated data

### 2. Raw vs Organized DICOM Files ✅ NOT DUPLICATES
- **data/raw/Anon*** folders (~40 GB total): Original CD/DVD images
  - Contains: DICOM files + viewer software + DICOMDIR + autorun files
  - Example: Anon10644 is 1.1 GB (raw) vs 240 MB (organized)
  - Purpose: Original source data with all metadata
- **data/raw/organized/**: Extracted and organized DICOM files only
  - Filtered and classified by sequence type
  - No viewer software or extras

**Recommendation**: KEEP both - raw folders are source backups

### 3. Output NIfTI Files
- **1,255 NIfTI files** in output/nifti/
- Many intermediate files (multiple echoes, phase images)
- Question: Should we keep all intermediate conversions or only final results?

## Storage Summary

| Directory | Size | Status | Keep? |
|-----------|------|--------|-------|
| data/organized | 7.4 GB | Outdated duplicate | ❌ DELETE |
| data/raw/Anon* | ~51 GB | Original CD images | ✅ KEEP (backup source) |
| data/raw/organized | 14 GB | Canonical organized | ✅ KEEP (active use) |
| output/nifti | 9.8 GB | Converted files | ✅ KEEP |
| output/brain_masks | 629 MB | Generated masks | ✅ KEEP |
| output/registered | 568 MB | Final alignments | ✅ KEEP |
| output/metrics | ~5 MB | Analysis results | ✅ KEEP |

**Total storage**: ~86 GB
**Recoverable**: 7.4 GB (by deleting data/organized)

## Recommended Cleanup Actions

### Phase 1: Safe Deletions (Immediate)
```bash
# 1. Delete outdated organized directory (saves 7.4 GB)
rm -rf data/organized/

# 2. Update config.yaml to prevent confusion
# (Already done - points to data/raw/organized)

# 3. Clean up .DS_Store files
find . -name ".DS_Store" -delete
```

### Phase 2: Archive Original CDs (Optional, for long-term storage)
```bash
# data/raw/Anon* folders contain original CD images (51 GB)
# These are source backups with viewer software, DICOMDIR, etc.
# NOT duplicates - contain extra metadata
# Recommendation: Keep unless disk space critical

# If archiving to external storage:
# tar -czf STAGE_original_CDs_backup.tar.gz data/raw/Anon*
# (Would save 51 GB on main drive)
```

### Phase 3: Output Optimization (Optional)
```bash
# Review NIfTI files - keep only what's needed for analysis
# Current: All intermediate conversions
# Option: Keep only final registered images (saves ~9 GB)

# Empty unused directories
rmdir output/segmentations output/logs output/report
```

## Abnormal Patterns Found

1. **Permission inconsistencies**:
   - Most data/raw/ folders have `drwx------` (700)
   - data/raw/Anon60837 has `drwxr-xr-x@` (755)

2. **Missing T1_STAGE in data/organized/**:
   - 43/43 patients report T1_STAGE as missing
   - This is folder structure issue, not actual data issue
   - Resolved in data/raw/organized/

3. **PD sequences**:
   - Some patients have PD_conv folders
   - Should be filtered out (not part of analysis)

4. **Multi-echo SWI files**:
   - SWI_STAGE generates multiple NIfTI files per patient
   - Creates naming complexity (e.g., SWI_STAGE_e3d.nii.gz)

## Post-Cleanup Structure (Recommended)

```
/Users/paul/Projects/STAGE_Study/
├── data/
│   └── raw/
│       └── organized/      [14 GB]   ← ONLY organized DICOMs
│           └── 43 patients
│
└── output/
    ├── nifti/              [9.8 GB]  ← Keep all conversions
    ├── brain_masks/        [629 MB]
    ├── registered/         [568 MB]
    ├── metrics/            [~5 MB]
    └── statistics/         [~1 MB]
```

**Total space saved**: 7.4 GB minimum (14+ GB if raw folders are duplicates)

## Next Steps

1. ✅ Wait for pipeline completion
2. ⏳ Verify data/raw/Anon* vs data/raw/organized are duplicates
3. ⏳ Execute Phase 1 cleanup (delete data/organized/)
4. ⏳ Run comprehensive analysis with full dataset
5. ⏳ Consider Phase 2 cleanup after verifying duplicates

---

*Generated automatically during data structure audit*
