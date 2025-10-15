#!/usr/bin/env python3
import pandas as pd

df = pd.read_csv('output/statistics/swi_metadata_deep_inspection.csv')

print("="*80)
print("MANUFACTURER VERIFICATION FOR SWI CLASSIFICATION")
print("="*80)

model_col = "Manufacturer's Model Name"

# Conventional SWI
conv = df[df['SeriesDescription'].str.contains('SWI AX|SWI_Images', case=False, regex=True, na=False)]
print(f'\n=== CONVENTIONAL SWI ===')
print(f'Count: {len(conv)}')
print(f"Manufacturers: {conv['Manufacturer'].unique()}")
print(f"Model Names: {conv[model_col].unique()}")
print(f"Series Descriptions: {conv['SeriesDescription'].unique()}")

# STAGE SWI
stage = df[df['SeriesDescription'].str.contains('STAGE|_STAGE', case=False, regex=True, na=False)]
print(f'\n=== STAGE SWI ===')
print(f'Count: {len(stage)}')
print(f"Manufacturers: {stage['Manufacturer'].unique()}")
print(f"Model Names: {stage[model_col].unique()}")
print(f"Series Descriptions: {stage['SeriesDescription'].unique()}")

# Verify 100% separation
print(f'\n=== VERIFICATION ===')
conv_manufacturers = set(conv['Manufacturer'].unique())
stage_manufacturers = set(stage['Manufacturer'].unique())

if len(conv_manufacturers & stage_manufacturers) == 0:
    print("✓ PERFECT SEPARATION: No manufacturer overlap between conventional and STAGE!")
    print(f"  Conventional uses: {conv_manufacturers}")
    print(f"  STAGE uses: {stage_manufacturers}")
else:
    print(f"✗ WARNING: Overlap found: {conv_manufacturers & stage_manufacturers}")
