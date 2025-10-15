#!/usr/bin/env python3
"""
Analyze why patients were skipped during organization
"""

import os
from pathlib import Path

raw_dir = Path('data/raw')
organized_dir = Path('data/organized')

# Get all patient folders
all_patients = sorted([d.name for d in raw_dir.iterdir() if d.is_dir() and not d.name.startswith('.')])
organized_patients = sorted([d.name for d in organized_dir.iterdir() if d.is_dir()])

skipped_patients = [p for p in all_patients if p not in organized_patients]

print("=" * 70)
print("ANALYSIS OF SKIPPED PATIENTS")
print("=" * 70)
print(f"\nTotal raw patients: {len(all_patients)}")
print(f"Successfully organized: {len(organized_patients)}")
print(f"Skipped: {len(skipped_patients)}")

print("\n" + "=" * 70)
print("ANALYZING SKIPPED PATIENTS")
print("=" * 70)

has_dicomdir = []
has_1000_folders = []
has_other_folders = []
truly_empty = []

for patient in skipped_patients:
    patient_path = raw_dir / patient

    # Check for DICOMDIR
    dicomdir_exists = (patient_path / 'DICOMDIR').exists()

    # Check for 1000* folders
    folders_1000 = list(patient_path.glob('1000*'))

    # Check for ANY folders (except hidden)
    all_folders = [d for d in patient_path.iterdir() if d.is_dir() and not d.name.startswith('.')]

    # Check for 1001* or other numeric folders
    other_numeric = [d for d in all_folders if d.name[0].isdigit() and not d.name.startswith('1000')]

    status = []
    if dicomdir_exists:
        status.append(f"DICOMDIR")
    if folders_1000:
        status.append(f"{len(folders_1000)} folders with 1000* pattern")
    if other_numeric:
        status.append(f"{len(other_numeric)} folders with other numeric patterns ({other_numeric[0].name[:8]}...)")
    if not status:
        if all_folders:
            status.append(f"{len(all_folders)} non-numeric folders")
        else:
            status.append("EMPTY")

    status_str = ", ".join(status)
    print(f"  {patient}: {status_str}")

    if dicomdir_exists:
        has_dicomdir.append(patient)
    if folders_1000:
        has_1000_folders.append(patient)
    if other_numeric:
        has_other_folders.append(patient)
    if not all_folders:
        truly_empty.append(patient)

print("\n" + "=" * 70)
print("SUMMARY OF SKIPPED PATIENTS")
print("=" * 70)
print(f"Patients with DICOMDIR: {len(has_dicomdir)}")
print(f"Patients with 1000* folders: {len(has_1000_folders)}")
print(f"Patients with OTHER numeric folders: {len(has_other_folders)}")
print(f"Truly empty directories: {len(truly_empty)}")

print("\n" + "=" * 70)
print("RECOMMENDATION")
print("=" * 70)
if has_other_folders:
    print(f"\n{len(has_other_folders)} patients have DICOM data but use different folder patterns.")
    print("These could be recovered by updating the organizer script to handle")
    print("more flexible folder patterns (not just '1000*').")
    print("\nPatients that could be recovered:")
    for p in has_other_folders[:10]:
        print(f"  - {p}")
    if len(has_other_folders) > 10:
        print(f"  ... and {len(has_other_folders) - 10} more")
else:
    print("\nAll skipped patients appear to be truly empty or have incompatible data.")
