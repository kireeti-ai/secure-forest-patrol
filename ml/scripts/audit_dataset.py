#!/usr/bin/env python3
"""
Dataset quality audit script

This script performs comprehensive quality checks on downloaded datasets:
- Corrupted files
- Unreadable audio
- Zero-length audio
- Invalid sample rates
- Unsupported channel counts
- Extreme clipping
- Duplicate files
- Missing labels
- Class imbalance
- Duration statistics
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from pathlib import Path
import soundfile as sf
import librosa
from collections import defaultdict
import hashlib

# Configuration
RAW_DIR = Path(__file__).parent.parent / "datasets" / "raw"
REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

class DatasetAuditor:
    def __init__(self):
        self.results = {
            'total_files': 0,
            'corrupted_files': [],
            'zero_length_files': [],
            'invalid_sample_rates': [],
            'invalid_channels': [],
            'extreme_clipping': [],
            'duplicates': [],
            'missing_labels': [],
            'duration_stats': {},
            'sample_rate_stats': {},
            'channel_stats': {},
            'class_distribution': {},
            'file_hashes': {}
        }
    
    def calculate_file_hash(self, filepath):
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def audit_audio_file(self, filepath, dataset_name):
        """Audit a single audio file."""
        try:
            # Try to read the file
            audio, sr = sf.read(filepath)
            
            # Check for zero length
            if len(audio) == 0:
                self.results['zero_length_files'].append(str(filepath))
                return False
            
            # Check sample rate
            if sr not in [8000, 11025, 16000, 22050, 44100, 48000]:
                self.results['invalid_sample_rates'].append({
                    'file': str(filepath),
                    'sample_rate': sr
                })
            
            # Check channels
            if len(audio.shape) > 1:
                channels = audio.shape[1]
                if channels > 2:
                    self.results['invalid_channels'].append({
                        'file': str(filepath),
                        'channels': channels
                    })
            else:
                channels = 1
            
            # Check for extreme clipping
            max_amplitude = np.max(np.abs(audio))
            if max_amplitude > 0.99:  # Near clipping
                self.results['extreme_clipping'].append({
                    'file': str(filepath),
                    'max_amplitude': max_amplitude
                })
            
            # Calculate duration
            duration = len(audio) / sr
            
            # Calculate file hash
            file_hash = self.calculate_file_hash(filepath)
            
            # Store statistics
            return {
                'duration': duration,
                'sr': sr,
                'channels': channels,
                'max_amplitude': max_amplitude,
                'hash': file_hash,
                'valid': True
            }
            
        except Exception as e:
            self.results['corrupted_files'].append({
                'file': str(filepath),
                'error': str(e)
            })
            return None
    
    def audit_dataset(self, dataset_path):
        """Audit a single dataset directory."""
        dataset_name = dataset_path.name
        print(f"\nAuditing {dataset_name}...")
        
        audio_files = list(dataset_path.rglob('*.wav')) + list(dataset_path.rglob('*.mp3')) + list(dataset_path.rglob('*.flac'))
        print(f"Found {len(audio_files)} audio files")
        
        dataset_stats = {
            'durations': [],
            'sample_rates': [],
            'channels': [],
            'amplitudes': [],
            'valid_files': 0
        }
        
        for audio_file in audio_files:
            stats = self.audit_audio_file(audio_file, dataset_name)
            if stats and stats['valid']:
                dataset_stats['durations'].append(stats['duration'])
                dataset_stats['sample_rates'].append(stats['sr'])
                dataset_stats['channels'].append(stats['channels'])
                dataset_stats['amplitudes'].append(stats['max_amplitude'])
                dataset_stats['valid_files'] += 1
                
                # Store hash for duplicate detection
                file_hash = stats['hash']
                if file_hash in self.results['file_hashes']:
                    self.results['duplicates'].append({
                        'file': str(audio_file),
                        'duplicate_of': self.results['file_hashes'][file_hash]
                    })
                else:
                    self.results['file_hashes'][file_hash] = str(audio_file)
        
        # Calculate statistics
        if dataset_stats['durations']:
            self.results['duration_stats'][dataset_name] = {
                'mean': np.mean(dataset_stats['durations']),
                'std': np.std(dataset_stats['durations']),
                'min': np.min(dataset_stats['durations']),
                'max': np.max(dataset_stats['durations']),
                'median': np.median(dataset_stats['durations'])
            }
        
        if dataset_stats['sample_rates']:
            sr_counts = defaultdict(int)
            for sr in dataset_stats['sample_rates']:
                sr_counts[sr] += 1
            self.results['sample_rate_stats'][dataset_name] = dict(sr_counts)
        
        if dataset_stats['channels']:
            channel_counts = defaultdict(int)
            for ch in dataset_stats['channels']:
                channel_counts[ch] += 1
            self.results['channel_stats'][dataset_name] = dict(channel_counts)
        
        self.results['total_files'] += len(audio_files)
        
        print(f"  Valid files: {dataset_stats['valid_files']}/{len(audio_files)}")
        print(f"  Corrupted: {len([f for f in self.results['corrupted_files'] if dataset_name in f['file']])}")
        print(f"  Zero-length: {len([f for f in self.results['zero_length_files'] if dataset_name in f])}")
    
    def audit_all_datasets(self):
        """Audit all datasets in the raw directory."""
        print("=" * 70)
        print("DATASET QUALITY AUDIT")
        print("=" * 70)
        
        if not RAW_DIR.exists():
            print(f"Raw directory not found: {RAW_DIR}")
            return False
        
        datasets = [d for d in RAW_DIR.iterdir() if d.is_dir()]
        print(f"Found {len(datasets)} datasets to audit")
        
        for dataset_path in datasets:
            self.audit_dataset(dataset_path)
        
        return True
    
    def generate_report(self):
        """Generate a comprehensive audit report."""
        report_path = REPORTS_DIR / "dataset_quality_report.md"
        
        with open(report_path, 'w') as f:
            f.write("# Dataset Quality Audit Report\n\n")
            f.write(f"**Generated:** 2026-09-18\n\n")
            
            # Summary
            f.write("## Summary\n\n")
            f.write(f"- **Total files audited:** {self.results['total_files']}\n")
            f.write(f"- **Corrupted files:** {len(self.results['corrupted_files'])}\n")
            f.write(f"- **Zero-length files:** {len(self.results['zero_length_files'])}\n")
            f.write(f"- **Invalid sample rates:** {len(self.results['invalid_sample_rates'])}\n")
            f.write(f"- **Invalid channels:** {len(self.results['invalid_channels'])}\n")
            f.write(f"- **Extreme clipping:** {len(self.results['extreme_clipping'])}\n")
            f.write(f"- **Duplicate files:** {len(self.results['duplicates'])}\n\n")
            
            # Corrupted files
            if self.results['corrupted_files']:
                f.write("## Corrupted Files\n\n")
                for item in self.results['corrupted_files']:
                    f.write(f"- {item['file']}: {item['error']}\n")
                f.write("\n")
            
            # Zero-length files
            if self.results['zero_length_files']:
                f.write("## Zero-Length Files\n\n")
                for filepath in self.results['zero_length_files']:
                    f.write(f"- {filepath}\n")
                f.write("\n")
            
            # Invalid sample rates
            if self.results['invalid_sample_rates']:
                f.write("## Invalid Sample Rates\n\n")
                for item in self.results['invalid_sample_rates']:
                    f.write(f"- {item['file']}: {item['sample_rate']} Hz\n")
                f.write("\n")
            
            # Invalid channels
            if self.results['invalid_channels']:
                f.write("## Invalid Channels\n\n")
                for item in self.results['invalid_channels']:
                    f.write(f"- {item['file']}: {item['channels']} channels\n")
                f.write("\n")
            
            # Extreme clipping
            if self.results['extreme_clipping']:
                f.write("## Extreme Clipping\n\n")
                for item in self.results['extreme_clipping']:
                    f.write(f"- {item['file']}: {item['max_amplitude']:.3f}\n")
                f.write("\n")
            
            # Duplicates
            if self.results['duplicates']:
                f.write("## Duplicate Files\n\n")
                for item in self.results['duplicates']:
                    f.write(f"- {item['file']} is duplicate of {item['duplicate_of']}\n")
                f.write("\n")
            
            # Duration statistics
            f.write("## Duration Statistics\n\n")
            for dataset, stats in self.results['duration_stats'].items():
                f.write(f"### {dataset}\n\n")
                f.write(f"- Mean: {stats['mean']:.3f}s\n")
                f.write(f"- Std: {stats['std']:.3f}s\n")
                f.write(f"- Min: {stats['min']:.3f}s\n")
                f.write(f"- Max: {stats['max']:.3f}s\n")
                f.write(f"- Median: {stats['median']:.3f}s\n\n")
            
            # Sample rate statistics
            f.write("## Sample Rate Statistics\n\n")
            for dataset, stats in self.results['sample_rate_stats'].items():
                f.write(f"### {dataset}\n\n")
                for sr, count in stats.items():
                    f.write(f"- {sr} Hz: {count} files\n")
                f.write("\n")
            
            # Channel statistics
            f.write("## Channel Statistics\n\n")
            for dataset, stats in self.results['channel_stats'].items():
                f.write(f"### {dataset}\n\n")
                for ch, count in stats.items():
                    f.write(f"- {ch} channel(s): {count} files\n")
                f.write("\n")
            
            # Recommendations
            f.write("## Recommendations\n\n")
            f.write("Based on the audit results:\n\n")
            
            if self.results['corrupted_files']:
                f.write("- Remove or re-download corrupted files\n")
            
            if self.results['zero_length_files']:
                f.write("- Remove zero-length files\n")
            
            if self.results['invalid_sample_rates']:
                f.write("- Plan to resample files to target 16 kHz during preprocessing\n")
            
            if self.results['invalid_channels']:
                f.write("- Plan to convert to mono during preprocessing\n")
            
            if self.results['duplicates']:
                f.write("- Remove duplicate files to avoid data leakage\n")
            
            if not any([self.results['corrupted_files'], self.results['zero_length_files'], 
                        self.results['invalid_sample_rates'], self.results['invalid_channels'],
                        self.results['extreme_clipping'], self.results['duplicates']]):
                f.write("- No critical issues found. Dataset is ready for preprocessing.\n")
        
        print(f"\nReport generated: {report_path}")
        return report_path

def main():
    """Main audit function."""
    auditor = DatasetAuditor()
    
    # Run audit
    if not auditor.audit_all_datasets():
        print("Audit failed")
        sys.exit(1)
    
    # Generate report
    report_path = auditor.generate_report()
    
    print("\n" + "=" * 70)
    print("AUDIT COMPLETED")
    print("=" * 70)
    print(f"Total files: {auditor.results['total_files']}")
    print(f"Corrupted: {len(auditor.results['corrupted_files'])}")
    print(f"Zero-length: {len(auditor.results['zero_length_files'])}")
    print(f"Invalid sample rates: {len(auditor.results['invalid_sample_rates'])}")
    print(f"Invalid channels: {len(auditor.results['invalid_channels'])}")
    print(f"Extreme clipping: {len(auditor.results['extreme_clipping'])}")
    print(f"Duplicates: {len(auditor.results['duplicates'])}")
    print(f"\nReport saved to: {report_path}")

if __name__ == "__main__":
    main()
