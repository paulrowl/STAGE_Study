# STAGE MRI Non-Inferiority Study - Complete Implementation Plan (Mac)

## Project Overview

**Objective:** Compare rapid STAGE MRI sequences to conventional sequences across three modalities (T1, T2, SWI) using quantitative imaging metrics and tissue-specific analysis.

**Data:** 50 stroke patients, each with 6 sequences:
- 3 Conventional: T1_conv, T2_conv, SWI_conv
- 3 STAGE: T1_STAGE, T2_STAGE, SWI_STAGE

**Total Comparisons:** 150 (50 patients × 3 sequence pairs)

**Platform:** macOS (Intel and Apple Silicon optimized)

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation Guide](#installation-guide)
3. [Pipeline Overview](#pipeline-overview)
4. [Detailed Implementation Steps](#detailed-implementation-steps)
5. [Timeline and Workflow](#timeline-and-workflow)
6. [Quality Control](#quality-control)
7. [Expected Outputs](#expected-outputs)
8. [Troubleshooting](#troubleshooting)
9. [Mac Quick Reference](#mac-quick-reference)

---

## System Requirements

### Hardware
- **Mac:** MacBook Pro, Mac Studio, or iMac (Intel or Apple Silicon)
- **RAM:** 16 GB minimum, 32 GB recommended
- **Storage:** 200 GB free space minimum
- **Processor:** Multi-core Intel i7+ or Apple M1/M2/M3

### Software
- **macOS:** 11.0 (Big Sur) or later
- **Python:** 3.9 (recommended for compatibility)
- **Terminal:** Default Terminal.app or iTerm2

### Expected Processing Times
| Mac Type | Time for 50 Patients |
|----------|---------------------|
| M3 Max | 10-12 hours |
| M2 Pro | 12-14 hours |
| M1 | 14-16 hours |
| Intel i9 | 15-18 hours |
| Intel i7 | 20-24 hours |

---

## Installation Guide

### Step 1: Install Homebrew (if not installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Step 2: Install Miniforge (Python Environment Manager)

**For Apple Silicon (M1/M2/M3):**
```bash
curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh"
bash Miniforge3-MacOSX-arm64.sh
```

**For Intel Mac:**
```bash
curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-x86_64.sh"
bash Miniforge3-MacOSX-x86_64.sh
```

Accept defaults and allow conda initialization. Then close and reopen Terminal.

### Step 3: Create Python 3.9 Environment

```bash
conda create -n stage_analysis python=3.9 -y
conda activate stage_analysis
```

### Step 4: Install Required Packages

```bash
# Core scientific packages
conda install -c conda-forge numpy pandas scipy matplotlib seaborn pyyaml cmake -y

# Neuroimaging packages
pip install nibabel pydicom scikit-image scikit-learn

# Brain extraction
pip install HD-BET

# Registration (ANTsPy - Apple Silicon note: installs from source, takes 5-10 min)
pip install antspyx

# ANTs command-line tools
conda install -c conda-forge ants -y

# Tissue segmentation
pip install SynthSeg

# DICOM conversion
brew install dcm2niix
```

### Step 5: Verify Installation

```bash
python << 'EOF'
import numpy, pandas, scipy
import nibabel, pydicom, ants
print("✓ All core packages installed successfully!")
print(f"NumPy: {numpy.__version__}")
print(f"ANTsPy: {ants.__version__}")
EOF
```

---

## Pipeline Overview

### Analysis Workflow

```
For each patient:
  For each sequence type (T1, T2, SWI):

    1. DICOM Organization
       ├─ Read DICOM headers (SeriesDescription)
       ├─ Identify sequence folders
       └─ Rename folders (T1_conv, T1_STAGE, etc.)

    2. DICOM → NIfTI Conversion
       └─ dcm2niix conversion

    3. Brain Extraction (HD-BET)
       ├─ Extract brain from conventional
       └─ Extract brain from STAGE

    4. Rigid Co-registration (ANTs)
       ├─ Register STAGE → Conventional
       └─ Apply transformation

    5. Tissue Segmentation (SynthSeg)
       ├─ Segment conventional → GM/WM/CSF masks
       └─ Apply masks to registered STAGE

    6. Signal Intensity Analysis
       ├─ Global metrics (SSIM, PSNR, NCC, MI)
       ├─ Tissue-specific metrics (SNR, CNR)
       ├─ Texture analysis (GLCM features)
       └─ Histogram similarity

    7. Statistical Analysis
       ├─ Non-inferiority testing
       ├─ Bland-Altman plots
       └─ Effect sizes
```

### Key Design Decisions

1. **Brain Extraction Tool:** HD-BET (deep learning, robust across sequences)
2. **Registration:** Rigid only (within-patient, same anatomy)
3. **Tissue Segmentation:** SynthSeg (works on ANY contrast without retraining)
4. **No Regional Masking:** Focus on tissue types (GM/WM/CSF), not brain regions
5. **Resampling:** Handled automatically by ANTs registration

---

## Detailed Implementation Steps

### Phase 0: DICOM Organization (Day 1)

#### Expected File Counts
| Sequence | SeriesDescription | Folder Name | Expected Images |
|----------|------------------|-------------|-----------------|
| Conv T1 | T1 MPRAGE SAG NON-SEL | T1_conv | 112 ± 10 |
| STAGE T1 | STAGE-T1W | T1_STAGE | 112 ± 10 |
| Conv T2 | T2 AX 3mm | T2_conv | 42 ± 5 |
| STAGE T2 | T2w_STAGE | T2_STAGE | 112 ± 10 |
| Conv SWI | SWI AX_SWI | SWI_conv | 88 ± 10 |
| STAGE SWI | SWI_STAGE | SWI_STAGE | 112 ± 10 |

#### Run DICOM Organizer

```bash
cd ~/Projects/STAGE_Study

# Dry run first (safe - no changes)
python scripts/dicom_folder_renamer.py data/raw --dry-run

# Review: dicom_renaming.log

# If satisfied, run live
python scripts/dicom_folder_renamer.py data/raw --live
```

**Expected output structure:**
```
data/raw/
├── Anon42647/
│   ├── T1_conv/      (112 DICOM files)
│   ├── T1_STAGE/     (112 DICOM files)
│   ├── T2_conv/      (42 DICOM files)
│   ├── T2_STAGE/     (112 DICOM files)
│   ├── SWI_conv/     (88 DICOM files)
│   └── SWI_STAGE/    (112 DICOM files)
└── Anon60837/
    └── ...
```

### Phase 1: Create Configuration (Day 1)

```bash
# Generate template config
python scripts/master_pipeline.py --create-config

# Edit config.yaml with your paths
nano config.yaml
```

**Key Mac-specific settings:**
```yaml
base_dir: '~/Projects/STAGE_Study/data/raw'
output_dir: '~/Projects/STAGE_Study/output'
device: 'cpu'  # Most Macs don't have NVIDIA GPUs
num_parallel: 4  # Adjust based on CPU cores
```

### Phase 2: Test with One Patient (Day 2)

```bash
# Dry run with one patient
python scripts/master_pipeline.py --config config.yaml --dry-run

# If successful, process one patient
# Edit config.yaml to include only one patient for testing
python scripts/master_pipeline.py --config config.yaml
```

**Check outputs:**
```bash
ls -lh output/nifti/
ls -lh output/brain_masks/
ls -lh output/registered/
ls -lh output/segmentations/
ls -lh output/metrics/
```

### Phase 3: Run Full Pipeline (Days 3-4)

```bash
# Use tmux to keep process running
tmux new -s stage_pipeline

# Prevent Mac from sleeping
caffeinate -i python scripts/master_pipeline.py --config config.yaml

# Detach from tmux: Ctrl+B, then D
# Reattach later: tmux attach -t stage_pipeline
```

**Monitor progress:**
```bash
# Check logs
tail -f output/logs/master_pipeline.log

# Check Activity Monitor
# Applications → Utilities → Activity Monitor
# Watch: Python process, CPU usage, Memory pressure
```

### Phase 4: Quality Control (Day 5)

```bash
# Check for failures
grep "ERROR" output/logs/master_pipeline.log

# Check completeness
python scripts/check_pipeline_completeness.py

# Visual verification
python scripts/dicom_viewer.py data/raw/organized
```

### Phase 5: Statistical Analysis (Days 6-7)

Results will be in:
```
output/statistics/
├── summary_statistics.csv       # Descriptive stats by sequence
├── non_inferiority_results.csv  # Primary outcomes
└── bland_altman_plots/          # Agreement visualizations
```

---

## Timeline and Workflow

### Day-by-Day Schedule (Mac-Optimized)

#### Day 1: Setup and Organization (3-4 hours)
- ☐ Install dependencies (1.5 hours)
- ☐ Run DICOM organizer (30 min)
- ☐ Create configuration (30 min)
- ☐ Verify setup (30 min)

#### Day 2: Test Run (2-3 hours)
- ☐ Process 1 patient completely
- ☐ Verify all outputs
- ☐ Adjust configuration if needed
- ☐ Test visualizations

#### Day 3-4: Full Processing (12-24 hours)
- ☐ Start overnight processing
- ☐ Monitor progress periodically
- ☐ Use `caffeinate` to prevent sleep
- ☐ Use `tmux` to keep session alive

#### Day 5: Quality Control (4-6 hours)
- ☐ Check for failed subjects
- ☐ Reprocess failures
- ☐ Visual inspection
- ☐ Verify data completeness

#### Day 6-7: Analysis and Reporting (6-8 hours)
- ☐ Statistical analysis
- ☐ Create visualizations
- ☐ Generate summary report
- ☐ Export for manuscript

---

## Quality Control

### Automated QC Checks

The pipeline automatically logs:
- ✅ Dimension changes during registration
- ✅ Interpolation effects on intensity
- ✅ SNR before and after processing
- ✅ Tissue segmentation quality
- ✅ Registration convergence

### Manual QC Checklist

For each patient, verify:
1. ☐ All 6 sequences present and identified
2. ☐ Brain extraction clean (no skull, full brain)
3. ☐ Registration alignment good (check edges)
4. ☐ Tissue segmentation reasonable (GM/WM/CSF)
5. ☐ No major artifacts in images

### QC Visualization

```bash
# Overview of all sequences
python scripts/dicom_viewer.py data/raw/organized

# Detailed slice navigation
python scripts/dicom_slice_viewer.py data/raw/organized

# Check registration results
python scripts/visualize_registration.py output/registered/
```

---

## Expected Outputs

### Directory Structure After Processing

```
output/
├── nifti/                        # DICOM → NIfTI conversions
│   ├── Anon42647/
│   │   ├── T1_conv.nii.gz
│   │   ├── T1_STAGE.nii.gz
│   │   └── ...
│   └── ...
│
├── brain_masks/                  # HD-BET results
│   ├── Anon42647/
│   │   ├── T1_conv_brain.nii.gz
│   │   ├── T1_conv_mask.nii.gz
│   │   └── ...
│   └── ...
│
├── registered/                   # ANTs co-registration
│   ├── Anon42647/
│   │   ├── T1_STAGE_registered.nii.gz
│   │   ├── T1_transform_0GenericAffine.mat
│   │   └── ...
│   └── ...
│
├── segmentations/                # SynthSeg tissue masks
│   ├── Anon42647/
│   │   ├── T1_conv_seg.nii.gz
│   │   ├── T1_conv_GM_mask.nii.gz
│   │   ├── T1_conv_WM_mask.nii.gz
│   │   ├── T1_conv_CSF_mask.nii.gz
│   │   └── ...
│   └── ...
│
├── metrics/                      # Quantitative results
│   ├── all_results_comprehensive.csv    # Main results file
│   ├── Anon42647_T1_metrics.json
│   └── ...
│
├── statistics/                   # Statistical analysis
│   ├── summary_statistics.csv
│   ├── non_inferiority_results.csv
│   ├── bland_altman_T1.png
│   ├── bland_altman_T2.png
│   └── bland_altman_SWI.png
│
├── report/                       # Summary documents
│   └── pipeline_summary_report.txt
│
└── logs/                         # Processing logs
    ├── master_pipeline.log
    ├── hd_bet.log
    └── registration.log
```

### Main Results File

`metrics/all_results_comprehensive.csv` contains ~70 columns including:

**Identifiers:**
- patient_id
- sequence_pair (T1, T2, or SWI)

**Global Similarity Metrics:**
- ssim_global
- psnr_global
- ncc_global
- mi_global

**Tissue-Specific Similarity (GM/WM/CSF):**
- ssim_gm, ssim_wm, ssim_csf
- psnr_gm, psnr_wm, psnr_csf
- ncc_gm, ncc_wm, ncc_csf
- mi_gm, mi_wm, mi_csf

**Signal Quality by Tissue:**
- snr_conv_gm, snr_conv_wm, snr_conv_csf
- snr_stage_gm, snr_stage_wm, snr_stage_csf
- cnr_gm_wm_conv, cnr_gm_wm_stage
- cnr_gm_csf_conv, cnr_gm_csf_stage

**Texture Features (GLCM - 6 features × 3 tissues × 2 sequences):**
- contrast_gm_conv, contrast_gm_stage
- dissimilarity_gm_conv, dissimilarity_gm_stage
- homogeneity_gm_conv, homogeneity_gm_stage
- energy_gm_conv, energy_gm_stage
- correlation_gm_conv, correlation_gm_stage
- asm_gm_conv, asm_gm_stage
- (Repeat for WM and CSF)

**Histogram Similarity:**
- histogram_correlation_gm
- histogram_chi_squared_gm
- (Repeat for WM and CSF)

**Edge Sharpness:**
- edge_sharpness_conv
- edge_sharpness_stage

**Processing Info:**
- original_dims_conv
- original_dims_stage
- registered_dims
- interpolation_method
- resampling_occurred

**Total:** 150 rows (50 patients × 3 sequence pairs) × ~70 metrics

---

## Troubleshooting

### Mac-Specific Issues

#### 1. ANTsPy Installation Fails (Apple Silicon)

**Problem:** `PackagesNotFoundError: antspyx`

**Solution:**
```bash
# Install via pip instead of conda
conda activate stage_analysis
pip install antspyx
# Takes 5-10 minutes to compile
```

#### 2. Xcode Command Line Tools Missing

**Problem:** `xcrun: error: invalid active developer path`

**Solution:**
```bash
xcode-select --install
# Follow prompts to install
```

#### 3. Mac Goes to Sleep During Processing

**Problem:** Pipeline stops when Mac sleeps

**Solution:**
```bash
# Use caffeinate
caffeinate -i python scripts/master_pipeline.py --config config.yaml
```

#### 4. Out of Memory Errors

**Problem:** `MemoryError` or system slowdown

**Solution:**
```bash
# Reduce parallel workers in config.yaml
num_parallel: 2  # Instead of 4

# Or process patients sequentially
num_parallel: 1
```

#### 5. HD-BET GPU Warning on Mac

**Problem:** `GPU device requested but not available`

**Solution:**
```yaml
# In config.yaml, set device to cpu
device: 'cpu'
```

Most Macs don't have NVIDIA GPUs. HD-BET runs fine on CPU.

#### 6. File Limit Exceeded

**Problem:** `OSError: [Errno 24] Too many open files`

**Solution:**
```bash
# Increase file limit
ulimit -n 4096

# Make permanent by adding to ~/.zshrc:
echo "ulimit -n 4096" >> ~/.zshrc
```

#### 7. SynthSeg Crashes

**Problem:** Segmentation fails silently

**Solution:**
```bash
# Check FreeSurfer setup
which mri_synthseg

# Or install standalone SynthSeg
pip install SynthSeg
```

#### 8. Permission Denied on External Drive

**Problem:** Can't write to external drive

**Solution:**
```bash
# Check drive permissions
ls -la /Volumes/YourDrive

# Grant full disk access:
# System Settings → Privacy & Security → Full Disk Access
# Add Terminal.app
```

---

## Mac Quick Reference

### Essential Terminal Commands

```bash
# Activate environment
conda activate stage_analysis

# Check free disk space
df -h

# Check memory usage
vm_stat

# Monitor CPU usage
top -o cpu

# Activity Monitor (GUI)
open -a "Activity Monitor"

# Kill process if needed
pkill -f python
```

### tmux Commands

```bash
# Create new session
tmux new -s stage_pipeline

# Detach from session
# Press: Ctrl+B, then D

# List sessions
tmux ls

# Reattach to session
tmux attach -t stage_pipeline

# Kill session
tmux kill-session -t stage_pipeline
```

### Progress Monitoring

```bash
# Watch log file live
tail -f output/logs/master_pipeline.log

# Count completed patients
ls output/metrics/*_metrics.json | wc -l

# Grep for errors
grep -i error output/logs/master_pipeline.log

# Check latest processed
ls -lt output/metrics/ | head -10
```

### Mac Keyboard Shortcuts

- **Cmd+T:** New Terminal tab
- **Cmd+N:** New Terminal window
- **Cmd+W:** Close tab
- **Cmd+Q:** Quit Terminal
- **Cmd+K:** Clear Terminal screen
- **Ctrl+C:** Stop running process
- **Ctrl+Z:** Pause process

### Useful Shell Aliases (Add to ~/.zshrc)

```bash
# Quick activation
alias stage='conda activate stage_analysis'

# Quick navigation
alias cdstage='cd ~/Projects/STAGE_Study'

# Progress check
alias stage-progress='ls output/metrics/*.json | wc -l'

# View latest log
alias stage-log='tail -f output/logs/master_pipeline.log'

# Run pipeline
alias stage-run='caffeinate -i python scripts/master_pipeline.py --config config.yaml'
```

### Expected Times and Resources

| Task | Time (M1/M2) | CPU Usage | RAM Usage |
|------|--------------|-----------|-----------|
| DICOM organization | 10-15 min | Low (10-20%) | <2 GB |
| Single patient (full) | 15-20 min | High (80-100%) | 4-8 GB |
| 50 patients (full) | 12-15 hours | High (80-100%) | 4-8 GB |
| Statistical analysis | 5-10 min | Medium (40-60%) | 2-4 GB |

**Disk Space:**
- Raw DICOM data: ~20 GB
- NIfTI files: ~5 GB
- Processed files: ~15 GB
- Total needed: ~50 GB (including intermediate files)

---

## Summary

This implementation plan provides a complete roadmap for running the STAGE MRI non-inferiority study on Mac. Key points:

✅ **Python 3.9** via Miniforge for maximum compatibility
✅ **CPU-only processing** (most Macs don't have NVIDIA GPUs)
✅ **Automated pipeline** from DICOM to final statistics
✅ **~12-15 hours** total processing time on Apple Silicon
✅ **Comprehensive QC** at every step
✅ **60+ metrics** per sequence comparison
✅ **Non-inferiority testing** with statistical rigor

**Key Mac optimizations:**
- Uses `caffeinate` to prevent sleep
- tmux for persistent sessions
- Parallel processing optimized for Mac CPUs
- Activity Monitor integration
- Native paths and conventions

The pipeline is ready to run! Follow the day-by-day timeline, use the QC checkpoints, and refer to the troubleshooting section as needed.

**Questions or issues?** Check the troubleshooting section or logs first.

---

**Document Version:** 1.0 (Mac-optimized)
**Last Updated:** October 2025
**Platform:** macOS 11.0+ (Intel and Apple Silicon)
