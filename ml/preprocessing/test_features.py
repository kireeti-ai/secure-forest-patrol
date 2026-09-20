#!/usr/bin/env python3
"""
Test feature extraction on processed data
"""

import numpy as np
import pandas as pd
import librosa
from pathlib import Path
from tqdm import tqdm

# Configuration
TARGET_SR = 16000
N_MFCC = 13
N_MELS = 40
N_FFT = 512
HOP_LENGTH = 160

# Paths
PROCESSED_DIR = Path(__file__).parent.parent / "datasets" / "processed"
MANIFESTS_DIR = Path(__file__).parent.parent / "datasets" / "manifests"

def extract_mfcc(audio, sr):
    """Extract MFCC features."""
    mfcc = librosa.feature.mfcc(
        y=audio,
        sr=sr,
        n_mfcc=N_MFCC,
        n_fft=N_FFT,
        hop_length=HOP_LENGTH,
        n_mels=N_MELS
    )
    return mfcc

def extract_mel_spectrogram(audio, sr):
    """Extract Mel-spectrogram features."""
    mel_spec = librosa.feature.melspectrogram(
        y=audio,
        sr=sr,
        n_fft=N_FFT,
        hop_length=HOP_LENGTH,
        n_mels=N_MELS
    )
    mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
    return mel_spec_db

def main():
    """Test feature extraction."""
    print("=" * 60)
    print("Feature Extraction Test")
    print("=" * 60)
    
    # Load processed manifest
    manifest_path = MANIFESTS_DIR / "processed_manifest.csv"
    manifest_df = pd.read_csv(manifest_path)
    
    print(f"Processing {len(manifest_df)} segments...")
    
    # Test on first few segments
    test_segments = manifest_df.head(5)
    
    for idx, row in test_segments.iterrows():
        sample_id = row['sample_id']
        file_path = PROCESSED_DIR / "audio" / "background" / f"{sample_id}.wav"
        
        if not file_path.exists():
            print(f"File not found: {file_path}")
            continue
        
        # Load audio
        audio, sr = librosa.load(file_path, sr=TARGET_SR)
        
        print(f"\n{sample_id}:")
        print(f"  Duration: {len(audio)/sr:.3f}s")
        print(f"  Sample rate: {sr} Hz")
        print(f"  Channels: 1 (mono)")
        
        # Extract MFCC
        mfcc = extract_mfcc(audio, sr)
        print(f"  MFCC shape: {mfcc.shape}")
        
        # Extract Mel-spectrogram
        mel_spec = extract_mel_spectrogram(audio, sr)
        print(f"  Mel-spectrogram shape: {mel_spec.shape}")
    
    print("\n" + "=" * 60)
    print("Feature extraction test complete!")
    print("=" * 60)
    print("\nFeature parameters:")
    print(f"  MFCC coefficients: {N_MFCC}")
    print(f"  Mel bins: {N_MELS}")
    print(f"  FFT size: {N_FFT}")
    print(f"  Hop length: {HOP_LENGTH}")
    print(f"  Expected MFCC shape: ({N_MFCC}, ~100)")
    print(f"  Expected Mel shape: ({N_MELS}, ~100)")

if __name__ == "__main__":
    main()
