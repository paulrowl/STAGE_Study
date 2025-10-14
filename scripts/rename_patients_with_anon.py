#!/usr/bin/env python3
"""
Rename all patients to use consistent "Anon" prefix naming convention.
Renames directories and updates all references in CSV files and documentation.
"""

import os
import shutil
import pandas as pd
from pathlib import Path
import re

# Define the mapping of old patient IDs to new IDs with Anon prefix
PATIENT_MAPPING = {
    '10644': 'Anon10644',
    '28689': 'Anon28689',
    '32898': 'Anon32898',
    '36506': 'Anon36506',
    '38716': 'Anon38716',
    '42647': 'Anon42647',
    '70370': 'Anon70370',
    '70749': 'Anon70749'
}

PROJECT_ROOT = Path('/Users/paul/Projects/STAGE_Study')

def rename_directories():
    """Rename patient directories across all output folders"""
    directories_to_check = [
        PROJECT_ROOT / 'data' / 'organized',
        PROJECT_ROOT / 'output' / 'metrics',
        PROJECT_ROOT / 'output' / 'nifti',
        PROJECT_ROOT / 'output' / 'brain_masks',
        PROJECT_ROOT / 'output' / 'registered',
        PROJECT_ROOT / 'output' / 'segmentations'
    ]

    print("=" * 70)
    print("RENAMING PATIENT DIRECTORIES")
    print("=" * 70)

    for base_dir in directories_to_check:
        if not base_dir.exists():
            print(f"\n⊘ Directory does not exist: {base_dir}")
            continue

        print(f"\n📁 Processing: {base_dir}")

        for old_id, new_id in PATIENT_MAPPING.items():
            old_path = base_dir / old_id
            new_path = base_dir / new_id

            if old_path.exists():
                if new_path.exists():
                    print(f"  ⚠️  Target already exists: {new_id}")
                else:
                    shutil.move(str(old_path), str(new_path))
                    print(f"  ✓ Renamed: {old_id} → {new_id}")
            else:
                print(f"  ⊘ Not found: {old_id}")

def update_csv_file(csv_path, columns_to_update):
    """Update patient IDs in a CSV file"""
    if not csv_path.exists():
        print(f"  ⊘ File not found: {csv_path.name}")
        return

    try:
        df = pd.read_csv(csv_path)
        updated = False

        for col in columns_to_update:
            if col in df.columns:
                for old_id, new_id in PATIENT_MAPPING.items():
                    # Update exact matches
                    mask = df[col] == old_id
                    if mask.any():
                        df.loc[mask, col] = new_id
                        updated = True

                    # Update comparison strings like "10644_T1_conv_vs_T1_STAGE"
                    mask = df[col].str.startswith(old_id + '_', na=False)
                    if mask.any():
                        df.loc[mask, col] = df.loc[mask, col].str.replace(
                            f'^{old_id}_', f'{new_id}_', regex=True
                        )
                        updated = True

        if updated:
            df.to_csv(csv_path, index=False)
            print(f"  ✓ Updated: {csv_path.name}")
        else:
            print(f"  → No changes needed: {csv_path.name}")

    except Exception as e:
        print(f"  ✗ Error updating {csv_path.name}: {e}")

def update_all_csv_files():
    """Update patient IDs in all CSV files"""
    print("\n" + "=" * 70)
    print("UPDATING CSV FILES")
    print("=" * 70)

    # Main statistics files
    stats_dir = PROJECT_ROOT / 'output' / 'statistics'
    main_csv_files = [
        (stats_dir / 'all_patients_metrics_normalized.csv', ['patient_id', 'comparison']),
        (stats_dir / 'all_patients_metrics_without_normalization.csv', ['patient_id', 'comparison']),
        (stats_dir / 'normalization_comparison_20251014_121047.csv', ['comparison']),
    ]

    print("\n📊 Main statistics files:")
    for csv_path, columns in main_csv_files:
        update_csv_file(csv_path, columns)

    # Individual patient metrics files
    print("\n📊 Individual patient metrics files:")
    metrics_dir = PROJECT_ROOT / 'output' / 'metrics'
    if metrics_dir.exists():
        for old_id, new_id in PATIENT_MAPPING.items():
            old_patient_dir = metrics_dir / old_id
            # Directory should already be renamed by now, so look in new location
            new_patient_dir = metrics_dir / new_id

            if new_patient_dir.exists():
                for csv_file in new_patient_dir.glob('*_metrics.csv'):
                    update_csv_file(csv_file, ['patient_id', 'comparison'])

def update_documentation():
    """Update patient IDs in documentation files"""
    print("\n" + "=" * 70)
    print("UPDATING DOCUMENTATION FILES")
    print("=" * 70)

    doc_files = [
        PROJECT_ROOT / 'PROBLEMATIC_PATIENTS.md',
        PROJECT_ROOT / 'NEURORAD_SCORES_ANALYSIS.md',
        PROJECT_ROOT / 'VENTRICLE_NORMALIZATION_RESULTS.md'
    ]

    for doc_path in doc_files:
        if not doc_path.exists():
            print(f"  ⊘ Not found: {doc_path.name}")
            continue

        try:
            with open(doc_path, 'r') as f:
                content = f.read()

            updated_content = content
            for old_id, new_id in PATIENT_MAPPING.items():
                # Replace patient IDs - need to be careful to match whole words
                # Replace "Patient 10644" or "patient 10644"
                updated_content = re.sub(
                    rf'\b[Pp]atient\s+{old_id}\b',
                    f'Patient {new_id}',
                    updated_content
                )
                # Replace bare patient IDs (with word boundaries)
                updated_content = re.sub(
                    rf'\b{old_id}\b',
                    new_id,
                    updated_content
                )

            if updated_content != content:
                with open(doc_path, 'w') as f:
                    f.write(updated_content)
                print(f"  ✓ Updated: {doc_path.name}")
            else:
                print(f"  → No changes needed: {doc_path.name}")

        except Exception as e:
            print(f"  ✗ Error updating {doc_path.name}: {e}")

def main():
    print("""
╔════════════════════════════════════════════════════════════════════╗
║          PATIENT RENAMING SCRIPT - Adding "Anon" Prefix           ║
╚════════════════════════════════════════════════════════════════════╝
    """)

    print("Patients to rename:")
    for old_id, new_id in PATIENT_MAPPING.items():
        print(f"  {old_id} → {new_id}")

    # Step 1: Rename directories
    rename_directories()

    # Step 2: Update CSV files
    update_all_csv_files()

    # Step 3: Update documentation
    update_documentation()

    print("\n" + "=" * 70)
    print("✓ RENAMING COMPLETE")
    print("=" * 70)
    print("\nAll patients now have consistent 'Anon' prefix naming convention.")
    print("Summary of changes:")
    print(f"  • {len(PATIENT_MAPPING)} patients renamed")
    print("  • Directories updated in data/organized/ and output/")
    print("  • CSV files updated with new patient IDs")
    print("  • Documentation files updated")

if __name__ == '__main__':
    main()
