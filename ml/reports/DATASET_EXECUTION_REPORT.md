# Dataset Execution Report

## EXECUTION STATUS

DATASET COLLECTION: PARTIAL
DATASET AUDIT: COMPLETED
PREPROCESSING: COMPLETED
FEATURE EXTRACTION: NOT STARTED
SPLITTING: COMPLETED
LEAKAGE CHECK: PASSED
FINAL DATASET: NOT READY FOR MODEL DEVELOPMENT

---

## ACTUAL DATA

### Raw Data Statistics
- **Total raw audio files:** 26 files
- **Total original recordings:** 16 recordings
- **Total datasets used:** 5 sources

### Processed Data Statistics
- **Total processed segments:** 663 segments
- **Total original recordings:** 16 recordings
- **Total datasets:** 5 sources
- **Audio format:** 16 kHz, mono, 1-second segments

### Class Distribution
- **chainsaw:** 577 segments (87.0%)
- **background:** 78 segments (11.8%)
- **gunshot:** 8 segments (1.2%)

### Split Statistics
- **Train:** 603 segments (11 recordings)
- **Validation:** 38 segments (2 recordings)
- **Test:** 22 segments (3 recordings)

### Original Recordings Per Class
- **background:** 10 recordings
- **chainsaw:** 4 recordings
- **gunshot:** 2 recordings

---

## DATA SOURCES

### Successfully Downloaded Datasets

1. **Sonilo Gunshot Dataset**
   - **Source:** Sonilo free sound effects
   - **Files:** 2 recordings
   - **License:** Free sound effects (for research use)
   - **Status:** Successfully downloaded and processed
   - **Recording:** 2 gunshot recordings

2. **Sonilo Chainsaw Dataset**
   - **Source:** Sonilo free sound effects
   - **Files:** 3 recordings
   - **License:** Free sound effects (for research use)
   - **Status:** Successfully downloaded and processed
   - **Recording:** 3 chainsaw recordings

3. **DESRA (partial)**
   - **Source:** Zenodo https://doi.org/10.5281/zenodo.2622626
   - **Files:** 10 recordings (partial download)
   - **License:** CC BY 4.0
   - **Status:** Successfully downloaded and processed
   - **Recording:** 10 environmental sound recordings

4. **DESRA Full (additional)**
   - **Source:** Zenodo https://doi.org/10.5281/zenodo.2622626
   - **Files:** 10 recordings
   - **License:** CC BY 4.0
   - **Status:** Successfully downloaded and processed
   - **Recording:** 10 additional environmental sound recordings

5. **Greek Chainsaw Dataset**
   - **Source:** Zenodo https://doi.org/10.5281/zenodo.5824433
   - **Files:** 1 recording (PR_20161205_115013.wav)
   - **License:** CC BY 4.0
   - **Status:** Successfully downloaded and processed
   - **Recording:** 1 long chainsaw recording (generates 545 segments)

---

## FAILED SOURCES

### Attempted but Failed to Download

1. **C3GD (Certus Caliber Classification Gunshot Dataset)**
   - **Source:** Zenodo https://doi.org/10.5281/zenodo.20274400
   - **License:** CC BY 4.0
   - **Target:** 8,015 gunshot recordings
   - **Issue:** Download timeout/cancelled due to large file size (735 MB)
   - **Status:** NOT DOWNLOADED
   - **Note:** This is a critical gap for gunshot data

2. **ESC-50 Dataset**
   - **Source:** GitHub https://github.com/karolpiczak/ESC-50
   - **License:** CC BY 4.0
   - **Target:** 2,000 environmental recordings
   - **Issue:** Download timeout/slow speed from GitHub
   - **Status:** NOT DOWNLOADED
   - **Note:** This is a critical gap for background data

3. **UrbanSound8K Dataset**
   - **Source:** Zenodo
   - **License:** Unknown (to be verified)
   - **Target:** ~8,700 recordings
   - **Issue:** URL format changes, direct download failed
   - **Status:** NOT DOWNLOADED

4. **FSD50K Dataset**
   - **Source:** Zenodo https://doi.org/10.5281/zenodo.4060432
   - **License:** CC BY 4.0
   - **Target:** 51,197 recordings
   - **Issue:** Large file size, download cancelled
   - **Status:** NOT DOWNLOADED

5. **RFCx FrugalAI**
   - **Source:** Hugging Face
   - **License:** CC BY-NC 4.0 (non-commercial)
   - **Target:** ~2,000 recordings
   - **Issue:** Hugging Face library compatibility issues
   - **Status:** NOT DOWNLOADED

6. **Zenodo Gunshot Dataset**
   - **Source:** Zenodo https://doi.org/10.5281/zenodo.7004819
   - **License:** CC BY 4.0
   - **Target:** ~10,000 recordings
   - **Issue:** Large file size (1.6 GB), download cancelled
   - **Status:** NOT DOWNLOADED

7. **Freesound Direct Downloads**
   - **Source:** Freesound.org
   - **Issue:** HTML responses instead of audio files (authentication/CORS issues)
   - **Status:** FAILED
   - **Note:** Multiple attempts returned HTML instead of WAV files

---

## FILES CREATED

### Audio Files
- **ml/datasets/raw/** - 26 raw audio files
- **ml/datasets/processed/** - 663 processed 16kHz mono 1-second segments

### Manifests
- **ml/datasets/manifests/train.csv** - 603 training segments
- **ml/datasets/manifests/val.csv** - 38 validation segments
- **ml/datasets/manifests/test.csv** - 22 test segments
- **ml/datasets/manifests/master_manifest.csv** - 663 total segments
- **ml/datasets/manifests/dataset_statistics.txt** - Detailed statistics report

### Download Scripts
- **ml/scripts/download_zenodo_gunshot.py** - Zenodo gunshot downloader
- **ml/scripts/download_greek_chainsaw.py** - Greek chainsaw downloader
- **ml/scripts/download_desra.py** - DESRA downloader
- **ml/scripts/download_fsd50k.py** - FSD50K downloader (created but not executed)

### Validation Scripts
- **ml/scripts/validate_leakage.py** - Leakage validation script
- **ml/scripts/generate_dataset_report.py** - Statistics generation script

### Preprocessing Scripts
- **ml/preprocessing/simple_preprocess.py** - Updated preprocessing pipeline

---

## VALIDATION

### Leakage Validation
- **Status:** ✅ PASSED
- **Train-Val leakage:** None
- **Train-Test leakage:** None
- **Val-Test leakage:** None
- **Source-level splitting:** Correctly implemented

### Audio Format Validation
- **Sample rate:** All files at 16 kHz ✅
- **Channels:** All files mono ✅
- **Duration:** All segments exactly 1.0 second ✅
- **Quality:** No clipping detected ✅

### Data Quality
- **Readable files:** All 26 raw files successfully processed ✅
- **Zero-length files:** None ✅
- **Corrupt files:** None ✅

---

## REMAINING GAP

### Scale Gap
- **Current:** 16 original recordings
- **Minimum Viable Target:** 200 recordings
- **Gap:** 184 recordings (11.5x insufficient)
- **Research Target:** 800 recordings
- **Gap:** 784 recordings (50x insufficient)

### Class Distribution Gap
- **Current:** chainsaw 87%, background 11.8%, gunshot 1.2%
- **Target:** Balanced distribution (~33% each)
- **Gap:** Severe class imbalance, especially gunshot class

### Source Diversity Gap
- **Current:** 5 total sources (gunshot: 1, chainsaw: 2, background: 2)
- **Minimum Viable Target:** 15+ sources (5+ per class)
- **Gap:** Gunshot has only 1 source, high overfitting risk

### Test Set Gap
- **Current:** 22 test segments (3 recordings)
- **Minimum Viable Target:** 120-150 test segments
- **Gap:** Test set too small for meaningful evaluation

### Domain Gap
- **Current:** No field data collected
- **Target:** Field data from deployment conditions
- **Gap:** Complete lack of deployment-domain data

### Geographic Gap
- **Current:** Limited geographic diversity
- **Target:** Multiple geographic regions
- **Gap:** Dataset lacks geographic diversity

### Environmental Gap
- **Current:** Limited environmental conditions
- **Target:** Diverse weather, seasons, times of day
- **Gap:** Minimal environmental variation

---

## CRITICAL LIMITATIONS

### 1. Dataset Scale Insufficient
The current dataset (16 recordings) is **11.5x smaller** than the minimum viable target (200 recordings). This is insufficient for:
- Reliable model training
- Meaningful evaluation
- Research-grade claims
- Generalization assessment

### 2. Severe Class Imbalance
- **Gunshot:** Only 8 segments (1.2%) from 2 recordings
- **Chainsaw:** 577 segments (87.0%) from 4 recordings
- **Background:** 78 segments (11.8%) from 10 recordings

This imbalance will cause:
- Poor model performance on minority classes
- Biased evaluation metrics
- High false negative rates for gunshots

### 3. Limited Source Diversity
- **Gunshot:** Only 1 source (Sonilo)
- **Chainsaw:** 2 sources (Sonilo, Greek)
- **Background:** 2 sources (DESRA variants)

This limitation will cause:
- High risk of learning source-specific artifacts
- Poor generalization to new sources
- Dataset-specific overfitting

### 4. No Field Data
- **Field recordings:** None collected
- **Deployment conditions:** Not represented
- **ESP32-S3 + INMP441:** Not tested

This limitation will cause:
- Unknown domain gap
- Unpredictable deployment performance
- No real-world validation

### 5. Insufficient Test Set
- **Test segments:** 22 segments
- **Test recordings:** 3 recordings
- **Per-class test:** Gunshot: 0 segments in test

This limitation will cause:
- Unreliable evaluation metrics
- No meaningful per-class test evaluation
- High variance in performance estimates

---

## NEXT STEPS REQUIRED

### Immediate Actions (Required for Model Development)

1. **Download C3GD Dataset**
   - **Priority:** CRITICAL for gunshot data
   - **Target:** 8,015 gunshot recordings
   - **Action:** Retry download with better network or use alternative mirror

2. **Download ESC-50 Dataset**
   - **Priority:** CRITICAL for background data
   - **Target:** 2,000 environmental recordings
   - **Action:** Use alternative download method or mirror

3. **Collect Field Data**
   - **Priority:** CRITICAL for deployment validation
   - **Target:** 50+ field recordings
   - **Action:** Set up ESP32-S3 + INMP441 for field recording

4. **Improve Class Balance**
   - **Priority:** HIGH
   - **Target:** ~33% per class
   - **Action:** Add more gunshot and background recordings

5. **Increase Source Diversity**
   - **Priority:** HIGH
   - **Target:** 5+ sources per class
   - **Action:** Download additional datasets per class

---

## FINAL ASSESSMENT

### Dataset Readiness: NOT READY FOR MODEL DEVELOPMENT

**Rationale:**
1. Dataset scale is 11.5x smaller than minimum viable target
2. Severe class imbalance (gunshot only 1.2% of data)
3. Limited source diversity (gunshot only 1 source)
4. No field data collected
5. Test set too small for meaningful evaluation
6. High risk of overfitting and poor generalization

**Recommendation:**
Proceed with **Phase 1: Minimum Viable Dataset Expansion** before model development. Focus on:
- Downloading C3GD (8,015 gunshot recordings)
- Downloading ESC-50 (2,000 environmental recordings)
- Collecting initial field data (50+ recordings)
- Achieving balanced class distribution

**Estimated Timeline to Readiness:** 4-6 weeks for minimum viable dataset expansion

---

**Report Date:** 2026-09-19
**Report Version:** 1.0
**Status:** DATASET INSUFFICIENT - EXPANSION REQUIRED