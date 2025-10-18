#!/usr/bin/env python3
"""
Cleanup and Organize STAGE Study Project Structure

Actions:
1. Move all log files from root to logs/
2. Remove empty folders
3. Archive outdated/redundant output folders
4. Create organized archives for old analysis runs
5. Generate cleanup report

Usage:
    python scripts/cleanup_project_structure.py [--dry-run] [--aggressive]

Options:
    --dry-run: Show what would be done without making changes
    --aggressive: Also archive older output files (keeps only latest)
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime
import gzip

BASE_DIR = Path('/Users/paul/Projects/STAGE_Study')

# Cleanup actions
cleanup_actions = {
    'moved': [],
    'removed': [],
    'archived': [],
    'errors': []
}

def format_size(size_bytes):
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def get_dir_size(path):
    """Get total size of directory"""
    total = 0
    try:
        for entry in os.scandir(path):
            if entry.is_file(follow_symlinks=False):
                total += entry.stat().st_size
            elif entry.is_dir(follow_symlinks=False):
                total += get_dir_size(entry.path)
    except PermissionError:
        pass
    return total

def move_log_files(dry_run=False):
    """Move all log files from root to logs/ directory"""
    print("\n" + "="*80)
    print("1. Moving log files from root to logs/")
    print("="*80)

    logs_dir = BASE_DIR / 'logs'
    logs_dir.mkdir(exist_ok=True)

    # Find all log files in root
    log_files = list(BASE_DIR.glob('*.log'))

    print(f"\nFound {len(log_files)} log files in root directory")

    for log_file in log_files:
        dest = logs_dir / log_file.name
        size = log_file.stat().st_size

        if dry_run:
            print(f"  [DRY RUN] Would move: {log_file.name} ({format_size(size)})")
        else:
            try:
                shutil.move(str(log_file), str(dest))
                print(f"  ✓ Moved: {log_file.name} ({format_size(size)})")
                cleanup_actions['moved'].append((str(log_file), str(dest), size))
            except Exception as e:
                print(f"  ✗ Error moving {log_file.name}: {e}")
                cleanup_actions['errors'].append(('move', str(log_file), str(e)))

def remove_empty_directories(dry_run=False):
    """Remove empty directories"""
    print("\n" + "="*80)
    print("2. Removing empty directories")
    print("="*80)

    empty_dirs = [
        BASE_DIR / 'output' / 'logs',
        BASE_DIR / 'output' / 'report',
        BASE_DIR / 'output' / 'segmentations',
        BASE_DIR / 'results',
    ]

    for dir_path in empty_dirs:
        if dir_path.exists():
            try:
                # Check if really empty
                if not any(dir_path.iterdir()):
                    if dry_run:
                        print(f"  [DRY RUN] Would remove: {dir_path.relative_to(BASE_DIR)}")
                    else:
                        dir_path.rmdir()
                        print(f"  ✓ Removed: {dir_path.relative_to(BASE_DIR)}")
                        cleanup_actions['removed'].append(('directory', str(dir_path), 0))
                else:
                    print(f"  ⚠ Not empty: {dir_path.relative_to(BASE_DIR)}")
            except Exception as e:
                print(f"  ✗ Error removing {dir_path.relative_to(BASE_DIR)}: {e}")
                cleanup_actions['errors'].append(('remove', str(dir_path), str(e)))

def archive_redundant_folders(dry_run=False):
    """Archive redundant or outdated output folders"""
    print("\n" + "="*80)
    print("3. Archiving redundant output folders")
    print("="*80)

    # Create archive directory
    archive_dir = BASE_DIR / 'output' / 'archive'
    if not dry_run:
        archive_dir.mkdir(exist_ok=True)

    # Folders to archive (outdated or redundant)
    folders_to_archive = [
        ('output/statistics_without_normalization', 'old_stats_no_norm'),
        ('output/metrics_without_normalization', 'old_metrics_no_norm'),
        ('output/organization', 'old_organization'),
    ]

    for folder_rel, archive_name in folders_to_archive:
        folder = BASE_DIR / folder_rel
        if folder.exists():
            size = get_dir_size(folder)
            archive_path = archive_dir / f"{archive_name}_{datetime.now().strftime('%Y%m%d')}"

            if dry_run:
                print(f"  [DRY RUN] Would archive: {folder_rel} -> archive/ ({format_size(size)})")
            else:
                try:
                    shutil.move(str(folder), str(archive_path))
                    print(f"  ✓ Archived: {folder_rel} ({format_size(size)})")
                    cleanup_actions['archived'].append((str(folder), str(archive_path), size))
                except Exception as e:
                    print(f"  ✗ Error archiving {folder_rel}: {e}")
                    cleanup_actions['errors'].append(('archive', str(folder), str(e)))

def archive_old_log_files(dry_run=False, aggressive=False):
    """Archive old log files by date"""
    print("\n" + "="*80)
    print("4. Archiving old log files")
    print("="*80)

    logs_dir = BASE_DIR / 'logs'
    archive_dir = logs_dir / 'archive'

    if not dry_run:
        archive_dir.mkdir(exist_ok=True)

    # Group log files by base name
    log_groups = {}
    for log_file in logs_dir.glob('*.log'):
        # Skip if already in archive
        if 'archive' in str(log_file):
            continue

        # Extract base name (without dates/timestamps)
        base_name = log_file.stem
        # Remove timestamps/dates from name
        for pattern in ['_20', '_2025', 'ground_truth_']:
            if pattern in base_name:
                base_name = base_name.split(pattern)[0]
                break

        if base_name not in log_groups:
            log_groups[base_name] = []
        log_groups[base_name].append(log_file)

    # For each group, keep only the latest file
    for base_name, files in log_groups.items():
        if len(files) > 1:
            # Sort by modification time
            files_sorted = sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)
            latest = files_sorted[0]
            old_files = files_sorted[1:]

            print(f"\n  Group '{base_name}': {len(files)} files")
            print(f"    Keeping: {latest.name}")

            for old_file in old_files:
                size = old_file.stat().st_size
                dest = archive_dir / old_file.name

                if dry_run:
                    print(f"    [DRY RUN] Would archive: {old_file.name} ({format_size(size)})")
                else:
                    try:
                        shutil.move(str(old_file), str(dest))
                        print(f"    ✓ Archived: {old_file.name} ({format_size(size)})")
                        cleanup_actions['archived'].append((str(old_file), str(dest), size))
                    except Exception as e:
                        print(f"    ✗ Error: {e}")
                        cleanup_actions['errors'].append(('archive_log', str(old_file), str(e)))

def clean_pycache(dry_run=False):
    """Remove Python cache directories"""
    print("\n" + "="*80)
    print("5. Removing Python cache directories")
    print("="*80)

    pycache_dirs = list(BASE_DIR.rglob('__pycache__'))

    if pycache_dirs:
        print(f"\nFound {len(pycache_dirs)} __pycache__ directories")

        for cache_dir in pycache_dirs:
            size = get_dir_size(cache_dir)

            if dry_run:
                print(f"  [DRY RUN] Would remove: {cache_dir.relative_to(BASE_DIR)} ({format_size(size)})")
            else:
                try:
                    shutil.rmtree(cache_dir)
                    print(f"  ✓ Removed: {cache_dir.relative_to(BASE_DIR)} ({format_size(size)})")
                    cleanup_actions['removed'].append(('cache', str(cache_dir), size))
                except Exception as e:
                    print(f"  ✗ Error: {e}")
                    cleanup_actions['errors'].append(('remove_cache', str(cache_dir), str(e)))
    else:
        print("\nNo __pycache__ directories found")

def generate_cleanup_report(dry_run=False):
    """Generate cleanup summary report"""
    print("\n" + "="*80)
    print("CLEANUP SUMMARY")
    print("="*80)

    total_moved = sum(size for _, _, size in cleanup_actions['moved'])
    total_archived = sum(size for _, _, size in cleanup_actions['archived'])
    total_removed = sum(size for _, _, size in cleanup_actions['removed'])
    total_freed = total_removed + total_archived

    print(f"\nActions completed:")
    print(f"  Files moved: {len(cleanup_actions['moved'])} ({format_size(total_moved)})")
    print(f"  Items archived: {len(cleanup_actions['archived'])} ({format_size(total_archived)})")
    print(f"  Items removed: {len(cleanup_actions['removed'])} ({format_size(total_removed)})")
    print(f"  Errors: {len(cleanup_actions['errors'])}")

    print(f"\nSpace management:")
    print(f"  Total archived/removed: {format_size(total_freed)}")

    if cleanup_actions['errors']:
        print(f"\nErrors encountered:")
        for action, path, error in cleanup_actions['errors']:
            print(f"  {action}: {path}")
            print(f"    Error: {error}")

    if not dry_run:
        # Save report
        report_file = BASE_DIR / 'logs' / f"cleanup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write("STAGE Study Project Cleanup Report\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")

            f.write("Files Moved:\n")
            for src, dest, size in cleanup_actions['moved']:
                f.write(f"  {Path(src).name} -> {Path(dest).name} ({format_size(size)})\n")

            f.write("\nItems Archived:\n")
            for src, dest, size in cleanup_actions['archived']:
                f.write(f"  {src} -> {dest} ({format_size(size)})\n")

            f.write("\nItems Removed:\n")
            for item_type, path, size in cleanup_actions['removed']:
                f.write(f"  [{item_type}] {path} ({format_size(size)})\n")

            if cleanup_actions['errors']:
                f.write("\nErrors:\n")
                for action, path, error in cleanup_actions['errors']:
                    f.write(f"  {action}: {path}\n    Error: {error}\n")

            f.write(f"\nTotal space managed: {format_size(total_freed)}\n")

        print(f"\nCleanup report saved to: {report_file}")

def show_current_structure():
    """Display current project structure and sizes"""
    print("\n" + "="*80)
    print("CURRENT PROJECT STRUCTURE")
    print("="*80)

    dirs_to_check = [
        'data',
        'output',
        'scripts',
        'logs',
        'docs',
    ]

    for dir_name in dirs_to_check:
        dir_path = BASE_DIR / dir_name
        if dir_path.exists():
            size = get_dir_size(dir_path)
            print(f"\n{dir_name}/: {format_size(size)}")

            # Show subdirectories
            try:
                subdirs = [d for d in dir_path.iterdir() if d.is_dir()]
                for subdir in sorted(subdirs, key=lambda d: get_dir_size(d), reverse=True)[:10]:
                    sub_size = get_dir_size(subdir)
                    print(f"  {subdir.name}/: {format_size(sub_size)}")
            except PermissionError:
                pass

def main():
    parser = argparse.ArgumentParser(description='Cleanup STAGE Study project structure')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')
    parser.add_argument('--aggressive', action='store_true',
                       help='Also archive older output files')

    args = parser.parse_args()

    print("="*80)
    print("STAGE Study Project Cleanup")
    print("="*80)
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"Aggressive: {args.aggressive}")
    print("="*80)

    # Show current structure
    show_current_structure()

    # Perform cleanup actions
    move_log_files(dry_run=args.dry_run)
    remove_empty_directories(dry_run=args.dry_run)
    archive_redundant_folders(dry_run=args.dry_run)
    archive_old_log_files(dry_run=args.dry_run, aggressive=args.aggressive)
    clean_pycache(dry_run=args.dry_run)

    # Generate report
    generate_cleanup_report(dry_run=args.dry_run)

    if args.dry_run:
        print("\n" + "="*80)
        print("DRY RUN COMPLETE - No changes were made")
        print("Run without --dry-run to apply changes")
        print("="*80)

if __name__ == '__main__':
    main()
