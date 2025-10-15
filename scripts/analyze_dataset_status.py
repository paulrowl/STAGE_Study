#!/usr/bin/env python3
"""
Analyze Dataset Status
Compare organized patients, processed metrics, and neuro-rad scores
"""

import pandas as pd
from pathlib import Path

print("=" * 80)
print("STAGE STUDY - DATASET STATUS ANALYSIS")
print("=" * 80)

# 1. Load organization summary
org_summary = pd.read_csv('data/organization_summary_20251014_202628.csv')
print(f"\n1. ORGANIZED PATIENTS: {len(org_summary)}")

# 2. Find patients with incomplete datasets
print("\n" + "=" * 80)
print("PATIENTS WITH INCOMPLETE DATASETS")
print("=" * 80)

# Expected sequences
expected = ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']

incomplete_patients = []
for idx, row in org_summary.iterrows():
    patient = row['Patient']
    missing_seqs = [seq for seq in expected if row[seq] == 'MISSING']

    if len(missing_seqs) > 0:
        incomplete_patients.append({
            'Patient': patient,
            'Missing_Count': len(missing_seqs),
            'Missing_Sequences': ', '.join(missing_seqs),
            'Has_Sequences': ', '.join([seq for seq in expected if row[seq] != 'MISSING'])
        })

incomplete_df = pd.DataFrame(incomplete_patients)
if len(incomplete_df) > 0:
    incomplete_df = incomplete_df.sort_values('Missing_Count', ascending=False)

    print(f"\nTotal patients with incomplete data: {len(incomplete_df)}/{len(org_summary)}")
    print(f"Patients with complete data (all 6 sequences): {len(org_summary) - len(incomplete_df)}")

    # Save incomplete patients list
    incomplete_df.to_csv('output/statistics/incomplete_datasets.csv', index=False)
    print(f"\n✓ Saved: output/statistics/incomplete_datasets.csv")

    # Show summary
    print("\nBreakdown by missing sequences:")
    missing_counts = incomplete_df['Missing_Count'].value_counts().sort_index()
    for count, num_patients in missing_counts.items():
        print(f"  {count} sequences missing: {num_patients} patients")

    # Most common missing sequences
    print("\nMost commonly missing sequences:")
    all_missing = []
    for missing_str in incomplete_df['Missing_Sequences']:
        all_missing.extend(missing_str.split(', '))
    missing_series = pd.Series(all_missing)
    print(missing_series.value_counts().to_string())

# 3. Load neuro-rad scores
print("\n" + "=" * 80)
print("NEURO-RAD SCORE COMPARISON")
print("=" * 80)

neuro_rad = pd.read_csv('output/statistics/neuro-rad-score-anon.csv')
# Extract unique patient IDs (column name is blank, but it's the second column)
neuro_rad_patients = neuro_rad.iloc[:, 1].dropna().unique()
# Filter to only Anon IDs
neuro_rad_patients = [p for p in neuro_rad_patients if str(p).startswith('Anon')]

print(f"\nPatients in neuro-rad-score-anon.csv: {len(neuro_rad_patients)}")

# 4. Compare with processed metrics
metrics_dir = Path('output/metrics')
processed_patients = sorted([d.name for d in metrics_dir.iterdir() if d.is_dir()])
print(f"Patients with processed metrics: {len(processed_patients)}")

# 5. Find overlap
organized_patients = set(org_summary['Patient'].tolist())
neuro_rad_set = set(neuro_rad_patients)
processed_set = set(processed_patients)

# Neuro-rad patients that have been analyzed
analyzed = neuro_rad_set & processed_set
not_analyzed = neuro_rad_set - processed_set

# Neuro-rad patients that aren't even organized yet
not_organized = neuro_rad_set - organized_patients

print(f"\n" + "=" * 80)
print("OVERLAP ANALYSIS")
print("=" * 80)
print(f"\nNeuro-rad patients already analyzed: {len(analyzed)}/{len(neuro_rad_patients)}")
print(f"Neuro-rad patients NOT yet analyzed: {len(not_analyzed)}")
print(f"Neuro-rad patients NOT even organized: {len(not_organized)}")

if len(not_analyzed) > 0:
    print(f"\nNeuro-rad patients still needing analysis:")
    not_analyzed_sorted = sorted(list(not_analyzed))
    for patient in not_analyzed_sorted:
        # Check if organized but not processed
        if patient in organized_patients:
            # Check why not processed - missing sequences?
            org_row = org_summary[org_summary['Patient'] == patient].iloc[0]
            missing = [seq for seq in expected if org_row[seq] == 'MISSING']
            if len(missing) > 0:
                print(f"  {patient:15s} - ORGANIZED but incomplete (missing: {', '.join(missing)})")
            else:
                print(f"  {patient:15s} - ORGANIZED with all sequences (likely processing failed)")
        else:
            print(f"  {patient:15s} - NOT ORGANIZED (no raw data available)")

if len(not_organized) > 0:
    print(f"\nNeuro-rad patients with NO raw data:")
    for patient in sorted(list(not_organized)):
        print(f"  {patient}")

# 6. Organized but not in neuro-rad
organized_only = organized_patients - neuro_rad_set
print(f"\n" + "=" * 80)
print("ORGANIZED PATIENTS NOT IN NEURO-RAD SCORES")
print("=" * 80)
print(f"\nTotal: {len(organized_only)} patients")
if len(organized_only) > 0:
    print("\nThese patients have imaging data but no neuro-rad scores:")
    for patient in sorted(list(organized_only)):
        print(f"  {patient}")

# 7. Create comprehensive status table
print(f"\n" + "=" * 80)
print("COMPREHENSIVE STATUS TABLE")
print("=" * 80)

status_data = []
for patient in sorted(neuro_rad_set):
    status = {
        'Patient': patient,
        'In_NeuroRad': 'Yes',
        'Organized': 'Yes' if patient in organized_patients else 'No',
        'Processed': 'Yes' if patient in processed_set else 'No',
        'Status': ''
    }

    if patient in processed_set:
        status['Status'] = 'Complete'
    elif patient in organized_patients:
        # Check if incomplete
        org_row = org_summary[org_summary['Patient'] == patient].iloc[0]
        missing = [seq for seq in expected if org_row[seq] == 'MISSING']
        if len(missing) > 0:
            status['Status'] = f'Incomplete ({len(missing)} seq missing)'
        else:
            status['Status'] = 'Processing failed'
    else:
        status['Status'] = 'No raw data'

    status_data.append(status)

status_df = pd.DataFrame(status_data)
status_df.to_csv('output/statistics/neuro_rad_analysis_status.csv', index=False)
print(f"\n✓ Saved: output/statistics/neuro_rad_analysis_status.csv")

# Print summary
print("\nStatus Summary:")
print(status_df['Status'].value_counts().to_string())

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE!")
print("=" * 80)
print("\nGenerated files:")
print("  - output/statistics/incomplete_datasets.csv")
print("  - output/statistics/neuro_rad_analysis_status.csv")
