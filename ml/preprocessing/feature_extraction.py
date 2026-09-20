#!/usr/bin/env python3
"""
Feature extraction module for SECURE FOREST PATROL

This module provides functions for extracting:
- MFCC (Mel-Frequency Cepstral Coefficients)
- Mel-spectrograms

These features are prepared for later model training but no model training occurs in this phase.
"""

import numpy as np
import librosa
import yaml
from pathlib import Path
from typing import Dict, Tuple, Optional
import warnings

warnings.filterwarnings('ignore')

# Load configuration
CONFIG_PATH = Path(__file__).parent.parent / "configs" / "preprocessing.yaml"
with open(CONFIG_PATH, 'r') as f:
    CONFIG = yaml.safe_load(f)

class FeatureExtractor:
    def __init__(self, config: Dict):
        self.config = config
        self.target_sr = config['target_sample_rate']
        
        # MFCC settings
        self.mfcc_config = config['mfcc']
        
        # Mel-spectrogram settings
        self.mel_config = config['mel_spectrogram']
    
    def extract_mfcc(self, audio: np.ndarray, sr: int = None) -> np.ndarray:
        """
        Extract MFCC features from audio.
        
        Args:
            audio: Audio signal (numpy array)
            sr: Sample rate (uses target_sr if not provided)
        
        Returns:
            MFCC features with shape (n_mfcc, time_frames)
        """
        if sr is None:
            sr = self.target_sr
        
        if not self.mfcc_config['enabled']:
            raise ValueError("MFCC extraction is disabled in config")
        
        mfcc = librosa.feature.mfcc(
            y=audio,
            sr=sr,
            n_mfcc=self.mfcc_config['n_mfcc'],
            n_fft=self.mfcc_config['n_fft'],
            hop_length=self.mfcc_config['hop_length'],
            n_mels=self.mfcc_config['n_mels'],
            fmin=self.mfcc_config['fmin'],
            fmax=self.mfcc_config['fmax']
        )
        
        return mfcc
    
    def extract_mel_spectrogram(self, audio: np.ndarray, sr: int = None) -> np.ndarray:
        """
        Extract Mel-spectrogram from audio.
        
        Args:
            audio: Audio signal (numpy array)
            sr: Sample rate (uses target_sr if not provided)
        
        Returns:
            Mel-spectrogram with shape (n_mels, time_frames)
        """
        if sr is None:
            sr = self.target_sr
        
        if not self.mel_config['enabled']:
            raise ValueError("Mel-spectrogram extraction is disabled in config")
        
        mel_spec = librosa.feature.melspectrogram(
            y=audio,
            sr=sr,
            n_fft=self.mel_config['n_fft'],
            hop_length=self.mel_config['hop_length'],
            n_mels=self.mel_config['n_mels'],
            fmin=self.mel_config['fmin'],
            fmax=self.mel_config['fmax'],
            power=self.mel_config['power']
        )
        
        # Convert to dB scale
        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
        
        return mel_spec_db
    
    def extract_features(self, audio: np.ndarray, sr: int = None, 
                        feature_type: str = "both") -> Dict[str, np.ndarray]:
        """
        Extract requested features from audio.
        
        Args:
            audio: Audio signal (numpy array)
            sr: Sample rate (uses target_sr if not provided)
            feature_type: Type of features to extract ("mfcc", "mel", "both")
        
        Returns:
            Dictionary containing requested features
        """
        if sr is None:
            sr = self.target_sr
        
        features = {}
        
        if feature_type in ["mfcc", "both"]:
            if self.mfcc_config['enabled']:
                features['mfcc'] = self.extract_mfcc(audio, sr)
        
        if feature_type in ["mel", "both"]:
            if self.mel_config['enabled']:
                features['mel_spectrogram'] = self.extract_mel_spectrogram(audio, sr)
        
        return features
    
    def get_feature_shapes(self, audio_duration: float, sr: int = None) -> Dict[str, Tuple]:
        """
        Calculate expected feature shapes for a given audio duration.
        
        Args:
            audio_duration: Duration of audio in seconds
            sr: Sample rate (uses target_sr if not provided)
        
        Returns:
            Dictionary with expected shapes for each feature type
        """
        if sr is None:
            sr = self.target_sr
        
        num_samples = int(audio_duration * sr)
        shapes = {}
        
        # Calculate time frames
        if self.mfcc_config['enabled']:
            hop_length = self.mfcc_config['hop_length']
            n_frames = 1 + (num_samples - self.mfcc_config['n_fft']) // hop_length
            shapes['mfcc'] = (self.mfcc_config['n_mfcc'], n_frames)
        
        if self.mel_config['enabled']:
            hop_length = self.mel_config['hop_length']
            n_frames = 1 + (num_samples - self.mel_config['n_fft']) // hop_length
            shapes['mel_spectrogram'] = (self.mel_config['n_mels'], n_frames)
        
        return shapes
    
    def normalize_features(self, features: Dict[str, np.ndarray], 
                         method: str = "standard") -> Dict[str, np.ndarray]:
        """
        Normalize features for model input.
        
        Args:
            features: Dictionary of features
            method: Normalization method ("standard", "minmax", "none")
        
        Returns:
            Dictionary of normalized features
        """
        normalized = {}
        
        for key, feature in features.items():
            if method == "standard":
                # Z-score normalization
                mean = np.mean(feature)
                std = np.std(feature)
                if std > 0:
                    normalized[key] = (feature - mean) / std
                else:
                    normalized[key] = feature - mean
            elif method == "minmax":
                # Min-max normalization to [0, 1]
                min_val = np.min(feature)
                max_val = np.max(feature)
                if max_val > min_val:
                    normalized[key] = (feature - min_val) / (max_val - min_val)
                else:
                    normalized[key] = feature - min_val
            else:  # none
                normalized[key] = feature
        
        return normalized

def get_feature_extractor() -> FeatureExtractor:
    """Factory function to get a configured feature extractor."""
    return FeatureExtractor(CONFIG)

# Convenience functions for direct use
def extract_mfcc(audio: np.ndarray, sr: int = None) -> np.ndarray:
    """Convenience function to extract MFCC features."""
    extractor = get_feature_extractor()
    return extractor.extract_mfcc(audio, sr)

def extract_mel_spectrogram(audio: np.ndarray, sr: int = None) -> np.ndarray:
    """Convenience function to extract Mel-spectrogram features."""
    extractor = get_feature_extractor()
    return extractor.extract_mel_spectrogram(audio, sr)

def extract_all_features(audio: np.ndarray, sr: int = None) -> Dict[str, np.ndarray]:
    """Convenience function to extract all available features."""
    extractor = get_feature_extractor()
    return extractor.extract_features(audio, sr, feature_type="both")

if __name__ == "__main__":
    # Test the feature extraction
    print("Testing feature extraction...")
    
    # Generate a test audio signal (1 second at 16 kHz)
    sr = 16000
    duration = 1.0
    audio = np.random.randn(int(sr * duration))
    
    extractor = get_feature_extractor()
    
    # Extract features
    features = extractor.extract_features(audio, sr, feature_type="both")
    
    print(f"Extracted features: {list(features.keys())}")
    for key, feature in features.items():
        print(f"  {key}: shape {feature.shape}")
    
    # Get expected shapes
    shapes = extractor.get_feature_shapes(duration, sr)
    print(f"\nExpected shapes for {duration}s audio:")
    for key, shape in shapes.items():
        print(f"  {key}: {shape}")
    
    print("\nFeature extraction test completed successfully!")
