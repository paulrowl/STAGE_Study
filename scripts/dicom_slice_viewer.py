#!/usr/bin/env python3
"""
Interactive DICOM Slice Viewer
Allows detailed inspection of individual sequences with slice navigation
"""

import pydicom
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, RadioButtons
from pathlib import Path
import sys

class InteractiveDICOMViewer:
    """Interactive viewer with slice navigation for each sequence"""

    def __init__(self, organized_dir):
        self.organized_dir = Path(organized_dir)
        self.subjects = sorted([d for d in self.organized_dir.iterdir() if d.is_dir()])

        if not self.subjects:
            print(f"No subjects found in {organized_dir}")
            sys.exit(1)

        self.current_subject_idx = 0
        self.sequence_types = ['T1_conv', 'T2_conv', 'SWI_conv', 'T1_STAGE', 'T2_STAGE', 'SWI_STAGE']
        self.current_sequence = 'T1_conv'
        self.current_slice_idx = 0
        self.files = []

        # Create figure
        self.fig = plt.figure(figsize=(15, 10))

        # Main image axis
        self.ax_image = plt.subplot(1, 1, 1, position=[0.25, 0.15, 0.7, 0.75])
        self.im = None

        # Add sequence selector (radio buttons)
        ax_radio = plt.axes([0.02, 0.15, 0.15, 0.75])
        self.radio = RadioButtons(ax_radio, self.sequence_types, active=0)
        self.radio.on_clicked(self.select_sequence)

        # Add navigation buttons
        ax_prev_subj = plt.axes([0.1, 0.02, 0.12, 0.04])
        ax_next_subj = plt.axes([0.78, 0.02, 0.12, 0.04])
        self.btn_prev_subj = Button(ax_prev_subj, '◄ Previous Subject')
        self.btn_next_subj = Button(ax_next_subj, 'Next Subject ►')
        self.btn_prev_subj.on_clicked(self.prev_subject)
        self.btn_next_subj.on_clicked(self.next_subject)

        # Add slice navigation buttons
        ax_prev_slice = plt.axes([0.35, 0.02, 0.08, 0.04])
        ax_next_slice = plt.axes([0.57, 0.02, 0.08, 0.04])
        self.btn_prev_slice = Button(ax_prev_slice, '◄ Slice')
        self.btn_next_slice = Button(ax_next_slice, 'Slice ►')
        self.btn_prev_slice.on_clicked(self.prev_slice)
        self.btn_next_slice.on_clicked(self.next_slice)

        # Info text
        self.info_text = self.fig.text(0.5, 0.08, '', ha='center', va='center', fontsize=10,
                                       bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))

        # Enable keyboard navigation
        self.fig.canvas.mpl_connect('key_press_event', self.on_key_press)

        # Load first subject
        self.load_subject()

    def on_key_press(self, event):
        """Handle keyboard shortcuts"""
        if event.key == 'left':
            self.prev_slice(None)
        elif event.key == 'right':
            self.next_slice(None)
        elif event.key == 'up':
            # Move to previous sequence
            try:
                current_idx = self.sequence_types.index(self.current_sequence)
                if current_idx > 0:
                    self.current_sequence = self.sequence_types[current_idx - 1]
                    self.radio.set_active(current_idx - 1)
                    self.load_sequence()
            except:
                pass
        elif event.key == 'down':
            # Move to next sequence
            try:
                current_idx = self.sequence_types.index(self.current_sequence)
                if current_idx < len(self.sequence_types) - 1:
                    self.current_sequence = self.sequence_types[current_idx + 1]
                    self.radio.set_active(current_idx + 1)
                    self.load_sequence()
            except:
                pass

    def read_dicom_slice(self, file_path):
        """Read DICOM file and return pixel array and metadata"""
        try:
            ds = pydicom.dcmread(file_path, force=True)
            img = ds.pixel_array.astype(float)

            # Normalize to 0-1 range
            img_min, img_max = np.percentile(img, [1, 99])  # Use percentiles for better contrast
            if img_max > img_min:
                img = np.clip(img, img_min, img_max)
                img = (img - img_min) / (img_max - img_min)

            metadata = {
                'SeriesDescription': str(getattr(ds, 'SeriesDescription', 'N/A')),
                'SeriesNumber': str(getattr(ds, 'SeriesNumber', 'N/A')),
                'SliceThickness': str(getattr(ds, 'SliceThickness', 'N/A')),
                'TE': str(getattr(ds, 'EchoTime', 'N/A')),
                'TR': str(getattr(ds, 'RepetitionTime', 'N/A')),
                'FlipAngle': str(getattr(ds, 'FlipAngle', 'N/A')),
                'ImageType': str(getattr(ds, 'ImageType', 'N/A')),
                'PixelBandwidth': str(getattr(ds, 'PixelBandwidth', 'N/A')),
            }

            return img, metadata
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return None, None

    def load_subject(self):
        """Load current subject"""
        self.load_sequence()

    def load_sequence(self):
        """Load current sequence"""
        if not self.subjects:
            return

        subject = self.subjects[self.current_subject_idx]
        seq_dir = subject / self.current_sequence

        # Update title
        title = f'{subject.name} - {self.current_sequence} ({self.current_subject_idx + 1}/{len(self.subjects)})'
        self.fig.suptitle(title, fontsize=14, fontweight='bold')

        # Clear previous image
        self.ax_image.clear()

        if not seq_dir.exists():
            self.ax_image.text(0.5, 0.5, f'{self.current_sequence}\nNOT PRESENT',
                              ha='center', va='center', fontsize=20, color='red',
                              transform=self.ax_image.transAxes)
            self.ax_image.axis('off')
            self.info_text.set_text('This sequence is not available for this subject.')
            self.files = []
            plt.draw()
            return

        # Get all files
        self.files = sorted([f for f in seq_dir.iterdir() if f.is_file() and not f.name.startswith('.')])

        if not self.files:
            self.ax_image.text(0.5, 0.5, f'{self.current_sequence}\nNO FILES',
                              ha='center', va='center', fontsize=20, color='red',
                              transform=self.ax_image.transAxes)
            self.ax_image.axis('off')
            self.info_text.set_text('')
            plt.draw()
            return

        # Start at middle slice
        self.current_slice_idx = len(self.files) // 2
        self.display_slice()

    def display_slice(self):
        """Display current slice"""
        if not self.files:
            return

        # Ensure slice index is valid
        self.current_slice_idx = max(0, min(self.current_slice_idx, len(self.files) - 1))

        # Load and display
        img, metadata = self.read_dicom_slice(self.files[self.current_slice_idx])

        self.ax_image.clear()

        if img is not None:
            self.im = self.ax_image.imshow(img, cmap='gray', aspect='auto')
            self.ax_image.axis('off')

            # Update info text
            info = (f"Slice {self.current_slice_idx + 1}/{len(self.files)} | "
                   f"Series: {metadata['SeriesDescription']} | "
                   f"TE: {metadata['TE']} ms | TR: {metadata['TR']} ms | "
                   f"Flip: {metadata['FlipAngle']}° | "
                   f"Type: {metadata['ImageType'][:50]}")

            self.info_text.set_text(info + '\n[←/→ arrows: navigate slices | ↑/↓ arrows: change sequence]')
        else:
            self.ax_image.text(0.5, 0.5, 'ERROR LOADING IMAGE',
                              ha='center', va='center', fontsize=20, color='red',
                              transform=self.ax_image.transAxes)
            self.ax_image.axis('off')

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

    def prev_slice(self, event):
        """Go to previous slice"""
        if self.files and self.current_slice_idx > 0:
            self.current_slice_idx -= 1
            self.display_slice()

    def next_slice(self, event):
        """Go to next slice"""
        if self.files and self.current_slice_idx < len(self.files) - 1:
            self.current_slice_idx += 1
            self.display_slice()

    def select_sequence(self, label):
        """Handle sequence selection"""
        self.current_sequence = label
        self.load_sequence()

    def show(self):
        """Display the viewer"""
        plt.show()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Interactive DICOM slice viewer with navigation'
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
        script_dir = Path(__file__).parent.parent
        organized_dir = script_dir / organized_dir

    if not organized_dir.exists():
        print(f"Error: Directory not found: {organized_dir}")
        sys.exit(1)

    print(f"Loading organized data from: {organized_dir}")
    print("\nKeyboard shortcuts:")
    print("  ← / → : Navigate between slices")
    print("  ↑ / ↓ : Switch between sequences")
    print()

    viewer = InteractiveDICOMViewer(organized_dir)
    viewer.show()


if __name__ == '__main__':
    main()
