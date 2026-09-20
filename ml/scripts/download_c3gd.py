#!/usr/bin/env python3
"""
Download script for C3GD (Certus Caliber Classification Gunshot Dataset)

Dataset: C3GD - Certus Caliber Classification Gunshot Dataset
Source: https://github.com/Stonewall-Defense/C3GD
License: CC BY 4.0
Size: ~430 MB (8,015 audio clips)
"""

import os
import sys
import requests
import zipfile
import hashlib
from pathlib import Path
from tqdm import tqdm
import json

# Configuration
DATASET_NAME = "c3gd"
DATASET_URL = "https://zenodo.org/records/22286299/files/C3GD.zip?download=1"
RAW_DIR = Path(__file__).parent.parent / "datasets" / "raw" / DATASET_NAME
TEMP_ZIP = Path(__file__).parent.parent / "datasets" / "raw" / f"{DATASET_NAME}.zip"

def create_directory():
    """Create the target directory for the dataset."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Created directory: {RAW_DIR}")

def download_dataset():
    """Download the C3GD dataset from GitHub."""
    print(f"Downloading {DATASET_NAME} from {DATASET_URL}")
    
    try:
        response = requests.get(DATASET_URL, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(TEMP_ZIP, 'wb') as f, tqdm(
            desc=DATASET_NAME,
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))
        
        print(f"Downloaded to: {TEMP_ZIP}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Error downloading dataset: {e}")
        return False

def extract_dataset():
    """Extract the downloaded zip file."""
    print(f"Extracting {TEMP_ZIP} to {RAW_DIR}")
    
    try:
        with zipfile.ZipFile(TEMP_ZIP, 'r') as zip_ref:
            zip_ref.extractall(RAW_DIR)
        
        # Clean up the zip file
        TEMP_ZIP.unlink()
        print(f"Extracted and cleaned up. Data in: {RAW_DIR}")
        return True
        
    except Exception as e:
        print(f"Error extracting dataset: {e}")
        return False

def verify_download():
    """Verify that the dataset was downloaded correctly."""
    print(f"Verifying download in {RAW_DIR}")
    
    if not RAW_DIR.exists():
        print(f"Directory {RAW_DIR} does not exist")
        return False
    
    # Check for expected files/directories
    expected_items = ['data', 'metadata', 'classes.json', 'README.md']
    found_items = [item.name for item in RAW_DIR.iterdir()]
    
    print(f"Found items: {found_items}")
    
    # Count audio files (check in data directory)
    audio_count = 0
    data_dir = RAW_DIR / 'data'
    if data_dir.exists():
        audio_count = len(list(data_dir.glob('*.wav')))
        print(f"Found {audio_count} audio files in {data_dir}")
    else:
        print(f"Data directory not found at {data_dir}")
        # Check if audio files are directly in the root
        audio_count = len(list(RAW_DIR.glob('*.wav')))
        print(f"Found {audio_count} audio files in root directory")
    
    if audio_count > 0:
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
        "source_url": DATASET_URL,
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "citation": "Stonewall Defense. (2024). Certus Caliber Classification Gunshot Dataset (C3GD). Zenodo. https://doi.org/10.5281/zenodo.20274399",
        "status": "downloaded"
    }
    
    metadata_file = RAW_DIR / "download_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Created metadata file: {metadata_file}")

def main():
    """Main download function."""
    print("=" * 60)
    print(f"C3GD Dataset Download Script")
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
    
    # Extract
    if not extract_dataset():
        print("Extraction failed")
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

if __name__ == "__main__":
    main()
