"""
Storage Management Utility

This script helps manage storage usage for the DGFT Regulatory Monitor.
It cleans temporary files, limits PDF storage, and provides statistics.
"""

import os
import shutil
from pathlib import Path
import argparse

def get_dir_size(path):
    """Get the size of a directory in bytes."""
    total = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_dir_size(entry.path)
    return total

def format_size(size_bytes):
    """Format bytes as human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024 or unit == 'GB':
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024

def analyze_storage():
    """Analyze storage usage and print statistics."""
    project_root = Path(".")
    
    # Gather statistics
    stats = []
    total_size = 0
    
    # Check common directories
    for directory in sorted(d for d in project_root.iterdir() if d.is_dir()):
        dir_size = get_dir_size(directory)
        total_size += dir_size
        stats.append((str(directory), dir_size))
    
    # Print statistics
    print("\nStorage Analysis:\n" + "="*50)
    for dir_name, size in sorted(stats, key=lambda x: x[1], reverse=True):
        print(f"{dir_name:<30} {format_size(size):>10}")
    print("="*50)
    print(f"Total project size: {format_size(total_size)}")
    
    return stats, total_size

def clean_storage(aggressive=False):
    """Clean temporary files and limit storage usage."""
    # Directories to clean entirely
    temp_dirs = [
        Path('logs'),
        Path('temp'),
        Path('__pycache__'),
    ]
    
    # Find and clean all __pycache__ directories
    for cache_dir in Path(".").rglob("__pycache__"):
        shutil.rmtree(cache_dir)
        print(f"Removed {cache_dir}")
    
    # Clean log files
    for log_file in Path(".").rglob("*.log"):
        log_file.unlink()
        print(f"Removed {log_file}")
    
    # Remove temporary directories
    for temp_dir in temp_dirs:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            print(f"Removed {temp_dir}")
            # Recreate essential empty directories
            if temp_dir in [Path('logs'), Path('temp')]:
                temp_dir.mkdir(exist_ok=True)
    
    # Limit stored PDFs
    storage_dir = Path("stored_pdfs")
    if storage_dir.exists():
        pdfs = sorted(storage_dir.glob("*.pdf"), 
                     key=lambda p: p.stat().st_mtime, reverse=True)
        # Keep only 5 newest PDFs
        for pdf in pdfs[5:]:
            pdf.unlink()
            print(f"Removed old PDF: {pdf}")
    
    # If aggressive, also clean all downloaded PDFs
    if aggressive:
        for pdf in Path(".").rglob("*.pdf"):
            pdf.unlink()
            print(f"Removed PDF: {pdf}")

def main():
    parser = argparse.ArgumentParser(description="Storage management utility")
    parser.add_argument("--analyze", action="store_true", help="Analyze storage usage")
    parser.add_argument("--clean", action="store_true", help="Clean temporary files")
    parser.add_argument("--aggressive", action="store_true", help="Aggressive cleaning (removes all PDFs)")
    
    args = parser.parse_args()
    
    if args.analyze or (not args.analyze and not args.clean):
        analyze_storage()
    
    if args.clean:
        clean_storage(aggressive=args.aggressive)
        # Show storage after cleaning
        print("\nStorage after cleaning:")
        analyze_storage()

if __name__ == "__main__":
    main()