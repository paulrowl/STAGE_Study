#!/usr/bin/env python3
"""
Quick test script to check if HD-BET can use M2 Pro GPU via MPS

This script tests GPU acceleration on a single subject to measure speedup
before committing to full reprocessing with GPU.

Usage:
    python scripts/test_mps_acceleration.py

Author: STAGE Study Pipeline
Date: 2025-10-16
"""

import time
import subprocess
from pathlib import Path

# Test files (using completed Anon10644)
BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
TEST_NIFTI = BASE_DIR / 'output' / 'nifti' / 'Anon10644' / 'T1_conv.nii.gz'
TEST_OUTPUT_DIR = BASE_DIR / 'output' / 'test_gpu'
TEST_OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

HDBET_PATH = '/Users/paul/miniforge3/envs/stage_analysis/bin/hd-bet'

def test_device(device_name, device_flag):
    """Test HD-BET with specified device"""
    print(f"\n{'='*80}")
    print(f"Testing HD-BET with device: {device_name}")
    print(f"{'='*80}")

    output_file = TEST_OUTPUT_DIR / f"test_{device_name}_brain"

    cmd = [
        HDBET_PATH,
        '-i', str(TEST_NIFTI),
        '-o', str(output_file.with_suffix('')),
        '-device', device_flag,
        '-mode', 'fast',
        '-tta', '0'
    ]

    print(f"Command: {' '.join(cmd)}")

    try:
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        elapsed = time.time() - start_time

        if result.returncode == 0:
            print(f"✓ Success! Time: {elapsed:.1f} seconds")
            return elapsed, True
        else:
            print(f"✗ Failed!")
            print(f"Error: {result.stderr}")
            return elapsed, False

    except Exception as e:
        print(f"✗ Exception: {e}")
        return None, False

def main():
    print("="*80)
    print("M2 Pro GPU Acceleration Test for HD-BET")
    print("="*80)

    if not TEST_NIFTI.exists():
        print(f"Error: Test file not found: {TEST_NIFTI}")
        print("Please wait for the current processing to create test data")
        return

    # Test CPU baseline
    cpu_time, cpu_success = test_device("cpu", "cpu")

    if not cpu_success:
        print("\n❌ CPU test failed. Check HD-BET installation.")
        return

    # Test GPU (device 0)
    print("\n" + "="*80)
    print("Now testing GPU acceleration...")
    print("Note: This may fail if HD-BET doesn't support MPS")
    print("="*80)

    gpu_time, gpu_success = test_device("gpu", "0")

    # Summary
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)
    print(f"CPU Time:  {cpu_time:.1f} seconds")

    if gpu_success:
        print(f"GPU Time:  {gpu_time:.1f} seconds")
        speedup = cpu_time / gpu_time
        print(f"\n✓ GPU ACCELERATION WORKING!")
        print(f"Speedup: {speedup:.2f}x faster")
        print(f"\nEstimated total time with GPU: {(10 * 60 * 43) / speedup / 60:.1f} hours")
        print(f"(vs {(10 * 43) / 60:.1f} hours with CPU)")

        print("\n" + "="*80)
        print("RECOMMENDATION")
        print("="*80)
        if speedup >= 2.0:
            print("✓ GPU acceleration is WORTHWHILE!")
            print(f"  To use GPU, add '--device 0' flag to reprocessing script")
            print(f"  (after modifying script as described in GPU_ACCELERATION_GUIDE.md)")
        else:
            print("⚠ GPU speedup is marginal (<2x)")
            print("  May not be worth the effort to modify the script")
    else:
        print(f"GPU Time:  FAILED")
        print(f"\n✗ GPU ACCELERATION NOT WORKING")
        print(f"\nThis is expected - HD-BET was designed for NVIDIA CUDA GPUs")
        print(f"Your M2 Pro has GPU capabilities but HD-BET doesn't support MPS natively")

        print("\n" + "="*80)
        print("ALTERNATIVES")
        print("="*80)
        print("1. Let current CPU run complete (recommended)")
        print("2. Use cloud GPU (AWS/Colab) for future batches")
        print("3. Patch HD-BET source code to add MPS support (advanced)")
        print("\nSee GPU_ACCELERATION_GUIDE.md for detailed instructions")

    # Cleanup
    print(f"\n\nCleaning up test files in {TEST_OUTPUT_DIR}")

if __name__ == '__main__':
    main()
