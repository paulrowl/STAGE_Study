#!/usr/bin/env python3
"""
Create a figure demonstrating the processing pipeline steps with example images
"""

import nibabel as nib
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from pathlib import Path
from skimage.metrics import structural_similarity as ssim

# Set white background
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['savefig.facecolor'] = 'white'
plt.rcParams['savefig.edgecolor'] = 'none'

def load_nifti_slice(nifti_path, slice_idx=None):
    """Load a middle slice from a NIfTI file"""
    nii = nib.load(nifti_path)
    data = nii.get_fdata()
    
    if slice_idx is None:
        slice_idx = data.shape[2] // 2
    
    return data[:, :, slice_idx]

def create_pipeline_figure(patient_id='Anon11271', sequence='T1'):
    """Create figure showing pipeline steps for a patient"""
    
    base_dir = Path('.')
    
    # Define paths for different pipeline stages
    conv_nifti = base_dir / 'output' / 'nifti' / patient_id / f'{sequence}_conv.nii.gz'
    stage_nifti = base_dir / 'output' / 'nifti' / patient_id / f'{sequence}_STAGE.nii.gz'
    conv_mask = base_dir / 'output' / 'brain_masks' / patient_id / f'{sequence}_conv_mask.nii.gz'
    stage_mask = base_dir / 'output' / 'brain_masks' / patient_id / f'{sequence}_STAGE_mask.nii.gz'
    brain_mask_file = base_dir / 'output' / 'brain_masks' / patient_id / f'{sequence}_STAGE_mask.nii.gz'
    
    # Check if all files exist
    if not all([conv_nifti.exists(), stage_nifti.exists(), conv_mask.exists(), stage_mask.exists()]):
        print(f"Missing files for {patient_id} {sequence}")
        return None
    
    # Load images
    print(f"Loading images for {patient_id} {sequence}...")
    conv_orig = load_nifti_slice(conv_nifti)
    stage_orig = load_nifti_slice(stage_nifti)
    
    # Load masked images
    conv_masked_img = nib.load(conv_mask)
    stage_masked_img = nib.load(stage_mask)
    conv_masked = conv_masked_img.get_fdata()[:, :, conv_masked_img.shape[2] // 2]
    stage_masked = stage_masked_img.get_fdata()[:, :, stage_masked_img.shape[2] // 2]
    
    # Create binary brain mask for visualization
    brain_mask = (stage_masked > 0).astype(float)
    
    # Normalize images for display
    def normalize_image(img):
        img = img.copy()
        p2, p98 = np.percentile(img[img > 0], [2, 98])
        img = np.clip(img, p2, p98)
        img = (img - img.min()) / (img.max() - img.min() + 1e-8)
        return img
    
    conv_orig_norm = normalize_image(conv_orig)
    stage_orig_norm = normalize_image(stage_orig)
    conv_masked_norm = normalize_image(conv_masked)
    stage_masked_norm = normalize_image(stage_masked)
    
    # Calculate SSIM between masked images
    # Need to ensure same dimensions
    if conv_masked_norm.shape != stage_masked_norm.shape:
        from scipy import ndimage
        zoom_factors = [s / c for s, c in zip(stage_masked_norm.shape, conv_masked_norm.shape)]
        conv_masked_norm_resized = ndimage.zoom(conv_masked_norm, zoom_factors, order=1)
    else:
        conv_masked_norm_resized = conv_masked_norm
    
    # Calculate SSIM with windowed approach
    ssim_map = ssim(conv_masked_norm_resized, stage_masked_norm, 
                    data_range=1.0, full=True, win_size=11)[1]
    
    # Create figure with 3 rows and 3 columns
    fig = plt.figure(figsize=(18, 15))
    gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.25, top=0.93, bottom=0.05, left=0.05, right=0.98)
    
    # Row 1: Original NIfTI images
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.imshow(conv_orig_norm.T, cmap='gray', origin='lower', aspect='auto')
    ax1.set_title(f'Step 1: Conventional {sequence}\n(DICOM → NIfTI Conversion)', 
                  fontsize=12, fontweight='bold')
    ax1.axis('off')
    ax1.text(0.02, 0.98, 'Raw converted image', transform=ax1.transAxes,
             fontsize=10, verticalalignment='top', bbox=dict(boxstyle='round', 
             facecolor='yellow', alpha=0.7))
    
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.imshow(stage_orig_norm.T, cmap='gray', origin='lower', aspect='auto')
    ax2.set_title(f'Step 1: STAGE {sequence}\n(DICOM → NIfTI Conversion)', 
                  fontsize=12, fontweight='bold')
    ax2.axis('off')
    ax2.text(0.02, 0.98, 'Raw converted image', transform=ax2.transAxes,
             fontsize=10, verticalalignment='top', bbox=dict(boxstyle='round', 
             facecolor='yellow', alpha=0.7))
    
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.imshow(brain_mask.T, cmap='hot', origin='lower', aspect='auto')
    ax3.set_title('Step 2: Brain Extraction Mask\n(HD-BET Algorithm)', 
                  fontsize=12, fontweight='bold')
    ax3.axis('off')
    ax3.text(0.02, 0.98, 'Binary brain mask', transform=ax3.transAxes,
             fontsize=10, verticalalignment='top', bbox=dict(boxstyle='round', 
             facecolor='yellow', alpha=0.7))
    
    # Row 2: Brain-masked images
    ax4 = fig.add_subplot(gs[1, 0])
    ax4.imshow(conv_masked_norm.T, cmap='gray', origin='lower', aspect='auto')
    ax4.set_title('Step 3: Brain-Extracted Conventional\n(Mask Applied)', 
                  fontsize=12, fontweight='bold')
    ax4.axis('off')
    ax4.text(0.02, 0.98, 'Background removed', transform=ax4.transAxes,
             fontsize=10, verticalalignment='top', bbox=dict(boxstyle='round', 
             facecolor='cyan', alpha=0.7))
    
    ax5 = fig.add_subplot(gs[1, 1])
    ax5.imshow(stage_masked_norm.T, cmap='gray', origin='lower', aspect='auto')
    ax5.set_title('Step 3: Brain-Extracted STAGE\n(Mask Applied)', 
                  fontsize=12, fontweight='bold')
    ax5.axis('off')
    ax5.text(0.02, 0.98, 'Background removed', transform=ax5.transAxes,
             fontsize=10, verticalalignment='top', bbox=dict(boxstyle='round', 
             facecolor='cyan', alpha=0.7))
    
    # Difference image
    ax6 = fig.add_subplot(gs[1, 2])
    diff_img = np.abs(conv_masked_norm_resized - stage_masked_norm)
    im6 = ax6.imshow(diff_img.T, cmap='hot', origin='lower', aspect='auto', vmin=0, vmax=0.3)
    ax6.set_title('Absolute Difference\n(Conv - STAGE)', 
                  fontsize=12, fontweight='bold')
    ax6.axis('off')
    plt.colorbar(im6, ax=ax6, fraction=0.046, pad=0.04)
    
    # Row 3: SSIM calculation and comparison
    ax7 = fig.add_subplot(gs[2, 0])
    ax7.imshow(conv_masked_norm_resized.T, cmap='gray', origin='lower', aspect='auto')
    ax7.set_title('Step 4: Registered Conventional\n(For Comparison)', 
                  fontsize=12, fontweight='bold')
    ax7.axis('off')
    ax7.text(0.02, 0.98, 'Spatially aligned', transform=ax7.transAxes,
             fontsize=10, verticalalignment='top', bbox=dict(boxstyle='round', 
             facecolor='lightgreen', alpha=0.7))
    
    ax8 = fig.add_subplot(gs[2, 1])
    ax8.imshow(stage_masked_norm.T, cmap='gray', origin='lower', aspect='auto')
    ax8.set_title('Step 4: STAGE (Reference)\n(For Comparison)', 
                  fontsize=12, fontweight='bold')
    ax8.axis('off')
    ax8.text(0.02, 0.98, 'Reference image', transform=ax8.transAxes,
             fontsize=10, verticalalignment='top', bbox=dict(boxstyle='round', 
             facecolor='lightgreen', alpha=0.7))
    
    ax9 = fig.add_subplot(gs[2, 2])
    im9 = ax9.imshow(ssim_map.T, cmap='RdYlGn', origin='lower', aspect='auto', vmin=0, vmax=1)
    ax9.set_title('Step 5: SSIM Quality Map\n(Structural Similarity)', 
                  fontsize=12, fontweight='bold')
    ax9.axis('off')
    cbar = plt.colorbar(im9, ax=ax9, fraction=0.046, pad=0.04)
    cbar.set_label('SSIM Score', fontsize=10)
    
    # Calculate overall SSIM
    mask_valid = (conv_masked_norm_resized > 0) & (stage_masked_norm > 0)
    overall_ssim = ssim(conv_masked_norm_resized, stage_masked_norm, 
                        data_range=1.0, full=False)
    
    ax9.text(0.02, 0.98, f'Mean SSIM: {overall_ssim:.3f}', transform=ax9.transAxes,
             fontsize=10, verticalalignment='top', bbox=dict(boxstyle='round', 
             facecolor='white', alpha=0.9), fontweight='bold')
    
    # Add main title
    fig.suptitle(f'Image Processing Pipeline Demonstration\n'
                 f'Patient: {patient_id} | Sequence: {sequence}', 
                 fontsize=16, fontweight='bold', y=0.98)
    
    # Add pipeline flow annotations
    fig.text(0.05, 0.67, '→', fontsize=40, ha='center', va='center', 
             color='blue', fontweight='bold', rotation=270)
    fig.text(0.05, 0.36, '→', fontsize=40, ha='center', va='center', 
             color='blue', fontweight='bold', rotation=270)
    
    # Save figure
    output_dir = Path('output/figures')
    output_dir.mkdir(exist_ok=True, parents=True)
    
    output_file = output_dir / f'pipeline_demonstration_{patient_id}_{sequence}.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    plt.close()
    
    print(f"\nSaved pipeline figure to: {output_file}")
    return output_file

def main():
    """Generate pipeline figures for available patients"""
    
    print("=" * 80)
    print("CREATING PIPELINE DEMONSTRATION FIGURES")
    print("=" * 80)
    
    # Try to create figures for a few good patients
    patients_to_try = ['Anon11271', 'Anon16167', 'Anon20584']
    sequences = ['T1', 'T2', 'SWI']
    
    created_figures = []
    
    for patient in patients_to_try:
        for sequence in sequences:
            try:
                fig_path = create_pipeline_figure(patient_id=patient, sequence=sequence)
                if fig_path:
                    created_figures.append((patient, sequence, fig_path))
                    break  # Create only one figure per patient
            except Exception as e:
                print(f"Could not create figure for {patient} {sequence}: {e}")
                continue
        
        if len(created_figures) >= 1:  # Create just one comprehensive example
            break
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    if created_figures:
        print(f"\nCreated {len(created_figures)} pipeline demonstration figure(s):\n")
        for patient, sequence, path in created_figures:
            print(f"  - {patient} ({sequence}): {path}")
    else:
        print("\nNo figures could be created. Check if processed data exists.")
    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
