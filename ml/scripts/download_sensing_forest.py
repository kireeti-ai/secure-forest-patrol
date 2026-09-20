#!/usr/bin/env python3
"""
Download script for Sensing the Forest - Natural Soundscape Dataset

Dataset: Sensing the Forest - Natural Soundscape Dataset - Part 1/2
Source: https://zenodo.org/records/18909809
License: CC0 1.0 (Public Domain)
Purpose: Authentic forest background ambience
"""

import os
import sys
import requests
import json
from pathlib import Path
from tqdm import tqdm

# Configuration
DATASET_NAME = "sensing_forest"
ZENODO_DOI = "10.5281/zenodo.18909809"
ZENODO_API_URL = f"https://zenodo.org/api/records/{ZENODO_DOI.split('.')[-1]}"
RAW_DIR = Path(__file__).parent.parent / "datasets" / "raw" / DATASET_NAME

def create_directory():
    """Create the target directory for the dataset."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Created directory: {RAW_DIR}")

def get_zenodo_files():
    """Get list of files from Zenodo record."""
    print(f"Fetching file list from Zenodo: {ZENODO_API_URL}")
    
    try:
        response = requests.get(ZENODO_API_URL)
        response.raise_for_status()
        
        record_data = response.json()
        files = record_data.get('files', [])
        
        print(f"Found {len(files)} files in Zenodo record")
        
        for file_info in files:
            print(f"  - {file_info['name']} ({file_info['size']} bytes)")
        
        return files
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Zenodo record: {e}")
        return None

def download_file(file_info):
    """Download a single file from Zenodo."""
    filename = file_info['name']
    download_url = file_info['links']['self']
    file_size = file_info['size']
    
    print(f"Downloading {filename} ({file_size} bytes)")
    
    try:
        response = requests.get(download_url, stream=True)
        response.raise_for_status()
        
        filepath = RAW_DIR / filename
        
        with open(filepath, 'wb') as f, tqdm(
            desc=filename,
            total=file_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))
        
        print(f"Downloaded: {filepath}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {filename}: {e}")
        return False

def download_dataset():
    """Download the Sensing the Forest dataset from Zenodo."""
    print(f"Downloading {DATASET_NAME} from Zenodo")
    
    # Get file list
    files = get_zenodo_files()
    if files is None:
        return False
    
    # Download each file
    success_count = 0
    for file_info in files:
        if download_file(file_info):
            success_count += 1
    
    print(f"Downloaded {success_count}/{len(files)} files")
    return success_count > 0

def verify_download():
    """Verify that the dataset was downloaded correctly."""
    print(f"Verifying download in {RAW_DIR}")
    
    if not RAW_DIR.exists():
        print(f"Directory {RAW_DIR} does not exist")
        return False
    
    # Check for downloaded files
    files = list(RAW_DIR.iterdir())
    print(f"Found {len(files)} files/directories")
    
    for item in files:
        size_mb = item.stat().st_size / (1024 * 1024)
        print(f"  {item.name}: {size_mb:.2f} MB")
    
    if len(files) > 0:
        print("Download verification successful")
        return True
    else:
        print("Download verification failed - no files found")
        return False

def create_metadata():
    """Create a metadata file recording the download information."""
    metadata = {
        "dataset_name": DATASET_NAME,
        "download_date": "2026-09-18",
        "source_url": f"https://zenodo.org/records/{ZENODO_DOI.split('.')[-1]}",
        "doi": ZENODO_DOI,
        "license": "CC0 1.0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "citation": "Sensing the Forest Project. (2024). Sensing the Forest - Natural Soundscape Dataset - Part 1/2. Zenodo.",
        "purpose": "Authentic forest background ambience",
        "location": "Alice Holt Forest, Surrey, UK",
        "time_period": "August 2024 - March 2025",
        "status": "downloaded",
        "note": "Part 1 of 2 - Part 2 available separately"
    }
    
    metadata_file = RAW_DIR / "download_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Created metadata file: {metadata_file}")

def main():
    """Main download function."""
    print("=" * 60)
    print("Sensing the Forest Dataset Download Script")
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
    print("NOTE: This dataset has a CC0 1.0 license (public domain)")

if __name__ == "__main__":
    main()
