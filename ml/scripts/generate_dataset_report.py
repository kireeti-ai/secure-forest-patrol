#!/usr/bin/env python3
"""
Generate comprehensive dataset statistics report
"""
import pandas as pd
import numpy as np
from pathlib import Path
import json

MANIFESTS_DIR = Path(__file__).parent.parent / "datasets" / "manifests"
RAW_DIR = Path(__file__).parent.parent / "datasets" / "raw"
PROCESSED_DIR = Path(__file__).parent.parent / "datasets" / "processed"

def generate_report():
    """Generate comprehensive dataset statistics."""
    print("=" * 70)
    print("DATASET STATISTICS REPORT")
    print("=" * 70)
    
    # Load manifests
    train_df = pd.read_csv(MANIFESTS_DIR / 'train.csv')
    val_df = pd.read_csv(MANIFESTS_DIR / 'val.csv')
    test_df = pd.read_csv(MANIFESTS_DIR / 'test.csv')
    master_df = pd.read_csv(MANIFESTS_DIR / 'master_manifest.csv')
    
    # Count raw audio files
    raw_files = list(RAW_DIR.rglob('*.wav'))
    print(f"\nRAW DATA:")
    print(f"  Total raw audio files: {len(raw_files)}")
    
    # Count processed files
    processed_files = list(PROCESSED_DIR.glob('*.wav'))
    print(f"  Total processed files: {len(processed_files)}")
    
    # Overall statistics
    print(f"\nOVERALL STATISTICS:")
    print(f"  Total segments: {len(master_df)}")
    print(f"  Total original recordings: {len(master_df['original_sample_id'].unique())}")
    print(f"  Total datasets: {len(master_df['dataset_id'].unique())}")
    
    # Class distribution
    print(f"\nCLASS DISTRIBUTION:")
    class_counts = master_df['class'].value_counts()
    for class_name, count in class_counts.items():
        percentage = (count / len(master_df)) * 100
        print(f"  {class_name}: {count} segments ({percentage:.1f}%)")
    
    # Dataset source distribution
    print(f"\nDATASET SOURCE DISTRIBUTION:")
    dataset_counts = master_df['dataset_id'].value_counts()
    for dataset_name, count in dataset_counts.items():
        print(f"  {dataset_name}: {count} segments")
    
    # Split statistics
    print(f"\nSPLIT STATISTICS:")
    print(f"  Train: {len(train_df)} segments ({len(train_df['original_sample_id'].unique())} recordings)")
    print(f"  Val: {len(val_df)} segments ({len(val_df['original_sample_id'].unique())} recordings)")
    print(f"  Test: {len(test_df)} segments ({len(test_df['original_sample_id'].unique())} recordings)")
    
    # Per-class split distribution
    print(f"\nPER-CLASS SPLIT DISTRIBUTION:")
    for split_name, split_df in [('train', train_df), ('val', val_df), ('test', test_df)]:
        print(f"  {split_name.upper()}:")
        class_split = split_df['class'].value_counts()
        for class_name, count in class_split.items():
            print(f"    {class_name}: {count}")
    
    # Recording statistics per class
    print(f"\nORIGINAL RECORDINGS PER CLASS:")
    for class_name in master_df['class'].unique():
        class_df = master_df[master_df['class'] == class_name]
        recordings = class_df['original_sample_id'].unique()
        print(f"  {class_name}: {len(recordings)} recordings")
        for recording in recordings:
            segments = len(class_df[class_df['original_sample_id'] == recording])
            print(f"    {recording}: {segments} segments")
    
    # Audio format validation
    print(f"\nAUDIO FORMAT VALIDATION:")
    print(f"  Sample rate: {master_df['sample_rate'].unique()}")
    print(f"  Channels: {master_df['channels'].unique()}")
    print(f"  Duration range: {master_df['duration'].min():.3f}s - {master_df['duration'].max():.3f}s")
    print(f"  Mean duration: {master_df['duration'].mean():.3f}s")
    
    # Source diversity analysis
    print(f"\nSOURCE DIVERSITY:")
    print(f"  Total unique sources: {len(master_df['dataset_id'].unique())}")
    for class_name in master_df['class'].unique():
        class_df = master_df[master_df['class'] == class_name]
        sources = class_df['dataset_id'].unique()
        print(f"  {class_name}: {len(sources)} sources - {list(sources)}")
    
    print(f"\n" + "=" * 70)
    print("DATASET STATISTICS COMPLETED")
    print("=" * 70)
    
    # Save report to file
    report_path = MANIFESTS_DIR / "dataset_statistics.txt"
    with open(report_path, 'w') as f:
        f.write("DATASET STATISTICS REPORT\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"RAW DATA:\n")
        f.write(f"  Total raw audio files: {len(raw_files)}\n")
        f.write(f"  Total processed files: {len(processed_files)}\n\n")
        f.write(f"OVERALL STATISTICS:\n")
        f.write(f"  Total segments: {len(master_df)}\n")
        f.write(f"  Total original recordings: {len(master_df['original_sample_id'].unique())}\n")
        f.write(f"  Total datasets: {len(master_df['dataset_id'].unique())}\n\n")
        f.write(f"CLASS DISTRIBUTION:\n")
        for class_name, count in class_counts.items():
            percentage = (count / len(master_df)) * 100
            f.write(f"  {class_name}: {count} segments ({percentage:.1f}%)\n")
        f.write(f"\nDATASET SOURCE DISTRIBUTION:\n")
        for dataset_name, count in dataset_counts.items():
            f.write(f"  {dataset_name}: {count} segments\n")
        f.write(f"\nSPLIT STATISTICS:\n")
        f.write(f"  Train: {len(train_df)} segments ({len(train_df['original_sample_id'].unique())} recordings)\n")
        f.write(f"  Val: {len(val_df)} segments ({len(val_df['original_sample_id'].unique())} recordings)\n")
        f.write(f"  Test: {len(test_df)} segments ({len(test_df['original_sample_id'].unique())} recordings)\n")
        f.write(f"\nSOURCE DIVERSITY:\n")
        f.write(f"  Total unique sources: {len(master_df['dataset_id'].unique())}\n")
        for class_name in master_df['class'].unique():
            class_df = master_df[master_df['class'] == class_name]
            sources = class_df['dataset_id'].unique()
            f.write(f"  {class_name}: {len(sources)} sources - {list(sources)}\n")
    
    print(f"Report saved to: {report_path}")

if __name__ == "__main__":
    generate_report()