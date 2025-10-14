#!/usr/bin/env python3
"""
Wait for pipeline completion and generate comparison statistics
between normalized and non-normalized results.
"""

import os
import sys
import time
import subprocess
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

def is_pipeline_running():
    """Check if the pipeline is still running"""
    try:
        result = subprocess.run(['pgrep', '-f', 'master_pipeline.py'],
                              capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def wait_for_completion():
    """Wait for pipeline to complete with progress updates"""
    print("=" * 80)
    print("WAITING FOR PIPELINE COMPLETION")
    print("=" * 80)
    print("")

    start_time = time.time()
    last_count = 0

    while is_pipeline_running():
        # Count metrics files
        try:
            metrics_files = list(Path('output/metrics').glob('**/*_metrics.csv'))
            count = len(metrics_files)

            if count != last_count:
                elapsed = time.time() - start_time
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Progress: {count} metrics calculated ({elapsed/60:.1f} min elapsed)")
                last_count = count
        except:
            pass

        time.sleep(30)  # Check every 30 seconds

    elapsed = time.time() - start_time
    print(f"\n✓ Pipeline completed in {elapsed/60:.1f} minutes")
    print("")

def load_metrics(metrics_dir):
    """Load all metrics files from a directory"""
    metrics_files = list(Path(metrics_dir).glob('**/*_metrics.csv'))

    if not metrics_files:
        return None

    # Load all metrics
    all_metrics = []
    for file in metrics_files:
        try:
            df = pd.read_csv(file)
            all_metrics.append(df)
        except Exception as e:
            print(f"Warning: Could not load {file}: {e}")

    if not all_metrics:
        return None

    return pd.concat(all_metrics, ignore_index=True)

def compare_metrics(normalized_df, non_normalized_df):
    """Compare metrics between normalized and non-normalized results"""

    print("=" * 80)
    print("COMPARISON: NORMALIZED vs NON-NORMALIZED RESULTS")
    print("=" * 80)
    print("")

    # Metrics to compare
    metrics = ['ssim_mean', 'ncc', 'pearson_r', 'psnr', 'mutual_information']

    # Extract sequence type from comparison name
    def get_sequence_type(comparison):
        if 'T1' in comparison:
            return 'T1'
        elif 'T2' in comparison:
            return 'T2'
        elif 'SWI' in comparison:
            return 'SWI'
        return 'Unknown'

    normalized_df['sequence_type'] = normalized_df['comparison'].apply(get_sequence_type)
    non_normalized_df['sequence_type'] = non_normalized_df['comparison'].apply(get_sequence_type)

    # Group by sequence type
    for seq_type in ['T1', 'T2', 'SWI']:
        norm_data = normalized_df[normalized_df['sequence_type'] == seq_type]
        non_norm_data = non_normalized_df[non_normalized_df['sequence_type'] == seq_type]

        if len(norm_data) == 0 or len(non_norm_data) == 0:
            continue

        print(f"\n{seq_type}-weighted Sequences (n={len(norm_data)}):")
        print("-" * 80)
        print(f"{'Metric':<25} {'Non-Normalized':<25} {'Normalized':<25} {'Change':<15}")
        print("-" * 80)

        for metric in metrics:
            if metric in norm_data.columns and metric in non_norm_data.columns:
                non_norm_mean = non_norm_data[metric].mean()
                non_norm_std = non_norm_data[metric].std()
                norm_mean = norm_data[metric].mean()
                norm_std = norm_data[metric].std()

                change = norm_mean - non_norm_mean
                change_pct = (change / abs(non_norm_mean) * 100) if non_norm_mean != 0 else 0

                print(f"{metric:<25} {non_norm_mean:>7.4f} ± {non_norm_std:<7.4f}   "
                      f"{norm_mean:>7.4f} ± {norm_std:<7.4f}   "
                      f"{change:>+7.4f} ({change_pct:>+6.1f}%)")

    print("\n" + "=" * 80)
    print("KEY OBSERVATIONS:")
    print("=" * 80)

    # Calculate overall improvements
    for metric in ['pearson_r', 'ncc', 'ssim_mean']:
        if metric in normalized_df.columns and metric in non_normalized_df.columns:
            non_norm_mean = non_normalized_df[metric].mean()
            norm_mean = normalized_df[metric].mean()
            change = norm_mean - non_norm_mean
            change_pct = (change / abs(non_norm_mean) * 100) if non_norm_mean != 0 else 0

            direction = "improved" if change > 0 else "decreased"
            print(f"  - {metric.upper()}: {direction} by {abs(change):.4f} ({abs(change_pct):.1f}%)")

    print("")

def generate_comparison_report():
    """Generate detailed comparison report"""

    print("\n" + "=" * 80)
    print("GENERATING COMPARISON REPORT")
    print("=" * 80)
    print("")

    # Load metrics
    print("Loading metrics...")
    normalized_metrics = load_metrics('output/metrics')
    non_normalized_metrics = load_metrics('output/metrics_without_normalization')

    if normalized_metrics is None:
        print("Error: Could not load normalized metrics")
        return

    if non_normalized_metrics is None:
        print("Error: Could not load non-normalized metrics")
        return

    print(f"  - Normalized: {len(normalized_metrics)} comparisons")
    print(f"  - Non-normalized: {len(non_normalized_metrics)} comparisons")
    print("")

    # Compare metrics
    compare_metrics(normalized_metrics, non_normalized_metrics)

    # Save detailed comparison
    output_file = f'output/statistics/normalization_comparison_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

    # Merge dataframes for comparison
    comparison_df = pd.DataFrame({
        'comparison': normalized_metrics['comparison'],
        'ssim_normalized': normalized_metrics['ssim_mean'],
        'ssim_non_normalized': non_normalized_metrics['ssim_mean'],
        'pearson_normalized': normalized_metrics['pearson_r'],
        'pearson_non_normalized': non_normalized_metrics['pearson_r'],
        'ncc_normalized': normalized_metrics['ncc'],
        'ncc_non_normalized': non_normalized_metrics['ncc'],
    })

    comparison_df['ssim_change'] = comparison_df['ssim_normalized'] - comparison_df['ssim_non_normalized']
    comparison_df['pearson_change'] = comparison_df['pearson_normalized'] - comparison_df['pearson_non_normalized']
    comparison_df['ncc_change'] = comparison_df['ncc_normalized'] - comparison_df['ncc_non_normalized']

    comparison_df.to_csv(output_file, index=False)
    print(f"\nDetailed comparison saved to: {output_file}")
    print("")

def generate_plots():
    """Run the plotting script"""
    print("\n" + "=" * 80)
    print("GENERATING PLOTS")
    print("=" * 80)
    print("")

    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, 'scripts/plot_normalization_comparison.py'],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            print(result.stdout)
            print("\n✓ Plots generated successfully")
        else:
            print(f"Warning: Plotting script returned error code {result.returncode}")
            if result.stderr:
                print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"Warning: Could not generate plots: {e}")
        print("You can manually run: python scripts/plot_normalization_comparison.py")

def main():
    # Wait for pipeline completion
    if is_pipeline_running():
        print("Pipeline is currently running...")
        wait_for_completion()
    else:
        print("Pipeline is not running. Proceeding with analysis...")

    # Small delay to ensure files are written
    time.sleep(5)

    # Generate comparison
    generate_comparison_report()

    # Generate plots
    generate_plots()

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print("")
    print("Results available:")
    print("  1. Comparison statistics: output/statistics/normalization_comparison_*.csv")
    print("  2. Visual plots: output/plots/")
    print("  3. Key summary figure: output/plots/SUMMARY_normalization_impact.png")
    print("")
    print("To view plots on Mac:")
    print("  open output/plots/SUMMARY_normalization_impact.png")
    print("")

if __name__ == '__main__':
    main()
