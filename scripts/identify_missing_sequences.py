#!/usr/bin/env python3
"""
Identify missing sequences based on ground truth data

Compares expected pairs vs actual pairs to find missing sequences
"""

import pandas as pd
import re
from pathlib import Path

# Paths
BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
GROUND_TRUTH_CSV = '/Users/paul/Downloads/sequence_folder_mapping - sequence_folder_mapping.csv'
STATS_FILE = BASE_DIR / 'output' / 'statistics' / 'gm_wm_tissue_stats_20251017_025955.csv'
OUTPUT_FILE = BASE_DIR / 'output' / 'statistics' / 'missing_sequences_analysis.csv'

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

# Load ground truth
print("Loading ground truth data...")
df_gt = pd.read_csv(GROUND_TRUTH_CSV)

# Parse series numbers
SEQUENCES = ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']
for seq in SEQUENCES:
    df_gt[f'{seq}_series'] = df_gt[seq].apply(parse_series_number)

# Load processing results
print("Loading processing results...")
df_results = pd.read_csv(STATS_FILE)

# Create set of successfully processed sequences
processed = set()
for _, row in df_results.iterrows():
    processed.add((row['subject_id'], row['sequence']))

print(f"\nProcessed {len(processed)} sequence instances")

# Analyze missing sequences
missing_data = []

for idx, row in df_gt.iterrows():
    subject_id = row['rAccession']

    # Check each sequence
    for seq in SEQUENCES:
        series_col = f'{seq}_series'
        has_series_number = pd.notna(row[series_col])
        was_processed = (subject_id, seq) in processed

        status = "OK"
        reason = ""

        if has_series_number and not was_processed:
            status = "MISSING"
            reason = f"Series {row[series_col]} exists but not processed"
        elif not has_series_number:
            status = "N/A"
            reason = "No series number in ground truth"
        elif was_processed:
            status = "Processed"
            reason = "Successfully processed"

        missing_data.append({
            'subject_id': subject_id,
            'sequence': seq,
            'series_number': row[series_col] if has_series_number else "N/A",
            'status': status,
            'reason': reason
        })

# Create DataFrame
df_missing = pd.DataFrame(missing_data)

# Summary statistics
print("\n" + "="*80)
print("MISSING SEQUENCES SUMMARY")
print("="*80)

for seq in SEQUENCES:
    seq_data = df_missing[df_missing['sequence'] == seq]

    total_in_gt = (seq_data['status'] != 'N/A').sum()
    processed = (seq_data['status'] == 'Processed').sum()
    missing = (seq_data['status'] == 'MISSING').sum()

    print(f"\n{seq}:")
    print(f"  In ground truth: {total_in_gt}")
    print(f"  Successfully processed: {processed}")
    print(f"  Missing/Failed: {missing}")
    if missing > 0:
        print(f"  Missing subjects: {list(seq_data[seq_data['status']=='MISSING']['subject_id'].values)}")

# Analyze pairs
print("\n" + "="*80)
print("SEQUENCE PAIRS ANALYSIS")
print("="*80)

pair_analysis = []

for idx, row in df_gt.iterrows():
    subject_id = row['rAccession']

    for seq_type in ['T1', 'T2', 'SWI']:
        conv_seq = f"{seq_type}_conv"
        stage_seq = f"{seq_type}_STAGE"

        has_conv = pd.notna(row[f'{conv_seq}_series'])
        has_stage = pd.notna(row[f'{stage_seq}_series'])

        processed_conv = (subject_id, conv_seq) in processed
        processed_stage = (subject_id, stage_seq) in processed

        pair_status = "N/A"
        pair_reason = ""

        if has_conv and has_stage:
            if processed_conv and processed_stage:
                pair_status = "Complete Pair"
                pair_reason = "Both sequences processed"
            elif processed_conv and not processed_stage:
                pair_status = "Incomplete - Missing STAGE"
                pair_reason = f"Conv processed but STAGE failed"
            elif not processed_conv and processed_stage:
                pair_status = "Incomplete - Missing Conv"
                pair_reason = f"STAGE processed but Conv failed"
            else:
                pair_status = "Both Failed"
                pair_reason = "Both sequences failed to process"
        elif has_conv and not has_stage:
            pair_status = "Conv Only"
            pair_reason = "No STAGE sequence in ground truth"
        elif not has_conv and has_stage:
            pair_status = "STAGE Only"
            pair_reason = "No Conv sequence in ground truth"
        else:
            pair_status = "No Data"
            pair_reason = "Neither sequence in ground truth"

        pair_analysis.append({
            'subject_id': subject_id,
            'sequence_type': seq_type,
            'has_conv_in_gt': has_conv,
            'has_stage_in_gt': has_stage,
            'conv_processed': processed_conv if has_conv else False,
            'stage_processed': processed_stage if has_stage else False,
            'pair_status': pair_status,
            'reason': pair_reason
        })

df_pairs = pd.DataFrame(pair_analysis)

# Print pair summary
for seq_type in ['T1', 'T2', 'SWI']:
    seq_pairs = df_pairs[df_pairs['sequence_type'] == seq_type]

    complete = (seq_pairs['pair_status'] == 'Complete Pair').sum()
    incomplete = seq_pairs['pair_status'].str.contains('Incomplete').sum()

    print(f"\n{seq_type} Pairs:")
    print(f"  Complete pairs processed: {complete}")
    print(f"  Incomplete pairs: {incomplete}")

    if incomplete > 0:
        incomplete_subjects = seq_pairs[seq_pairs['pair_status'].str.contains('Incomplete')]['subject_id'].values
        print(f"  Subjects with incomplete pairs: {list(incomplete_subjects)}")

# Save results
df_missing.to_csv(OUTPUT_FILE, index=False)
print(f"\n\nSaved detailed analysis to: {OUTPUT_FILE}")

# Create summary spreadsheet for user
summary_file = BASE_DIR / 'output' / 'statistics' / 'missing_sequences_summary.csv'

# Filter to only show problematic cases
problematic = df_missing[df_missing['status'].isin(['MISSING', 'N/A'])]

# Pivot to wide format for easier reading
summary_data = []
for subject_id in df_gt['rAccession'].unique():
    subject_data = {'subject_id': subject_id}

    for seq in SEQUENCES:
        seq_info = df_missing[(df_missing['subject_id']==subject_id) &
                             (df_missing['sequence']==seq)].iloc[0]
        subject_data[seq] = seq_info['status']
        subject_data[f'{seq}_reason'] = seq_info['reason']

    # Add pair completeness
    subject_pairs = df_pairs[df_pairs['subject_id'] == subject_id]
    for seq_type in ['T1', 'T2', 'SWI']:
        pair_info = subject_pairs[subject_pairs['sequence_type'] == seq_type].iloc[0]
        subject_data[f'{seq_type}_pair_status'] = pair_info['pair_status']

    summary_data.append(subject_data)

df_summary = pd.DataFrame(summary_data)

# Save summary
df_summary.to_csv(summary_file, index=False)
print(f"Saved summary spreadsheet to: {summary_file}")

print("\n" + "="*80)
print("EXPECTED vs ACTUAL")
print("="*80)
print(f"\nUser expected:")
print(f"  T1 pairs: 42")
print(f"  T2 pairs: 30")
print(f"  SWI pairs: 39")

print(f"\nActual results:")
t1_complete = (df_pairs['sequence_type']=='T1') & (df_pairs['pair_status']=='Complete Pair')
t2_complete = (df_pairs['sequence_type']=='T2') & (df_pairs['pair_status']=='Complete Pair')
swi_complete = (df_pairs['sequence_type']=='SWI') & (df_pairs['pair_status']=='Complete Pair')

print(f"  T1 pairs: {t1_complete.sum()} (missing {42 - t1_complete.sum()})")
print(f"  T2 pairs: {t2_complete.sum()} (expected 30, got {t2_complete.sum() - 30} extra!)")
print(f"  SWI pairs: {swi_complete.sum()} (missing {39 - swi_complete.sum()})")

# Identify specific missing subjects
print("\n" + "="*80)
print("MISSING SEQUENCE DETAILS")
print("="*80)

# T1 pairs - should be 42 but got 33
print(f"\nT1 Pairs - Missing {42 - t1_complete.sum()} pairs:")
t1_incomplete = df_pairs[(df_pairs['sequence_type']=='T1') &
                         (df_pairs['pair_status']!='Complete Pair') &
                         (df_pairs['has_conv_in_gt']==True) &
                         (df_pairs['has_stage_in_gt']==True)]
for _, row in t1_incomplete.iterrows():
    print(f"  {row['subject_id']}: {row['pair_status']} - {row['reason']}")

# SWI pairs - should be 39 but got 38
print(f"\nSWI Pairs - Missing {39 - swi_complete.sum()} pair:")
swi_incomplete = df_pairs[(df_pairs['sequence_type']=='SWI') &
                          (df_pairs['pair_status']!='Complete Pair') &
                          (df_pairs['has_conv_in_gt']==True) &
                          (df_pairs['has_stage_in_gt']==True)]
for _, row in swi_incomplete.iterrows():
    print(f"  {row['subject_id']}: {row['pair_status']} - {row['reason']}")
