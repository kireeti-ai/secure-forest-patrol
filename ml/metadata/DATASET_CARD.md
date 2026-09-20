# Dataset Card - SECURE FOREST PATROL

## Overview

This dataset card documents the ML dataset foundation for the SECURE OFFLINE FOREST PATROL system, designed for on-device acoustic event classification in forest environments.

**CRITICAL STATUS:** DATASET EXECUTION FAILED - NO DATA AVAILABLE

**Problem:** Forest Acoustic Event Classification  
**Primary Classes:** GUNSHOT, CHAINSAW, BACKGROUND/NON-THREAT  
**Target Deployment:** ESP32-S3 with TFLite Micro  
**Audio Specifications:** 16 kHz, mono, ~1-second windows  
**Feature Representations:** MFCC, Mel-spectrogram  
**Current Data Status:** NO DATA AVAILABLE - Dataset downloads failed

---

## Dataset Sources

**BLOCKED - NO DATASETS SUCCESSFULLY DOWNLOADED**

The previous agent selected four datasets, but all failed to download due to technical access issues:

### Selected Datasets (NOT AVAILABLE)
1. **C3GD (Certus Caliber Classification Gunshot Dataset)**
   - **Status:** DOWNLOAD FAILED
   - **Issue:** Zenodo download corrupted, GitHub repository contained no audio files
   - **Expected:** 8,015+ gunshot recordings

2. **RFCx FrugalAI Chainsaw Dataset**
   - **Status:** NOT ATTEMPTED
   - **Issue:** Hugging Face dependency issues
   - **Expected:** Large chainsaw dataset from forest deployments

3. **ESC-50 (Dataset for Environmental Sound Classification)**
   - **Status:** DOWNLOAD FAILED
   - **Issue:** Extremely slow download speeds leading to timeout
   - **Expected:** 2,000 environmental recordings

4. **Sensing the Forest - Natural Soundscape Dataset**
   - **Status:** NOT ATTEMPTED
   - **Issue:** Zenodo reliability concerns
   - **Expected:** Forest soundscapes

### Actual Status
- **Total Downloaded Audio Files:** 0
- **Total Processed Audio Files:** 0
- **Available Data:** NONE

**See `ml/reports/download_report.md` for detailed technical analysis.**

---

## Classes

**BLOCKED - NO ACTUAL CLASSES AVAILABLE**

**Expected Classes:** (NOT VALIDATED)
1. **GUNSHOT** - Acoustic signature of firearm discharge
2. **CHAINSAW** - Acoustic signature of chainsaw operation
3. **BACKGROUND/NON-THREAT** - Environmental forest sounds

**Expected Class Mapping:** (NOT VALIDATED)
- `gunshot`: 0
- `chainsaw`: 1
- `background`: 2

**Actual Status:** No data available to validate class existence or mapping

---

## Dataset Size

**BLOCKED - NO DATA AVAILABLE**

**Expected Sample Counts (Previous Estimates):**
- **Gunshot:** ~8,000+ samples (from C3GD)
- **Chainsaw:** ~3,000+ samples (from RFCx FrugalAI + ESC-50)
- **Background:** ~2,000+ samples (from ESC-50 + Sensing the Forest)

**Actual Sample Counts:**
- **Total Raw Files:** 0
- **Total Processed Files:** 0
- **Gunshot:** 0
- **Chainsaw:** 0
- **Background:** 0

**Reason:** Dataset downloads failed, no data available for processing
- Sensing the Forest: TBD (depends on download)

---

## Audio Format

### Original Formats (Before Preprocessing)
- **C3GD:** WAV (sample rate TBD)
- **RFCx FrugalAI:** Opus (lossy compression), 12 kHz typical
- **ESC-50:** WAV, 44.1 kHz
- **Sensing the Forest:** WAV (sample rate TBD)

### Target Format (After Preprocessing)
- **Sample Rate:** 16 kHz
- **Channels:** Mono
- **Duration:** ~1 second windows
- **Format:** WAV
- **Bit Depth:** 16-bit

---

## Preprocessing

### Pipeline Steps
1. **Audio Loading:** Load original audio files with error handling
2. **Resampling:** Convert all audio to 16 kHz using high-quality resampling
3. **Mono Conversion:** Convert stereo to mono by averaging channels
4. **Normalization:** Peak normalization to -3 dB
5. **Windowing:** Segment into 1-second windows with 50% overlap
6. **Quality Checks:** Remove corrupted, zero-length, or extremely clipped audio
7. **Hash Calculation:** Compute SHA256 hashes for duplicate detection
8. **Metadata Generation:** Create comprehensive manifest

### Windowing Strategy
- **Window Length:** 1.0 second
- **Hop Length:** 0.5 second (50% overlap)
- **Padding Strategy:** Repeat audio for short files
- **Truncation Strategy:** Center truncation for long files

### Quality Checks
- Corrupted file detection
- Zero-length audio removal
- Invalid sample rate identification
- Invalid channel count detection
- Extreme clipping detection (>0.95 amplitude)
- Duplicate file detection using SHA256 hashes

---

## Splitting

### Split Strategy
- **Method:** By source (original file) to prevent data leakage
- **Rationale:** All segments from the same original recording remain in the same split
- **Seed:** 42 (for reproducibility)

### Split Ratios
- **Train:** 70%
- **Validation:** 15%
- **Test:** 15%

### Leakage Prevention
The splitting algorithm ensures:
- No original recording appears in multiple splits
- Source-level grouping prevents leakage from overlapping windows
- Reproducible splits using fixed random seed

---

## Licenses

### Dataset Licenses
1. **C3GD:** CC BY 4.0 (permissive, commercial use allowed with attribution)
2. **RFCx FrugalAI:** CC BY-NC 4.0 (non-commercial only)
3. **ESC-50:** CC BY-NC 3.0 (non-commercial only)
4. **Sensing the Forest:** CC0 1.0 (public domain, most permissive)

### Usage Restrictions
- **Research Phase:** All datasets can be used for academic research
- **Commercial Deployment:** C3GD and Sensing the Forest allow commercial use
- **Commercial Deployment:** RFCx FrugalAI and ESC-50 require commercial license alternatives

### Attribution Requirements
- C3GD: Stonewall Defense (2024). Certus Caliber Classification Gunshot Dataset
- RFCx FrugalAI: Rainforest Connection (2024). RFCx Chainsaw Audio Dataset
- ESC-50: Piczak, K. J. (2015). ESC: Dataset for Environmental Sound Classification
- Sensing the Forest: Sensing the Forest Project (2024). Sensing the Forest - Natural Soundscape Dataset

---

## Known Limitations

### Domain Mismatch
- **Recording Conditions:** Public data may not match specific forest deployment conditions
- **Microphone Differences:** Datasets use various microphones vs. deployment microphone
- **Geographic Variation:** Training data from different regions than deployment
- **Environmental Noise:** Background conditions may differ from deployment sites

### Class Imbalance
- **Expected Imbalance:** Gunshot and chainsaw classes likely larger than background
- **Impact:** May require class weighting or oversampling during model training
- **Monitoring:** Class distribution will be measured and reported

### Audio Quality Variations
- **Compression:** RFCx FrugalAI uses lossy Opus compression
- **Sample Rate Variability:** Datasets have different original sample rates
- **Recording Quality:** Field recordings vary in quality and conditions

### License Restrictions
- **Non-Commercial:** 2 of 4 datasets have non-commercial licenses
- **Commercial Deployment:** May require alternative datasets or licensing for production

### Temporal Coverage
- **Seasonal Variation:** Limited seasonal coverage in some datasets
- **Time of Day:** Not all datasets cover diurnal variations
- **Weather Conditions:** Limited weather diversity in training data

---

## Potential Biases

### Geographic Bias
- **RFCx FrugalAI:** Primarily South America and Southeast Asia
- **Sensing the Forest:** United Kingdom (specific forest)
- **ESC-50:** Global but from Freesound contributors
- **C3GD:** Unspecified geographic locations

### Equipment Bias
- **Microphone Types:** Various microphones across datasets
- **Recording Devices:** Different recording equipment and settings
- **Sample Rates:** Original sample rates vary significantly

### Environmental Bias
- **Forest Types:** Limited forest type diversity
- **Weather Conditions:** Limited weather condition coverage
- **Background Noise:** Background noise profiles may not match deployment

### Temporal Bias
- **Time Periods:** Datasets collected in different time periods
- **Seasonal Coverage:** Incomplete seasonal coverage
- **Diurnal Patterns:** Not all datasets cover full diurnal cycles

---

## Acoustic Conditions

### Target Environment
- **Setting:** Forest areas with limited connectivity
- **Deployment:** Outdoor, fixed or mobile sensors
- **Microphone:** Omnidirectional, weather-protected
- **Conditions:** Variable weather, vegetation, wildlife

### Training Data Conditions
- **C3GD:** Outdoor firing ranges, controlled conditions
- **RFCx FrugalAI:** Real forest canopies, authentic conditions
- **ESC-50:** Mixed environments (urban, natural, indoor)
- **Sensing the Forest:** Authentic forest soundscapes

### Acoustic Challenges
- **Distance from Source:** Variable distances in training data
- **Reverberation:** Different reverberation characteristics
- **Background Noise:** Varying background noise levels
- **Weather Effects:** Wind, rain, temperature effects on sound propagation

---

## Data Leakage Precautions

### Source-Level Splitting
- **Strategy:** Split by original recording, not by individual segments
- **Implementation:** All windows from the same file stay in the same split
- **Verification:** Automated checks for source leakage across splits

### Duplicate Detection
- **Method:** SHA256 hashing of all audio files
- **Action:** Remove duplicates before splitting
- **Cross-Dataset:** Check for duplicates across different datasets

### Temporal Leakage Prevention
- **Strategy:** Avoid mixing temporally adjacent recordings
- **Implementation:** Group by recording session where possible
- **Metadata:** Use temporal metadata when available

---

## Intended Use

### Primary Use Case
- **Task:** Acoustic event classification for forest patrol
- **Classes:** Gunshot, chainsaw, background
- **Deployment:** On-device inference on ESP32-S3
- **Application:** Real-time threat detection in forest areas

### Research Applications
- **Algorithm Development:** Testing acoustic classification algorithms
- **Feature Engineering:** Developing robust audio features
- **Model Evaluation:** Benchmarking model performance
- **Domain Adaptation:** Studying domain transfer techniques

### Limitations on Use
- **Not for:** General-purpose audio classification
- **Not for:** Music or speech recognition
- **Not for:** Commercial applications without proper licensing
- **Not for:** Surveillance or privacy-invasive applications

---

## Not Intended Use

### Prohibited Uses
- **Surveillance:** Mass surveillance or privacy violations
- **Weapon Development:** Developing weapons or weapon systems
- **Privacy Violation:** Eavesdropping or unauthorized recording
- **Military Combat:** Direct military combat applications
- **Illegal Activities:** Any illegal or unethical applications

### Misuse Prevention
- **Ethical Guidelines:** Follow ethical AI principles
- **Privacy:** Respect privacy rights and regulations
- **Legal Compliance:** Comply with all applicable laws
- **Environmental Impact:** Consider environmental impact of deployments

---

## Maintenance and Updates

### Version Control
- **Dataset Version:** 1.0 (initial release)
- **Manifest Tracking:** All changes tracked in Git
- **Reproducibility:** Fixed seeds and configuration files
- **Documentation:** Comprehensive documentation of all changes

### Future Updates
- **Additional Datasets:** May add more datasets as needed
- **Field Recordings:** Plan to add real forest field recordings
- **Quality Improvements:** Iterative quality improvements
- **License Clarification:** Ongoing license verification and compliance

---

## Contacts and Support

### Dataset Maintainers
- **Project:** SECURE FOREST PATROL
- **Phase:** ML Dataset Foundation (Data + Preprocessing Only)
- **Status:** Research Phase

### Issues and Questions
- **Documentation:** See `ml/README.md` for usage instructions
- **License Questions:** Refer to individual dataset licenses
- **Technical Issues:** Check preprocessing and audit reports

---

## References

### Dataset Citations
- Stonewall Defense. (2024). Certus Caliber Classification Gunshot Dataset (C3GD). Zenodo. https://doi.org/10.5281/zenodo.20274399
- Rainforest Connection. (2024). RFCx Chainsaw Audio Dataset. Hugging Face Datasets.
- Piczak, K. J. (2015). ESC: Dataset for Environmental Sound Classification. In Proceedings of the 23rd ACM International Conference on Multimedia.
- Sensing the Forest Project. (2024). Sensing the Forest - Natural Soundscape Dataset. Zenodo.

### Related Research
- Certus Innovations. (2026). Exploring Feature Extraction Technique Parameters for Acoustic Gunshot Classification. DCASE 2026.
- Stefanakis, N., et al. (2022). An open-access system for long-range chainsaw sound detection. EUSIPCO 2022.

---

## Appendix

### File Structure
```
ml/
├── datasets/
│   ├── raw/              # Original downloaded datasets
│   ├── interim/          # Intermediate processing results
│   ├── processed/        # Final processed dataset
│   └── manifests/        # Dataset manifests and splits
├── preprocessing/        # Audio preprocessing pipeline
├── scripts/              # Download and utility scripts
├── notebooks/            # Jupyter notebooks for exploration/QA
├── metadata/             # Dataset metadata, licenses, citations
├── configs/              # Configuration files
└── reports/              # Quality reports and analysis
```

### Configuration Files
- `configs/preprocessing.yaml` - Audio preprocessing settings
- `configs/augmentation.yaml` - Data augmentation configuration

### Key Scripts
- `scripts/download_all.py` - Master download script
- `scripts/audit_dataset.py` - Quality audit script
- `scripts/create_splits.py` - Dataset splitting script
- `preprocessing/audio_preprocess.py` - Audio preprocessing pipeline
- `preprocessing/feature_extraction.py` - Feature extraction module

### Reports
- `reports/dataset_quality_report.md` - Quality audit results
- `reports/class_distribution.md` - Class balance analysis
- `reports/domain_gap.md` - Domain gap analysis
- `reports/preprocessing_validation.md` - Preprocessing validation
- `reports/MODEL_HANDOFF.md` - Model training handoff

---

**Document Version:** 1.0  
**Last Updated:** 2026-09-18  
**Status:** Research Foundation Phase (No Model Training)
