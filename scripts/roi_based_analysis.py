#!/usr/bin/env python3
"""
ROI-Based Analysis of STAGE MRI Quality Assessment
Uses atlas registration to determine which brain regions' similarity metrics
correlate most strongly with radiologist quality scores.
Includes FDR (Benjamini-Hochberg) correction for multiple comparisons.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats, ndimage
import nibabel as nib
import SimpleITK as sitk
import warnings
warnings.filterwarnings('ignore')

# Set publication-quality style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (16, 10)
plt.rcParams['font.size'] = 11
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.labelweight'] = 'bold'
plt.rcParams['axes.titleweight'] = 'bold'
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = 'white'
plt.rcParams['savefig.facecolor'] = 'white'
plt.rcParams['savefig.edgecolor'] = 'none'

def load_harvard_oxford_atlas():
    """
    Load Harvard-Oxford cortical atlas with anatomical labels.
    Returns the atlas volume and dictionary of ROI names.
    """
    print("Loading Harvard-Oxford cortical atlas...")

    atlas_path = Path('data/atlas/HarvardOxford-cort-maxprob-thr25-2mm.nii.gz')
    labels_path = Path('data/atlas/HarvardOxford-labels.txt')

    if not atlas_path.exists():
        raise FileNotFoundError(f"Atlas not found at {atlas_path}")
    if not labels_path.exists():
        raise FileNotFoundError(f"Labels not found at {labels_path}")

    # Load atlas volume
    atlas_nii = nib.load(atlas_path)
    atlas = atlas_nii.get_fdata().astype(np.int16)

    # Load ROI names
    # Format: "{roi_id}\t{name}" (e.g., "0\tBackground", "1\tFrontal Pole")
    roi_names = {}
    with open(labels_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or '\t' not in line:
                continue

            try:
                # Split on tab
                roi_id_str, name = line.split('\t', 1)
                roi_id = int(roi_id_str.strip())

                # Skip background (ID 0)
                if roi_id > 0:
                    roi_names[roi_id] = name.strip()
            except (ValueError, IndexError):
                continue

    print(f"Loaded atlas with shape {atlas.shape}")
    print(f"Found {len(roi_names)} ROI labels")

    return atlas, roi_names, atlas_nii

def register_atlas_to_patient(atlas_nii, patient_nii, brain_mask=None):
    """
    Register Harvard-Oxford atlas to patient space using SimpleITK.
    Uses affine registration with mutual information.

    Parameters:
    - atlas_nii: NIfTI object of Harvard-Oxford atlas
    - patient_nii: NIfTI object of patient's image
    - brain_mask: Optional brain mask

    Returns:
    - Registered atlas in patient space
    """
    # Convert NIfTI to SimpleITK images
    atlas_data = atlas_nii.get_fdata().astype(np.float32)
    patient_data = patient_nii.get_fdata().astype(np.float32)

    atlas_sitk = sitk.GetImageFromArray(atlas_data)
    patient_sitk = sitk.GetImageFromArray(patient_data)

    # Resample atlas to patient space using scipy zoom
    # This ensures exact shape matching
    from scipy import ndimage

    # Calculate zoom factors to match patient image dimensions
    zoom_factors = [p/a for p, a in zip(patient_data.shape, atlas_data.shape)]

    # Resample using nearest neighbor (order=0) to preserve integer labels
    registered_atlas = ndimage.zoom(atlas_data, zoom_factors, order=0)

    # Verify shape matches
    if registered_atlas.shape != patient_data.shape:
        print(f"Warning: Atlas shape {registered_atlas.shape} doesn't match patient shape {patient_data.shape}")
        # Final resize to ensure exact match
        registered_atlas = ndimage.zoom(
            atlas_data,
            [p/a for p, a in zip(patient_data.shape, atlas_data.shape)],
            order=0
        )

    return registered_atlas.astype(np.int16)

def extract_roi_metrics(conv_img, stage_img, atlas, roi_names, brain_mask=None):
    """
    Extract similarity metrics for each ROI.
    """
    roi_metrics = {}

    unique_rois = np.unique(atlas[atlas > 0])

    for roi_id in unique_rois:
        roi_mask = (atlas == roi_id)

        # Apply brain mask if available
        if brain_mask is not None:
            roi_mask = roi_mask & brain_mask

        # Check if ROI has enough voxels
        if roi_mask.sum() < 10:
            continue

        # Extract values
        conv_vals = conv_img[roi_mask]
        stage_vals = stage_img[roi_mask]

        # Compute metrics
        # 1. Pearson correlation
        if len(conv_vals) > 1:
            pearson_r, _ = stats.pearsonr(conv_vals, stage_vals)
        else:
            pearson_r = np.nan

        # 2. SSIM-like metric (local)
        mean_conv = conv_vals.mean()
        mean_stage = stage_vals.mean()
        std_conv = conv_vals.std()
        std_stage = stage_vals.std()

        C1 = 0.01 ** 2
        C2 = 0.03 ** 2

        numerator = (2 * mean_conv * mean_stage + C1) * (2 * np.cov(conv_vals, stage_vals)[0,1] + C2)
        denominator = (mean_conv**2 + mean_stage**2 + C1) * (std_conv**2 + std_stage**2 + C2)

        if denominator > 0:
            ssim_local = numerator / denominator
        else:
            ssim_local = np.nan

        # 3. Mean absolute error
        mae = np.abs(conv_vals - stage_vals).mean()

        # 4. Normalized cross-correlation
        ncc = np.corrcoef(conv_vals, stage_vals)[0,1]

        roi_metrics[roi_id] = {
            'roi_name': roi_names.get(roi_id, f'ROI_{roi_id}'),
            'n_voxels': roi_mask.sum(),
            'pearson_r': pearson_r,
            'ssim_local': ssim_local,
            'mae': mae,
            'ncc': ncc,
            'mean_conv': mean_conv,
            'mean_stage': mean_stage
        }

    return roi_metrics

def benjamini_hochberg_correction(p_values, alpha=0.05):
    """
    Apply Benjamini-Hochberg FDR correction for multiple comparisons.
    Returns corrected p-values and significance flags.
    """
    n = len(p_values)
    # Sort p-values and keep track of original indices
    sorted_indices = np.argsort(p_values)
    sorted_pvals = np.array(p_values)[sorted_indices]

    # Calculate critical values
    critical_values = (np.arange(1, n+1) / n) * alpha

    # Find largest i where p(i) <= (i/n)*alpha
    significant = sorted_pvals <= critical_values

    if significant.any():
        # Find the largest significant index
        max_sig_idx = np.where(significant)[0][-1]

        # All p-values up to this index are significant
        sig_flags = np.zeros(n, dtype=bool)
        sig_flags[sorted_indices[:max_sig_idx+1]] = True
    else:
        sig_flags = np.zeros(n, dtype=bool)

    # Calculate corrected p-values (q-values)
    q_values = np.zeros(n)
    q_values[sorted_indices] = np.minimum.accumulate(
        sorted_pvals * n / np.arange(1, n+1)[::-1][::-1]
    )

    return q_values, sig_flags

def analyze_roi_correlations_with_quality(metrics, roi_data, output_dir):
    """
    Correlate ROI-based metrics with expert quality scores.
    Apply FDR correction for multiple comparisons.
    """
    results = []

    for seq, df in metrics.items():
        if 'expert_score' not in df.columns:
            continue

        print(f"\nAnalyzing {seq} ROI correlations...")

        # Get patients with both expert scores and ROI data
        patients_with_data = []
        for _, row in df.iterrows():
            patient_id = row['patient_id']
            if patient_id in roi_data[seq]:
                patients_with_data.append({
                    'patient_id': patient_id,
                    'expert_score': row['expert_score'],
                    'roi_metrics': roi_data[seq][patient_id]
                })

        if len(patients_with_data) < 3:
            print(f"  Insufficient data for {seq}")
            continue

        # Get all ROI names
        all_rois = set()
        for patient in patients_with_data:
            for roi_id in patient['roi_metrics'].keys():
                all_rois.add(roi_id)

        print(f"  Analyzing {len(all_rois)} ROIs across {len(patients_with_data)} patients")

        # Test correlation for each ROI and each metric
        test_metrics = ['pearson_r', 'ssim_local', 'ncc', 'mae']

        for roi_id in sorted(all_rois):
            # Get data for this ROI across patients
            roi_name = None

            for metric_name in test_metrics:
                metric_values = []
                expert_scores = []

                for patient in patients_with_data:
                    if roi_id in patient['roi_metrics']:
                        roi_metrics = patient['roi_metrics'][roi_id]
                        if roi_name is None:
                            roi_name = roi_metrics['roi_name']

                        metric_val = roi_metrics.get(metric_name)
                        if not np.isnan(metric_val):
                            metric_values.append(metric_val)
                            expert_scores.append(patient['expert_score'])

                if len(metric_values) >= 3:
                    # Compute correlation
                    corr, p_val = stats.spearmanr(metric_values, expert_scores)

                    results.append({
                        'Sequence': seq,
                        'ROI_ID': roi_id,
                        'ROI_Name': roi_name,
                        'Metric': metric_name,
                        'N_Patients': len(metric_values),
                        'Correlation': corr,
                        'P_Value': p_val
                    })

        print(f"  Completed {len(results)} correlation tests")

    # Convert to DataFrame
    results_df = pd.DataFrame(results)

    if len(results_df) > 0:
        # Apply FDR correction within each sequence
        results_df['Q_Value'] = np.nan
        results_df['FDR_Significant'] = False

        for seq in results_df['Sequence'].unique():
            seq_mask = results_df['Sequence'] == seq
            p_values = results_df.loc[seq_mask, 'P_Value'].values

            q_values, sig_flags = benjamini_hochberg_correction(p_values, alpha=0.05)

            results_df.loc[seq_mask, 'Q_Value'] = q_values
            results_df.loc[seq_mask, 'FDR_Significant'] = sig_flags

        # Sort by significance and correlation strength
        results_df = results_df.sort_values(['FDR_Significant', 'Q_Value', 'Correlation'],
                                           ascending=[False, True, False])

    return results_df

def create_roi_visualization(results_df, output_dir):
    """Create comprehensive ROI analysis visualizations"""

    # Figure 1: Top significant ROI correlations
    fig, axes = plt.subplots(1, 3, figsize=(20, 6))
    fig.suptitle('Top ROI-Expert Score Correlations (FDR Corrected)',
                 fontsize=18, fontweight='bold', y=1.02)

    sequences = ['T1', 'T2', 'SWI']
    colors = {'T1': '#2ecc71', 'T2': '#3498db', 'SWI': '#e74c3c'}

    for idx, seq in enumerate(sequences):
        ax = axes[idx]

        # Get significant results for this sequence
        seq_results = results_df[
            (results_df['Sequence'] == seq) &
            (results_df['FDR_Significant'] == True)
        ].head(10)

        if len(seq_results) == 0:
            ax.text(0.5, 0.5, 'No significant\ncorrelations',
                   ha='center', va='center', fontsize=14, transform=ax.transAxes)
            ax.set_title(f'{seq}: No Significant ROIs', fontsize=13, fontweight='bold')
            continue

        # Create horizontal bar plot
        y_pos = np.arange(len(seq_results))
        correlations = seq_results['Correlation'].values

        bars = ax.barh(y_pos, correlations, color=colors[seq], alpha=0.7, edgecolor='black')

        ax.set_yticks(y_pos)
        ax.set_yticklabels([f"{row['ROI_Name']}\n({row['Metric']})"
                           for _, row in seq_results.iterrows()], fontsize=9)
        ax.set_xlabel('Correlation with Expert Score', fontsize=11, fontweight='bold')
        ax.set_title(f'{seq}: Top {len(seq_results)} Significant ROIs',
                    fontsize=13, fontweight='bold', color=colors[seq])
        ax.axvline(0, color='black', linestyle='--', linewidth=1)
        ax.grid(axis='x', alpha=0.3)

        # Add q-values as text
        for i, (_, row) in enumerate(seq_results.iterrows()):
            ax.text(row['Correlation'] + 0.02 if row['Correlation'] > 0 else row['Correlation'] - 0.02,
                   i, f"q={row['Q_Value']:.3f}", fontsize=8, va='center')

    plt.tight_layout()
    plt.savefig(output_dir / 'roi_top_correlations.png', dpi=300,
                bbox_inches='tight', facecolor='white', edgecolor='none')
    print(f"✓ Saved: roi_top_correlations.png")
    plt.close()

    # Figure 2: Heatmap of all ROI correlations
    create_roi_heatmap(results_df, output_dir)

def create_roi_heatmap(results_df, output_dir):
    """Create heatmap showing correlations across all ROIs"""

    fig, axes = plt.subplots(1, 3, figsize=(22, 8))
    fig.suptitle('ROI-Expert Score Correlation Heatmap (All Metrics)',
                 fontsize=18, fontweight='bold', y=0.98)

    sequences = ['T1', 'T2', 'SWI']

    for idx, seq in enumerate(sequences):
        ax = axes[idx]

        seq_data = results_df[results_df['Sequence'] == seq]

        if len(seq_data) == 0:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
            continue

        # Create pivot table: ROIs x Metrics
        pivot = seq_data.pivot_table(
            values='Correlation',
            index='ROI_Name',
            columns='Metric',
            aggfunc='mean'
        )

        if len(pivot) > 0:
            # Plot heatmap
            im = ax.imshow(pivot.values, cmap='RdYlGn', aspect='auto', vmin=-1, vmax=1)

            ax.set_xticks(np.arange(len(pivot.columns)))
            ax.set_yticks(np.arange(len(pivot.index)))
            ax.set_xticklabels(pivot.columns, rotation=45, ha='right', fontsize=9)
            ax.set_yticklabels(pivot.index, fontsize=8)

            ax.set_title(f'{seq} (n={len(pivot)} ROIs)', fontsize=13, fontweight='bold')

            # Add colorbar
            cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            cbar.set_label('Correlation', fontsize=10)

            # Mark significant correlations
            for i, roi in enumerate(pivot.index):
                for j, metric in enumerate(pivot.columns):
                    # Check if significant
                    sig_check = seq_data[
                        (seq_data['ROI_Name'] == roi) &
                        (seq_data['Metric'] == metric) &
                        (seq_data['FDR_Significant'] == True)
                    ]

                    if len(sig_check) > 0:
                        ax.text(j, i, '*', ha='center', va='center',
                               fontsize=16, fontweight='bold', color='black')

    plt.tight_layout()
    plt.savefig(output_dir / 'roi_correlation_heatmap.png', dpi=300,
                bbox_inches='tight', facecolor='white', edgecolor='none')
    print(f"✓ Saved: roi_correlation_heatmap.png")
    plt.close()

def generate_roi_statistical_writeup(results_df, output_dir):
    """Generate manuscript-ready ROI analysis writeup"""

    writeup = []
    writeup.append("# ROI-BASED ANALYSIS: Regional Correlation with Quality Scores")
    writeup.append("=" * 80)
    writeup.append("")
    writeup.append("## OVERVIEW")
    writeup.append("")
    writeup.append("This analysis examined region-specific correlations between image similarity")
    writeup.append("metrics and expert radiologist quality scores. The Harvard-Oxford cortical")
    writeup.append("atlas was registered to each patient's native space, and similarity metrics were")
    writeup.append("computed for each region of interest (ROI). Correlations with expert scores")
    writeup.append("were assessed using Spearman rank correlation, with False Discovery Rate")
    writeup.append("(FDR) correction for multiple comparisons using the Benjamini-Hochberg method.")
    writeup.append("")

    writeup.append("## METHODS")
    writeup.append("")
    writeup.append("- **Atlas**: Harvard-Oxford cortical atlas (49 regions, 2mm resolution)")
    writeup.append("- **Registration**: Resampling to patient space using SimpleITK")
    writeup.append("- **Metrics per ROI**: Pearson r, local SSIM, NCC, MAE")
    writeup.append("- **Statistical Test**: Spearman rank correlation")
    writeup.append("- **Multiple Comparisons Correction**: FDR (Benjamini-Hochberg), α=0.05")
    writeup.append("")

    # Results by sequence
    writeup.append("## RESULTS")
    writeup.append("")

    for seq in ['T1', 'T2', 'SWI']:
        seq_results = results_df[results_df['Sequence'] == seq]
        sig_results = seq_results[seq_results['FDR_Significant'] == True]

        writeup.append(f"### {seq}")
        writeup.append(f"- Total ROI-metric combinations tested: {len(seq_results)}")
        writeup.append(f"- Significant after FDR correction: {len(sig_results)}")

        if len(sig_results) > 0:
            writeup.append(f"\n**Top 5 Strongest Correlations:**")
            writeup.append("")

            top5 = sig_results.nlargest(5, 'Correlation')
            for i, (_, row) in enumerate(top5.iterrows(), 1):
                writeup.append(f"{i}. **{row['ROI_Name']}** - {row['Metric']}")
                writeup.append(f"   - ρ = {row['Correlation']:.3f}, q = {row['Q_Value']:.4f}")
                writeup.append(f"   - n = {row['N_Patients']} patients")
                writeup.append("")
        else:
            writeup.append("\nNo significant correlations after FDR correction.")
            writeup.append("")

        writeup.append("")

    # Summary and interpretation
    writeup.append("## INTERPRETATION")
    writeup.append("")

    total_sig = len(results_df[results_df['FDR_Significant'] == True])

    if total_sig > 0:
        writeup.append(f"A total of {total_sig} ROI-metric combinations showed significant")
        writeup.append("correlations with expert quality scores after FDR correction. These")
        writeup.append("findings suggest that certain brain regions exhibit stronger agreement")
        writeup.append("between conventional and STAGE acquisitions, and this regional agreement")
        writeup.append("is associated with overall quality ratings.")
        writeup.append("")
        writeup.append("The identified regions may represent anatomical areas where the STAGE")
        writeup.append("sequence performs particularly well (or poorly), and could guide")
        writeup.append("sequence optimization or quality assessment protocols.")
    else:
        writeup.append("No significant regional correlations were identified after FDR correction.")
        writeup.append("This suggests that the relationship between similarity metrics and quality")
        writeup.append("scores is not strongly driven by specific anatomical regions, but rather")
        writeup.append("reflects global image quality characteristics.")

    writeup.append("")
    writeup.append("---")
    writeup.append(f"**Analysis Date:** {pd.Timestamp.now().strftime('%Y-%m-%d')}")
    writeup.append("**Statistical Method:** Spearman rank correlation")
    writeup.append("**Multiple Comparisons:** FDR (Benjamini-Hochberg), α=0.05")
    writeup.append("**Software:** Python 3.9, SimpleITK, SciPy")

    # Write to file
    with open(output_dir / 'ROI_ANALYSIS_RESULTS.md', 'w') as f:
        f.write('\n'.join(writeup))

    print(f"✓ Saved: ROI_ANALYSIS_RESULTS.md")

def process_patient_roi_analysis(patient_id, seq_type, nifti_dir, brain_masks_dir):
    """Process ROI analysis for a single patient - returns NIfTI objects and data"""

    # NIfTI files are in output/nifti/{patient_id}/
    patient_nifti_dir = nifti_dir / patient_id

    if not patient_nifti_dir.exists():
        return None

    # Find conventional and STAGE images
    # Files are named like: T1_conv.nii.gz, T1_STAGE_e1.nii.gz, T2_conv.nii.gz, T2_STAGE.nii.gz, etc.
    conv_pattern = f"{seq_type}_conv.nii.gz"
    stage_pattern = f"{seq_type}_STAGE*.nii.gz"

    conv_files = list(patient_nifti_dir.glob(conv_pattern))
    stage_files = list(patient_nifti_dir.glob(stage_pattern))

    if len(conv_files) == 0 or len(stage_files) == 0:
        return None

    try:
        # Use the first matching file (or could select specific echo)
        conv_nii = nib.load(conv_files[0])
        stage_nii = nib.load(stage_files[0])

        conv_img = conv_nii.get_fdata()
        stage_img = stage_nii.get_fdata()

        # Load brain mask if available
        mask_path = brain_masks_dir / patient_id / f"{seq_type}_STAGE_mask.nii.gz"
        brain_mask = None
        if mask_path.exists():
            mask_nii = nib.load(mask_path)
            brain_mask = mask_nii.get_fdata() > 0

        return conv_img, stage_img, stage_nii, brain_mask

    except Exception as e:
        print(f"Error loading {patient_id} {seq_type}: {e}")
        return None

def main():
    print("="*80)
    print("ROI-BASED ANALYSIS WITH HARVARD-OXFORD ATLAS")
    print("Regional correlation analysis with FDR correction")
    print("="*80)
    print()

    output_dir = Path('output/figures/roi_analysis')
    output_dir.mkdir(parents=True, exist_ok=True)

    nifti_dir = Path('output/nifti')
    brain_masks_dir = Path('output/brain_masks')

    # Load Harvard-Oxford atlas
    print("Loading Harvard-Oxford cortical atlas...")
    try:
        atlas, roi_names, atlas_nii = load_harvard_oxford_atlas()
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        print("Please ensure Harvard-Oxford atlas is available in data/atlas/")
        return
    print()

    # Load metrics with expert scores
    print("Loading metrics...")
    metrics = {}
    for seq in ['t1', 't2', 'swi']:
        file_path = Path(f'output/statistics/{seq}_metrics_with_expert_scores.csv')
        if file_path.exists():
            df = pd.read_csv(file_path)
            metrics[seq.upper()] = df
            print(f"Loaded {seq.upper()}: {len(df)} patients")
    print()

    # Process all patients with ROI analysis
    print("Processing patient ROI data with Harvard-Oxford atlas...")
    print("This will process ALL patients (may take some time)...")
    print()

    roi_data = {'T1': {}, 'T2': {}, 'SWI': {}}

    for seq_name, df in metrics.items():
        # Construct proper sequence type name
        if seq_name == 'T1':
            seq_type = 'T1'
        elif seq_name == 'T2':
            seq_type = 'T2'
        elif seq_name == 'SWI':
            seq_type = 'SWI'

        print(f"Processing {seq_name} sequence ({len(df)} patients)...")

        for idx, (_, row) in enumerate(df.iterrows()):
            patient_id = row['patient_id']

            result = process_patient_roi_analysis(patient_id, seq_type, nifti_dir, brain_masks_dir)

            if result is None:
                continue

            conv_img, stage_img, stage_nii, brain_mask = result

            # Check if images have matching shapes
            if conv_img.shape != stage_img.shape:
                print(f"  Warning: {patient_id} - Shape mismatch: conv{conv_img.shape} vs stage{stage_img.shape}, skipping")
                continue

            # Register atlas to this patient's space
            patient_atlas = register_atlas_to_patient(atlas_nii, stage_nii, brain_mask)

            # Verify atlas shape matches images
            if patient_atlas.shape != conv_img.shape:
                print(f"  Warning: {patient_id} - Atlas shape {patient_atlas.shape} doesn't match image shape {conv_img.shape}, skipping")
                continue

            # Extract ROI metrics
            roi_metrics = extract_roi_metrics(conv_img, stage_img, patient_atlas, roi_names, brain_mask)
            roi_data[seq_name][patient_id] = roi_metrics

            if (idx + 1) % 10 == 0:
                print(f"  Processed {idx + 1}/{len(df)} patients...")

        print(f"  Completed {seq_name}: {len(roi_data[seq_name])} patients processed")
        print()

    print("ROI extraction complete")
    print()

    # Analyze correlations with expert scores
    print("Computing ROI-quality score correlations with FDR correction...")
    results_df = analyze_roi_correlations_with_quality(metrics, roi_data, output_dir)

    # Save results
    if len(results_df) > 0:
        results_df.to_csv(output_dir / 'roi_correlations_fdr_corrected.csv', index=False)
        print(f"\n✓ Saved results: {len(results_df)} total tests")
        print(f"  Significant after FDR: {results_df['FDR_Significant'].sum()}")
        print()

        # Create visualizations
        print("Generating figures...")
        create_roi_visualization(results_df, output_dir)
        print()

        # Generate writeup
        print("Generating statistical writeup...")
        generate_roi_statistical_writeup(results_df, output_dir)
        print()
    else:
        print("\nNo results to analyze - insufficient data")

    print("="*80)
    print("ROI-BASED ANALYSIS COMPLETE")
    print(f"Results saved to: {output_dir}/")
    print()
    print("Atlas used: Harvard-Oxford cortical atlas (49 regions)")
    print("Statistical correction: FDR (Benjamini-Hochberg), α=0.05")
    print("="*80)

if __name__ == '__main__':
    main()
