# GPU Acceleration Guide for STAGE Study Pipeline

This guide explains how to accelerate the HD-BET brain extraction pipeline using GPU resources.

## Current Performance Baseline

**CPU Performance (M2 Pro):**
- HD-BET time per sequence: ~1.3 minutes
- Total per subject (6 sequences): ~8-10 minutes
- Full dataset (43 subjects): ~7 hours

**Bottleneck:** HD-BET brain extraction (Step 4) accounts for ~80% of processing time.

---

## Option 1: Local M2 Pro GPU Acceleration

### System Capabilities

Your M2 Pro chip has:
- 10-core GPU (10 TFLOPS)
- 16-core Neural Engine (15.8 TOPS)
- Unified memory architecture
- PyTorch MPS (Metal Performance Shaders) support available

### Testing MPS Support

First, verify PyTorch MPS is working:

```bash
/Users/paul/miniforge3/envs/stage_analysis/bin/python3 -c "
import torch
print(f'MPS Available: {torch.backends.mps.is_available()}')
print(f'MPS Built: {torch.backends.mps.is_built()}')
"
```

**Status:** ✓ MPS is available and built (confirmed)

### Modifying HD-BET for M2 Pro GPU

HD-BET was designed for NVIDIA CUDA GPUs but may work with MPS. To test:

#### Step 1: Modify the reprocessing script

Edit `scripts/reprocess_with_ground_truth.py`, line 136-196, in the `run_hdbet()` function:

**Current code (line 177):**
```python
'-device', 'cpu',
```

**Change to:**
```python
'-device', '0',  # Try GPU device 0 (may work with MPS)
```

Or add a command-line argument:

**Add to argument parser (line 534-543):**
```python
parser.add_argument('--device', default='cpu', choices=['cpu', '0', 'mps'],
                   help='Device for HD-BET: cpu, 0 (GPU), or mps')
```

**Modify run_hdbet call (line 177):**
```python
'-device', device,  # Pass from function argument
```

**Update function signature (line 136):**
```python
def run_hdbet(subject_id: str, nifti_files: Dict[str, Path],
              device: str = 'cpu', dry_run: bool = False) -> Dict[str, Path]:
```

#### Step 2: Test on a single subject

```bash
cd /Users/paul/Projects/STAGE_Study
/Users/paul/miniforge3/envs/stage_analysis/bin/python3 scripts/reprocess_with_ground_truth.py \
  --subjects Anon42647 \
  --device 0
```

#### Step 3: Check for errors

If you see errors like "CUDA not available" or "device 0 not found", HD-BET doesn't support MPS natively.

### Workaround: Patch HD-BET for MPS

If HD-BET fails with MPS, you would need to patch the HD-BET source code to recognize 'mps' as a device:

```python
# In HD-BET's run_hd_bet.py (typically in site-packages/HD_BET/)
# Change device handling from:
device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

# To:
if torch.backends.mps.is_available():
    device = torch.device('mps')
elif torch.cuda.is_available():
    device = torch.device('cuda:0')
else:
    device = torch.device('cpu')
```

### Expected Speedup

- **Conservative estimate:** 2-3x faster (total time: ~2-3 hours instead of 7 hours)
- **Optimistic estimate:** 3-5x faster (total time: ~1.5-2 hours)

Note: M2 Pro GPU is significantly less powerful than dedicated NVIDIA datacenter GPUs (V100/A100).

---

## Option 2: Cloud GPU Services

### A. Google Colab (Easiest for Testing)

**Pros:**
- Free tier available with T4 GPU (16GB VRAM)
- Simple Jupyter notebook interface
- Pre-installed deep learning libraries

**Cons:**
- Need to upload ~40GB of DICOM data
- 12-hour session limit (free tier)
- May disconnect during long runs

**Setup Steps:**

1. Go to https://colab.research.google.com
2. Create new notebook
3. Enable GPU: Runtime → Change runtime type → GPU → T4

4. Upload data (one-time):
```python
from google.colab import drive
drive.mount('/content/drive')

# Or upload to Colab storage:
!mkdir -p /content/STAGE_Study/data/raw
# Use Colab's file upload widget or rsync
```

5. Install dependencies:
```python
!pip install pydicom nibabel dcm2niix HD-BET
```

6. Run processing:
```python
!python /content/scripts/reprocess_with_ground_truth.py --device 0
```

**Expected speedup:** 5-10x faster than M2 Pro CPU
**Cost:** Free or $10/month (Colab Pro)
**Estimated runtime:** ~1-1.5 hours for 43 subjects

---

### B. AWS EC2 with GPU

**Pros:**
- Powerful GPUs (V100, A100, H100)
- Full control over environment
- Can run indefinitely
- Good for repeated analyses

**Cons:**
- More complex setup
- Requires AWS account
- Costs accumulate while running

**Recommended Instance Types:**

| Instance | GPU | VRAM | vCPU | RAM | Cost/hr |
|----------|-----|------|------|-----|---------|
| p3.2xlarge | V100 | 16GB | 8 | 61GB | $3.06 |
| p3.8xlarge | 4x V100 | 64GB | 32 | 244GB | $12.24 |
| g4dn.xlarge | T4 | 16GB | 4 | 16GB | $0.526 |

**Recommendation:** Start with **g4dn.xlarge** (T4 GPU, cheapest option at $0.53/hr)

**Setup Steps:**

1. Launch EC2 instance with Deep Learning AMI:
   - Go to AWS Console → EC2 → Launch Instance
   - Search AMI: "Deep Learning AMI GPU PyTorch 2.0" (Ubuntu)
   - Instance type: g4dn.xlarge
   - Storage: 200GB EBS volume
   - Security group: Allow SSH (port 22)

2. Connect to instance:
```bash
ssh -i your-key.pem ubuntu@your-instance-ip
```

3. Transfer data to AWS (from your local machine):
```bash
# Option A: Direct transfer via scp
scp -i your-key.pem -r /Users/paul/Projects/STAGE_Study/data ubuntu@your-instance-ip:/home/ubuntu/

# Option B: Upload to S3 first (recommended for large data)
aws s3 sync /Users/paul/Projects/STAGE_Study/data s3://your-bucket/stage-study-data/
# Then download on EC2:
aws s3 sync s3://your-bucket/stage-study-data/ /home/ubuntu/STAGE_Study/data/
```

4. Set up environment:
```bash
cd /home/ubuntu
git clone https://github.com/MIC-DKFZ/HD-BET.git
pip install -e HD-BET/

# Install other dependencies
pip install pydicom nibabel dcm2niix
```

5. Run processing:
```bash
python scripts/reprocess_with_ground_truth.py --device 0 2>&1 | tee gpu_processing.log
```

6. Download results:
```bash
# From your local machine:
scp -i your-key.pem -r ubuntu@your-instance-ip:/home/ubuntu/STAGE_Study/output /Users/paul/Projects/STAGE_Study/
```

7. **IMPORTANT:** Terminate instance when done to stop charges!

**Expected speedup:** 8-15x faster than M2 Pro CPU
**Estimated cost:** ~$0.50-1.00 for full dataset (1-2 hours @ $0.53/hr)
**Estimated runtime:** ~30-60 minutes for 43 subjects

---

### C. Paperspace Gradient

**Pros:**
- Similar to Colab but better GPU options
- Persistent storage
- Good for neuroimaging workloads
- Can pause/resume

**Cons:**
- Requires account setup
- Costs more than Colab free tier

**Setup Steps:**

1. Sign up at https://gradient.run
2. Create new notebook
3. Select GPU: P4000 or P5000 (or free tier GPU if available)
4. Upload data or connect to cloud storage
5. Install dependencies and run

**GPU Options:**

| GPU | VRAM | Cost/hr |
|-----|------|---------|
| Free GPU | 8GB | Free (limited hours) |
| P4000 | 8GB | $0.51/hr |
| P5000 | 16GB | $0.78/hr |
| V100 | 16GB | $2.30/hr |

**Expected speedup:** 5-10x faster than M2 Pro CPU
**Cost:** $0.50-2/hour depending on GPU
**Estimated runtime:** ~45-90 minutes for 43 subjects

---

## Option 3: Multi-GPU Parallel Processing

For even faster processing, you can parallelize across multiple subjects:

### Parallel Processing Strategy

Since subjects are independent, you can process multiple subjects simultaneously:

**Single GPU with batching:**
```python
# Modify script to process subjects in parallel batches
from concurrent.futures import ThreadPoolExecutor

def process_batch(subject_ids):
    for subject_id in subject_ids:
        process_subject(subject_id, ...)

# Split subjects into batches
batch_size = 4
batches = [subjects[i:i+batch_size] for i in range(0, len(subjects), batch_size)]
```

**Multiple GPUs (AWS p3.8xlarge with 4x V100):**
```python
# Assign subjects to different GPUs
import os
subjects_per_gpu = len(subjects) // 4

for gpu_id in range(4):
    gpu_subjects = subjects[gpu_id * subjects_per_gpu:(gpu_id + 1) * subjects_per_gpu]
    os.environ['CUDA_VISIBLE_DEVICES'] = str(gpu_id)
    # Process in parallel
```

**Expected speedup:** 20-40x faster with 4x V100 GPUs
**Cost:** ~$12-15/hr for p3.8xlarge
**Estimated runtime:** ~10-15 minutes for 43 subjects

---

## Recommendation Summary

For your use case (43 subjects, one-time processing):

### Current Run:
✓ **Let it continue** - will complete overnight (~7 hours remaining)

### Future Batches or Re-runs:

1. **Quick test (free):** Try Google Colab free tier with T4 GPU
   - Expected time: 1-1.5 hours
   - Cost: Free
   - Best for: One-off processing

2. **Production pipeline:** AWS g4dn.xlarge with T4 GPU
   - Expected time: 30-60 minutes
   - Cost: ~$0.50-1.00 per run
   - Best for: Regular reprocessing, flexible scheduling

3. **Fast turnaround:** AWS p3.2xlarge with V100 GPU
   - Expected time: 20-30 minutes
   - Cost: ~$1.50-3.00 per run
   - Best for: When you need results urgently

4. **Ultra-fast (overkill):** AWS p3.8xlarge with 4x V100 GPUs
   - Expected time: 10-15 minutes
   - Cost: ~$3-6 per run
   - Best for: Large-scale batch processing (>100 subjects)

---

## Testing Workflow

Before committing to cloud resources, test locally:

1. Test M2 Pro MPS acceleration on 1 subject (~5 minutes)
2. If 2-3x speedup achieved, use locally
3. If MPS doesn't work or need faster, try Colab free tier
4. If regular processing needed, set up AWS workflow

---

## Notes

- HD-BET is the bottleneck (~80% of runtime)
- dcm2niix, tissue segmentation, and intensity extraction are already fast
- GPU acceleration only helps HD-BET step
- M2 Pro has capable GPU, but HD-BET may need patching for MPS support
- Cloud GPUs (especially V100/A100) will be 5-15x faster than M2 Pro CPU

---

## Future Optimizations

1. **Cache HD-BET results:** Once brain masks are generated, they don't need recomputation unless input changes
2. **Parallel subject processing:** Process multiple subjects simultaneously (limited by memory)
3. **GPU-accelerated registration:** If adding ANTs registration, consider GPU-accelerated alternatives (e.g., NiftyReg GPU, MONAI)
4. **Batch normalization:** Process all 43 subjects in one batch for efficiency

---

Last updated: 2025-10-16
Current status: Processing all 43 subjects on CPU (subject 2/43, ~7 hours remaining)
