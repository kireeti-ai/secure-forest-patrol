#!/usr/bin/env python3
"""
Leakage validation script for dataset splits
Ensures no original recordings leak across train/val/test splits
"""
import pandas as pd
from pathlib import Path

V1_DIR = Path(__file__).parent.parent / "datasets" / "v1"
ID_COL = 'original_recording_id'

def validate_leakage():
    """Validate that no recordings leak across splits."""
    print("=" * 70)
    print("LEAKAGE VALIDATION")
    print("=" * 70)

    # Load v1 manifests
    train_df = pd.read_csv(V1_DIR / 'train_v1.csv')
    val_df = pd.read_csv(V1_DIR / 'validation_v1.csv')
    test_df = pd.read_csv(V1_DIR / 'test_v1.csv')
    ext_path = V1_DIR / 'external_test_v1.csv'
    ext_df = pd.read_csv(ext_path) if ext_path.exists() else pd.DataFrame(columns=[ID_COL])

    print(f"\nTrain samples: {len(train_df)}")
    print(f"Val samples: {len(val_df)}")
    print(f"Test samples: {len(test_df)}")
    print(f"External test samples: {len(ext_df)}")

    # Get unique original recordings per split
    train_recordings = set(train_df[ID_COL].unique())
    val_recordings = set(val_df[ID_COL].unique())
    test_recordings = set(test_df[ID_COL].unique())
    ext_recordings = set(ext_df[ID_COL].unique()) if len(ext_df) else set()
    
    print(f"\nTrain recordings: {len(train_recordings)}")
    print(f"Val recordings: {len(val_recordings)}")
    print(f"Test recordings: {len(test_recordings)}")
    
    # Check for leaks
    train_val_leak = train_recordings & val_recordings
    train_test_leak = train_recordings & test_recordings
    val_test_leak = val_recordings & test_recordings
    ext_leak = ext_recordings & (train_recordings | val_recordings | test_recordings)
    
    print(f"\n" + "=" * 70)
    print("LEAKAGE CHECK RESULTS")
    print("=" * 70)
    
    if train_val_leak:
        print(f"❌ FAILED: {len(train_val_leak)} recordings leak between train and val")
        print(f"   Leaked recordings: {train_val_leak}")
    else:
        print(f"✅ PASSED: No recordings leak between train and val")
    
    if train_test_leak:
        print(f"❌ FAILED: {len(train_test_leak)} recordings leak between train and test")
        print(f"   Leaked recordings: {train_test_leak}")
    else:
        print(f"✅ PASSED: No recordings leak between train and test")
    
    if val_test_leak:
        print(f"❌ FAILED: {len(val_test_leak)} recordings leak between val and test")
        print(f"   Leaked recordings: {val_test_leak}")
    else:
        print(f"✅ PASSED: No recordings leak between val and test")
    
    if ext_leak:
        print(f"❌ FAILED: {len(ext_leak)} recordings leak between external_test and train/val/test")
    else:
        print(f"✅ PASSED: No recordings leak between external_test and train/val/test")

    # Overall result
    if not train_val_leak and not train_test_leak and not val_test_leak and not ext_leak:
        print(f"\n" + "=" * 70)
        print("✅ LEAKAGE VALIDATION PASSED")
        print("=" * 70)
        return True
    else:
        print(f"\n" + "=" * 70)
        print("❌ LEAKAGE VALIDATION FAILED")
        print("=" * 70)
        return False

if __name__ == "__main__":
    result = validate_leakage()
    exit(0 if result else 1)