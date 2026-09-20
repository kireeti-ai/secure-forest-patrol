#!/usr/bin/env python3
"""
Download script for RFCx FrugalAI Chainsaw Dataset

Dataset: RFCx Chainsaw Audio Dataset
Source: https://huggingface.co/datasets/rfcx/frugalai
License: CC BY-NC 4.0
Purpose: Chainsaw detection in forest environments
"""

import os
import sys
from pathlib import Path
from datasets import load_dataset
import json
import pandas as pd

# Configuration
DATASET_NAME = "rfcx_frugalai"
HF_DATASET_ID = "rfcx/frugalai"
RAW_DIR = Path(__file__).parent.parent / "datasets" / "raw" / DATASET_NAME

def create_directory():
    """Create the target directory for the dataset."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Created directory: {RAW_DIR}")

def download_dataset():
    """Download the RFCx FrugalAI dataset from Hugging Face."""
    print(f"Downloading {DATASET_NAME} from Hugging Face")
    print(f"Dataset ID: {HF_DATASET_ID}")
    
    try:
        # Load dataset from Hugging Face
        dataset = load_dataset(HF_DATASET_ID)
        
        print(f"Dataset loaded successfully")
        print(f"Available splits: {list(dataset.keys())}")
        
        # Save audio files and metadata
        for split_name, split_data in dataset.items():
            print(f"Processing split: {split_name}")
            
            split_dir = RAW_DIR / split_name
            split_dir.mkdir(exist_ok=True)
            
            # Save metadata
            metadata_list = []
            
            for idx, item in enumerate(split_data):
                # Get audio data
                audio_array = item['audio']['array']
                sampling_rate = item['audio']['sampling_rate']
                label = item['label']
                
                # Save audio file
                import soundfile as sf
                audio_filename = f"{split_name}_{idx:05d}_label_{label}.wav"
                audio_path = split_dir / audio_filename
                sf.write(audio_path, audio_array, sampling_rate)
                
                # Collect metadata
                metadata = {
                    'filename': audio_filename,
                    'split': split_name,
                    'label': int(label),
                    'label_name': 'chainsaw' if label == 0 else 'environment',
                    'sampling_rate': sampling_rate,
                    'original_sampling_rate': item['audio']['sampling_rate'],
                    'duration': len(audio_array) / sampling_rate
                }
                metadata_list.append(metadata)
                
                if (idx + 1) % 100 == 0:
                    print(f"  Processed {idx + 1} samples")
            
            # Save metadata as CSV
            metadata_df = pd.DataFrame(metadata_list)
            metadata_file = split_dir / "metadata.csv"
            metadata_df.to_csv(metadata_file, index=False)
            print(f"  Saved metadata to {metadata_file}")
            print(f"  Total samples in {split_name}: {len(metadata_list)}")
        
        print(f"Dataset downloaded to: {RAW_DIR}")
        return True
        
    except Exception as e:
        print(f"Error downloading dataset: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_download():
    """Verify that the dataset was downloaded correctly."""
    print(f"Verifying download in {RAW_DIR}")
    
    if not RAW_DIR.exists():
        print(f"Directory {RAW_DIR} does not exist")
        return False
    
    # Check for expected splits
    total_audio_files = 0
    split_info = {}
    
    for split_dir in RAW_DIR.iterdir():
        if split_dir.is_dir():
            audio_files = list(split_dir.glob('*.wav'))
            total_audio_files += len(audio_files)
            split_info[split_dir.name] = len(audio_files)
            
            # Check for metadata
            metadata_file = split_dir / "metadata.csv"
            if metadata_file.exists():
                print(f"  {split_dir.name}: {len(audio_files)} audio files, metadata found")
            else:
                print(f"  {split_dir.name}: {len(audio_files)} audio files, NO metadata")
    
    print(f"Total audio files: {total_audio_files}")
    print(f"Split distribution: {split_info}")
    
    if total_audio_files > 0:
        print("Download verification successful")
        return True
    else:
        print("Download verification failed - no audio files found")
        return False

def create_metadata():
    """Create a metadata file recording the download information."""
    metadata = {
        "dataset_name": DATASET_NAME,
        "download_date": "2026-09-18",
        "source_url": "https://huggingface.co/datasets/rfcx/frugalai",
        "license": "CC BY-NC 4.0",
        "license_url": "https://creativecommons.org/licenses/by-nc/4.0/",
        "citation": "Rainforest Connection. (2024). RFCx Chainsaw Audio Dataset. Hugging Face Datasets.",
        "purpose": "Chainsaw detection in forest environments",
        "original_format": "Opus (lossy compression)",
        "original_sample_rate": "12 kHz (typical)",
        "status": "downloaded"
    }
    
    metadata_file = RAW_DIR / "download_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Created metadata file: {metadata_file}")

def main():
    """Main download function."""
    print("=" * 60)
    print("RFCx FrugalAI Dataset Download Script")
    print("=" * 60)
    
    # Check if already downloaded
    if RAW_DIR.exists() and any(RAW_DIR.iterdir()):
        print(f"Dataset already exists in {RAW_DIR}")
        response = input("Do you want to re-download? (y/n): ")
        if response.lower() != 'y':
            print("Download cancelled")
            return
    
    # Create directory
    create_directory()
    
    # Download
    if not download_dataset():
        print("Download failed")
        sys.exit(1)
    
    # Verify
    if not verify_download():
        print("Verification failed")
        sys.exit(1)
    
    # Create metadata
    create_metadata()
    
    print("=" * 60)
    print("Download completed successfully!")
    print("=" * 60)
    print("NOTE: This dataset has a CC BY-NC 4.0 license (non-commercial)")

if __name__ == "__main__":
    main()
