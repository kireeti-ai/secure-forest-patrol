#!/usr/bin/env python3
"""
Download script for ESC-50 (Dataset for Environmental Sound Classification)

Dataset: ESC-50
Source: https://github.com/karolpiczak/ESC-50
License: CC BY-NC 3.0
Size: ~400 MB (2,000 environmental audio recordings)
"""

import os
import sys
import requests
import zipfile
import json
from pathlib import Path
from tqdm import tqdm

# Configuration
DATASET_NAME = "esc50"
DATASET_URL = "https://codeload.github.com/karolpiczak/ESC-50/zip/master"
RAW_DIR = Path(__file__).parent.parent / "datasets" / "raw" / DATASET_NAME
TEMP_ZIP = Path(__file__).parent.parent / "datasets" / "raw" / f"{DATASET_NAME}.zip"

def create_directory():
    """Create the target directory for the dataset."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Created directory: {RAW_DIR}")

def download_dataset():
    """Download the ESC-50 dataset from GitHub."""
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
            zip_ref.extractall(RAW_DIR.parent)
        
        # Move files from the extracted directory to our target directory
        extracted_dir = RAW_DIR.parent / "ESC-50-master"
        if extracted_dir.exists():
            for item in extracted_dir.iterdir():
                if item.name != ".git":  # Skip git directory if present
                    dest = RAW_DIR / item.name
                    if item.is_dir():
                        import shutil
                        if dest.exists():
                            shutil.rmtree(dest)
                        shutil.move(str(item), str(dest))
                    else:
                        import shutil
                        shutil.move(str(item), str(dest))
            
            # Remove the extracted directory
            import shutil
            shutil.rmtree(extracted_dir)
        
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
    expected_items = ['audio', 'meta', 'esc50.csv', 'README.md', 'LICENSE']
    found_items = [item.name for item in RAW_DIR.iterdir()]
    
    print(f"Found items: {found_items}")
    
    # Count audio files
    audio_count = 0
    if (RAW_DIR / 'audio').exists():
        audio_count = len(list((RAW_DIR / 'audio').glob('*.wav')))
    
    print(f"Found {audio_count} audio files")
    
    # Check for metadata
    if (RAW_DIR / 'esc50.csv').exists():
        print("Metadata file esc50.csv found")
    else:
        print("Warning: Metadata file esc50.csv not found")
    
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
        "license": "CC BY-NC 3.0",
        "license_url": "http://creativecommons.org/licenses/by-nc/3.0/",
        "citation": "Piczak, K. J. (2015). ESC: Dataset for Environmental Sound Classification. In Proceedings of the 23rd ACM International Conference on Multimedia.",
        "num_classes": 50,
        "num_samples": 2000,
        "sample_rate": 44100,
        "duration": "5 seconds per clip",
        "status": "downloaded"
    }
    
    metadata_file = RAW_DIR / "download_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Created metadata file: {metadata_file}")

def main():
    """Main download function."""
    print("=" * 60)
    print("ESC-50 Dataset Download Script")
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
    print("NOTE: This dataset has a CC BY-NC 3.0 license (non-commercial)")

if __name__ == "__main__":
    main()
