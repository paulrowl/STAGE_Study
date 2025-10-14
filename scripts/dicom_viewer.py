#!/usr/bin/env python3
"""
DICOM Classification Viewer
Visual inspection tool for verifying DICOM sequence classification
"""

import pydicom
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, Slider
from pathlib import Path
import sys

class DICOMClassificationViewer:
    """Interactive viewer for checking DICOM classification results"""

    def __init__(self, organized_dir):
        self.organized_dir = Path(organized_dir)
        self.subjects = sorted([d for d in self.organized_dir.iterdir() if d.is_dir()])
        self.current_subject_idx = 0
        self.current_slice = {}

        if not self.subjects:
            print(f"No subjects found in {organized_dir}")
            sys.exit(1)

        # Create figure
        self.fig = plt.figure(figsize=(18, 10))
        self.fig.suptitle('DICOM Classification Viewer', fontsize=16, fontweight='bold')

        # Create grid for images
        self.sequence_types = ['T1_conv', 'T2_conv', 'SWI_conv', 'T1_STAGE', 'T2_STAGE', 'SWI_STAGE']
        self.axes = {}
        self.images = {}
        self.texts = {}

        # Create 2 rows x 3 columns grid
        for idx, seq_type in enumerate(self.sequence_types):
            row = idx // 3
            col = idx % 3
            ax = plt.subplot(2, 3, idx + 1)
            self.axes[seq_type] = ax
            ax.set_title(seq_type, fontweight='bold', fontsize=12)
            ax.axis('off')

            # Add text box for info
            text = ax.text(0.5, -0.1, '', transform=ax.transAxes,
                          ha='center', va='top', fontsize=8,
                          bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            self.texts[seq_type] = text

        plt.subplots_adjust(left=0.05, right=0.95, top=0.92, bottom=0.15, hspace=0.3, wspace=0.2)

        # Add navigation buttons
        ax_prev = plt.axes([0.2, 0.02, 0.1, 0.04])
        ax_next = plt.axes([0.7, 0.02, 0.1, 0.04])
        self.btn_prev = Button(ax_prev, 'Previous Subject')
        self.btn_next = Button(ax_next, 'Next Subject')
        self.btn_prev.on_clicked(self.prev_subject)
        self.btn_next.on_clicked(self.next_subject)

        # Add slice navigation info
        ax_info = plt.axes([0.35, 0.02, 0.3, 0.04])
        ax_info.axis('off')
        self.info_text = ax_info.text(0.5, 0.5, '', ha='center', va='center', fontsize=10)

        # Load first subject
        self.load_subject()

    def read_dicom_slice(self, file_path):
        """Read DICOM file and return pixel array and metadata"""
        try:
            ds = pydicom.dcmread(file_path, force=True)
            img = ds.pixel_array.astype(float)

            # Normalize to 0-1 range
            img_min, img_max = img.min(), img.max()
            if img_max > img_min:
                img = (img - img_min) / (img_max - img_min)

            metadata = {
                'SeriesDescription': getattr(ds, 'SeriesDescription', 'N/A'),
                'SliceThickness': getattr(ds, 'SliceThickness', 'N/A'),
                'TE': getattr(ds, 'EchoTime', 'N/A'),
                'TR': getattr(ds, 'RepetitionTime', 'N/A'),
                'FlipAngle': getattr(ds, 'FlipAngle', 'N/A'),
            }

            return img, metadata
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return None, None

    def load_subject(self):
        """Load and display data for current subject"""
        if not self.subjects:
            return

        subject = self.subjects[self.current_subject_idx]
        self.fig.suptitle(f'DICOM Classification Viewer - {subject.name} ({self.current_subject_idx + 1}/{len(self.subjects)})',
                         fontsize=16, fontweight='bold')

        for seq_type in self.sequence_types:
            ax = self.axes[seq_type]
            text = self.texts[seq_type]

            seq_dir = subject / seq_type

            # Clear previous image
            ax.clear()
            ax.set_title(seq_type, fontweight='bold', fontsize=12)
            ax.axis('off')

            if not seq_dir.exists():
                ax.text(0.5, 0.5, 'NOT PRESENT', ha='center', va='center',
                       transform=ax.transAxes, fontsize=14, color='red')
                text.set_text('')
                continue

            # Get middle slice
            files = sorted([f for f in seq_dir.iterdir() if f.is_file() and not f.name.startswith('.')])

            if not files:
                ax.text(0.5, 0.5, 'NO FILES', ha='center', va='center',
                       transform=ax.transAxes, fontsize=14, color='red')
                text.set_text('')
                continue

            # Load middle slice
            middle_idx = len(files) // 2
            img, metadata = self.read_dicom_slice(files[middle_idx])

            if img is not None:
                ax.imshow(img, cmap='gray', aspect='auto')

                # Create info text
                info_lines = [
                    f"{len(files)} files",
                    f"Series: {metadata['SeriesDescription'][:30]}",
                    f"TE: {metadata['TE']}, TR: {metadata['TR']}"
                ]
                text.set_text('\n'.join(info_lines))
            else:
                ax.text(0.5, 0.5, 'ERROR LOADING', ha='center', va='center',
                       transform=ax.transAxes, fontsize=14, color='red')
                text.set_text('')

        self.info_text.set_text('Use buttons to navigate between subjects. Close window when done.')
        plt.draw()

    def prev_subject(self, event):
        """Go to previous subject"""
        if self.current_subject_idx > 0:
            self.current_subject_idx -= 1
            self.load_subject()

    def next_subject(self, event):
        """Go to next subject"""
        if self.current_subject_idx < len(self.subjects) - 1:
            self.current_subject_idx += 1
            self.load_subject()

    def show(self):
        """Display the viewer"""
        plt.show()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Visual inspector for DICOM classification results'
    )
    parser.add_argument(
        'organized_dir',
        type=str,
        nargs='?',
        default='data/raw/organized',
        help='Directory containing organized subjects (default: data/raw/organized)'
    )

    args = parser.parse_args()

    # Resolve path
    organized_dir = Path(args.organized_dir)
    if not organized_dir.is_absolute():
        # Try relative to script directory
        script_dir = Path(__file__).parent.parent
        organized_dir = script_dir / organized_dir

    if not organized_dir.exists():
        print(f"Error: Directory not found: {organized_dir}")
        sys.exit(1)

    print(f"Loading organized data from: {organized_dir}")
    viewer = DICOMClassificationViewer(organized_dir)
    viewer.show()


if __name__ == '__main__':
    main()
