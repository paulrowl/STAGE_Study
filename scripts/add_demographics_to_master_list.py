#!/usr/bin/env python3
"""
Add age and sex from Nuance-export-44pts to the master patient list
"""
import pandas as pd

# Read the patient master list
master_df = pd.read_csv('/Users/paul/Projects/STAGE_Study/output/statistics/PATIENT_MASTER_LIST.csv')

# Drop age and sex columns if they already exist (in case script is re-run)
master_df = master_df.drop(columns=['age', 'sex'], errors='ignore')

# Read the Nuance export file
nuance_df = pd.read_csv('/Users/paul/Projects/STAGE_Study/output/statistics/Nuance-export-44pts.csv')

# Select relevant columns from Nuance file
nuance_demographics = nuance_df[['Accession Number', 'Patient Sex', 'Patient Age']].copy()

# Rename columns for clarity
nuance_demographics = nuance_demographics.rename(columns={
    'Accession Number': 'research_mrn',
    'Patient Sex': 'sex',
    'Patient Age': 'age'
})

# Keep only unique patients (some may have multiple exams in the Nuance export)
# Take the first occurrence for each accession number
nuance_demographics = nuance_demographics.drop_duplicates(subset='research_mrn', keep='first')

# Convert research_mrn to numeric in both dataframes for matching
master_df['research_mrn_numeric'] = pd.to_numeric(master_df['research_mrn'], errors='coerce')
nuance_demographics['research_mrn_numeric'] = pd.to_numeric(nuance_demographics['research_mrn'], errors='coerce')

print("Master list research_mrn values (first 10):")
print(master_df['research_mrn'].head(10).tolist())
print("\nNuance export Accession Number values (first 10):")
print(nuance_demographics['research_mrn'].head(10).tolist())

# Check for matches
master_mrns = set(master_df['research_mrn_numeric'].dropna())
nuance_mrns = set(nuance_demographics['research_mrn_numeric'].dropna())

print(f"\nMaster list: {len(master_mrns)} unique research MRNs")
print(f"Nuance export: {len(nuance_mrns)} unique accession numbers")
print(f"Matching: {len(master_mrns & nuance_mrns)} patients")

if len(master_mrns - nuance_mrns) > 0:
    print(f"\nPatients in master list but not in Nuance export: {len(master_mrns - nuance_mrns)}")
    missing_subjects = master_df[master_df['research_mrn_numeric'].isin(master_mrns - nuance_mrns)][['subject_id', 'research_mrn']].values.tolist()
    print(missing_subjects[:5])

# Merge the demographics based on research_mrn_numeric
master_with_demographics = master_df.merge(
    nuance_demographics[['research_mrn_numeric', 'sex', 'age']],
    on='research_mrn_numeric',
    how='left'
)

# Drop the temporary numeric column
master_with_demographics = master_with_demographics.drop('research_mrn_numeric', axis=1)

# Remove any duplicate subject_ids (keep first occurrence)
master_with_demographics = master_with_demographics.drop_duplicates(subset='subject_id', keep='first')

# Reorder columns to put demographics near the front
cols = ['subject_id', 'research_mrn', 'age', 'sex', 'acute_infarct_present'] + \
       [col for col in master_with_demographics.columns if col not in ['subject_id', 'research_mrn', 'age', 'sex', 'acute_infarct_present']]
master_with_demographics = master_with_demographics[cols]

# Save the updated master list
output_path = '/Users/paul/Projects/STAGE_Study/output/statistics/PATIENT_MASTER_LIST.csv'
master_with_demographics.to_csv(output_path, index=False)

print(f"\n✓ Updated master patient list saved: {output_path}")
print(f"\nDemographics summary:")
print(f"  - Patients with age: {master_with_demographics['age'].notna().sum()}")
print(f"  - Patients with sex: {master_with_demographics['sex'].notna().sum()}")
print(f"\nAge statistics:")
print(master_with_demographics['age'].describe())
print(f"\nSex distribution:")
print(master_with_demographics['sex'].value_counts(dropna=False))
