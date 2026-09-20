# SECURE FOREST PATROL - ML Dataset & Preprocessing

This directory contains the ML dataset foundation and preprocessing pipeline for the SECURE OFFLINE FOREST PATROL system.

## Purpose

This phase focuses on creating a research-ready dataset and reproducible preprocessing pipeline for on-device acoustic event classification in forest environments. **Model training is NOT included in this phase.**

## Target Problem

**Forest Acoustic Event Classification**

Primary classes:
- GUNSHOT
- CHAINSAW  
- BACKGROUND / NON-THREAT

## Audio Specifications

- Sample rate: 16 kHz
- Channels: Mono
- Window length: ~1 second
- Feature representations: MFCC, Mel-spectrogram
- Target deployment: ESP32-S3 with TFLite Micro

## Directory Structure

```
ml/
├── README.md                      # This file
├── datasets/
│   ├── raw/                       # Original downloaded datasets (not in Git)
│   ├── interim/                   # Intermediate processing results
│   ├── processed/                 # Final processed dataset
│   └── manifests/                 # Dataset manifests and splits
├── preprocessing/                 # Audio preprocessing pipeline
├── scripts/                       # Download and utility scripts
├── notebooks/                     # Jupyter notebooks for exploration/QA
├── metadata/                      # Dataset metadata, licenses, citations
├── configs/                       # Configuration files
├── reports/                       # Quality reports and analysis
└── tests/                         # Unit tests
```

## Quick Start

### 1. Install Dependencies

```bash
cd ml
pip install -r requirements.txt
```

### 2. Download Datasets

```bash
python scripts/download_all.py
```

**Individual dataset downloads:**
```bash
python scripts/download_c3gd.py              # Gunshot data
python scripts/download_frugalai.py          # Chainsaw data
python scripts/download_esc50.py              # Environmental sounds
python scripts/download_sensing_forest.py     # Forest background
```

### 3. Audit Dataset Quality

```bash
python scripts/audit_dataset.py
```

This will generate `reports/dataset_quality_report.md` with quality analysis.

### 4. Preprocess Audio

```bash
python preprocessing/audio_preprocess.py
```

This will:
- Resample all audio to 16 kHz
- Convert to mono
- Normalize to -3 dB
- Segment into 1-second windows
- Generate master manifest

### 5. Extract Features (Optional)

```bash
python preprocessing/feature_extraction.py
```

This tests the MFCC and Mel-spectrogram extraction functions.

### 6. Create Train/Val/Test Splits

```bash
python scripts/create_splits.py
```

This will:
- Split by source to prevent data leakage
- Create train/val/test CSV files
- Generate split report

### 7. Visual QA (Optional)

```bash
jupyter notebook notebooks/data_qa.ipynb
```

This provides visual inspection of samples from each class.

## Dataset Sources

See `metadata/dataset_sources.md` for detailed information about selected datasets, including:
- Dataset names and URLs
- License information
- Available classes
- Audio specifications
- Selection rationale

## Documentation

### Dataset Documentation
- `metadata/DATASET_CARD.md` - Comprehensive dataset documentation
- `metadata/dataset_sources.md` - Dataset research and selection
- `metadata/dataset_selection.md` - Dataset selection rationale
- `metadata/licenses.csv` - License tracking
- `metadata/dataset_citations.md` - Academic citations

### Reports
- `reports/dataset_quality_report.md` - Quality audit results
- `reports/dataset_split_report.md` - Train/val/test split analysis
- `reports/domain_gap.md` - Domain gap analysis
- `reports/MODEL_HANDOFF.md` - Handoff documentation for model training phase

### Configuration
- `configs/preprocessing.yaml` - Audio preprocessing settings
- `configs/augmentation.yaml` - Data augmentation configuration

## Configuration

Preprocessing parameters are defined in:
- `configs/preprocessing.yaml` - Audio preprocessing settings
- `configs/augmentation.yaml` - Data augmentation configuration

## Important Notes

- **Raw datasets are not committed to Git** due to size
- Only scripts, metadata, manifests, and documentation are versioned
- No model training occurs in this phase
- Preprocessing is deterministic and reproducible
- Train/validation/test splits prevent source leakage
- All decisions are documented with rationale

## Current Status

### Completed
✅ 6 real datasets downloaded to `datasets/raw/`: `c3gd`, `fsc22`, `rodopi`, `esc50_hf`, `rfcx_frugalai`, `sensing_forest` (15,177 raw audio files total)
✅ Audio preprocessing pipeline (`preprocessing/audio_preprocess.py`) rewritten with per-dataset labeling logic for all 6 datasets
✅ Frozen dataset v1 (`datasets/v1/{master,train,validation,test,external_test}_v1.csv`) with grouped, leakage-checked splits
✅ Feature extraction (MFCC + Mel-spectrogram, `preprocessing/feature_extraction.py`)
✅ Baseline (MFCC + Logistic Regression), compact CNN, and final compact depthwise-separable model trained
✅ FP32 → TFLite → INT8 quantization pipeline with TFLite Micro op-compatibility check
✅ Notebooks 01–10 executed end to end
✅ Reports: `DATASET_V1_REPORT.md`, `ROBUSTNESS_REPORT.md`, `FAILURE_ANALYSIS.md`, `QUANTIZATION_REPORT.md`, `FINAL_MODEL_REPORT.md`

### Not Included (hardware-dependent, blocked — see `reports/FINAL_MODEL_REPORT.md`)
❌ ESP32-S3 firmware integration of TFLite Micro
❌ INMP441 I2S audio capture + embedded feature extraction
❌ Real-time on-device inference loop
❌ On-device vs Python prediction-consistency test
❌ Edge resource measurement (flash/RAM/tensor arena/latency/power)
❌ Real audio hardware testing
❌ LoRa → Gateway → MQTT → Backend → Dashboard end-to-end wiring/testing

## Optional digital audio filter
`preprocessing/audio_filter.py` (causal 2nd-order 80 Hz Butterworth high-pass, one ESP32-friendly biquad; applied after resample+mono, before windowing). Off by default (`filter.enabled: false` in `configs/preprocessing.yaml`). Coefficients, C snippet, A/B results: `reports/FILTER_REPORT.md`. Tests: `pytest tests`.

## Execution Workflow

```bash
cd ml
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python preprocessing/audio_preprocess.py     # -> datasets/manifests/master_manifest.csv + processed audio
python preprocessing/create_splits.py        # -> datasets/v1/*.csv (frozen v1 splits)
python scripts/audit_dataset.py              # quality gate
python scripts/validate_leakage.py           # quality gate
# then models/ training scripts and notebooks/ 01-10
```

The following workflow cannot be executed due to dataset access issues:

```bash
# 1. Install dependencies ✅ COMPLETED
pip install -r requirements.txt

# 2. Download all datasets ❌ FAILED
python scripts/download_all.py

# 3. Audit dataset quality ❌ BLOCKED (no data)
python scripts/audit_dataset.py

# 4. Preprocess audio ❌ BLOCKED (no data)
python preprocessing/audio_preprocess.py

# 5. Create train/val/test splits ❌ BLOCKED (no data)
python scripts/create_splits.py

# 6. (Optional) Visual inspection ❌ BLOCKED (no data)
jupyter notebook notebooks/data_qa.ipynb
```

**Blocking Issue:** Dataset downloads failed due to technical access problems with Zenodo, GitHub, and Hugging Face platforms. See `reports/download_report.md` for details.

## Next Phase

After completing this dataset foundation, the next phase will include:
- Model architecture selection
- CNN training
- Hyperparameter tuning
- Quantization for TFLite Micro
- Edge deployment optimization

## License

See individual dataset licenses in `metadata/licenses.csv` for usage terms.
