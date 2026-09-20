# Final Model Report — Forest Acoustic Event Classification (v1)

All numbers in this report come from real executed scripts/notebooks in this repository
(`models/baseline/train_baseline.py`, `models/train_cnn.py`, `models/convert_tflite.py`,
`models/robustness_eval.py`, and notebooks 01–10). None are estimated or fabricated.

## 1. Dataset (v1)

See `reports/DATASET_V1_REPORT.md` for full detail. Summary:

- 58,918 segments (1.0s, 16kHz mono) from 1,975 source recordings across 6 real datasets
  (`c3gd`, `fsc22`, `rodopi`, `esc50_hf`, `rfcx_frugalai`, `sensing_forest`), 16.37 hours total.
- Classes: background (55,069 segments), chainsaw (3,407), gunshot (442) — real-world imbalance,
  corrected for via class-weighted training, not data discarding.
- Grouped 70/15/15 split by `original_recording_id` (train 28,741 / val 6,999 / test 2,119
  segments), plus a fully held-out `external_test` (21,059 segments, 77 recordings from
  `sensing_forest` + a held-out `c3gd` event + 2 held-out `rodopi` recordings).
- Quality gates passed: `scripts/audit_dataset.py` (0 corrupted/zero-length files) and
  `scripts/validate_leakage.py` (0 leaked recordings across any split pair).

## 2. Model architectures & comparison

| Model | Features | Params | FP32 weights | Val macro-F1 | Test macro-F1 | External-test macro-F1 |
|---|---|---|---|---|---|---|
| Baseline (MFCC stats + LogisticRegression) | 26-dim MFCC mean+std | n/a (sklearn) | n/a | 0.4251 | 0.3595 | 0.5899 |
| Compact CNN (Conv-BN-ReLU-Pool x2) | Mel-spectrogram (40×101) | 6,147 | 24.0 KB | 0.5358 | 0.3285 | 0.2207 |
| **Final (depthwise-separable, selected)** | Mel-spectrogram (40×101) | **1,315** | **5.1 KB** | **0.6542** | **0.5611** | **0.5793** |

**Model selection was made on validation macro-F1 only** (test/external-test evaluated once, after
selection). The final depthwise-separable model won on validation macro-F1 despite having ~5x
fewer parameters than the compact CNN — likely because its smaller capacity combined with
class-weighted training and augmentation generalized better on this small, imbalanced dataset,
whereas the larger compact CNN overfit toward validation-specific train sources (its external-test
macro-F1 of 0.22 vs the final model's 0.58 supports this).

### Final model per-class results (test_v1, frozen, evaluated once)

| Class | F1 | Recall |
|---|---|---|
| background | 0.798 | 0.679 |
| chainsaw | 0.494 | 0.851 |
| gunshot | 0.392 | 0.860 |

Both target event classes (chainsaw, gunshot) have high recall (>0.85) at the cost of background
precision — a reasonable operating point for an alerting system where missing a real event is worse
than a false alarm, though the background false-alarm rate (~32% at test time, see below) would
need further tuning before field deployment.

### Training configuration (reproducible)

- Seed: 42 (numpy + TensorFlow)
- Optimizer: Adam, LR 1e-3, batch size 32
- Epochs requested: 15, early stopping on val_loss (patience 4, restore best weights)
- Class weights: computed via `sklearn.utils.class_weight.compute_class_weight('balanced', ...)`
- Training-only augmentation (`models/augment.py`, per `configs/augmentation.yaml`): random gain
  (±6dB), time shift (roll), background-noise mel-mixing, SpecAugment time/frequency masking —
  applied only to the training split, never validation/test/external.

## 3. FP32 → TFLite → INT8 (edge table)

| Metric | FP32 (Keras) | FP32 (.tflite) | INT8 (.tflite) |
|---|---|---|---|
| Test accuracy | 0.7069 | (verified ≈FP32, argmax match 100% on sample) | 0.7192 |
| Test macro-F1 | 0.5611 | — | 0.5733 |
| Model size | 5,260 bytes | 13,272 bytes | 13,072 bytes |
| Flash usage | N/A — hardware unavailable in this environment | | |
| RAM / tensor arena | N/A — hardware unavailable in this environment | | |
| Inference latency | N/A — hardware unavailable in this environment | | |

- Keras FP32 vs INT8-TFLite prediction agreement (test set): **98.21%**
- Representative dataset for INT8 calibration: 300 samples from `train_v1` only (never test data)
- All operators in the final `.tflite` (`CONV_2D`, `DEPTHWISE_CONV_2D`, `FULLY_CONNECTED`,
  `MAX_POOL_2D`, `MEAN`, `SOFTMAX`) are in the TFLite Micro commonly-supported op set — **0
  unsupported ops**, no architecture changes were needed.
- Final INT8 model size (13.1 KB) is far under the ~200KB target for ESP32-S3 flash budget.

Full detail: `reports/QUANTIZATION_REPORT.md`.

## 4. Robustness (synthetic noise, final INT8 model, test_v1)

| Condition | SNR | Accuracy | Macro-F1 |
|---|---|---|---|
| clean | N/A | 0.7216 | 0.5760 |
| moderate | 15 dB | 0.5295 | 0.3793 |
| strong | 5 dB | 0.0203 | 0.0133 |

The model degrades sharply under strong synthetic noise, as expected for a 1,315-parameter model
with no explicit noise-robust design beyond training-time augmentation. This is an honest limitation
to flag for future work (e.g. more aggressive noise augmentation, or a slightly larger model).
Full detail: `reports/ROBUSTNESS_REPORT.md`.

## 5. External test set (fully held-out sources)

Accuracy 0.4372, macro-F1 0.5793 (higher macro-F1 than accuracy reflects strong per-class balance
despite the external set being background-heavy). Gunshot F1 was notably high (0.91) on external
data — the held-out `c3gd` event provides genuinely new platform/mic/cartridge combinations, and
the model generalized well to them.

## 6. Failure analysis

See `reports/FAILURE_ANALYSIS.md` for concrete misclassified `sample_id`s with dataset/path and a
likely-cause note (mainly: background samples with transient/percussive content confused for
chainsaw/gunshot, and low-energy event windows misclassified as background).

## 7. Notebooks

`notebooks/01_dataset_exploration.ipynb` through `10_audio_file_demo.ipynb` were all executed
end-to-end via `jupyter nbconvert --execute` with real, baked-in outputs (no placeholders). Figures
saved to `reports/figures/`.

## 8. NOT COMPLETED — HARDWARE DEPLOYMENT BLOCKED

The following were **not attempted** because no physical ESP32-S3 / INMP441 hardware is available
in this environment:

- ESP32-S3 firmware integration of the TFLite Micro runtime
- INMP441 I2S audio capture and embedded feature extraction (on-device Mel-spectrogram computation)
- Real-time on-device inference loop
- On-device vs Python prediction-consistency test (only desktop `tf.lite.Interpreter` validation
  was performed, as a stand-in — see notebook 09 and `QUANTIZATION_REPORT.md`)
- Edge resource measurement: flash usage, RAM/tensor arena sizing, inference latency, power draw
- Real audio hardware testing (playback of background/chainsaw/gunshot audio captured live through
  an INMP441 microphone)
- Acoustic event → LoRa → Gateway → MQTT → Backend → Dashboard end-to-end wiring and integration test

These require physical hardware not present in this environment and remain for a follow-up phase.
