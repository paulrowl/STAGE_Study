#!/usr/bin/env python3
"""
Merge research and clinical neuroradiology scoring data.

Matches rMRN (research sheet) with Clinical_Accession (clinical sheet)
to create a unified dataset.
"""

import pandas as pd
import numpy as np
from pathlib import Path

def load_and_merge_data(excel_path):
    """Load both sheets and merge on matching columns"""

    print("=" * 80)
    print("NEURORADIOLOGY SCORING DATA MERGE")
    print("=" * 80)
    print("")

    # Load both sheets
    print("Loading Excel file...")
    research_df = pd.read_excel(excel_path, sheet_name='research')
    clinical_df = pd.read_excel(excel_path, sheet_name='clinical')

    print(f"  - Research sheet: {len(research_df)} rows, {len(research_df.columns)} columns")
    print(f"  - Clinical sheet: {len(clinical_df)} rows, {len(clinical_df.columns)} columns")
    print("")

    # Show column names
    print("Research sheet columns:", list(research_df.columns))
    print("Clinical sheet columns:", list(clinical_df.columns))
    print("")

    # Merge on rMRN = Clinical_Accession
    print("Merging datasets on rMRN ↔ Clinical_Accession...")

    # Ensure both key columns are strings for matching
    research_df['rMRN'] = research_df['rMRN'].astype(str)
    clinical_df['Clinical_Accession'] = clinical_df['Clinical_Accession'].astype(str)

    # Perform left join to keep all research entries
    merged_df = pd.merge(
        research_df,
        clinical_df,
        left_on='rMRN',
        right_on='Clinical_Accession',
        how='outer',  # Keep all records from both sheets
        indicator=True  # Track merge source
    )

    print(f"  - Merged dataset: {len(merged_df)} rows")
    print("")

    # Analyze merge results
    print("=" * 80)
    print("MERGE STATISTICS")
    print("=" * 80)
    print("")

    merge_stats = merged_df['_merge'].value_counts()
    print("Match Statistics:")
    print(f"  - Both (matched): {merge_stats.get('both', 0)} records")
    print(f"  - Research only (no clinical data): {merge_stats.get('left_only', 0)} records")
    print(f"  - Clinical only (no research ID): {merge_stats.get('right_only', 0)} records")
    print("")

    # Show matched research IDs
    matched_df = merged_df[merged_df['_merge'] == 'both']
    print(f"Matched Research IDs (n={len(matched_df)}):")
    if len(matched_df) > 0:
        for _, row in matched_df[['rAccession', 'rMRN']].iterrows():
            print(f"  - {row['rAccession']}: {row['rMRN']}")
    print("")

    # Show unmatched research IDs
    research_only = merged_df[merged_df['_merge'] == 'left_only']
    print(f"Research IDs without clinical data (n={len(research_only)}):")
    if len(research_only) > 0:
        for _, row in research_only[['rAccession', 'rMRN']].iterrows():
            print(f"  - {row['rAccession']}: {row['rMRN']}")
    print("")

    # Show unmatched clinical entries
    clinical_only = merged_df[merged_df['_merge'] == 'right_only']
    print(f"Clinical entries without research ID (n={len(clinical_only)}):")
    if len(clinical_only) > 0:
        for _, row in clinical_only[['Clinical_MRN', 'Clinical_Accession']].head(10).iterrows():
            print(f"  - MRN {row['Clinical_MRN']}: Accession {row['Clinical_Accession']}")
        if len(clinical_only) > 10:
            print(f"  ... and {len(clinical_only) - 10} more")
    print("")

    # Quality score statistics (for matched records only)
    if len(matched_df) > 0:
        print("=" * 80)
        print("QUALITY SCORE STATISTICS (Matched Records Only)")
        print("=" * 80)
        print("")

        for score_col in ['Q1', 'Q2', 'Q3']:
            if score_col in matched_df.columns:
                scores = matched_df[score_col].dropna()
                if len(scores) > 0:
                    print(f"{score_col} Statistics:")
                    print(f"  - Mean: {scores.mean():.2f}")
                    print(f"  - Median: {scores.median():.1f}")
                    print(f"  - Range: {scores.min():.0f} - {scores.max():.0f}")
                    print(f"  - N: {len(scores)}")
                    print("")

    return merged_df

def save_unified_dataset(merged_df, output_dir='output/statistics'):
    """Save unified dataset in multiple formats"""

    print("=" * 80)
    print("SAVING UNIFIED DATASET")
    print("=" * 80)
    print("")

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Save as CSV (main format)
    csv_path = Path(output_dir) / 'neurorad_scores_unified.csv'
    merged_df.to_csv(csv_path, index=False)
    print(f"✓ CSV saved: {csv_path}")

    # Save as Excel with multiple sheets
    excel_path = Path(output_dir) / 'neurorad_scores_unified.xlsx'
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        # All data
        merged_df.to_excel(writer, sheet_name='All_Data', index=False)

        # Matched records only
        matched_df = merged_df[merged_df['_merge'] == 'both']
        if len(matched_df) > 0:
            matched_df.to_excel(writer, sheet_name='Matched_Only', index=False)

        # Unmatched records
        unmatched_research = merged_df[merged_df['_merge'] == 'left_only']
        if len(unmatched_research) > 0:
            unmatched_research.to_excel(writer, sheet_name='Research_No_Clinical', index=False)

        unmatched_clinical = merged_df[merged_df['_merge'] == 'right_only']
        if len(unmatched_clinical) > 0:
            unmatched_clinical.to_excel(writer, sheet_name='Clinical_No_Research', index=False)

    print(f"✓ Excel saved: {excel_path}")
    print("")
    print("Excel sheets:")
    print("  - All_Data: Complete merged dataset")
    print("  - Matched_Only: Records with both research and clinical data")
    print("  - Research_No_Clinical: Research IDs without clinical data")
    print("  - Clinical_No_Research: Clinical entries without research ID")
    print("")

def main():
    excel_path = '/Users/paul/Projects/STAGE_Study/stage-data-neurorad-scores.xlsx'

    # Load and merge
    merged_df = load_and_merge_data(excel_path)

    # Save
    save_unified_dataset(merged_df)

    print("=" * 80)
    print("MERGE COMPLETE")
    print("=" * 80)
    print("")
    print("Output files:")
    print("  - output/statistics/neurorad_scores_unified.csv")
    print("  - output/statistics/neurorad_scores_unified.xlsx")
    print("")

if __name__ == '__main__':
    main()
