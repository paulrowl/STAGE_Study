#!/usr/bin/env python3
"""Monitor recovery progress with loading bar"""

import time
import sys
from pathlib import Path

LOG_FILE = Path('/Users/paul/Projects/STAGE_Study/recovery_output.log')

SUBJECTS = ['Anon13609', 'Anon21108', 'Anon27334', 'Anon28584', 'Anon39526',
            'Anon43113', 'Anon50199', 'Anon72813', 'Anon88788']

TOTAL_SEQUENCES = 13  # 9 T1_conv + 4 more from Anon43113

def parse_log():
    """Parse log file for progress"""
    if not LOG_FILE.exists():
        return None

    with open(LOG_FILE, 'r') as f:
        content = f.read()

    # Count subjects processed
    subjects_started = []
    for subject in SUBJECTS:
        if f"Processing subject: {subject}" in content:
            subjects_started.append(subject)

    # Count successes and failures
    nifti_created = content.count('✓ Created:')
    hdbet_success = content.count('✓ Created mask:')
    hdbet_failed = content.count('✗ HD-BET failed')
    tissue_seg_success = content.count('✓ GM mean:')
    successfully_processed = content.count('✓ Successfully processed')

    # Check if complete
    is_complete = 'RECOVERY COMPLETE' in content

    return {
        'subjects_started': len(subjects_started),
        'current_subject': subjects_started[-1] if subjects_started else None,
        'nifti_created': nifti_created,
        'hdbet_success': hdbet_success,
        'hdbet_failed': hdbet_failed,
        'tissue_seg_success': tissue_seg_success,
        'sequences_recovered': successfully_processed,
        'is_complete': is_complete
    }

def draw_progress_bar(progress, total, width=50):
    """Draw a progress bar"""
    filled = int(width * progress / total)
    bar = '█' * filled + '░' * (width - filled)
    percent = 100 * progress / total
    return f"[{bar}] {percent:.1f}% ({progress}/{total})"

def main():
    print("\n" + "="*80)
    print("RECOVERY PROGRESS MONITOR")
    print("="*80)

    start_time = time.time()

    while True:
        stats = parse_log()

        if stats is None:
            print("\nWaiting for recovery to start...")
            time.sleep(5)
            continue

        # Clear screen (for updating display)
        print("\033[2J\033[H")  # ANSI escape codes

        print("\n" + "="*80)
        print("RECOVERY PROGRESS MONITOR")
        print("="*80)

        elapsed = time.time() - start_time
        elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))

        print(f"\nElapsed Time: {elapsed_str}")
        print(f"\nCurrent Subject: {stats['current_subject'] or 'N/A'}")

        # Overall progress
        print(f"\n📊 Overall Progress:")
        print(f"  {draw_progress_bar(stats['subjects_started'], len(SUBJECTS), 50)}")
        print(f"  Subjects: {stats['subjects_started']}/{len(SUBJECTS)}")

        # Sequence recovery progress
        print(f"\n🔬 Sequences Recovered:")
        print(f"  {draw_progress_bar(stats['sequences_recovered'], TOTAL_SEQUENCES, 50)}")
        print(f"  Recovered: {stats['sequences_recovered']}/{TOTAL_SEQUENCES}")

        # Detailed steps
        print(f"\n📋 Processing Steps:")
        print(f"  NIfTI conversions: {stats['nifti_created']} ✓")
        print(f"  HD-BET successes: {stats['hdbet_success']} ✓")
        print(f"  HD-BET failures: {stats['hdbet_failed']} ✗")
        print(f"  Tissue segmentation: {stats['tissue_seg_success']} ✓")

        # Warning if HD-BET is failing
        if stats['hdbet_failed'] > 5:
            print(f"\n⚠️  WARNING: High HD-BET failure rate!")
            print(f"  This may indicate a configuration issue.")

        # Estimate completion
        if stats['subjects_started'] > 0 and not stats['is_complete']:
            avg_time_per_subject = elapsed / stats['subjects_started']
            remaining_subjects = len(SUBJECTS) - stats['subjects_started']
            est_remaining = avg_time_per_subject * remaining_subjects
            est_remaining_str = time.strftime("%H:%M:%S", time.gmtime(est_remaining))
            print(f"\n⏱️  Estimated time remaining: {est_remaining_str}")

        if stats['is_complete']:
            print(f"\n✅ RECOVERY COMPLETE!")
            print(f"\nTotal sequences recovered: {stats['sequences_recovered']}/{TOTAL_SEQUENCES}")
            print(f"Total time: {elapsed_str}")
            break

        print(f"\n(Updating every 10 seconds... Press Ctrl+C to stop monitoring)")

        time.sleep(10)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user.")
        sys.exit(0)
