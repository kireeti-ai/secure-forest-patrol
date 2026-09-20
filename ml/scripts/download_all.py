#!/usr/bin/env python3
"""
Master download script for all selected datasets

This script runs the individual download scripts for all selected datasets:
1. C3GD (Gunshot data)
2. RFCx FrugalAI (Chainsaw data)
3. ESC-50 (Environmental sounds)
4. Sensing the Forest (Forest background)
"""

import sys
import subprocess
from pathlib import Path

# Configuration
SCRIPTS_DIR = Path(__file__).parent
DATASETS = [
    {
        "name": "C3GD",
        "script": "download_c3gd.py",
        "description": "Gunshot data (CC BY 4.0)"
    },
    {
        "name": "RFCx FrugalAI",
        "script": "download_frugalai.py",
        "description": "Chainsaw data (CC BY-NC 4.0)"
    },
    {
        "name": "ESC-50",
        "script": "download_esc50.py",
        "description": "Environmental sounds (CC BY-NC 3.0)"
    },
    {
        "name": "Sensing the Forest",
        "script": "download_sensing_forest.py",
        "description": "Forest background (CC0 1.0)"
    }
]

def print_header():
    """Print the header for the download process."""
    print("=" * 70)
    print("SECURE FOREST PATROL - MASTER DATASET DOWNLOAD")
    print("=" * 70)
    print("\nThis script will download the following datasets:")
    for i, dataset in enumerate(DATASETS, 1):
        print(f"{i}. {dataset['name']}: {dataset['description']}")
    print("\n" + "=" * 70)

def download_dataset(dataset_info):
    """Download a single dataset."""
    script_path = SCRIPTS_DIR / dataset_info["script"]
    
    print(f"\n{'=' * 70}")
    print(f"Downloading {dataset_info['name']}")
    print(f"{'=' * 70}")
    
    if not script_path.exists():
        print(f"Error: Script not found: {script_path}")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=SCRIPTS_DIR,
            capture_output=False
        )
        
        if result.returncode == 0:
            print(f"✓ {dataset_info['name']} downloaded successfully")
            return True
        else:
            print(f"✗ {dataset_info['name']} download failed")
            return False
            
    except Exception as e:
        print(f"Error running download script: {e}")
        return False

def main():
    """Main download function."""
    print_header()
    
    # Ask for confirmation
    response = input("\nDo you want to proceed with downloading all datasets? (y/n): ")
    if response.lower() != 'y':
        print("Download cancelled")
        return
    
    # Download each dataset
    results = {}
    for dataset in DATASETS:
        success = download_dataset(dataset)
        results[dataset['name']] = success
    
    # Print summary
    print("\n" + "=" * 70)
    print("DOWNLOAD SUMMARY")
    print("=" * 70)
    
    for dataset, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"{dataset}: {status}")
    
    successful = sum(1 for s in results.values() if s)
    total = len(results)
    
    print(f"\nTotal: {successful}/{total} datasets downloaded successfully")
    
    if successful == total:
        print("\nAll datasets downloaded successfully!")
        print("Next step: Run python scripts/audit_dataset.py")
    else:
        print("\nSome datasets failed to download. Please check the errors above.")
        print("You can run individual download scripts manually if needed.")

if __name__ == "__main__":
    main()
