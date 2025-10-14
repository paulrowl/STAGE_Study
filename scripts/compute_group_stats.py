#!/usr/bin/env python3
"""
STAGE Study - Compute Group Statistics
======================================
Computes group-level statistics across all patients and generates reports.

This script:
1. Collects all individual patient metrics from output/metrics/
2. Computes group statistics (mean, std, median, quartiles)
3. Performs paired t-tests for conventional vs STAGE sequences
4. Identifies patients with missing/incomplete data
5. Generates comprehensive CSV reports

Usage:
    python compute_group_stats.py
"""

import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from scipy import stats
import json
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class GroupStatsCalculator:
    """Computes group statistics for STAGE study"""

    def __init__(self, metrics_dir, output_dir):
        self.metrics_dir = Path(metrics_dir)
        self.output_dir = Path(output_dir)
        self.logger = logging.getLogger(__name__)

        # Expected sequences
        self.expected_pairs = [
            ('T1_conv', 'T1_STAGE'),
            ('T2_conv', 'T2_STAGE'),
            ('SWI_conv', 'SWI_STAGE')
        ]

    def collect_patient_metrics(self):
        """Collect all patient metrics from individual CSV files"""
        self.logger.info("Collecting patient metrics...")

        all_metrics = []
        patient_status = []

        # Find all patient folders
        patient_folders = [d for d in self.metrics_dir.iterdir() if d.is_dir()]

        for patient_folder in sorted(patient_folders):
            patient_id = patient_folder.name
            patient_data = {'patient_id': patient_id}
            sequences_processed = []

            # Look for metric CSV files
            metric_files = list(patient_folder.glob('*_metrics.csv'))

            for metric_file in metric_files:
                # Read metrics
                try:
                    df = pd.read_csv(metric_file)
                    if len(df) > 0:
                        metrics = df.iloc[0].to_dict()
                        comparison = metrics.get('comparison', '')

                        # Extract sequence names from comparison
                        # Format: PatientID_SeqA_vs_SeqB
                        if '_vs_' in comparison:
                            seq_pair = comparison.split('_vs_')[-2:]
                            seq_pair = ('_'.join(seq_pair[0].split('_')[-2:]),
                                       '_'.join(seq_pair[1].split('_')[:2]))

                            sequences_processed.append(seq_pair)

                            # Add to all_metrics with patient_id
                            metrics['patient_id'] = patient_id
                            metrics['seq_pair'] = f"{seq_pair[0]}_vs_{seq_pair[1]}"
                            all_metrics.append(metrics)

                except Exception as e:
                    self.logger.warning(f"Error reading {metric_file}: {e}")

            # Track patient status
            patient_status.append({
                'patient_id': patient_id,
                'num_sequences_processed': len(sequences_processed),
                'sequences': ', '.join([f"{s[0]} vs {s[1]}" for s in sequences_processed]),
                'has_T1': any('T1' in str(s) for s in sequences_processed),
                'has_T2': any('T2' in str(s) for s in sequences_processed),
                'has_SWI': any('SWI' in str(s) for s in sequences_processed),
                'complete': len(sequences_processed) >= 2  # At least T1 and T2
            })

        self.logger.info(f"Collected metrics from {len(patient_folders)} patients")
        self.logger.info(f"Total comparisons: {len(all_metrics)}")

        return pd.DataFrame(all_metrics), pd.DataFrame(patient_status)

    def compute_group_statistics(self, metrics_df):
        """Compute group-level statistics for each sequence pair"""
        self.logger.info("Computing group statistics...")

        # Key metrics to analyze
        key_metrics = [
            'ssim_mean', 'ncc', 'pearson_r', 'mutual_information',
            'mae', 'rmse', 'psnr',
            'conv_snr', 'stage_snr', 'conv_cnr', 'stage_cnr',
            'conv_mean', 'stage_mean', 'conv_std', 'stage_std',
            'conv_cv', 'stage_cv'
        ]

        group_stats = []

        # Group by sequence pair
        for seq_pair, group in metrics_df.groupby('seq_pair'):
            self.logger.info(f"  Processing: {seq_pair} (n={len(group)})")

            stats_row = {
                'sequence_pair': seq_pair,
                'n_patients': len(group)
            }

            # Compute statistics for each metric
            for metric in key_metrics:
                if metric in group.columns:
                    values = group[metric].dropna()
                    if len(values) > 0:
                        stats_row[f'{metric}_mean'] = float(np.mean(values))
                        stats_row[f'{metric}_std'] = float(np.std(values))
                        stats_row[f'{metric}_median'] = float(np.median(values))
                        stats_row[f'{metric}_q25'] = float(np.percentile(values, 25))
                        stats_row[f'{metric}_q75'] = float(np.percentile(values, 75))
                        stats_row[f'{metric}_min'] = float(np.min(values))
                        stats_row[f'{metric}_max'] = float(np.max(values))

            # Paired comparisons: conv vs stage
            paired_metrics = [
                ('conv_snr', 'stage_snr', 'SNR'),
                ('conv_cnr', 'stage_cnr', 'CNR'),
                ('conv_mean', 'stage_mean', 'Mean Intensity'),
                ('conv_std', 'stage_std', 'Std Dev'),
                ('conv_cv', 'stage_cv', 'Coefficient of Variation')
            ]

            for conv_col, stage_col, metric_name in paired_metrics:
                if conv_col in group.columns and stage_col in group.columns:
                    conv_vals = group[conv_col].dropna()
                    stage_vals = group[stage_col].dropna()

                    # Match indices
                    common_idx = conv_vals.index.intersection(stage_vals.index)
                    if len(common_idx) > 1:
                        conv_paired = conv_vals[common_idx]
                        stage_paired = stage_vals[common_idx]

                        # Paired t-test
                        t_stat, p_value = stats.ttest_rel(conv_paired, stage_paired)
                        stats_row[f'{metric_name.lower().replace(" ", "_")}_ttest_t'] = float(t_stat)
                        stats_row[f'{metric_name.lower().replace(" ", "_")}_ttest_p'] = float(p_value)

                        # Effect size (Cohen's d for paired samples)
                        diff = conv_paired - stage_paired
                        cohens_d = np.mean(diff) / np.std(diff)
                        stats_row[f'{metric_name.lower().replace(" ", "_")}_cohens_d'] = float(cohens_d)

            group_stats.append(stats_row)

        return pd.DataFrame(group_stats)

    def generate_summary_report(self, patient_status_df):
        """Generate summary report of patient completion status"""
        self.logger.info("Generating summary report...")

        summary = {
            'total_patients': len(patient_status_df),
            'complete_patients': int(patient_status_df['complete'].sum()),
            'incomplete_patients': int((~patient_status_df['complete']).sum()),
            'patients_with_T1': int(patient_status_df['has_T1'].sum()),
            'patients_with_T2': int(patient_status_df['has_T2'].sum()),
            'patients_with_SWI': int(patient_status_df['has_SWI'].sum()),
        }

        self.logger.info(f"\n{'='*60}")
        self.logger.info("SUMMARY REPORT")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Total patients: {summary['total_patients']}")
        self.logger.info(f"Complete patients: {summary['complete_patients']}")
        self.logger.info(f"Incomplete patients: {summary['incomplete_patients']}")
        self.logger.info(f"  - Patients with T1: {summary['patients_with_T1']}")
        self.logger.info(f"  - Patients with T2: {summary['patients_with_T2']}")
        self.logger.info(f"  - Patients with SWI: {summary['patients_with_SWI']}")

        return summary

    def save_results(self, metrics_df, group_stats_df, patient_status_df, summary):
        """Save all results to files"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Save individual metrics (combined)
        all_metrics_file = self.output_dir / f'all_patient_metrics_{timestamp}.csv'
        metrics_df.to_csv(all_metrics_file, index=False)
        self.logger.info(f"Saved all patient metrics: {all_metrics_file}")

        # Save group statistics
        group_stats_file = self.output_dir / f'group_statistics_{timestamp}.csv'
        group_stats_df.to_csv(group_stats_file, index=False)
        self.logger.info(f"Saved group statistics: {group_stats_file}")

        # Save patient status
        patient_status_file = self.output_dir / f'patient_completion_status_{timestamp}.csv'
        patient_status_df.to_csv(patient_status_file, index=False)
        self.logger.info(f"Saved patient status: {patient_status_file}")

        # Save summary JSON
        summary_file = self.output_dir / f'summary_{timestamp}.json'
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        self.logger.info(f"Saved summary: {summary_file}")

        # Save human-readable summary
        summary_txt_file = self.output_dir / f'summary_{timestamp}.txt'
        with open(summary_txt_file, 'w') as f:
            f.write("="*60 + "\n")
            f.write("STAGE Study - Analysis Summary\n")
            f.write("="*60 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("Overall Summary:\n")
            f.write("-"*60 + "\n")
            for key, value in summary.items():
                f.write(f"  {key}: {value}\n")
            f.write("\n")

            f.write("Group Statistics by Sequence Pair:\n")
            f.write("-"*60 + "\n")
            for _, row in group_stats_df.iterrows():
                f.write(f"\n{row['sequence_pair']} (n={row['n_patients']}):\n")
                f.write(f"  SSIM: {row.get('ssim_mean_mean', 'N/A'):.4f} ± {row.get('ssim_mean_std', 'N/A'):.4f}\n")
                f.write(f"  NCC: {row.get('ncc_mean', 'N/A'):.4f} ± {row.get('ncc_std', 'N/A'):.4f}\n")
                f.write(f"  Pearson r: {row.get('pearson_r_mean', 'N/A'):.4f} ± {row.get('pearson_r_std', 'N/A'):.4f}\n")
                f.write(f"  PSNR: {row.get('psnr_mean', 'N/A'):.2f} ± {row.get('psnr_std', 'N/A'):.2f}\n")

            f.write("\n\nPatient Completion Status:\n")
            f.write("-"*60 + "\n")
            f.write(patient_status_df.to_string())

        self.logger.info(f"Saved summary text: {summary_txt_file}")

    def run(self):
        """Run the complete group statistics analysis"""
        self.logger.info("="*60)
        self.logger.info("STAGE Study - Group Statistics Analysis")
        self.logger.info("="*60)

        # Collect metrics
        metrics_df, patient_status_df = self.collect_patient_metrics()

        if len(metrics_df) == 0:
            self.logger.error("No metrics found! Pipeline may not have completed.")
            return

        # Compute group statistics
        group_stats_df = self.compute_group_statistics(metrics_df)

        # Generate summary
        summary = self.generate_summary_report(patient_status_df)

        # Save results
        self.save_results(metrics_df, group_stats_df, patient_status_df, summary)

        self.logger.info("\n" + "="*60)
        self.logger.info("Analysis Complete!")
        self.logger.info("="*60)


def main():
    # Default paths
    metrics_dir = Path('~/Projects/STAGE_Study/output/metrics').expanduser()
    output_dir = Path('~/Projects/STAGE_Study/output/statistics').expanduser()

    if not metrics_dir.exists():
        print(f"Error: Metrics directory not found: {metrics_dir}")
        print("Please run the analysis pipeline first.")
        sys.exit(1)

    # Run analysis
    calculator = GroupStatsCalculator(metrics_dir, output_dir)
    calculator.run()


if __name__ == '__main__':
    main()
