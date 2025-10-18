#!/usr/bin/env python3
"""
Quality Control for Tissue Segmentation Masks

Generate overlay visualizations of GM and WM masks on original brain images
for manual QC review.

Usage:
    python scripts/qc_tissue_masks.py [--subject SUBJECT_ID]

Author: Analysis Pipeline
Date: 2025-10-16
"""

import os
import sys
import argparse
from pathlib import Path
import numpy as np
import nibabel as nib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

# Project paths
BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')
NIFTI_DIR = BASE_DIR / 'output' / 'nifti'
MASK_DIR = BASE_DIR / 'output' / 'brain_masks'
SEG_DIR = BASE_DIR / 'output' / 'tissue_segmentations'
QC_DIR = BASE_DIR / 'output' / 'qc' / 'tissue_masks'

# Ensure QC directory exists
QC_DIR.mkdir(parents=True, exist_ok=True)

# Validated subjects
VALIDATED_SUBJECTS = [
    'Anon10644', 'Anon11271', 'Anon12335', 'Anon13609', 'Anon15062',
    'Anon16167', 'Anon20584', 'Anon21108', 'Anon26462', 'Anon27334',
    'Anon28027', 'Anon28076', 'Anon28584'
]

SEQUENCES = ['T1_conv', 'T1_STAGE', 'T2_conv', 'T2_STAGE', 'SWI_conv', 'SWI_STAGE']


def create_overlay_image(img_data, gm_mask, wm_mask, slice_idx, title):
    """
    Create an overlay visualization showing GM and WM masks on brain image.

    Args:
        img_data: 3D brain image array
        gm_mask: 3D GM mask array
        wm_mask: 3D WM mask array
        slice_idx: Slice index to display
        title: Plot title

    Returns:
        matplotlib figure
    """
    fig = plt.figure(figsize=(20, 5))
    gs = GridSpec(1, 5, figure=fig, wspace=0.3)

    # Get the slice
    img_slice = img_data[:, :, slice_idx]
    gm_slice = gm_mask[:, :, slice_idx]
    wm_slice = wm_mask[:, :, slice_idx]

    # Normalize image for display
    img_slice_norm = (img_slice - np.min(img_slice)) / (np.max(img_slice) - np.min(img_slice) + 1e-8)

    # 1. Original image
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.imshow(np.rot90(img_slice_norm), cmap='gray')
    ax1.set_title('Original Image', fontweight='bold')
    ax1.axis('off')

    # 2. GM mask only
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.imshow(np.rot90(img_slice_norm), cmap='gray', alpha=0.7)
    gm_overlay = np.ma.masked_where(gm_slice == 0, gm_slice)
    ax2.imshow(np.rot90(gm_overlay), cmap='Reds', alpha=0.5)
    ax2.set_title(f'Gray Matter ({np.sum(gm_slice):,} voxels)', fontweight='bold', color='red')
    ax2.axis('off')

    # 3. WM mask only
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.imshow(np.rot90(img_slice_norm), cmap='gray', alpha=0.7)
    wm_overlay = np.ma.masked_where(wm_slice == 0, wm_slice)
    ax3.imshow(np.rot90(wm_overlay), cmap='Blues', alpha=0.5)
    ax3.set_title(f'White Matter ({np.sum(wm_slice):,} voxels)', fontweight='bold', color='blue')
    ax3.axis('off')

    # 4. Both masks overlaid
    ax4 = fig.add_subplot(gs[0, 3])
    ax4.imshow(np.rot90(img_slice_norm), cmap='gray', alpha=0.7)
    ax4.imshow(np.rot90(gm_overlay), cmap='Reds', alpha=0.4)
    ax4.imshow(np.rot90(wm_overlay), cmap='Blues', alpha=0.4)
    ax4.set_title('GM + WM Overlay', fontweight='bold')
    ax4.axis('off')

    # 5. Tissue map
    ax5 = fig.add_subplot(gs[0, 4])
    tissue_map = np.zeros_like(img_slice)
    tissue_map[gm_slice > 0] = 1  # GM = red
    tissue_map[wm_slice > 0] = 2  # WM = blue
    colors = ['black', 'red', 'blue']
    from matplotlib.colors import ListedColormap
    cmap = ListedColormap(colors)
    ax5.imshow(np.rot90(tissue_map), cmap=cmap, vmin=0, vmax=2)
    ax5.set_title('Tissue Classification', fontweight='bold')
    ax5.axis('off')

    # Add legend
    red_patch = mpatches.Patch(color='red', label=f'GM ({np.sum(gm_mask):,} total voxels)')
    blue_patch = mpatches.Patch(color='blue', label=f'WM ({np.sum(wm_mask):,} total voxels)')
    fig.legend(handles=[red_patch, blue_patch], loc='lower center', ncol=2,
               frameon=True, fontsize=11)

    fig.suptitle(title, fontsize=14, fontweight='bold', y=0.98)

    return fig


def qc_subject(subject_id):
    """
    Generate QC images for one subject across all sequences.

    Args:
        subject_id: Patient ID
    """
    print(f"\n{'='*100}")
    print(f"QC for subject: {subject_id}")
    print(f"{'='*100}")

    subject_seg_dir = SEG_DIR / subject_id
    subject_qc_dir = QC_DIR / subject_id
    subject_qc_dir.mkdir(exist_ok=True)

    sequences_processed = 0

    for seq in SEQUENCES:
        # Check if files exist
        nifti_file = NIFTI_DIR / subject_id / f"{seq}.nii.gz"
        gm_mask_file = subject_seg_dir / f"{seq}_GM_mask.nii.gz"
        wm_mask_file = subject_seg_dir / f"{seq}_WM_mask.nii.gz"

        if not nifti_file.exists():
            print(f"  {seq}: NIfTI not found, skipping")
            continue

        if not gm_mask_file.exists() or not wm_mask_file.exists():
            print(f"  {seq}: Tissue masks not found, skipping")
            continue

        print(f"  Processing {seq}...")

        try:
            # Load data
            img = nib.load(nifti_file)
            img_data = img.get_fdata()

            gm_mask = nib.load(gm_mask_file).get_fdata()
            wm_mask = nib.load(wm_mask_file).get_fdata()

            # Get dimensions
            shape = img_data.shape

            # Calculate statistics
            gm_voxels = np.sum(gm_mask > 0)
            wm_voxels = np.sum(wm_mask > 0)
            overlap_voxels = np.sum((gm_mask > 0) & (wm_mask > 0))

            print(f"    Shape: {shape}")
            print(f"    GM voxels: {gm_voxels:,}")
            print(f"    WM voxels: {wm_voxels:,}")
            print(f"    Overlap: {overlap_voxels:,} ({overlap_voxels/(gm_voxels+wm_voxels)*100:.1f}%)")

            # Generate QC images for multiple slices
            slice_indices = [
                shape[2] // 4,      # 25%
                shape[2] // 3,      # 33%
                shape[2] // 2,      # 50% (middle)
                2 * shape[2] // 3,  # 66%
                3 * shape[2] // 4   # 75%
            ]

            for i, slice_idx in enumerate(slice_indices):
                title = f"{subject_id} - {seq} - Slice {slice_idx}/{shape[2]} ({slice_idx/shape[2]*100:.0f}%)"

                fig = create_overlay_image(img_data, gm_mask, wm_mask, slice_idx, title)

                output_file = subject_qc_dir / f"{seq}_slice_{i+1}_of_5.png"
                fig.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
                plt.close(fig)

            print(f"    ✓ Generated 5 QC images")
            sequences_processed += 1

        except Exception as e:
            print(f"    ✗ Error: {e}")
            continue

    print(f"\n{subject_id}: Processed {sequences_processed} sequences")

    return sequences_processed


def create_summary_page(subject_id):
    """
    Create a summary page showing all sequences for one subject.

    Args:
        subject_id: Patient ID
    """
    subject_qc_dir = QC_DIR / subject_id

    # Find all QC images
    qc_images = sorted(list(subject_qc_dir.glob("*_slice_3_of_5.png")))  # Use middle slice

    if len(qc_images) == 0:
        print(f"  No QC images found for {subject_id}")
        return

    print(f"\n  Creating summary page for {subject_id}...")

    # Create summary figure
    n_images = len(qc_images)
    n_cols = min(2, n_images)
    n_rows = (n_images + n_cols - 1) // n_cols

    fig = plt.figure(figsize=(20, 6*n_rows))
    fig.suptitle(f"Tissue Segmentation QC Summary: {subject_id} (Middle Slice)",
                 fontsize=16, fontweight='bold')

    for i, img_path in enumerate(qc_images):
        ax = plt.subplot(n_rows, n_cols, i+1)
        img = plt.imread(img_path)
        ax.imshow(img)
        ax.axis('off')

        # Extract sequence name from filename
        seq_name = img_path.stem.replace('_slice_3_of_5', '')
        ax.set_title(seq_name, fontsize=12, fontweight='bold')

    plt.tight_layout()

    summary_file = subject_qc_dir / f"SUMMARY_{subject_id}_tissue_masks.png"
    plt.savefig(summary_file, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)

    print(f"    ✓ Saved: {summary_file.name}")


def create_master_summary():
    """Create a master summary showing all subjects."""
    print(f"\n{'='*100}")
    print("Creating master summary across all subjects...")
    print(f"{'='*100}")

    # Collect middle slice images from all subjects
    all_summaries = []
    for subject_id in VALIDATED_SUBJECTS:
        subject_qc_dir = QC_DIR / subject_id
        summary_file = subject_qc_dir / f"SUMMARY_{subject_id}_tissue_masks.png"
        if summary_file.exists():
            all_summaries.append(summary_file)

    if len(all_summaries) == 0:
        print("  No summary images found")
        return

    print(f"  Found {len(all_summaries)} subject summaries")

    # Create master summary
    n_subjects = len(all_summaries)
    n_cols = 2
    n_rows = (n_subjects + n_cols - 1) // n_cols

    fig = plt.figure(figsize=(20, 8*n_rows))
    fig.suptitle("Tissue Segmentation QC: All Validated Subjects",
                 fontsize=18, fontweight='bold')

    for i, img_path in enumerate(all_summaries):
        ax = plt.subplot(n_rows, n_cols, i+1)
        img = plt.imread(img_path)
        ax.imshow(img)
        ax.axis('off')

    plt.tight_layout()

    master_file = QC_DIR / "MASTER_SUMMARY_all_subjects.png"
    plt.savefig(master_file, dpi=100, bbox_inches='tight', facecolor='white')
    plt.close(fig)

    print(f"  ✓ Saved: {master_file.name}")


def generate_qc_html(subjects):
    """Generate an HTML file for easy browsing of QC images."""
    print(f"\n{'='*100}")
    print("Generating HTML QC viewer...")
    print(f"{'='*100}")

    html_content = []
    html_content.append("<!DOCTYPE html>")
    html_content.append("<html>")
    html_content.append("<head>")
    html_content.append("  <title>Tissue Segmentation QC</title>")
    html_content.append("  <style>")
    html_content.append("    body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }")
    html_content.append("    h1 { color: #333; }")
    html_content.append("    h2 { color: #666; margin-top: 30px; }")
    html_content.append("    .subject { background-color: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }")
    html_content.append("    .sequence { margin: 20px 0; }")
    html_content.append("    .slice-container { display: flex; flex-wrap: wrap; gap: 10px; }")
    html_content.append("    img { max-width: 100%; height: auto; border: 1px solid #ddd; }")
    html_content.append("    .slice { flex: 1; min-width: 300px; }")
    html_content.append("    .summary-img { width: 100%; max-width: 1200px; }")
    html_content.append("  </style>")
    html_content.append("</head>")
    html_content.append("<body>")
    html_content.append("  <h1>Tissue Segmentation QC: Validated STAGE Study Subjects</h1>")
    html_content.append(f"  <p>Generated: {Path(QC_DIR).absolute()}</p>")
    html_content.append("  <p><strong>Legend:</strong> Red = Gray Matter (GM), Blue = White Matter (WM)</p>")

    # Add master summary
    master_file = QC_DIR / "MASTER_SUMMARY_all_subjects.png"
    if master_file.exists():
        html_content.append("  <div class='subject'>")
        html_content.append("    <h2>Master Summary: All Subjects</h2>")
        html_content.append(f"    <img class='summary-img' src='{master_file.name}' alt='Master Summary'>")
        html_content.append("  </div>")

    # Add each subject
    for subject_id in subjects:
        subject_qc_dir = QC_DIR / subject_id

        if not subject_qc_dir.exists():
            continue

        html_content.append("  <div class='subject'>")
        html_content.append(f"    <h2>{subject_id}</h2>")

        # Add subject summary
        summary_file = subject_qc_dir / f"SUMMARY_{subject_id}_tissue_masks.png"
        if summary_file.exists():
            rel_path = f"{subject_id}/{summary_file.name}"
            html_content.append(f"    <img class='summary-img' src='{rel_path}' alt='{subject_id} Summary'>")

        # Add individual sequences
        for seq in SEQUENCES:
            seq_images = sorted(list(subject_qc_dir.glob(f"{seq}_slice_*.png")))

            if len(seq_images) > 0:
                html_content.append(f"    <div class='sequence'>")
                html_content.append(f"      <h3>{seq}</h3>")
                html_content.append(f"      <div class='slice-container'>")

                for img_path in seq_images:
                    rel_path = f"{subject_id}/{img_path.name}"
                    html_content.append(f"        <div class='slice'>")
                    html_content.append(f"          <img src='{rel_path}' alt='{seq}'>")
                    html_content.append(f"        </div>")

                html_content.append(f"      </div>")
                html_content.append(f"    </div>")

        html_content.append("  </div>")

    html_content.append("</body>")
    html_content.append("</html>")

    # Write HTML file
    html_file = QC_DIR / "tissue_segmentation_qc.html"
    with open(html_file, 'w') as f:
        f.write('\n'.join(html_content))

    print(f"  ✓ Saved: {html_file.name}")
    print(f"\n  Open in browser: file://{html_file.absolute()}")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='QC for tissue segmentation masks')
    parser.add_argument('--subject', type=str, help='Process specific subject only')
    parser.add_argument('--skip-images', action='store_true', help='Skip image generation, only create HTML')

    args = parser.parse_args()

    print("=" * 100)
    print("Tissue Segmentation QC")
    print("=" * 100)
    print(f"Output directory: {QC_DIR}")
    print("=" * 100)

    subjects = [args.subject] if args.subject else VALIDATED_SUBJECTS

    if not args.skip_images:
        # Process each subject
        total_processed = 0
        for subject_id in subjects:
            try:
                n = qc_subject(subject_id)
                total_processed += n

                # Create subject summary
                create_summary_page(subject_id)

            except Exception as e:
                print(f"Error processing {subject_id}: {e}")
                continue

        print(f"\n{'='*100}")
        print(f"Total sequences processed: {total_processed}")
        print(f"{'='*100}")

        # Create master summary
        if not args.subject:
            create_master_summary()

    # Generate HTML viewer
    generate_qc_html(subjects)

    print(f"\n{'='*100}")
    print("QC Complete!")
    print(f"{'='*100}")
    print(f"\nQC files saved to: {QC_DIR}")
    print(f"\nTo view:")
    print(f"  1. Open: file://{QC_DIR}/tissue_segmentation_qc.html")
    print(f"  2. Or browse images in: {QC_DIR}")
    print(f"{'='*100}")


if __name__ == '__main__':
    main()
