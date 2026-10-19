# Phase 2 — Preprocessing and Quantization Consistency Audit

Status: **COMPLETE — diagnostic/reference audit only**  
Audit date: 2026-10-18

No model, dataset, split, label, threshold, alert logic, firmware, or frozen evaluation artifact was changed. Phase 3 has not started.

## Executive result

The frozen desktop path is internally reproducible. Re-reading the existing processed WAV files and recomputing the mel features reproduced the frozen test cache exactly for the selected golden references. Five repeated feature/model evaluations per golden sample produced zero feature, quantized-input, output, or class disagreements.

The most important deployment risk is not the INT8 flatbuffer itself; it is reproducing the desktop feature contract on ESP32. The contract depends on librosa-compatible centered STFT padding, Hann windowing, Slaney-normalized mel filters, dB conversion referenced to each window maximum, and the frozen global mean/std. These details must be implemented and validated on paired ESP32 recordings before claiming hardware parity.

## Frozen pipeline traced from source

### Audio and segmentation

- Input is decoded with `soundfile` as float32. Multichannel audio is averaged across channels to mono.
- Non-16-kHz audio is resampled to 16 kHz using `librosa.resample(..., res_type="kaiser_best")`.
- The configured digital high-pass filter is disabled for v1, so no filter is part of the frozen path.
- Continuous audio is peak-normalized before segmentation to `10^(-3/20) = 0.707945784` peak. This is per input recording/interval, not per 1-second model window.
- Window length is 16,000 samples; hop is 8,000 samples. Windows are mono, 1.0 s, with 50% overlap.
- If an input is shorter than one window, the configured strategy is repeat-to-length. Empty input produces no segment. For longer inputs, regular starts are used and a final `len(audio)-16000` start is added only when the uncovered tail is greater than 8,000 samples.
- Segments are written as PCM16 WAV and later decoded as float32 for feature extraction. This PCM16 round trip is part of the frozen cache path.
- Dataset-generation quality checks reject empty, clipping (`abs(audio) > 0.95`), or predominantly silent segments; the frozen-id reproduction path bypasses those checks for already-selected IDs.
- There is no explicit NaN/Inf sanitization in the current preprocessing implementation. ESP32 input must reject or sanitize non-finite values before FFT.

The frozen test files audited here are all readable 16-kHz mono 1-second files. They do not provide a valid short-input/padding example, so padding parity remains an untested reference gap. A segment with `segment_index=8` is an end-position example, not proof that padding was exercised.

### Feature extraction

The exact model feature is:

```text
mel_power = librosa.feature.melspectrogram(
    y=audio, sr=16000, n_fft=512, hop_length=160, n_mels=40,
    fmin=0, fmax=8000, power=2.0)
mel_db = librosa.power_to_db(mel_power, ref=np.max)
```

With the installed librosa 0.11.0 defaults this means a Hann window, `win_length=512`, centered frames, constant padding, HTK=False, and Slaney mel normalization. The output is `(40, 101)` float32-compatible data; the model input adds a final channel axis to make `(40, 101, 1)`.

The dB conversion uses the maximum of the current mel array as its reference and librosa's `amin=1e-10`, `top_db=80` defaults. Therefore this is not a fixed-reference log-power transform and must not be replaced by a per-device RMS/peak normalization after feature extraction.

### Feature normalization

The frozen training metadata supplies one global scalar mean and standard deviation:

```text
mean = -36.31850051879883
std  =  21.19044303894043
x    = (mel_db - mean) / std
```

No per-bin or per-window z-score normalization is used at inference. The normalized tensor is float32 before INT8 quantization.

## INT8 flatbuffer verification

Verified from `forest_acoustic_int8.tflite` with the desktop interpreter:

| Item | Frozen value |
|---|---|
| Input | `int8`, `[1, 40, 101, 1]` |
| Input quantization | `q = round(x / 0.014805045910179615 + 11)` |
| Input safety range | `[-128, 127]`; frozen test rounding produced no out-of-range values |
| Output | `int8`, `[1, 3]` |
| Output quantization | `real = (q - (-128)) * 0.00390625` |
| Class decision | `argmax` on raw output int8; ties select the first class index |
| Operators | `CONV_2D`, `DEPTHWISE_CONV_2D`, `FULLY_CONNECTED`, `MAX_POOL_2D`, `MEAN`, `SOFTMAX` |
| Quantized tensors inspected | 25 |
| Activation quantization | Per-tensor in inspected activation tensors |
| Weight/bias quantization | Per-channel scales are present for convolution/dense weights and bias tensors |
| Unsupported operators | None against the repository's manual TFLM compatibility set |

The repository evaluator does not explicitly clip before casting to int8. The frozen test values rounded into range, but the ESP32 implementation should saturate to `[-128,127]` after rounding to protect against future numeric drift. This is a deployment safety requirement, not a claim that the historical evaluator performed clipping.

## Runtime comparisons

- Recomputed golden mel features versus the frozen cache: maximum absolute difference `0.0` for all 10 selected references.
- FP32 Keras versus FP32 TFLite on the first 50 test samples: maximum absolute output difference `3.8743e-7`; argmax agreement `100%`.
- FP32 Keras versus delegate-free INT8 class agreement on the full test set: `98.2067%`.
- Default desktop TFLite INT8 versus delegate-free INT8: 9/2,119 class disagreements. Six occurred on rows where the default output contained an exact int8 tie. The default confusion matrix is the canonical Phase 0 matrix; delegate-free execution changes only the small runtime comparison shown in diagnostics.
- Default INT8 output ties occurred in 55/2,119 rows. This makes the first-index tie rule operationally relevant.

These comparisons show that FP32 conversion is numerically faithful and that INT8 differences are small but can change decisions near quantized ties. They do not establish ESP32 kernel/delegate parity.

## Golden references and determinism

`phase2_diagnostics/golden_manifest.csv` and `golden_references.npz` contain 10 references selected from existing processed data: ordinary background, background→chainsaw, background→gunshot, correct chainsaw, chainsaw→background, correct gunshot, gunshot→background, low-energy, high-amplitude, and an end-position window. Each includes source/sample identity, feature tensor, normalized input, quantized input, output tensor, and dequantized output.

All 10 recomputed features matched their cache entries exactly. Five repeats per sample produced:

| Check | Result |
|---|---:|
| Feature max absolute repeat difference | 0.0 |
| Quantized-input disagreements | 0 |
| Output max absolute repeat difference | 0.0 |
| Prediction-class disagreements | 0 |

## Acceptance criteria

| Criterion | Result | Evidence/limitation |
|---|---|---|
| Exact desktop preprocessing traced | PASS | Source inspection plus cache-reproduction references |
| INT8 input/output contract verified | PASS | Flatbuffer tensor details and evaluator comparison |
| Golden references generated | PASS | 10 existing-data references; no padding example available |
| Determinism checked | PASS | Five repeats, zero disagreements |
| FP32/INT8 discrepancy explained | PASS | 98.2067% agreement; 9 runtime disagreements; ties documented |
| TFLM operator compatibility | PASS/PARTIAL | No unsupported ops in manual set; actual ESP32 build not run |
| ESP32 preprocessing parity | PARTIAL | Contract written; no INMP441/ESP32 paired capture or cycle/RAM test |
| Deployment readiness | PARTIAL | Feature implementation and hardware acceptance tests remain |

## Frozen artifact hashes

The before/after audit hashes are recorded in `phase2_diagnostics/phase2_summary.json` and remained unchanged:

```text
final.keras                         4ebad60f4de804cdf2659e34bed05e4b56dfc08bade8c1d3058657efaba430bd
forest_acoustic_fp32.tflite        890cf5cd74b28c3618ddbf64bdc9399a68f9048c5fe1117b45177056bded3811
forest_acoustic_int8.tflite        c9b3a391dc45b211587a5946ee15e357aef8c9c6baff6021866884b951972b9b
test_v1.csv                         efdb3aeffe986b0347af617575fc34734a12663557ec3ca755510f53ee9b2d28
features_cache/test.npz             649a4a3dce19ff470ac773ea99e3d09459ef9b3d98b5a8c2c80f5c43f20743b9
```

Phase 2 stops here. The next authorized phase should first implement the contract on the target audio path and run paired desktop/device golden tests; it should not silently change the frozen v1 preprocessing.
