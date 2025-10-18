#!/usr/bin/env python3
"""Create spreadsheet of missing sequences"""

import pandas as pd
import re
from pathlib import Path

# Paths
BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
GROUND_TRUTH_CSV = '/Users/paul/Downloads/sequence_folder_mapping - sequence_folder_mapping.csv'
STATS_FILE = BASE_DIR / 'output' / 'statistics' / 'gm_wm_tissue_stats_20251017_025955.csv'
OUTPUT_FILE = BASE_DIR / 'output' / 'statistics' / 'MISSING_SEQUENCES_REPORT.csv'

def parse_series_number(cell_value):
    """Extract series number from CSV cell"""
    if pd.isna(cell_value) or str(cell_value).strip() == '':
        return None
    cell_str = str(cell_value).strip()
    match = re.match(r'([A-F0-9]+)\s*\(#\d+\)', cell_str)
    if match:
        return match.group(1)
    match = re.match(r'\(#(\d+)\)', cell_str)
    if match:
        return match.group(1)
    if re.match(r'^[A-F0-9]+$', cell_str):
        return cell_str
    return None

# Load data
print("Loading data...")
df_gt = pd.read_csv(GROUND_TRUTH_CSV)
df_results = pd.read_csv(STATS_FILE)

# Parse series numbers
SEQUENCES = ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']
for seq in SEQUENCES:
    df_gt[f'{seq}_series'] = df_gt[seq].apply(parse_series_number)

# Create processed set
processed = set()
for _, row in df_results.iterrows():
    processed.add((row['subject_id'], row['sequence']))

# Build report
report_data = []

for _, row in df_gt.iterrows():
    subject_id = row['rAccession']

    subject_report = {
        'Subject_ID': subject_id,
    }

    # Check each sequence
    for seq in SEQUENCES:
        series_col = f'{seq}_series'
        has_series = pd.notna(row[series_col])
        was_processed = (subject_id, seq) in processed

        if has_series:
            if was_processed:
                subject_report[seq] = 'OK'
            else:
                subject_report[seq] = f'MISSING (series: {row[series_col]})'
        else:
            subject_report[seq] = 'N/A (not in ground truth)'

    # Check pairs
    for seq_type in ['T1', 'T2', 'SWI']:
        conv = f'{seq_type}_conv'
        stage = f'{seq_type}_STAGE'

        has_conv = pd.notna(row[f'{conv}_series'])
        has_stage = pd.notna(row[f'{stage}_series'])
        proc_conv = (subject_id, conv) in processed
        proc_stage = (subject_id, stage) in processed

        if has_conv and has_stage:
            if proc_conv and proc_stage:
                subject_report[f'{seq_type}_Pair_Status'] = 'Complete'
            else:
                missing_parts = []
                if not proc_conv:
                    missing_parts.append('conv')
                if not proc_stage:
                    missing_parts.append('STAGE')
                subject_report[f'{seq_type}_Pair_Status'] = f'INCOMPLETE - missing {", ".join(missing_parts)}'
        elif has_conv:
            subject_report[f'{seq_type}_Pair_Status'] = 'Conv only'
        elif has_stage:
            subject_report[f'{seq_type}_Pair_Status'] = 'STAGE only'
        else:
            subject_report[f'{seq_type}_Pair_Status'] = 'No data'

    report_data.append(subject_report)

# Create DataFrame
df_report = pd.DataFrame(report_data)

# Save
df_report.to_csv(OUTPUT_FILE, index=False)
print(f"\nSaved report to: {OUTPUT_FILE}")

# Print summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)

for seq in SEQUENCES:
    total_in_gt = df_report[seq].str.contains('N/A', na=False).sum()
    total_ok = df_report[seq].str.contains('^OK$', na=False, regex=True).sum()
    total_missing = df_report[seq].str.contains('MISSING', na=False).sum()

    print(f"\n{seq}:")
    print(f"  In ground truth: {43 - total_in_gt}")
    print(f"  Processed successfully: {total_ok}")
    print(f"  Missing/Failed: {total_missing}")

print("\n" + "="*80)
print("PAIR ANALYSIS")
print("="*80)

for seq_type in ['T1', 'T2', 'SWI']:
    col = f'{seq_type}_Pair_Status'
    complete = df_report[col].str.contains('^Complete$', na=False, regex=True).sum()
    incomplete = df_report[col].str.contains('INCOMPLETE', na=False).sum()

    print(f"\n{seq_type} Pairs:")
    print(f"  Complete: {complete}")
    print(f"  Incomplete: {incomplete}")

    if incomplete > 0:
        incomplete_subjects = df_report[df_report[col].str.contains('INCOMPLETE', na=False)]['Subject_ID'].values
        print(f"  Subjects: {list(incomplete_subjects)}")

print(f"\n\nExpected vs Actual:")
print(f"  T1 pairs: Expected 42, Got {df_report['T1_Pair_Status'].str.contains('^Complete$', regex=True).sum()}")
print(f"  T2 pairs: Expected 30, Got {df_report['T2_Pair_Status'].str.contains('^Complete$', regex=True).sum()}")
print(f"  SWI pairs: Expected 39, Got {df_report['SWI_Pair_Status'].str.contains('^Complete$', regex=True).sum()}")
