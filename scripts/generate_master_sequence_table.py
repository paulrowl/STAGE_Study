#!/usr/bin/env python3
"""
Generate master table combining patient ID, folder names, and series numbers
"""

import pandas as pd
from pathlib import Path

def main():
    print("Generating master sequence identifier table...")
    print("=" * 80)
    
    # Load the two existing tables
    folder_mapping = pd.read_csv('output/statistics/sequence_folder_mapping.csv')
    series_mapping = pd.read_csv('output/statistics/series_number_mapping.csv')
    
    # Verify they have the same patients
    if not folder_mapping['rAccession'].equals(series_mapping['rAccession']):
        print("Warning: Patient lists don't match perfectly")
    
    # Sequence types
    sequence_types = ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']
    
    # Create comprehensive table with all identifiers
    master_data = []
    
    for _, row in folder_mapping.iterrows():
        patient_id = row['rAccession']
        series_row = series_mapping[series_mapping['rAccession'] == patient_id]
        
        for seq_type in sequence_types:
            folder_name = row[seq_type] if pd.notna(row[seq_type]) and row[seq_type] != '' else ''
            series_num = ''
            if not series_row.empty:
                series_val = series_row[seq_type].values[0]
                series_num = str(int(series_val)) if pd.notna(series_val) and series_val != '' else ''
            
            master_data.append({
                'rAccession': patient_id,
                'Sequence_Type': seq_type,
                'Folder_Name': folder_name,
                'Series_Number': series_num
            })
    
    # Create DataFrame
    df_long = pd.DataFrame(master_data)
    
    # Save long format
    output_long = 'output/statistics/master_sequence_table_long.csv'
    df_long.to_csv(output_long, index=False)
    print(f"\nSaved long format to: {output_long}")
    
    # Also create wide format (more readable)
    master_wide = []
    
    for _, row in folder_mapping.iterrows():
        patient_id = row['rAccession']
        series_row = series_mapping[series_mapping['rAccession'] == patient_id]
        
        wide_row = {'rAccession': patient_id}
        
        for seq_type in sequence_types:
            folder_name = row[seq_type] if pd.notna(row[seq_type]) and row[seq_type] != '' else ''
            series_num = ''
            if not series_row.empty:
                series_val = series_row[seq_type].values[0]
                series_num = str(int(series_val)) if pd.notna(series_val) and series_val != '' else ''
            
            # Create combined identifier: "FolderName (Series#)"
            if folder_name or series_num:
                if folder_name and series_num:
                    combined = f"{folder_name} (#{series_num})"
                elif folder_name:
                    combined = folder_name
                elif series_num:
                    combined = f"(#{series_num})"
                else:
                    combined = ''
            else:
                combined = ''
            
            wide_row[seq_type] = combined
        
        master_wide.append(wide_row)
    
    df_wide = pd.DataFrame(master_wide)
    
    # Save wide format
    output_wide = 'output/statistics/master_sequence_table_wide.csv'
    df_wide.to_csv(output_wide, index=False)
    print(f"Saved wide format to: {output_wide}")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    # Count complete entries
    for seq_type in sequence_types:
        complete = df_long[(df_long['Sequence_Type'] == seq_type) & 
                          (df_long['Folder_Name'] != '') & 
                          (df_long['Series_Number'] != '')].shape[0]
        total = df_long[df_long['Sequence_Type'] == seq_type].shape[0]
        print(f"{seq_type}: {complete}/{total} complete entries")
    
    print("\n" + "=" * 80)
    print("PREVIEW - Wide Format (First 10 patients)")
    print("=" * 80)
    print(df_wide.head(10).to_string(index=False))
    
    print("\n" + "=" * 80)
    print("PREVIEW - Long Format (First 20 rows)")
    print("=" * 80)
    print(df_long.head(20).to_string(index=False))

if __name__ == '__main__':
    main()
