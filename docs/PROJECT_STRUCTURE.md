# STAGE Study - Project Structure

Last updated: 2025-10-17

## Root Directory

Clean root with only essential files:
- `README.md` - Main project documentation
- `config.yaml` - Project configuration
- `.gitignore` - Git ignore rules
- `*.sh` - Utility scripts (cleanup, monitoring)

## Directory Organization

### `/data/`
Raw DICOM data organized by subject and sequence type
```
data/
└── raw/
    └── organized/
        └── Anon*/
            ├── T1_conv/
            ├── T1_STAGE/
            ├── T2_conv/
            ├── T2_STAGE/
            ├── SWI_conv/
            └── SWI_STAGE/
```

### `/scripts/`
All Python analysis scripts
- DICOM classification and organization
- NIfTI conversion
- Brain extraction
- Tissue segmentation
- Statistical analysis
- Visualization generation
- Report creation

### `/output/`
All analysis outputs and results
```
output/
├── nifti/              # Converted NIfTI files
├── brain_masks/        # HD-BET extracted masks
├── statistics/         # CSV files with analysis results
├── visualizations/     # Generated figures and PDF reports
└── classifier_training/ # Ground truth data
```

### `/logs/`
Log files from pipeline runs
```
logs/
└── archive/           # Historical log files (38 files archived)
```

### `/docs/`
Project documentation
```
docs/
├── summaries/         # Analysis summary documents
│   ├── AUTOMATION_SUMMARY.md
│   ├── CLEANUP_SUMMARY.md
│   ├── DATA_STRUCTURE_AUDIT.md
│   ├── NEURORAD_SCORES_ANALYSIS.md
│   ├── PLOTTING_GUIDE.md
│   ├── PROBLEMATIC_PATIENTS.md
│   ├── RECOVERY_SUMMARY.md
│   ├── RESULTS_SUMMARY.md
│   ├── VENTRICLE_NORMALIZATION_RESULTS.md
│   └── VENTRICLE_NORMALIZATION_STATUS.md
├── GPU_ACCELERATION_GUIDE.md
├── IMPLEMENTATION_PLAN.md
├── neuro-rad-score-anon.numbers
└── validated_subjects_list.txt
```

## Data Flow

1. **Input**: Raw DICOM files → `data/raw/organized/`
2. **Processing**: 
   - Convert to NIfTI → `output/nifti/`
   - Extract brain → `output/brain_masks/`
   - Segment tissues → `output/statistics/`
3. **Analysis**: Statistical comparisons and visualizations
4. **Output**: Figures and PDF reports → `output/visualizations/`

## Key Files

### Statistics
- `gm_wm_tissue_stats_MERGED.csv` - All 240 sequences with tissue intensity stats
- `paired_comparisons_MERGED.csv` - 112 paired conv/STAGE comparisons
- `intensity_with_expert_scores.csv` - Merged with neuroradiologist scores

### Reports
- `STAGE_Study_Comprehensive_Report.pdf` - Main analysis report
- `subject_pairing_audit.csv` - Pairing status audit
- `PAIRING_AUDIT_SUMMARY.txt` - Detailed pairing analysis
- `RECOVERY_COMPLETE_SUMMARY.txt` - Missing data recovery summary

## Cleanup Performed

- Moved 38 log files to `logs/archive/`
- Moved 10 markdown summaries to `docs/summaries/`
- Moved reference files to `docs/`
- Organized project for clarity and maintainability
