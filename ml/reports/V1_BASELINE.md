# SECURE FOREST PATROL — v1 Baseline Freeze and Audit

Audit date: 2026-10-18  
Scope: Phase 0 only. No retraining, architecture changes, label changes, split changes, threshold tuning, alert-logic changes, or firmware changes were performed.

## Result

The selected v1 artifacts are present, load successfully, and their reported desktop metrics were reproduced. The frozen dataset manifests pass recording-level leakage validation. The INT8 model is TFLite Micro operator-compatible according to the repository's static operator check. Physical ESP32-S3/TFLite Micro validation remains incomplete.

Authoritative freeze data is in [V1_BASELINE_MANIFEST.json](./V1_BASELINE_MANIFEST.json).

## Repository and authoritative artifacts

The repository was on `main`. Existing unrelated user changes were present in firmware, gateway, and documentation files; they were not touched. Running the requested raw-data audit regenerated `reports/dataset_quality_report.md`, which is an audit output and is now marked modified by Git.

Authoritative v1 artifacts are:

- Dataset: `datasets/v1/*.csv` and matching `datasets/features_cache/*.npz`.
- Selected model: `models/final/final.keras`.
- Desktop FP32 graph: `models/final/forest_acoustic_fp32.tflite`.
- Selected INT8 graph: `models/final/forest_acoustic_int8.tflite`.
- Model metadata: `models/final/final_metadata.json`, `model_metadata.json`, and `labels.txt`.
- Reproduction implementations: `models/train_cnn.py`, `models/convert_tflite.py`, and `models/robustness_eval.py`.

Historical reports are evidence of previous runs but are not substitutes for the hashes and fresh results in the manifest.

## Dataset and split integrity

The live manifests contain 58,918 segments from 1,975 source recordings:

| Split | Segments | Recordings | Background | Chainsaw | Gunshot |
|---|---:|---:|---:|---:|---:|
| Train | 28,741 | 1,328 | 26,344 | 2,093 | 304 |
| Validation | 6,999 | 284 | 6,501 | 444 | 54 |
| Test | 2,119 | 286 | 1,781 | 295 | 43 |
| External test | 21,059 | 77 | 20,443 | 575 | 41 |

The master counts are background 55,069, chainsaw 3,407, and gunshot 442. Direct pairwise checks found zero overlapping `original_recording_id` values across all six split pairs. `validate_leakage.py` also exited successfully.

The implementation creates 1-second, 16 kHz segments in `audio_preprocess.py`; `create_splits.py` then assigns the already-created segments by `original_recording_id`. The external set is carved out by source before the grouped 70/15/15 split. Training augmentation is applied only by the training sequence in `train_cnn.py`; validation, test, and external-test caches are not augmented.

The raw audit completed against 15,103 files: 0 corrupted, 0 zero-length, 682 non-standard sample rates, 1 non-standard channel count, 8,169 extreme-clipping flags, and 3 exact duplicates. Resampling and peak normalization are part of the preprocessing design; the audit findings should not be read as proof of hardware-domain equivalence.

## Model artifact verification

The selected model is a 1,315-parameter depthwise-separable CNN with input `[1, 40, 101, 1]`. The INT8 graph is 13,072 bytes; the FP32 TFLite graph is 13,272 bytes; the Keras container is 111,772 bytes and contains 5,260 bytes of model weights.

The INT8 input is `int8`, scale `0.014805045910179615`, zero-point `11`; output is `int8`, scale `0.00390625`, zero-point `-128`. The actual flatbuffer operators are `CONV_2D`, `DEPTHWISE_CONV_2D`, `FULLY_CONNECTED`, `MAX_POOL_2D`, `MEAN`, and `SOFTMAX`; the repository check found zero unsupported operators. The Keras and both TFLite artifacts loaded successfully in the current desktop environment.

## Reproduced metrics

### FP32 Keras and FP32 TFLite

FP32 Keras and FP32 TFLite predictions matched on validation, test, and external-test evaluation in this audit. Test results:

| Metric | Test | External test |
|---|---:|---:|
| Accuracy | 0.7069 | 0.4372 |
| Balanced accuracy | 0.7969 | 0.7153 |
| Macro-F1 | 0.5611 | 0.5793 |

FP32 test confusion matrix, rows true and columns predicted in `[background, chainsaw, gunshot]` order:

```text
[[1210, 471, 100],
 [  35, 251,   9],
 [   6,   0,  37]]
```

Test per-class recall was background 0.6794, chainsaw 0.8508, and gunshot 0.8605. Test per-class F1 was background 0.7982, chainsaw 0.4936, and gunshot 0.3915.

### INT8 TFLite

With the quantization evaluator's interpreter configured without default delegates, the reproduced test result is accuracy 0.7192, balanced accuracy 0.7980, and macro-F1 0.5733. The Keras-to-INT8 test prediction agreement is 98.21%. External-test INT8 results under the same no-default-delegate path are accuracy 0.4452, balanced accuracy 0.7152, and macro-F1 0.5938.

INT8 test confusion matrix under that path:

```text
[[1240, 451,  90],
 [  39, 247,   9],
 [   6,   0,  37]]
```

### Existing robustness procedure

The existing robustness evaluator uses the default desktop TFLite interpreter and adds Gaussian noise to cached Mel features. Fresh reproduction matched the existing report exactly:

| Condition | Accuracy | Macro-F1 | Background false-alarm rate |
|---|---:|---:|---:|
| Clean | 0.7216 | 0.5760 | 0.3010 |
| 15 dB | 0.5295 | 0.3793 | 0.4526 |
| 5 dB | 0.0203 | 0.0133 | 1.0000 |

## Metric reconciliation

The reports contain several valid numbers from different evaluation paths:

1. `FINAL_MODEL_REPORT.md` and `QUANTIZATION_REPORT.md` report FP32 Keras test metrics of 0.7069 accuracy and 0.5611 macro-F1.
2. The same quantization report reports INT8 TFLite metrics of 0.7192 accuracy and 0.5733 macro-F1 using `BUILTIN_WITHOUT_DEFAULT_DELEGATES`.
3. `ROBUSTNESS_REPORT.md` reports the clean INT8 value 0.7216/0.5760 using the default desktop interpreter. Re-running that exact procedure reproduced it.
4. The two INT8 desktop paths produce a small difference in five background-window predictions. This is attributable to the different interpreter/delegate execution paths; it is not a split or label difference. The artifact and cache hashes remained fixed.
5. The external-test 0.5793 macro-F1 in `FINAL_MODEL_REPORT.md` is the FP32 Keras value. Fresh no-default-delegate INT8 evaluation is 0.5938 macro-F1; this value was not present in the historical report.

No metric was altered to force agreement. The discrepancy should be resolved for future release reporting by selecting and documenting one canonical runtime path, followed by on-device comparison.

## False-alarm metric definition

In `models/robustness_eval.py`, the metric is calculated from the window-level confusion matrix as:

```text
(CM[background, chainsaw] + CM[background, gunshot]) /
(CM[background, background] + CM[background, chainsaw] + CM[background, gunshot])
```

Therefore 0.3010 means 536 of 1,781 true-background test windows were classified as a target event under the clean/default-interpreter run. It is not false alerts per recording, false alerts per hour, or the fraction of recordings containing at least one false detection. Operational alert-rate metrics have not been established.

## Commands executed

```bash
python3 ml/scripts/validate_leakage.py
python3 ml/scripts/audit_dataset.py
cd ml && pytest -q
```

The model and metric checks were performed with non-mutating desktop evaluation of the existing Keras and TFLite files. The repository's conversion and robustness implementations were inspected; conversion was not rerun because `convert_tflite.py` writes model artifacts. The robustness calculation was reproduced in memory so the existing report and model files were not overwritten.

Environment used: Python 3.10.13, TensorFlow 2.21.0, NumPy 2.2.6, pandas 2.3.3, scikit-learn 1.5.2, librosa 0.11.0, PyYAML 6.0.1, pytest 9.1.1, joblib 1.4.2.

## Unresolved blockers and limitations

- No physical ESP32-S3, INMP441, or TFLite Micro runtime was available; desktop TFLite execution is not hardware validation.
- The exact embedded tensor-arena size, latency, power, I2S capture behavior, and Python-to-device feature equivalence remain unverified.
- Raw-data audit flags require interpretation in the deployed audio domain; especially clipping and channel/sample-rate behavior.
- The INT8 metric depends slightly on desktop interpreter/delegate path; a canonical runtime and hardware comparison are still required.
- The current false-alarm metric is window-level only; alert-level rates per recording/hour are unknown.
- The reported robustness test is feature-space Gaussian noise, not a raw-audio adversarial or replay-attack evaluation.

No Phase 1 work was performed.
