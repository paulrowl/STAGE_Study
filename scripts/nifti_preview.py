#!/usr/bin/env python3
"""
NIFTI Preview Tool
Quick visualization of NIFTI files showing orthogonal slices and metadata
"""

import sys
import argparse
import nibabel as nib
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from pathlib import Path


def load_nifti(filepath):
    """Load NIFTI file and return image data and header."""
    try:
        img = nib.load(filepath)
        data = img.get_fdata()
        return img, data
    except Exception as e:
        print(f"Error loading NIFTI file: {e}")
        sys.exit(1)


def normalize_slice(slice_data):
    """Normalize slice data to 0-1 range for display."""
    if slice_data.size == 0:
        return slice_data

    # Remove NaN and Inf values
    slice_data = np.nan_to_num(slice_data, nan=0.0, posinf=0.0, neginf=0.0)

    # Get percentile range for robust normalization
    vmin, vmax = np.percentile(slice_data, [2, 98])

    if vmax > vmin:
        normalized = (slice_data - vmin) / (vmax - vmin)
        normalized = np.clip(normalized, 0, 1)
    else:
        normalized = np.zeros_like(slice_data)

    return normalized


def get_orthogonal_slices(data):
    """Extract middle slices from each orthogonal plane."""
    # Get middle slice indices
    mid_axial = data.shape[2] // 2
    mid_coronal = data.shape[1] // 2
    mid_sagittal = data.shape[0] // 2

    # Extract slices
    axial = data[:, :, mid_axial]
    coronal = data[:, mid_coronal, :]
    sagittal = data[mid_sagittal, :, :]

    # Normalize for display
    axial_norm = normalize_slice(axial)
    coronal_norm = normalize_slice(coronal)
    sagittal_norm = normalize_slice(sagittal)

    return {
        'axial': (axial_norm.T, mid_axial),
        'coronal': (coronal_norm.T, mid_coronal),
        'sagittal': (sagittal_norm.T, mid_sagittal)
    }


def format_header_info(img):
    """Format essential header information for display."""
    header = img.header

    info = []
    info.append(f"Dimensions: {img.shape}")
    info.append(f"Data type: {header.get_data_dtype()}")
    info.append(f"Voxel size: {header.get_zooms()[:3]} mm")

    # Affine info
    info.append(f"\nOrientation:")
    info.append(f"{nib.aff2axcodes(img.affine)}")

    # Data range
    data = img.get_fdata()
    data_clean = np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)
    info.append(f"\nIntensity range:")
    info.append(f"  Min: {data_clean.min():.2f}")
    info.append(f"  Max: {data_clean.max():.2f}")
    info.append(f"  Mean: {data_clean.mean():.2f}")
    info.append(f"  Std: {data_clean.std():.2f}")

    return '\n'.join(info)


def create_preview(filepath, save_path=None, show=True):
    """Create a multi-panel preview of the NIFTI file."""
    # Load NIFTI
    img, data = load_nifti(filepath)

    # Get orthogonal slices
    slices = get_orthogonal_slices(data)

    # Create figure
    fig = plt.figure(figsize=(16, 10))
    gs = GridSpec(2, 3, figure=fig, hspace=0.3, wspace=0.3)

    # Title
    filename = Path(filepath).name
    fig.suptitle(f'NIFTI Preview: {filename}', fontsize=16, fontweight='bold')

    # Plot axial slice
    ax1 = fig.add_subplot(gs[0, 0])
    axial_img, axial_idx = slices['axial']
    ax1.imshow(axial_img, cmap='gray', aspect='auto')
    ax1.set_title(f'Axial (slice {axial_idx}/{data.shape[2]})', fontsize=12)
    ax1.axis('off')

    # Plot coronal slice
    ax2 = fig.add_subplot(gs[0, 1])
    coronal_img, coronal_idx = slices['coronal']
    ax2.imshow(coronal_img, cmap='gray', aspect='auto')
    ax2.set_title(f'Coronal (slice {coronal_idx}/{data.shape[1]})', fontsize=12)
    ax2.axis('off')

    # Plot sagittal slice
    ax3 = fig.add_subplot(gs[0, 2])
    sagittal_img, sagittal_idx = slices['sagittal']
    ax3.imshow(sagittal_img, cmap='gray', aspect='auto')
    ax3.set_title(f'Sagittal (slice {sagittal_idx}/{data.shape[0]})', fontsize=12)
    ax3.axis('off')

    # Histogram
    ax4 = fig.add_subplot(gs[1, 0])
    data_clean = np.nan_to_num(data.flatten(), nan=0.0, posinf=0.0, neginf=0.0)
    data_clean = data_clean[data_clean != 0]  # Remove zero background
    if len(data_clean) > 0:
        ax4.hist(data_clean, bins=100, color='steelblue', alpha=0.7, edgecolor='black')
        ax4.set_title('Intensity Distribution', fontsize=12)
        ax4.set_xlabel('Intensity')
        ax4.set_ylabel('Frequency')
        ax4.grid(True, alpha=0.3)

    # Header information
    ax5 = fig.add_subplot(gs[1, 1:])
    header_text = format_header_info(img)
    ax5.text(0.05, 0.95, header_text, transform=ax5.transAxes,
             fontsize=11, verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    ax5.set_title('Header Information', fontsize=12)
    ax5.axis('off')

    # Save or show
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Preview saved to: {save_path}")

    if show:
        plt.show()
    else:
        plt.close()


def main():
    parser = argparse.ArgumentParser(
        description='Generate preview images for NIFTI files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview a NIFTI file interactively
  %(prog)s brain.nii.gz

  # Save preview to PNG without displaying
  %(prog)s brain.nii.gz --save brain_preview.png --no-show

  # Preview multiple files
  for f in *.nii.gz; do %(prog)s "$f" --save "${f%.nii.gz}_preview.png" --no-show; done
        """
    )

    parser.add_argument('nifti_file', type=str,
                        help='Path to NIFTI file (.nii or .nii.gz)')
    parser.add_argument('--save', type=str, default=None,
                        help='Save preview to file (PNG recommended)')
    parser.add_argument('--no-show', action='store_true',
                        help='Do not display preview interactively')

    args = parser.parse_args()

    # Check if file exists
    filepath = Path(args.nifti_file)
    if not filepath.exists():
        print(f"Error: File not found: {filepath}")
        sys.exit(1)

    # Create preview
    create_preview(
        filepath,
        save_path=args.save,
        show=not args.no_show
    )


if __name__ == '__main__':
    main()
