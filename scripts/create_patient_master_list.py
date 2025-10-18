#!/usr/bin/env python3
"""
Create a master patient list with infarct status
"""
import pandas as pd
import glob

# Read the neurorad scores file
neurorad_df = pd.read_excel('/Users/paul/Projects/STAGE_Study/output/statistics/neurorad_scores_unified.xlsx')

# Get unique patients - use correct column names
neurorad_df = neurorad_df.rename(columns={'rAccession': 'subject_id', 'Acute INFARCT?': 'acute_infarct_present', 'rMRN': 'research_mrn'})

# Standardize infarct status values
def standardize_infarct_status(val):
    if pd.isna(val):
        return None
    val_str = str(val).strip().upper()
    # Any mention of 'Y' or 'YES' means infarct present
    if 'Y' in val_str or 'YES' in val_str:
        return 'Yes'
    # Any mention of 'N' or 'NO' or 'NORMAL' means no infarct
    elif 'N' in val_str or 'NO' in val_str or 'NORMAL' in val_str:
        return 'No'
    else:
        return None

neurorad_df['acute_infarct_present'] = neurorad_df['acute_infarct_present'].apply(standardize_infarct_status)

# For patients with multiple entries, take the first non-null value for infarct status and first value for MRN
patients = neurorad_df.groupby('subject_id').agg({
    'acute_infarct_present': 'first',
    'research_mrn': 'first'
}).reset_index()

# Sort by subject_id
patients = patients.sort_values('subject_id').reset_index(drop=True)

# Get list of all patients in organized directory
organized_dirs = glob.glob('/Users/paul/Projects/STAGE_Study/data/raw/organized/Anon*/')
all_patients = sorted([d.split('/')[-2] for d in organized_dirs])

# Create master dataframe with all patients
master_list = pd.DataFrame({'subject_id': all_patients})

# Merge with infarct status (left join to keep all patients)
master_list = master_list.merge(patients, on='subject_id', how='left')

# Check which patients have T1, T2, SWI sequences
for seq in ['T1_conv', 'T2_conv', 'SWI_conv']:
    master_list[f'has_{seq}'] = master_list['subject_id'].apply(
        lambda x: glob.glob(f'/Users/paul/Projects/STAGE_Study/output/nifti/{x}/{seq}.nii.gz') != []
    )

for seq in ['T1_STAGE', 'T2_STAGE', 'SWI_STAGE']:
    master_list[f'has_{seq}'] = master_list['subject_id'].apply(
        lambda x: glob.glob(f'/Users/paul/Projects/STAGE_Study/output/nifti/{x}/{seq}.nii.gz') != []
    )

# Add paired sequence indicators
master_list['has_T1_pair'] = master_list['has_T1_conv'] & master_list['has_T1_STAGE']
master_list['has_T2_pair'] = master_list['has_T2_conv'] & master_list['has_T2_STAGE']
master_list['has_SWI_pair'] = master_list['has_SWI_conv'] & master_list['has_SWI_STAGE']

# Output path
output_path = '/Users/paul/Projects/STAGE_Study/output/statistics/PATIENT_MASTER_LIST.csv'
master_list.to_csv(output_path, index=False)

print(f"✓ Created master patient list: {output_path}")
print(f"\nTotal patients: {len(master_list)}")
print(f"Patients with infarct status: {master_list['acute_infarct_present'].notna().sum()}")
print(f"  - With acute infarct (Yes): {(master_list['acute_infarct_present'] == 'Yes').sum()}")
print(f"  - Without acute infarct (No): {(master_list['acute_infarct_present'] == 'No').sum()}")
print(f"  - Infarct status unknown (blank): {master_list['acute_infarct_present'].isna().sum()}")
print(f"\nPaired sequences:")
print(f"  - T1 pairs: {master_list['has_T1_pair'].sum()}")
print(f"  - T2 pairs: {master_list['has_T2_pair'].sum()}")
print(f"  - SWI pairs: {master_list['has_SWI_pair'].sum()}")

# Show sample of patients with and without infarct
print(f"\n{'='*60}")
print("Sample patients WITH acute infarct:")
print(master_list[master_list['acute_infarct_present'] == 'Yes']['subject_id'].head(10).tolist())
print("\nSample patients WITHOUT acute infarct:")
print(master_list[master_list['acute_infarct_present'] == 'No']['subject_id'].head(10).tolist())
if master_list['acute_infarct_present'].isna().sum() > 0:
    print("\nPatients with UNKNOWN infarct status:")
    print(master_list[master_list['acute_infarct_present'].isna()]['subject_id'].tolist())
