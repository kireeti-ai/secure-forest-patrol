# Model Training Handoff Document

## Overview

This document provides a handoff for the model training phase of the SECURE FOREST PATROL project.

**CRITICAL STATUS:** DATASET EXPANSION REQUIRED - NOT READY FOR MODEL TRAINING

**IMPORTANT:** The current dataset (15 original recordings, 40 segments) is insufficient for research-grade model development. The dataset is suitable only for pipeline validation. A comprehensive dataset expansion phase is required before model training can proceed.

**REVISED REQUIREMENTS:** This document has been updated to reflect the comprehensive dataset expansion and evaluation requirements established in the ML Dataset Expansion + Model-Readiness Phase.

---

## CRITICAL DATASET INSUFFICIENCY

### Current Dataset Status
**Dataset Status:** PIPELINE VALIDATION ONLY - NOT RESEARCH-GRADE  
**Original Recordings:** 15  
**Generated Segments:** 40  
**Classes:** 3 (background, chainsaw, gunshot)  
**Train/Validation/Test:** 29/4/7 segments  
**Model Training Readiness:** NOT READY

### Dataset Scale Gap
**Current vs Minimum Viable:**
- Current: 15 recordings
- Minimum Viable: 200 recordings
- Gap: 13x insufficient

**Current vs Target Research:**
- Current: 15 recordings  
- Target Research: 800 recordings
- Gap: 53x insufficient

### Critical Blockers
1. **Insufficient Dataset Scale:** 13x smaller than minimum viable target
2. **Insufficient Source Diversity:** Only 3 independent sources (1 per class)
3. **No Field Data:** No deployment-like conditions represented
4. **Insufficient Test Set:** Only 7 test segments (too small for evaluation)
5. **Missing Environmental Diversity:** No documented environmental variation

### Required Actions Before Model Training
1. **Dataset Expansion** - Expand to minimum 200 recordings (50 per class)
2. **Source Diversity** - Achieve 15+ independent sources (5+ per class)
3. **Field Data Collection** - Collect field data from deployment conditions
4. **Test Set Expansion** - Expand to 120-150 test segments
5. **Environmental Diversity** - Ensure diverse environmental conditions

---

## Train/Validation/Test Manifests

### CURRENT STATUS - INSUFFICIENT SIZE

**Status:** Manifests exist but dataset is insufficient for model training

**Current Manifest Structure:**
Each manifest CSV contains the following columns:

| Column | Description | Type |
|--------|-------------|------|
| `sample_id` | Unique identifier for each sample | string |
| `original_sample_id` | Original recording identifier | string |
| `dataset_id` | Source dataset name | string |
| `original_file` | Path to original audio file | string |
| `class` | Class label (gunshot/chainsaw/background) | string |
| `split` | Train/val/test assignment | string |
| `duration` | Duration in seconds | float |
| `sample_rate` | Sample rate in Hz (should be 16000) | int |
| `channels` | Number of channels (should be 1) | int |
| `segment_index` | Index of segment within original file | int |
| `sha256` | SHA256 hash of segment | string |

**Current Manifest Statistics:**
- **Train:** 29 segments (72.5%)
- **Validation:** 4 segments (10%)
- **Test:** 7 segments (17.5%)
- **Total:** 40 segments

**Required Manifest Statistics (Minimum Viable):**
- **Train:** 560-700 segments (70%)
- **Validation:** 120-150 segments (15%)
- **Test:** 120-150 segments (15%)
- **Total:** 800-1,000 segments

**Access Code Example:**
```python
import pandas as pd
from pathlib import Path

# Load manifests
manifests_dir = Path('ml/datasets/manifests')
train_df = pd.read_csv(manifests_dir / 'train.csv')
val_df = pd.read_csv(manifests_dir / 'val.csv')
test_df = pd.read_csv(manifests_dir / 'test.csv')

# Check class distribution
print("Train class distribution:")
print(train_df['class'].value_counts())
print("\nValidation class distribution:")
print(val_df['class'].value_counts())
print("\nTest class distribution:")
print(test_df['class'].value_counts())
```

---

## Class Labels

### CURRENT STATUS - VALIDATED BUT INSUFFICIENT SAMPLES

**Status:** Class mapping validated but insufficient samples per class

**Class Mapping:**
```python
CLASS_MAPPING = {
    'gunshot': 0,
    'chainsaw': 1,
    'background': 2
}

NUM_CLASSES = 3
```

**Class Descriptions:**
- **Gunshot (0):** Acoustic signature of firearm discharge
- **Chainsaw (1):** Acoustic signature of chainsaw operation  
- **Background (2):** Environmental forest sounds (birds, wind, rain, etc.)

**Current Class Distribution:**
- **Gunshot:** 2 recordings (4 segments) - 10% of data
- **Chainsaw:** 3 recordings (14 segments) - 35% of data
- **Background:** 10 recordings (22 segments) - 55% of data

**Required Class Distribution (Minimum Viable):**
- **Gunshot:** 50 recordings (200-250 segments) - 25% of data
- **Chainsaw:** 50 recordings (200-250 segments) - 25% of data
- **Background:** 100 recordings (400-500 segments) - 50% of data

**Current Class Sources:**
- **Gunshot:** Sonilo Gunshot dataset (1 source)
- **Chainsaw:** Sonilo Chainsaw dataset (1 source)
- **Background:** DESRA dataset (1 source)

**Required Source Diversity (Minimum Viable):**
- **Gunshot:** 5+ independent sources
- **Chainsaw:** 5+ independent sources
- **Background:** 5+ independent sources

---

## Input Representation

### Audio Specifications
- **Sample Rate:** 16,000 Hz
- **Channels:** Mono (1 channel)
- **Duration:** ~1 second windows
- **Format:** WAV (16-bit)
- **Normalization:** Peak normalized to -3 dB

### Feature Representations

#### MFCC (Mel-Frequency Cepstral Coefficients)
```python
# Configuration
N_MFCC = 13              # Number of MFCC coefficients
N_FFT = 512              # FFT window size
HOP_LENGTH = 160          # Hop length in samples (10ms at 16kHz)
N_MELS = 40              # Number of Mel bins
FMIN = 0                 # Minimum frequency
FMAX = 8000              # Maximum frequency (Nyquist at 16kHz)

# Expected shape: (13, time_frames)
# For 1-second audio: (13, ~100 frames)
```

#### Mel-Spectrogram
```python
# Configuration
N_FFT = 512              # FFT window size
HOP_LENGTH = 160          # Hop length in samples (10ms at 16kHz)
N_MELS = 40              # Number of Mel bins
FMIN = 0                 # Minimum frequency
FMAX = 8000              # Maximum frequency (Nyquist at 16kHz)
POWER = 2.0              # Power for mel spectrogram

# Expected shape: (40, time_frames)
# For 1-second audio: (40, ~100 frames)
```

### Feature Extraction Code
```python
from preprocessing.feature_extraction import FeatureExtractor, get_feature_extractor
import numpy as np

# Load configuration
import yaml
with open('ml/configs/preprocessing.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Initialize feature extractor
extractor = FeatureExtractor(config)

# Extract features from audio
audio, sr = librosa.load('audio_file.wav', sr=16000)  # Load at 16 kHz

# Extract MFCC
mfcc = extractor.extract_mfcc(audio, sr)
print(f"MFCC shape: {mfcc.shape}")  # Expected: (13, ~100)

# Extract Mel-spectrogram
mel_spec = extractor.extract_mel_spectrogram(audio, sr)
print(f"Mel-spectrogram shape: {mel_spec.shape}")  # Expected: (40, ~100)

# Extract both
features = extractor.extract_features(audio, sr, feature_type="both")
```

---

## Sample Dimensions

### Audio Input
- **Raw Audio:** (16000,) samples for 1-second audio
- **Batch:** (batch_size, 16000)

### MFCC Features
- **Single Sample:** (13, time_frames) where time_frames ≈ 100
- **Batch:** (batch_size, 13, time_frames)
- **For CNN:** May need reshape to (batch_size, 13, time_frames, 1)

### Mel-Spectrogram Features
- **Single Sample:** (40, time_frames) where time_frames ≈ 100
- **Batch:** (batch_size, 40, time_frames)
- **For CNN:** May need reshape to (batch_size, 40, time_frames, 1)

### Normalization
Features should be normalized before model training:
```python
# Z-score normalization
mean = np.mean(features, axis=1, keepdims=True)
std = np.std(features, axis=1, keepdims=True)
normalized_features = (features - mean) / (std + 1e-8)
```

---

## Normalization

### Audio Normalization
- **Method:** Peak normalization
- **Target:** -3 dB
- **Applied during:** Preprocessing phase
- **Status:** Already applied to processed audio

### Feature Normalization
- **Method:** Z-score normalization (recommended)
- **Applied during:** Model training data loading
- **Per-feature normalization:** Compute statistics on training set only

### Normalization Implementation
```python
# Compute normalization statistics from training set
def compute_normalization_stats(train_features):
    mean = np.mean(train_features, axis=(0, 2), keepdims=True)  # Per-channel mean
    std = np.std(train_features, axis=(0, 2), keepdims=True)    # Per-channel std
    return mean, std

# Apply normalization
def normalize_features(features, mean, std):
    return (features - mean) / (std + 1e-8)
```

---

## Augmentation Policy

### Configuration File
- **Location:** `ml/configs/augmentation.yaml`
- **Application:** Training data only
- **Validation/Test:** No augmentation applied

### Augmentation Types
1. **Background Noise Addition:** Mix with real forest recordings
2. **Gain Variation:** ±6 dB gain changes
3. **Time Shifting:** ±100ms shifts
4. **Time Masking:** SpecAugment-style time masking
5. **Frequency Masking:** SpecAugment-style frequency masking

### Disabled Augmentations
- **Pitch Shifting:** Disabled (may change class semantics)
- **Speed Perturbation:** Disabled (may change class semantics)

### Augmentation Code
```python
import yaml

# Load augmentation config
with open('ml/configs/augmentation.yaml', 'r') as f:
    aug_config = yaml.safe_load(f)

# Apply augmentation during training
# (Implementation depends on chosen framework)
```

---

## Data Leakage Precautions

### Split Strategy
- **Method:** By source (original file)
- **Implementation:** All segments from same recording stay in same split
- **Verification:** Automated leakage checks performed

### Leakage Prevention
1. **Source-Level Grouping:** Original files used as splitting unit
2. **Duplicate Detection:** SHA256 hashing to detect duplicates
3. **Cross-Dataset Checks:** No duplicates across different datasets
4. **Temporal Separation:** Temporally adjacent recordings separated

### Verification
- **Leakage Check:** Performed by `scripts/create_splits.py`
- **Report:** Available in `reports/dataset_split_report.md`
- **Status:** Must show "No source leakage detected" before training

---

## Known Limitations

### Current Dataset Limitations
1. **CRITICAL: Dataset Scale:** 13x smaller than minimum viable target
2. **CRITICAL: Source Diversity:** Only 3 sources (1 per class) - high overfitting risk
3. **CRITICAL: No Field Data:** No deployment-like conditions represented
4. **CRITICAL: Test Set Size:** Only 7 test segments - insufficient for evaluation
5. **Class Imbalance:** Current distribution not representative of target
6. **Environmental Diversity:** No documented environmental variation
7. **Geographic Bias:** Single geographic location only
8. **Device Diversity:** Single microphone and recording device

### Expected Limitations After Expansion
1. **Domain Gap:** Gap between public data and forest deployment
2. **License Restrictions:** Some datasets have non-commercial licenses
3. **Geographic Bias:** Training data from different regions than deployment
4. **Temporal Coverage:** Limited seasonal and diurnal coverage
5. **Audio Quality:** Variable quality across datasets

### Technical Limitations
1. **Sample Rate Variability:** Original datasets have different sample rates
2. **Audio Quality:** Variable quality across datasets
3. **Format Variations:** Different original formats (WAV, Opus)
4. **Metadata Completeness:** Some metadata missing or incomplete

### Performance Expectations
- **Detection Accuracy:** Expected 15-25% reduction in real deployment vs. test set
- **False Positive Rate:** Expected 2-3x increase in real deployment
- **Range Performance:** Significant degradation beyond 50m range
- **Weather Performance:** 50%+ degradation during adverse weather

---

## Preprocessing Pipeline

### Pipeline Stages
1. **Audio Loading:** Load with error handling
2. **Resampling:** Convert to 16 kHz
3. **Mono Conversion:** Convert stereo to mono
4. **Normalization:** Peak normalization to -3 dB
5. **Windowing:** Segment to 1-second windows (50% overlap)
6. **Quality Checks:** Remove corrupted/invalid audio
7. **Hash Calculation:** SHA256 for duplicate detection
8. **Metadata Generation:** Create comprehensive manifest

### Pipeline Execution
```bash
# Complete preprocessing pipeline
python preprocessing/audio_preprocess.py

# Individual components
python preprocessing/feature_extraction.py  # Feature extraction
python scripts/create_splits.py             # Dataset splitting
```

### Pipeline Validation
- **Quality Audit:** `python scripts/audit_dataset.py`
- **Validation Report:** `reports/preprocessing_validation.md`
- **Status:** Must pass all validation checks before training

---

## Reproducibility

### Random Seeds
- **Split Seed:** 42 (fixed in config)
- **Augmentation Seed:** 123 (fixed in config)
- **Framework Seeds:** Set in model training code

### Configuration Files
- **Preprocessing:** `ml/configs/preprocessing.yaml`
- **Augmentation:** `ml/configs/augmentation.yaml`
- **All parameters:** Documented and version-controlled

### Reproducible Commands
```bash
# Complete preprocessing (reproducible)
python scripts/download_all.py           # Download datasets
python scripts/audit_dataset.py          # Quality audit
python preprocessing/audio_preprocess.py # Preprocess audio
python preprocessing/feature_extraction.py # Extract features
python scripts/create_splits.py          # Create splits
python scripts/validate_preprocessing.py  # Validate results
```

---

## Hardware Compatibility

### Target Deployment
- **Hardware:** ESP32-S3
- **Framework:** TFLite Micro
- **Constraints:** Limited memory, processing power
- **Quantization:** INT8 quantization required

### Model Constraints
- **Input Size:** Compatible with 1-second audio windows
- **Memory:** Must fit in ESP32-S3 memory constraints
- **Latency:** Real-time inference required
- **Power:** Low-power operation

### Feature Considerations
- **Fixed Dimensions:** Model must handle variable time frames
- **Quantization-Friendly:** Features should quantize well to INT8
- **Memory Efficient:** Minimize feature memory footprint
- **Compute Efficient:** Real-time feature extraction

---

## CRITICAL BLOCKER - MODEL TRAINING CANNOT PROCEED

### Required Pre-Conditions (NOT MET)
1. ✅ Dataset research - COMPLETED
2. ✅ Dataset size justification - COMPLETED
3. ✅ Public dataset research - COMPLETED
4. ✅ Field data collection protocol - COMPLETED
5. ✅ Data collection plan - COMPLETED
6. ✅ Evaluation protocol - COMPLETED
7. ✅ Cross-dataset generalization plan - COMPLETED
8. ✅ Edge evaluation plan - COMPLETED
9. ✅ Failure analysis plan - COMPLETED
10. ✅ Dataset readiness assessment - COMPLETED
11. ❌ Dataset scale - FAILED (13x insufficient)
12. ❌ Source diversity - FAILED (insufficient sources)
13. ❌ Field data - FAILED (none collected)
14. ❌ Test set size - FAILED (insufficient for evaluation)
15. ❌ Environmental diversity - FAILED (not documented)

### Model Training Readiness: NOT READY
**Cannot proceed with model training until dataset expansion is completed.**

### Required Next Steps
1. **CRITICAL:** Execute Phase 1: Minimum Viable Dataset expansion
2. **CRITICAL:** Achieve 200 recordings (50 per class)
3. **CRITICAL:** Achieve 15+ independent sources
4. **CRITICAL:** Collect initial field data
5. **CRITICAL:** Expand test set to 120-150 segments
6. **CRITICAL:** Validate dataset readiness gates

### Alternative Approaches
1. **Dataset Strategy Revision:** Select more accessible datasets
2. **Manual Download:** Manual download through browser/download managers
3. **Alternative Sources:** Investigate other data sources
4. **Field Data Collection:** Collect custom field recordings
5. **Synthetic Data:** Generate synthetic data for initial development

### Model Training Cannot Begin Until
- Dataset access is resolved
- Data is successfully downloaded
- Preprocessing is executed
- Train/val/test splits are created
- Dataset quality is validated

---

## Important Notes

### What Has Been Completed (This Phase)
✅ Dataset scale research and justification  
✅ Literature-backed dataset requirements  
✅ Updated public dataset research (2024-2025 sources)  
✅ Field data collection protocol  
✅ Comprehensive data collection plan  
✅ Metrics and evaluation protocol  
✅ Cross-dataset generalization plan  
✅ Edge evaluation plan  
✅ Failure analysis plan  
✅ Dataset readiness assessment  
✅ License tracking and documentation  
✅ Preprocessing pipeline validation (16kHz, mono, 1-second windows)  
✅ Feature extraction modules (MFCC, Mel-spectrogram)  
✅ Dataset splitting with leakage prevention  
✅ Data augmentation configuration  
✅ Comprehensive documentation  

### What Has NOT Been Done (This Phase)
❌ Dataset expansion to minimum viable scale  
❌ Public dataset integration (C3GD, FSD50K, etc.)  
❌ Field data collection  
❌ Source diversity expansion  
❌ Environmental diversity documentation  
❌ Test set expansion  
❌ Cross-dataset evaluation  
❌ Domain gap validation  

### Next Phase Requirements (Model Development)
❌ Model training (BLOCKED until dataset ready)  
❌ Baseline model development  
❌ Hyperparameter tuning  
❌ Model evaluation  
❌ Ablation studies  
❌ Robustness evaluation  
❌ Quantization  
❌ TFLite conversion  
❌ Edge deployment  

### Critical Constraints
- **NO MODEL TRAINING YET:** Dataset must meet minimum viable requirements first
- **DATASET EXPANSION REQUIRED:** Current dataset 13x insufficient
- **LICENSE COMPLIANCE:** Must respect non-commercial license restrictions
- **DOMAIN GAP:** Must collect field data for deployment validation
- **FIELD VALIDATION:** Essential for real-world performance assessment

---

## Troubleshooting

### Common Issues

#### Dataset Not Found
- **Symptom:** Scripts fail to find datasets
- **Solution:** Run `python scripts/download_all.py` first

#### Preprocessing Errors
- **Symptom:** Audio preprocessing fails
- **Solution:** Check `reports/dataset_quality_report.md` for corrupted files

#### Splitting Errors
- **Symptom:** Dataset splitting fails
- **Solution:** Ensure master manifest exists from preprocessing

#### Feature Extraction Errors
- **Symptom:** Feature extraction fails
- **Solution:** Verify audio is properly preprocessed (16kHz, mono)

#### Memory Issues
- **Symptom:** Out of memory during training
- **Solution:** Reduce batch size or use data loaders with memory mapping

---

## Contact and Support

### Documentation
- **Main README:** `ml/README.md`
- **Dataset Card:** `ml/metadata/DATASET_CARD.md`
- **Domain Gap:** `ml/reports/domain_gap.md`
- **Configuration:** `ml/configs/`

### Scripts
- **Downloads:** `ml/scripts/download_*.py`
- **Audit:** `ml/scripts/audit_dataset.py`
- **Splits:** `ml/scripts/create_splits.py`
- **Preprocessing:** `ml/preprocessing/*.py`

### Reports
- **Quality:** `ml/reports/dataset_quality_report.md`
- **Splits:** `ml/reports/dataset_split_report.md`
- **Domain Gap:** `ml/reports/domain_gap.md`

---

## Success Criteria

### Before Model Training (Phase 1 Completion)
- [ ] Dataset expanded to 200 recordings (50 per class)
- [ ] 15+ independent sources achieved (5+ per class)
- [ ] Field data collected (50+ recordings)
- [ ] Test set expanded to 120-150 segments
- [ ] Environmental diversity documented
- [ ] Quality audit passes (95%+ pass rate)
- [ ] All dataset readiness gates passed
- [ ] Cross-dataset evaluation possible
- [ ] Deployment readiness assessed

### Model Training Readiness (Full Requirements)
- [ ] Dataset scale meets minimum viable requirements
- [ ] Source diversity sufficient (15+ sources)
- [ ] Field data represents deployment conditions
- [ ] Test set sufficient for meaningful evaluation
- [ ] Environmental diversity documented
- [ ] Processed audio available in correct format
- [ ] Manifests contain comprehensive metadata
- [ ] Feature extraction pipeline tested
- [ ] Data augmentation configured
- [ ] Domain gap understood and documented
- [ ] Hardware constraints documented
- [ ] Evaluation protocols implemented
- [ ] Success criteria defined

---

**Handoff Status:** NOT READY FOR MODEL TRAINING PHASE  
**Data Foundation:** PIPELINE VALIDATION ONLY  
**Preprocessing Pipeline:** COMPLETE AND VALIDATED  
**Documentation:** COMPREHENSIVE  
**Next Phase:** DATASET EXPANSION (Phase 1: Minimum Viable Dataset)

**Handoff Date:** 2026-09-19  
**Handoff Version:** 2.0 (Updated with ML Dataset Expansion Requirements)  
**Status:** DATASET EXPANSION REQUIRED

**Revised Requirements:**
- **Dataset Size Justification:** `ml/reports/DATASET_SIZE_JUSTIFICATION.md`
- **Dataset Readiness Assessment:** `ml/reports/DATASET_READINESS.md`
- **Data Collection Plan:** `ml/reports/DATA_COLLECTION_PLAN.md`
- **Field Data Collection Protocol:** `ml/metadata/FIELD_DATA_COLLECTION_PROTOCOL.md`
- **Metrics and Evaluation Protocol:** `ml/reports/METRICS_AND_EVALUATION_PROTOCOL.md`
- **Cross-Dataset Generalization Plan:** `ml/reports/CROSS_DATASET_GENERALIZATION_PLAN.md`
- **Edge Evaluation Plan:** `ml/reports/EDGE_EVALUATION_PLAN.md`
- **Failure Analysis Plan:** `ml/reports/FAILURE_ANALYSIS_PLAN.md`

**Authorization Status:**
- **Model Development:** NOT AUTHORIZED (dataset insufficient)
- **Dataset Expansion:** AUTHORIZED
- **Field Collection:** AUTHORIZED (with safety protocols)
- **Public Dataset Integration:** AUTHORIZED

**Estimated Timeline to Model Training Readiness:** 4-6 months (realistic)
