# STAGE Study - MRI Data Analysis Pipeline

## Overview

This pipeline classifies and organizes DICOM data from the STAGE MRI study into standardized folders for analysis. It extracts:
- **3 Conventional sequences**: T1_conv, T2_conv, SWI_conv
- **3 STAGE sequences**: T1_STAGE, T2_STAGE, SWI_STAGE

All data is filtered to include only **axial/transverse plane** images. PD_STAGE and phase images are excluded.

## Quick Start

### 1. Classify and organize DICOM files
```bash
cd ~/Projects/STAGE_Study
python scripts/dicom_sequence_classifier.py data/raw --live
```

This will:
- Scan all DICOM files in `data/raw/`
- Classify sequences based on DICOM metadata
- Organize into `data/raw/organized/` with 6 standardized folders per subject
- Exclude non-axial orientations, PD_STAGE, and phase data

### 2. Visually verify classification

**Option A: Overview viewer** (all 6 sequences side-by-side)
```bash
python scripts/dicom_viewer.py data/raw/organized
```

**Option B: Detailed slice viewer** (interactive navigation)
```bash
python scripts/dicom_slice_viewer.py data/raw/organized
```

Use arrow keys (←/→) to navigate slices, (↑/↓) to switch sequences.

### 3. Check organized output
```bash
ls -lh data/raw/organized/Anon*/
```

## Expected Directory Structure

### Before (raw):
```
data/raw/
├── Anon42647/
│   ├── 1000ACFF/
│   │   ├── 1000B604/  (DICOM files)
│   │   ├── 1000B69F/  (DICOM files)
│   │   └── ...
│   └── DICOMDIR
└── Anon60837/
    └── (similar structure)
```

### After (organized):
```
data/raw/organized/
├── Anon42647/
│   ├── T1_conv/      (170 files - T1 MPRAGE axial)
│   ├── T2_conv/      (210 files - T2 SPACE + FLAIR axial)
│   ├── SWI_conv/     (257 files - SWI magnitude + mIP)
│   ├── T1_STAGE/     (112 files - STAGE T1w)
│   ├── T2_STAGE/     (112 files - STAGE T2w derived)
│   └── SWI_STAGE/    (1008 files - QSM, R2*, MRA, etc.)
└── Anon60837/
    ├── T1_conv/      (200 files)
    ├── T2_conv/      (84 files)
    ├── SWI_conv/     (257 files)
    ├── T1_STAGE/     (112 files)
    └── SWI_STAGE/    (432 files)
    # Note: No T2_STAGE for this subject
```

## Classification Criteria

The classifier uses DICOM metadata to identify sequences:

### Conventional Sequences
- **T1_conv**: T1 MPRAGE axial (PixelBandwidth: 200-250, FlipAngle: 8-12°)
- **T2_conv**: T2 SPACE/FLAIR axial (includes MPR reconstructions, SeriesDesc: *tra*, *ax*)
- **SWI_conv**: SWI magnitude and mIP (TE: 18-22ms, FlipAngle: 13-17°)

### STAGE Sequences
- **T1_STAGE**: STAGE T1-weighted echo1 (PixelBandwidth: 200-350, FlipAngle: 25-29°)
- **T2_STAGE**: T2w_STAGE derived images (SeriesDesc: "T2w_STAGE", derived from PD_STAGE)
- **SWI_STAGE**: All other STAGE-derived contrasts (QSM, R2*, MRA, etc.)

### Filtering
- **Orientation**: Only axial/transverse plane images included
- **Excluded**: PD_STAGE sequences, phase images, sagittal/coronal reconstructions

## Visual Verification Tools

### Overview Viewer (`dicom_viewer.py`)
- Shows all 6 sequences in a 2×3 grid
- Displays middle slice from each sequence
- Navigate between subjects with buttons
- Quick verification of classification accuracy

### Slice Viewer (`dicom_slice_viewer.py`)
- Interactive single-sequence viewer
- Navigate slices with arrow keys (←/→)
- Switch sequences with arrow keys (↑/↓)
- Radio buttons for sequence selection
- Detailed metadata display (SeriesDescription, TE, TR, FlipAngle, ImageType)

## Troubleshooting

### If sequences are misclassified:
1. Use the slice viewer to identify which sequence looks wrong
2. Check the SeriesDescription and DICOM metadata
3. Edit `scripts/dicom_sequence_classifier.py` in the `sequence_signatures` dictionary
4. Adjust scoring weights in the `calculate_match_score()` method
5. Re-run classification

### Common issues:
- **Wrong contrast**: Sequence signature may need updated TE/TR ranges
- **Missing sequences**: Check if they're being excluded by orientation filter
- **Too few/many files**: Adjust `expected_slices` range in signature
- **JPEG decoding errors**: Install `pylibjpeg` and `pylibjpeg-libjpeg` packages

## Scripts

- **`dicom_sequence_classifier.py`**: Main classification and organization script
- **`dicom_viewer.py`**: Overview viewer for quick verification
- **`dicom_slice_viewer.py`**: Detailed interactive slice viewer
