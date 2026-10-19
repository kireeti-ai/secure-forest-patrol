# Acoustic ML: from dataset to detection on the ESP32-S3 node

End-to-end description of the forest acoustic classifier (`background` / `chainsaw` / `gunshot`): where the data
came from, how it was prepared, trained, evaluated, quantised, embedded in `node-firmware`, and how the node uses it
to raise an event.

Every number here was re-checked against code, data files or metadata (not only against the written reports).
Each claim is tagged:

- **Measured**: read from a data file / metadata / test output in this repo.
- **Configured**: a constant in code or config.
- **Unverified**: not tested on real hardware or real forest audio.

Paths are relative to the repo root (`SECURE-FOREST-PATROL/`). Section 16 lists places where the existing reports
or docs disagree with the code.

---

## 1. Pipeline at a glance

```
 download (ml/scripts)         audit + leakage gates              preprocess (ml/preprocessing)
 6 public datasets  ───────►   audit_dataset.py            ───►   16 kHz mono, -3 dBFS peak, 1 s windows
 15,177 raw files              validate_leakage.py                58,918 segments, 1,975 recordings
                                                                          │
                                                                          ▼
   ml/datasets/v1/*.csv  ◄──  create_splits.py  (grouped by recording, external test held out)
                                                                          │
                                                                          ▼
   prepare_features.py  ──►  log-mel (40 × 101)  ──►  train_cnn.py  ──►  final.keras (1,315 params)
   (class-capped caches)      global z-norm            Adam + class weights + augmentation
                                                                          │
                                                                          ▼
   convert_tflite.py  ──►  FP32 .tflite (13,272 B)  ──►  full-integer INT8 .tflite (13,072 B)
                                                                          │
                                       node-firmware/tools/embed_model.py │ gen_acoustic_tables.py
                                                                          ▼
   AcousticModelData.h + AcousticTables.h  ──►  TFLite Micro on ESP32-S3
                                                                          │
   MAX4466 trigger → INMP441 1 s window → C++ log-mel → INT8 inference → argmax
                                                                          │
                               6-byte 'A' payload → flash log → LoRa DATA packet → gateway ACK → MQTT → backend
```

---

## 2. Datasets

### 2.1 Sources and what each contributes

| Dataset (`dataset_id`) | Origin | Licence | Acquisition | Contributes |
|---|---|---|---|---|
| **C3GD** (`c3gd`) | https://github.com/Stonewall-Defense/C3GD (Zenodo file URL in `ml/scripts/download_c3gd.py:22`) | CC BY 4.0 | `ml/scripts/download_c3gd.py` | gunshot |
| **FSC22** (`fsc22`) | https://ieee-dataport.org/documents/fsc22-dataset (2,025 clips from Freesound, 34 classes) | Unknown / "to be verified" | No script in `ml/scripts/`; placed manually in `ml/datasets/raw/fsc22/` | gunshot, chainsaw, background |
| **Rodopi / Greece chainsaw events** (`rodopi`) | https://doi.org/10.5281/zenodo.5824433 (8 kHz ARU recordings with Praat TextGrids) | Unknown ("likely CC BY") | No script; placed manually in `ml/datasets/raw/rodopi/`; parsed by `ml/scripts/textgrid.py` | chainsaw (`saw` intervals), background (other intervals) |
| **ESC-50 via Hugging Face** (`esc50_hf`) | https://github.com/karolpiczak/ESC-50 ; mirror used: `yangwang825/esc50` (`ml/scripts/download_esc50_hf.py:33`) | CC BY-NC 3.0 | `ml/scripts/download_esc50.py`, `download_esc50_hf.py` | chainsaw, background |
| **RFCx FrugalAI** (`rfcx_frugalai`) | https://huggingface.co/datasets/rfcx/frugalai (12 kHz Opus, Guardian devices) | CC BY-NC 4.0 | `ml/scripts/download_frugalai.py` | chainsaw, background |
| **Sensing the Forest** (`sensing_forest`) | https://zenodo.org/records/18909809 (Alice Holt Forest, UK) | CC0 1.0 | `ml/scripts/download_sensing_forest.py`, `retry_stf.py` | background (long ambient recordings) |

Licence bookkeeping is in `ml/metadata/licenses.csv`, citations in `ml/metadata/dataset_citations.md`, selection
rationale in `ml/metadata/dataset_selection.md`, and the full research list (including datasets that were
researched but not used, such as the Certus DCASE 2026 gunshot set, Gabon and Vietnam gunshots) in
`ml/metadata/dataset_sources.md`. `ml/metadata/DATASET_CARD.md` is the dataset card.

**Licence caveat:** FrugalAI and ESC-50 are non-commercial. FSC22 and Rodopi licences were never verified. Check this
before any commercial use of the trained model.

### 2.2 Raw and processed counts (Measured)

Raw audio: 15,177 files in `ml/datasets/raw/` (`ml/README.md`). Quality audit
(`ml/scripts/audit_dataset.py`, report `ml/reports/dataset_quality_report.md`): 15,103 files audited, 0 corrupted,
0 zero-length, 682 non-standard sample rates, 8,169 near-clipping, 3 exact duplicates (left in place).

After preprocessing (`ml/datasets/v1/master_v1.csv`, 58,918 rows; source: `ml/reports/DATASET_V1_REPORT.md`):

| Class | Segments (1 s windows) |
|---|---|
| background | 55,069 |
| chainsaw | 3,407 |
| gunshot | 442 |
| **Total** | **58,918** (1,975 source recordings, 16.37 h) |

| Dataset | background | chainsaw | gunshot | Recordings |
|---|---|---|---|---|
| c3gd | 0 | 0 | 100 | 100 |
| esc50_hf | 3,764 | 356 | 0 | 493 |
| fsc22 | 6,665 | 669 | 342 | 939 |
| rfcx_frugalai | 1,246 | 741 | 0 | 400 |
| rodopi | 25,056 | 1,641 | 0 | 9 |
| sensing_forest | 18,338 | 0 | 0 | 34 |

Notes on the imbalance: gunshot has only 442 segments (about 0.75 %). Most of the gunshot data comes from only
4 C3GD shooting events (100 clips) plus 342 FSC22 segments from 75 recordings. Most of the background data
(43,394 segments) comes from just two sources: `rodopi` (9 long recordings) and `sensing_forest` (34 recordings).

### 2.3 Labelling rules (`ml/preprocessing/audio_preprocess.py`)

- **C3GD** (`process_c3gd`): a diversity-maximising subset of 130 recordings is picked from `metadata.csv`
  (12,112 rows) by round-robin over unique `(event_id, platform_id, cartridge_id, mic_id)` combinations, seed 42
  (`subset_size: 130` in `ml/configs/preprocessing.yaml`). All are `gunshot`. 100 of 130 pass the quality gate.
- **FSC22** (`FSC22_LABEL_MAP`, lines 52-81): `Gunshot`→gunshot, `Chainsaw`→chainsaw; `BirdChirping, Frog, Insect,
  Rain, Wind, WaterDrops, Thunderstorm, WolfHowl, Squirrel, WingFlaping, Lion`→background. Everything else is
  discarded (`Fire, Clapping, Footsteps, Speaking, Whistling, WoodChop, Firework, Handsaw, Generator, Axe,
  VehicleEngine, Helicopter, TreeFalling, Silence`). `Handsaw` is dropped on purpose because it sounds close to
  chainsaw but is not.
- **Rodopi**: TextGrid intervals labelled `saw`→chainsaw; other intervals→background (capped at 30 background
  intervals per recording).
- **ESC-50** (lines 84-88): `chainsaw`→chainsaw; `chirping_birds, rain, wind, crickets, insects, water_drops, frog,
  crow, crackling_fire, footsteps, thunderstorm, engine`→background.
- **FrugalAI**: folder label (`chainsaw`→chainsaw, `environment`→background); 12 kHz resampled to 16 kHz.
- **Sensing the Forest**: all 34 recordings are background.

Two consequences worth knowing: `engine` and `crackling_fire` are labelled background, and the background class
mixes bird/rain/wind with vehicles and footsteps.

### 2.4 Data-quality gates

- `ml/scripts/audit_dataset.py`: corruption, zero-length, sample rate, clipping and duplicate checks.
- `ml/scripts/validate_leakage.py`: **PASSED**, no `original_recording_id` appears in more than one split
  (`ml/reports/DATASET_V1_REPORT.md`). `create_splits.py` also asserts this at split time (lines 76-81).
- `ml/tests/test_audio_filter.py`: 7 unit tests for the optional high-pass filter.

---

## 3. Preprocessing (per recording → 1 s segments)

Config: `ml/configs/preprocessing.yaml`. Code: `ml/preprocessing/audio_preprocess.py` (`AudioPreprocessor`).
Order of operations (`_load_resample_mono_norm`, lines 239-247, then `_write_segments`):

| Step | Detail | Setting |
|---|---|---|
| 1. Load | `soundfile.read`, float32 | - |
| 2. Mono | mean over channels | `target_channels: 1` |
| 3. Resample | `librosa.resample`, `kaiser_best` | 16 kHz |
| 4. Filter (optional) | causal 2nd-order Butterworth high-pass, 80 Hz, `sosfilt` | **off** (`filter.enabled: false`); `ml/preprocessing/audio_filter.py` |
| 5. Normalise | **peak normalisation of the whole recording** to -3 dBFS (gain = 10^(-3/20) / max) | `normalization_method: peak`, `target_dB: -3.0` |
| 6. Segment | 1.0 s windows, **0.5 s hop (50 % overlap)**; a tail window aligned to the end is added if more than 0.5 s is left; files shorter than 1 s are repeat-tiled | `window_duration: 1.0`, `hop_duration: 0.5`, `padding_strategy: repeat` |
| 7. Quality check per segment | reject if peak > 0.95 (clipping) or more than 80 % of samples below 0.01 (silence) | `clipping_threshold`, `silence_threshold`, `silence_ratio_threshold` |
| 8. Write | 16-bit PCM WAV to `ml/datasets/processed/<sample_id>.wav` + manifest row (`ml/datasets/manifests/master_manifest.csv`) | `output_bit_depth: 16` |

Unreadable files are logged in `ml/datasets/manifests/skipped_files.json`.

Because segments overlap by 50 %, neighbouring segments of one recording are highly correlated. This is why the
split is grouped by recording (section 4).

Optional high-pass filter: coefficients `b = [0.97803048, -1.95606096, 0.97803048]`, `a = [1, -1.95557824,
0.95654368]`, Direct Form II Transposed (`ml/reports/FILTER_REPORT.md`). It was tested and **not adopted**
(section 8.5). A filtered copy of all 58,918 segments exists in `ml/datasets/processed_filtered/` with matching
features in `ml/datasets/features_cache_filtered/`.

---

## 4. Train / validation / test / external-test split

`ml/preprocessing/create_splits.py` (seed 42, ratios 0.70 / 0.15 / 0.15):

1. **External test** is carved out first from sources that never enter train/val/test:
   all `sensing_forest` recordings, the last (alphabetically) C3GD `event_id`, and 2 randomly chosen Rodopi recordings.
2. The remaining recordings are shuffled and split **by `original_recording_id`**, so no recording spans two splits.
3. Leakage assertions run on every split pair.

| Split | Segments | Recordings | background | chainsaw | gunshot |
|---|---|---|---|---|---|
| train_v1 | 28,741 | 1,328 | 26,344 | 2,093 | 304 |
| validation_v1 | 6,999 | 284 | 6,501 | 444 | 54 |
| test_v1 | 2,119 | 286 | 1,781 | 295 | 43 |
| external_test_v1 | 21,059 | 77 | 20,443 | 575 | 41 |

(**Measured**: row counts of `ml/datasets/v1/*.csv` are 28,741 / 6,999 / 2,119 / 21,059 / 58,918.)

Limitations: the split is grouped by *recording*, not by *site or event*. Segments from one C3GD event or one
FSC22 Freesound uploader can still land in different splits. The test set holds only 43 gunshot segments, so
gunshot metrics are noisy.

---

## 5. Feature extraction and the capped training caches

Code: `ml/preprocessing/feature_extraction.py` (`extract_mel_spectrogram`), `ml/models/prepare_features.py`.

**Model input feature (log-mel), per 1 s segment:**

```
librosa.feature.melspectrogram(y, sr=16000, n_fft=512, hop_length=160, n_mels=40, fmin=0, fmax=8000, power=2.0)
librosa.power_to_db(mel, ref=np.max)          # top_db default 80; reference = maximum of THIS clip
-> array (40 mel bins, 101 frames)             # center=True → 1 + 16000/160 = 101 frames
```

Then, at training time, a single global z-score using the training-set statistics:
`x = (dB - (-36.3185)) / 21.1904` (`feature_mean`, `feature_std` in `ml/models/final/final_metadata.json`).

MFCC (13 × 101) is also cached but only used by the baseline model.

**The training caches are class-capped, not the full split** (`prepare_features.py:75-78`). **Measured** from
`ml/datasets/features_cache/*.npz` (identical shapes in `features_cache_filtered/`):

| Cache | Cap per class | Array shape | background / chainsaw / gunshot |
|---|---|---|---|
| train | 6,000 | (8,397, 40, 101) | 6,000 / 2,093 / 304 |
| validation | 2,000 | (2,498, 40, 101) | 2,000 / 444 / 54 |
| test | none | (2,119, 40, 101) | 1,781 / 295 / 43 |
| external_test | 3,000 | (3,616, 40, 101) | 3,000 / 575 / 41 |

Background is randomly sampled (seed 42) down to the cap; all chainsaw and gunshot segments are kept. So the model
trains on **8,397** samples (not 28,741), validates on 2,498, and the "external test" figures are on a 3,616-sample
subset of the 21,059-segment external set.

---

## 6. Data augmentation (training only)

`ml/models/augment.py` (called from `AugmentedSequence`, `train_cnn.py:107-131`; parameters in
`ml/configs/augmentation.yaml`). Applied to log-mel arrays, per sample with probability 0.5:

| Augmentation | Probability | Detail |
|---|---|---|
| Gain | 0.4 | add uniform -6 to +6 dB to the dB-scale mel |
| Time shift | 0.3 | circular `np.roll` by up to ±10 % of frames |
| Background mix | 0.3 | linear mix in the dB domain with a random background sample of the same batch, alpha 0.05-0.25 (approximation; a real waveform mix is not done) |
| SpecAugment time mask | 0.3 | 2 masks, width up to 20 % of frames, filled with the sample mean |
| SpecAugment frequency mask | 0.3 | 2 masks, height up to 20 % of mel bins |

Never applied to validation, test or external data.

---

## 7. Models and training

### 7.1 Models compared

| Model | Features | Params | Weights (FP32) | Script |
|---|---|---|---|---|
| Baseline | 26-dim MFCC mean+std → Logistic Regression | n/a | n/a | `ml/models/baseline/train_baseline.py` → `baseline_model.joblib` |
| Compact CNN | log-mel (40×101×1) | 6,147 | 24.0 KB | `ml/models/train_cnn.py --variant compact_cnn` → `ml/models/compact_cnn/` |
| **Final (deployed)** | log-mel (40×101×1) | **1,315** | **5,260 B** | `ml/models/train_cnn.py --variant final` → `ml/models/final/final.keras` |

### 7.2 Final architecture (`build_final_model`, `train_cnn.py:59-84`)

| # | Layer | Output shape | Note |
|---|---|---|---|
| 0 | Input | 40 × 101 × 1 | |
| 1 | Conv2D 8, 3×3, stride 2, same + BN + ReLU | 20 × 51 × 8 | |
| 2 | DepthwiseConv2D 3×3 + BN + ReLU | 20 × 51 × 8 | |
| 3 | Conv2D 16, 1×1 (pointwise) + BN + ReLU | 20 × 51 × 16 | |
| 4 | MaxPool 2×2 | 10 × 25 × 16 | |
| 5 | DepthwiseConv2D 3×3 + BN + ReLU | 10 × 25 × 16 | |
| 6 | Conv2D 16, 1×1 + BN + ReLU | 10 × 25 × 16 | |
| 7 | GlobalAveragePooling2D | 16 | becomes `MEAN` in TFLite |
| 8 | Dense 16, ReLU | 16 | |
| 9 | Dense 3, softmax | 3 | order: background, chainsaw, gunshot |

Shapes are from the layer configs in `final_metadata.json`. BatchNorm is folded into the convolutions by the
TFLite converter (no BN op in the `.tflite`).

### 7.3 Training configuration (**Measured** from `final_metadata.json`)

| Item | Value |
|---|---|
| Framework | TensorFlow / Keras |
| Seed | 42 (`np.random`, `tf.random`); TF is not bit-deterministic (see 8.5) |
| Optimiser / LR | Adam, 1e-3 |
| Loss | sparse categorical cross-entropy |
| Batch size | 32 |
| Epochs | 15 requested, 15 ran |
| Early stopping | monitor `val_loss`, patience 4, `restore_best_weights=True`; never triggered. The stored validation accuracy (0.8267) equals epoch 13, the best val_loss epoch (0.4409), so the epoch-13 weights were restored |
| Class weights | `compute_class_weight('balanced')` on the capped train set: background 0.4665, chainsaw 1.3373, gunshot 9.2072 |
| Normalisation | global mean -36.3185, std 21.1904 from the train set |
| Train time | 35.4 s |
| Final-epoch train accuracy | 0.8035 |
| Model selection | on **validation macro-F1 only**; test and external sets were evaluated after selection |

Validation loss is noisy across epochs (0.44 to 0.86), so the result depends on which epoch is restored.

---

## 8. Evaluation

Metrics code: `evaluate()` in `train_cnn.py` (accuracy, balanced accuracy, macro-F1/precision/recall, per-class F1
and recall, confusion matrix). Protocol notes: `ml/reports/METRICS_AND_EVALUATION_PROTOCOL.md`.

### 8.1 Model comparison (macro-F1, FP32)

| Model | Validation | Test | External |
|---|---|---|---|
| Baseline (MFCC + LogReg) | 0.4251 | 0.3595 | 0.5899 |
| Compact CNN | 0.5358 | 0.3285 | 0.2207 |
| **Final** | **0.6542** | **0.5611** | **0.5793** |

Source: `ml/reports/FINAL_MODEL_REPORT.md`; final row matches `final_metadata.json` exactly.

### 8.2 Final model, FP32 Keras (Measured)

| Split | Accuracy | Balanced acc. | Macro-F1 |
|---|---|---|---|
| Validation (2,498) | 0.8267 | 0.6931 | 0.6542 |
| Test (2,119) | 0.7069 | 0.7969 | 0.5611 |
| External (3,616) | 0.4372 | 0.7153 | 0.5793 |

Per class on the test set:

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| background | 0.97 | 0.68 | 0.80 | 1,781 |
| chainsaw | 0.35 | 0.85 | 0.49 | 295 |
| gunshot | 0.25 | 0.86 | 0.39 | 43 |

Test confusion matrix (rows = true, columns = predicted: background, chainsaw, gunshot):

```
background   1210  471  100
chainsaw       35  251    9
gunshot         6    0   37
```

On the external set, background recall is only **0.36** (1,919 of 3,000 background segments are called chainsaw).
Gunshot is strong there (F1 0.91, recall 0.98) but has only 41 support. So the operating point is
high-recall, low-precision: it will rarely miss a chainsaw/gunshot but will raise many false alarms.

### 8.3 Robustness (INT8, `ml/models/robustness_eval.py`, `ml/reports/ROBUSTNESS_REPORT.md`)

Gaussian noise added to the mel features of the test set (feature space, not waveform space):

| Condition | Accuracy | Macro-F1 | Background false-alarm rate |
|---|---|---|---|
| clean | 0.7216 | 0.5760 | 0.3010 |
| 15 dB SNR | 0.5295 | 0.3793 | 0.4526 |
| 5 dB SNR | 0.0203 | 0.0133 | 1.0000 |

### 8.4 Failure analysis and domain gap

- `ml/reports/FAILURE_ANALYSIS.md` lists concrete misclassified `sample_id`s: mostly background segments with
  transient or percussive content called chainsaw/gunshot, and low-energy event windows called background.
- `ml/reports/domain_gap.md` rates the gap to the real deployment (microphone, distance, vegetation, weather) as
  HIGH for several factors. No data from the INMP441 or from the target forest was ever collected
  (`ml/reports/DATA_COLLECTION_PLAN.md`, `ml/metadata/FIELD_DATA_COLLECTION_PROTOCOL.md` describe the plan only).

### 8.5 Optional-filter A/B experiment (`ml/models/ab_filter_experiment.py`, `ml/reports/FILTER_REPORT.md`)

3 seeds (42, 1, 2) each for no-filter (A) and 80 Hz high-pass (B), same architecture and settings, artifacts in
`ml/models/ab_filter/`:

| Metric (mean ± std) | A no filter | B filter |
|---|---|---|
| val macro-F1 | 0.596 ± 0.047 | 0.612 ± 0.083 |
| test macro-F1 | 0.464 ± 0.008 | 0.399 ± 0.072 |
| external macro-F1 | 0.359 ± 0.045 | 0.404 ± 0.102 |

Conclusions: the filter shows no consistent gain, so `ml/models/final` was **not** retrained and the filter is off
in firmware. More importantly, the **A seed-42 re-run scored test macro-F1 0.455 vs 0.561 for the shipped model**
(`ml/reports/ab_filter_results.json`). Run-to-run variance with this tiny model and small gunshot set is large;
the shipped model's 0.561 is a good draw, not a stable expectation.

### 8.6 Notebooks (`ml/notebooks/`)

`01_dataset_exploration`, `02_preprocessing_and_features`, `03_dataset_validation`, `04_baseline_training`,
`05_compact_cnn_training`, `06_model_evaluation`, `07_robustness_and_external_test`, `08_quantization_and_tflite`,
`09_tflite_micro_validation`, `10_audio_file_demo`, `11_filter_ab_comparison`, plus `data_qa.ipynb`. They are built
by `build_notebooks.py` / `_nb_builder.py`.

---

## 9. Conversion to TFLite and INT8 quantisation

Script: `ml/models/convert_tflite.py`. Outputs in `ml/models/final/`.

1. **FP32 TFLite**: `TFLiteConverter.from_keras_model(model).convert()` → `forest_acoustic_fp32.tflite`
   (13,272 B). Check vs Keras on the first 50 test windows: max abs diff **3.87e-7**, argmax match 100 %.
2. **Full-integer post-training quantisation (PTQ)**:
   - `optimizations = [Optimize.DEFAULT]`
   - `target_spec.supported_ops = [TFLITE_BUILTINS_INT8]`
   - `inference_input_type = int8`, `inference_output_type = int8`
   - **Representative dataset:** 300 samples drawn at random (seed 42) from the normalised **train** cache only
     (never test data).
   - Result: `forest_acoustic_int8.tflite`, **13,072 B**. It is larger than the 5,260 B of raw weights because of
     the flatbuffer structure and quantisation parameters.
   - Weights are quantised **per-channel** (the converter default for conv/dense layers). This matters on the
     device (section 11.5).
3. **Op check**: the op list was read with default delegates disabled. Ops: `CONV_2D`, `DEPTHWISE_CONV_2D`,
   `FULLY_CONNECTED`, `MAX_POOL_2D`, `MEAN`, `SOFTMAX`. 30 tensors. 0 ops outside the TFLite Micro set used for the
   check (`TFLM_SUPPORTED_OPS` in the script).

**Quantised interface (Measured, `ml/reports/QUANTIZATION_REPORT.json`, matches `AcousticTables.h`):**

| | Shape | Type | Scale | Zero point |
|---|---|---|---|---|
| Input | [1, 40, 101, 1] | int8 | 0.014805045910179615 | 11 |
| Output | [1, 3] | int8 | 1/256 = 0.00390625 | -128 |

Encoding: `q = round(x_normalised / 0.014805 + 11)`, clamped to [-128, 127]. Output probability is
`(q + 128) / 256`.

**FP32 vs INT8 on the frozen test set (2,119 windows), Measured:**

| | FP32 Keras | INT8 TFLite |
|---|---|---|
| Accuracy | 0.7069 | 0.7192 |
| Macro-F1 | 0.5611 | 0.5733 |
| Prediction agreement FP32↔INT8 | | 98.21 % |
| Size | 5,260 B weights | 13,072 B file |

INT8 confusion matrix (true rows; background, chainsaw, gunshot): `[[1240,451,90],[39,247,9],[6,0,37]]`. Test
precision for the INT8 model is about 0.35 (chainsaw) and 0.27 (gunshot).

The INT8 model was validated on the desktop `tf.lite.Interpreter` and, separately, on TFLite Micro (section 12).
Notebooks `08_quantization_and_tflite` and `09_tflite_micro_validation` cover this.

Extra artifacts: `labels.txt` (`background`, `chainsaw`, `gunshot`, in class-index order),
`model_metadata.json` (`version: forest-acoustic-v1`, input scale/zero-point, 16 kHz, 1.0 s, n_fft 512, hop 160,
40 mels), `final_metadata.json`, `ml/models/forest_acoustic_fp32/`.

---

## 10. Getting the model into the firmware

All in `node-firmware/`. Nothing is hand-copied: three generators read `ml/` and write C++ headers.

| Tool | Reads | Writes | What it does |
|---|---|---|---|
| `tools/embed_model.py` | `ml/models/final/forest_acoustic_int8.tflite` | `lib/Acoustic/src/AcousticModelData.h` | Emits `alignas(16) inline const unsigned char kModelData[13072]` (in flash, because `const`) and `kModelDataLen`; header records the sha256 |
| `tools/gen_acoustic_tables.py` | `ml/configs/preprocessing.yaml`, `final_metadata.json`, `labels.txt`, librosa/scipy | `lib/Acoustic/src/AcousticTables.h` | Hann window `kHann[512]` (periodic, from `scipy.signal.get_window`), Slaney mel filterbank stored sparsely (`kMelStart[40]`, `kMelLen[40]`, `kMelOffset[41]`, `kMelWeights[490]`), `kNBins=257`, `kNFrames=101`, `kFeatureMean/Std`, input/output scale and zero point, class names. **Asserts** that sample rate, n_fft, hop, n_mels, fmin, fmax and power equal 16000 / 512 / 160 / 40 / 0 / 8000 / 2.0, so drift between `ml/` and firmware fails the build step |
| `tools/gen_acoustic_testvectors.py` | real test windows from `ml/` | `test/data/vectors.bin`, `lib/Acoustic/src/AcousticTestVectors.h` | Known PCM windows with librosa features, INT8 tensors and Python-TFLite outputs, used by the parity tests |

**Verified now:** `shasum -a 256 ml/models/final/forest_acoustic_int8.tflite` =
`c9b3a391dc45b211587a5946ee15e357aef8c9c6baff6021866884b951972b9b`, identical to the hash in the header of
`AcousticModelData.h`, and the scale (0.01480505), zero point (11), mean (-36.3185), std (21.1904) in
`AcousticTables.h` equal the ML metadata.

Because the mel filterbank is a sparse table generated by librosa, there is no runtime mel-matrix maths and no DCT
(the model uses log-mel, not MFCC).

Build config (`node-firmware/platformio.ini`, default env `esp32-s3-devkitm-1`): ESP32-S3, Arduino framework,
16 MB flash, PSRAM enabled, LittleFS, libraries `sandeepmistry/LoRa` and `tanakamasayuki/TensorFlowLite_ESP32`,
C++17, flags `FOREST_ACOUSTIC=1`, `FOREST_ACOUSTIC_TEST_MODE=0`, `ACOUSTIC_RELATIVE_TRIGGER=0`,
`MAX4466_TRIGGER_HIGH=6.0f`, `MAX4466_TRIGGER_LOW=3.0f`, `ACOUSTIC_DEBUG_LOG=1`.

---

## 11. On-device detection pipeline

Code: `node-firmware/lib/Acoustic/src/` (`AcousticConfig.h`, `AcousticTrigger.*`, `AudioCapture.*`,
`AudioPreprocessor.*`, `AcousticClassifier.*`, `AcousticKernels.*`, `AcousticPipeline.*`) and
`node-firmware/lib/ForestSensors/src/` (`MAX4466.*`, `INMP441.*`). Everything is a compile-time `-D` flag.

### 11.1 Two microphones, one classifier

The classifier is **never run continuously**. A cheap analog microphone acts as a trigger and only then is the
digital microphone's audio classified.

| Part | Role | Pins / rate |
|---|---|---|
| **MAX4466** (analog) | always-on energy detector | GPIO 1 (ADC1_CH0), 12-bit, DMA, 8 kHz, blocks of 128 samples (16 ms) |
| **INMP441** (I2S MEMS) | audio the model sees | I2S0 RX, BCLK GPIO 6, WS GPIO 7, SD GPIO 8, 16 kHz, 32-bit slot, left channel, 6 × 256-sample DMA buffers, sample `>> 16` to PCM16 |

### 11.2 Trigger (MAX4466)

Per 128-sample block the detector removes the DC mean and computes RMS (`EnergyDetector`, `AcousticTrigger.cpp`).
The **build as configured uses fixed thresholds** (`ACOUSTIC_RELATIVE_TRIGGER=0`): trigger when block RMS >= **6**,
release when RMS < **3** (hysteresis), then a 5 s cooldown. These are experimental bench numbers and are **not
calibrated** (Unverified).

Two other modes are implemented and unit-tested but disabled: a relative-dB trigger (median noise floor over a
4 s warm-up; +10 dB single block or +6 dB for 4 consecutive blocks, with a sensor-fault guard), and an adaptive
floor trigger. The MAX4466 currently has a known wiring/power problem on the bench (`docs/ACOUSTIC_NODE.md`,
"Bench findings").

### 11.3 Capture

INMP441 samples are written continuously into a **2 s ring buffer** (32,000 samples, PSRAM). On a trigger the
pipeline waits for 750 ms of new audio and then copies **250 ms before + 750 ms after** the trigger point,
giving the 16,000-sample (1.000 s) window the model was trained on. If the ring was overrun during the copy, the
window is discarded.

### 11.4 Feature extraction on the device (`AudioPreprocessor.cpp`)

Float32 C++ that reproduces `librosa` exactly (`node-firmware/test/acoustic_parity_test.cpp`):

1. Peak-normalise the 1 s window to -3 dBFS (`ACOUSTIC_PEAK_TARGET = 0.70794578`). *(Deviation from training, see 16.)*
2. Optional 80 Hz biquad high-pass (**off**, `ACOUSTIC_FILTER_ENABLED=0`, because the model was trained without it).
3. 512-point radix-2 FFT with the periodic Hann window; frame `t` starts at `t*160 - 256`, zero padded
   (librosa `center=True`) → 101 frames.
4. Power spectrum → sparse Slaney mel bank → 40 mel bands (0-8 kHz).
5. `power_to_db` with `ref = max of this clip`, `amin = 1e-10`, `top_db = 80`.
6. `(dB - (-36.3185)) / 21.1904`.
7. Quantise: `round(x / 0.014805 + 11)`, clamp to int8. Tensor layout is `[mel][frame]` = 40 × 101 = 4,040 bytes.

**Measured on the ESP32-S3:** feature extraction about **70 ms** per window (`docs/ACOUSTIC_NODE.md`).

### 11.5 TFLite Micro inference (`AcousticClassifier.cpp`, `AcousticKernels.cpp`)

- Interpreter with `MicroMutableOpResolver<6>`: Conv2D, DepthwiseConv2D, FullyConnected (**custom**), MaxPool2D,
  Mean, Softmax.
- Tensor arena: 65,536 B allocated (internal RAM first, PSRAM fallback); **26,804 B used** (measured on the device
  before the custom kernel was added).
- `begin()` refuses to run unless the loaded model's input/output shape, type, scale and zero point match the
  constants from `AcousticTables.h`, so a wrong model file cannot run silently.
- **Custom `FULLY_CONNECTED` kernel.** The stock kernel in `TensorFlowLite_ESP32` uses only the first channel's
  weight scale for every output, but this model has per-channel quantised dense layers. Measured on 343 real test
  windows against Python TFLite:

  | | exact match | worst error | class agrees with Python |
  |---|---|---|---|
  | stock TFLite Micro | 1.2 % | 61/256 | 93.6 % |
  | `AcousticKernels.cpp` (per-channel) | 63.6 % | 8/256 | **99.7 %** |

  The model is unchanged; the firmware registers its own kernel. Reproduce with `tools/tflm_host_parity/run.sh`
  (see 16, this script is stale). On the board (test mode 3, 3 known windows) the max output difference was 3/256.
- **Measured** `Invoke()` latency about **268 ms** (with the stock reference kernels, not re-measured with the
  custom kernel).
- Output: `(q + 128) / 256` per class; **class = argmax**, **confidence = probability of that class**.

### 11.6 Decision and tasks (`AcousticPipeline.cpp`)

State machine: `MONITORING → TRIGGERED → CAPTURE → INFERENCE → RESULT → COOLDOWN → MONITORING`.

- Tasks are pinned to **core 0** (`ac-capture` prio 3, `ac-trigger` prio 2, `ac-infer` prio 1, 16 KB stack), so RFID and LoRa
  in `loop()` on core 1 are never blocked by DSP or inference.
- **One inference per trigger.** There is no smoothing, no multi-window voting and no second opinion.
- If class is chainsaw (1) or gunshot (2) and confidence >= `ACOUSTIC_MIN_CONFIDENCE`, an `AcousticEvent`
  (class, confidence, trigger RMS) is pushed to a 4-slot queue. `background` produces no event.
- `ACOUSTIC_MIN_CONFIDENCE` defaults to **0.0**, so any chainsaw/gunshot argmax becomes an event.
- Only `loop()` touches SPI/LoRa (the RC522 and SX1278 share one SPI bus).

Test modes (`FOREST_ACOUSTIC_TEST_MODE`): 0 field pipeline (default build), 1 MAX4466 RMS monitor, 2 INMP441
statistics, 3 known-tensor TFLM self-test with no microphones, 4 continuous bench demo (classifies the newest 1 s
every 2 s and only sends over LoRa with `ACOUSTIC_DEMO_SEND_EVENTS=1`).

---

## 12. From classification to the gateway

1. **Payload** (`sendAcousticEvent`, `src/main.cpp` ~287-310): 6 bytes `'A'` (0x41), version 0x01,
   class (1 chainsaw / 2 gunshot), confidence `u8 = p*255 + 0.5`, trigger RMS `u16` little-endian. No raw audio
   leaves the node, and the payload carries no timestamp or model version.
2. **Local store first** (`lib/ForestStorage`): a 48-byte `EventRecord` (magic 0xE7, type 2 = acoustic, status
   PENDING_SYNC, local id, boot count, uptime ms, payload, CRC16-CCITT) is appended to LittleFS `/events.log`
   (max 512 records, torn-tail recovery, compaction of SYNCED records). Event ids look like `N01-ACOUSTIC-000007`.
   Time is uptime + boot count only; the node has no wall clock (the DS3231 is not used for event timestamps).
3. **Packet** (`lib/Protocol`, `lib/PacketFactory`): protocol v4 DATA packet, `0xA5`, version 4, type, source =
   node id, destination = gateway `0xFE`, sequence u16, payload length, payload, CRC16.
4. **Radio** (`Config.h`): SX1278 LoRa 433 MHz, SF7, BW 125 kHz, CR 4/5, sync word 0x12, CRC on.
5. **ACK**: node waits **1,500 ms** for an Acknowledgement whose payload equals the sent sequence number. On ACK
   the record becomes SYNCED; otherwise it stays PENDING and `retryPendingEvent()` retries the oldest every 15 s
   (no retry cap; each attempt blocks `loop()` about 1.5 s).
6. **Gateway** (`gateway/src/Gateway/GatewayService.cpp:115`): payload starting `0x41` is parsed as an acoustic
   event, ACKed, and published to MQTT `forest/events/acoustic` (JSON with node_id, sequence, classification,
   confidence, model_version, trigger_rms).
7. **Backend**: `POST /api/ingest/gateway/acoustic-node-event`. Events are **unsigned**, stored with
   `signature_status = chain_status = PENDING`, and enter the human review queue (`PENDING_REVIEW`).
   See `docs/ACOUSTIC_NODE.md`, `docs/GATEWAY_BACKEND_CONTRACT.md`, `docs/MQTT.md`.

---

## 13. One sound, start to finish

Example: a gunshot near the node.

1. Sound pressure reaches the MAX4466 (GPIO 1) and the INMP441 (I2S) at the same time.
2. `ac-capture` reads 128-sample I2S chunks continuously, shifts `>> 16` to PCM16, writes them into the 2 s ring.
3. `ac-trigger` reads 8 kHz ADC blocks, removes DC, computes RMS; the gunshot gives a block RMS >= 6 while in
   MONITORING → rising edge → records the ring position, wakes `ac-infer`.
4. `ac-infer` waits until 750 ms of audio after the trigger exists, then copies 250 ms before + 750 ms after = 16,000
   samples.
5. `AudioPreprocessor` peak-normalises, runs the 512-point STFT (hop 160), 40 mel bands, dB, z-score and int8
   quantisation into a 4,040-byte tensor (~70 ms).
6. `AcousticClassifier::invoke` runs the 13 KB INT8 model in TFLite Micro with the per-channel FC kernel (~268 ms) and
   dequantises three probabilities, for example `[0.03, 0.05, 0.92]`.
7. argmax = 2 (gunshot), confidence 0.92 >= 0.0 → event queued. (A "background" result stops here, no event.)
8. `loop()` on core 1 pops the event, builds the 6-byte `'A'` payload, appends a PENDING_SYNC record to flash, and
   shows an amber LED.
9. The DATA packet goes out over LoRa (433 MHz, SF7).
10. The gateway ACKs; the node marks the record SYNCED. No ACK within 1.5 s → stays PENDING and is retried every 15 s.
11. Gateway publishes MQTT → backend creates an unsigned `PENDING_REVIEW` event → a human reviews it on the dashboard.
12. Cooldown of 5 s, then back to MONITORING.

---

## 14. Tests and validation status

### 14.1 What each test verifies

| Test | File | Verifies |
|---|---|---|
| Audio filter | `ml/tests/test_audio_filter.py` | 7 tests: identity when off, no NaN, DC removed, matches manual biquad, streaming == whole, feature shapes, INT8 inference runs |
| Acoustic parity (host) | `node-firmware/test/acoustic_parity_test.cpp`, `run_acoustic_parity_test.sh` | device dB features vs librosa max diff <= 0.05 dB; INT8 tensor vs `ml/` no element off by more than 1 LSB and at most 4 elements differ; peak-normalised path at most 8 differ; high-pass vs scipy <= 1e-4 |
| Trigger and ring (host) | `node-firmware/test/acoustic_trigger_test.cpp`, `run_acoustic_tests.sh` | DC independence, hysteresis, adaptive floor, relative-dB mode, sensor fault, ring wrap and overrun |
| Local store (host) | `node-firmware/test/local_event_store_test.cpp`, `run_local_store_tests.sh` | record round trip, CRC, torn-tail recovery, overflow, counters |
| TFLM vs Python (host) | `node-firmware/tools/tflm_host_parity/` | stock vs per-channel kernel vs Python TFLite on 150 windows per class |
| On-board self-test | `FOREST_ACOUSTIC_TEST_MODE=3` | 3 known INT8 tensors through TFLM plus preprocessing of a real gunshot window (4040/4040 identical) |

### 14.2 What is and is not verified

| Item | Status |
|---|---|
| Model files, embedded array and tables match `ml/` | **Verified** (hash and constants, this document) |
| Device preprocessing equals librosa on real windows | **Verified** (host tests; on board for one gunshot window) |
| TFLM loads the model, output matches Python (max diff 3/256 on 3 windows) | **Verified on board** |
| One trigger→capture→inference→cooldown cycle | **Verified as a state machine only** (fired on noise, result background 0.47) |
| INMP441 I2S capture | **Partial**: varying non-clipping samples; sample rate and shift not validated |
| MAX4466 trigger and thresholds | **Not verified**: hardware fault; thresholds uncalibrated |
| Classification accuracy on real INMP441 / forest audio | **Unverified**: the model has never heard such audio |
| Acoustic event over real LoRa → gateway → backend | **Not verified end to end** |

---

## 15. Reproduce

```bash
# ML (from ml/)
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
python scripts/download_c3gd.py; python scripts/download_frugalai.py
python scripts/download_esc50_hf.py; python scripts/download_sensing_forest.py
#   FSC22 and Rodopi must be placed manually in datasets/raw/
python scripts/audit_dataset.py
python preprocessing/audio_preprocess.py         # → datasets/processed + manifests/master_manifest.csv
python preprocessing/create_splits.py            # → datasets/v1/*.csv
python scripts/validate_leakage.py
python models/prepare_features.py                # → datasets/features_cache/*.npz (class-capped)
python models/baseline/train_baseline.py
python models/train_cnn.py --variant final       # → models/final/final.keras + final_metadata.json
python models/convert_tflite.py                  # → fp32 + int8 .tflite, labels, metadata, QUANTIZATION_REPORT.json
python models/robustness_eval.py
pytest tests

# Firmware (from node-firmware/)
python tools/embed_model.py                      # → lib/Acoustic/src/AcousticModelData.h
python tools/gen_acoustic_tables.py              # → AcousticTables.h (asserts ml/ config matches)
python tools/gen_acoustic_testvectors.py         # → test/data/vectors.bin
bash test/run_acoustic_tests.sh; bash test/run_acoustic_parity_test.sh; bash test/run_local_store_tests.sh
pio run -e esp32-s3-devkitm-1 -t upload          # default env already includes the acoustic pipeline
```

Model-selection scripts use `--seed`, `--cache-dir` and `--out-dir` (see `train_cnn.py`) for A/B runs.

---

## 16. Discrepancies and risks found while checking

**Numbers and labels**

1. **Train/val sizes in reports vs what was trained.** `DATASET_V1_REPORT.md` / `FINAL_MODEL_REPORT.md` quote train
   28,741 and validation 6,999. The model trains on the capped caches: **8,397** train, **2,498** validation, and the
   "external test" metrics are on **3,616** of 21,059 segments (section 5).
2. **Stale class mapping.** `ml/configs/preprocessing.yaml` `class_mapping` says gunshot 0, chainsaw 1, background 2.
   The trained model and firmware use `ml/models/final/labels.txt`: **background 0, chainsaw 1, gunshot 2**. Do not
   use the YAML mapping.
3. **Robustness "clean" accuracy** is 0.7216 in `ROBUSTNESS_REPORT.md` but INT8 test accuracy is 0.7192 in the
   quantisation report; the runs differ slightly and the reports do not explain it.
4. **Retraining variance:** the A seed-42 re-run reached test macro-F1 0.455, not the shipped 0.561 (8.5).
5. **C3GD source URL** differs between `download_c3gd.py` (Zenodo record 22286299) and the DOIs in the docs
   (20274399 / 20274400).

**Stale documents**

6. `ml/README.md` and `ml/reports/FINAL_MODEL_REPORT.md` state that firmware integration, I2S capture and on-device
   inference are "blocked/not attempted". They exist now and were run on a board (`docs/ACOUSTIC_NODE.md`).
   `ml/README.md` also still shows a "download failed" workflow block.
7. `docs/ACOUSTIC_NODE.md` says the default env is `esp32-s3-acoustic` in test mode 4 with relative-dB trigger.
   `node-firmware/platformio.ini` has no such env: the default env is `esp32-s3-devkitm-1` with test mode 0, fixed
   thresholds 6/3. `node-firmware/tools/tflm_host_parity/run.sh` still points at `esp32-s3-acoustic`, and
   `AcousticKernels.h` cites a non-existent `tools/verify_tflm_parity.py`.
8. `docs/ACOUSTIC_NODE.md` claims 5e-5 dB and identical INT8 tensors; the parity test only enforces 0.05 dB and
   at most 4 differing elements (it may still pass with tighter real results).
9. `node-firmware/README.md`, `ARCHITECTURE.md`, `test/protocol_v4_test.cpp` and `test/test_command_parser.cpp`
   describe a removed architecture (heartbeat, neighbour, boat protocol) and do not build against the current tree.

**Training vs deployment mismatches**

10. **Normalisation scope.** Training peak-normalises each *recording* to -3 dBFS; the device normalises each
    *1 s window*. Because the dB step uses `ref = max of the clip` this is nearly gain-invariant (0 of 443 test windows
    changed prediction, `gen_acoustic_testvectors.py --sensitivity`), but a quiet noise-only window is amplified to
    -3 dBFS and may look like an event. Not measured on real microphone audio.
11. **Domain gap:** no INMP441 or field data in training (section 8.4). Expect performance below the numbers in
    section 8.

**Behavioural risks in the current firmware**

12. Test precision is only 0.35 (chainsaw) / 0.25-0.27 (gunshot) and the external set shows 64 % of background
    called an event class. With `ACOUSTIC_MIN_CONFIDENCE = 0`, no smoothing and an uncalibrated trigger, **expect many
    false alarms**. Options: raise the confidence gate, require two consecutive windows, calibrate the trigger, and
    collect INMP441 field data for retraining.
13. `retryPendingEvent` has no attempt limit, and each retry blocks `loop()` (and the RFID reader) for about 1.5 s.
14. The event payload has no timestamp or model version; time is uptime + boot count only.
15. Licence exposure: CC BY-NC (ESC-50, FrugalAI) and unverified FSC22 / Rodopi data are in the training set.
