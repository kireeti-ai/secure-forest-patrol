# ESP32 Preprocessing Contract — Frozen v1 Reference

This is the implementation contract for matching the frozen desktop model path. It is a reference specification, not a firmware change. Values marked **verified** come from the repository/model audit. Values marked **hardware-unverified** require an ESP32/INMP441 acceptance test.

## Required input

1. Capture mono PCM audio at 16,000 Hz.
2. Use 16,000 samples per inference window and an 8,000-sample hop.
3. Treat samples as finite real values. Reject or sanitize NaN/Inf before any max, FFT, or logarithm operation (**verified gap: desktop code has no explicit sanitizer; hardware behavior is unverified**).
4. The frozen desktop path performs source-level preprocessing before segmentation: decode float32, mono-average channels, resample to 16 kHz when needed, apply no filter, then peak-normalize the continuous stream to `0.707945784` peak. For a native 16-kHz mono microphone stream, apply the same peak normalization over the continuous capture interval used to create the window. Do not normalize each model window independently unless a later experiment explicitly changes the contract.

## Windowing

- `window_samples = 16000`
- `hop_samples = 8000`
- For a short non-empty source, the configured v1 policy is repeat the source cyclically until 16,000 samples. Empty input yields no inference window. Zero padding is not the configured v1 policy.
- For a long source, emit starts `0, 8000, 16000, ...` while a complete 16,000-sample window fits. If the remaining uncovered tail is greater than 8,000 samples, emit one final window beginning at `len(source)-16000`.
- Preserve the segment index and source timing in firmware logs if possible. The model itself receives no timestamp channel.

## Mel feature algorithm

For each 16,000-sample float32 window:

```text
n_fft       = 512
win_length  = 512
hop_length  = 160
window      = Hann
center      = true
pad_mode    = constant (zero padding)
n_mels      = 40
fmin        = 0 Hz
fmax        = 8000 Hz
power       = 2.0
mel scale   = librosa default: HTK=False, Slaney normalization
```

Compute the power mel spectrogram, then convert each window to dB using the maximum value in that window as the reference, with librosa-compatible `amin=1e-10` and `top_db=80`. The expected result is 40 mel bins × 101 time frames. The layout passed to the model is `[1, 40, 101, 1]`, with mel bin first and time second.

The ESP32 implementation must be validated against `golden_references.npz`; matching only the shape is insufficient. In particular, centered STFT padding, Hann coefficients, FFT scaling, mel filter boundaries/normalization, dB reference, epsilon, and frame rounding can each alter the quantized input.

## Model normalization and input quantization

Apply the scalar normalization to every mel element:

```text
normalized = (mel_db - (-36.31850051879883)) / 21.19044303894043
```

Then quantize with:

```text
q_real = normalized / 0.014805045910179615 + 11
q      = round(q_real)
q      = saturate(q, -128, 127)
```

The frozen Python evaluator used NumPy `round` followed by an int8 cast and did not explicitly clip. Firmware must use a documented, deterministic round-to-nearest rule and saturate. Exact half-way behavior must be tested against the golden vectors; do not rely on an unspecified C cast.

Input tensor:

```text
type:  int8
shape: [1, 40, 101, 1]
scale: 0.014805045910179615
zero:  11
```

## Output and decision

The flatbuffer returns three int8 scores in class order:

```text
[background, chainsaw, gunshot]
```

For diagnostics, dequantize with:

```text
score_real = (output_q - (-128)) * 0.00390625
```

The frozen decision is `argmax` on the raw int8 values. If values tie, select the lowest index (background before chainsaw before gunshot). Do not apply a new threshold or probability calibration under this contract.

## Runtime and resource status

The flatbuffer contains `CONV_2D`, `DEPTHWISE_CONV_2D`, `FULLY_CONNECTED`, `MAX_POOL_2D`, `MEAN`, and `SOFTMAX`; these passed the repository's manual TFLM compatibility check. This is not a proof that the selected ESP32/TFLM build has every kernel enabled.

The audit does not claim RAM, flash arena size, latency, throughput, power, microphone DMA behavior, or thermal performance. Those are **hardware-unverified** and require the actual board, firmware build, TensorFlow Lite Micro/LiteRT version, compiler flags, and INMP441 capture path.

## Hardware acceptance tests before deployment

1. Record paired samples through the actual INMP441/ESP32 path and the desktop reference path.
2. Compare the post-normalization waveform, one 40×101 mel tensor, the normalized tensor, and the 40×101 int8 input tensor against the golden vectors and tolerance budgets agreed for the implementation.
3. Run the same frozen flatbuffer on-device and compare output int8 tensors and class decisions, including tie cases.
4. Measure arena allocation, peak RAM, inference latency, sustained throughput, and power on the target board. Record exact toolchain/runtime versions.
5. Test short input, long input tail behavior, silence, clipping, overflow/saturation, and non-finite-input handling explicitly.

Until these tests pass, ESP32 preprocessing/model parity is **PARTIAL**, even though the desktop reference path is reproducible.
