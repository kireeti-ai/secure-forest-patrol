# Digital Audio Filter Report (A/B)

## Filter
- **Type / order:** causal Butterworth **high-pass, 2nd order** (one biquad section), **fc = 80 Hz**, fs = 16 kHz.
- **Rationale:** removes DC offset and sub-80 Hz rumble/wind/handling noise (-3 dB at 80 Hz, -12 dB at 40 Hz, -24 dB at 20 Hz) while leaving chainsaw/gunshot energy (>100 Hz; -0.1 dB at 200 Hz) essentially untouched. One biquad = 5 multiplies/sample and 2 state values on the ESP32-S3; deterministic, fixed parameters. No denoising/spectral subtraction/NN.
- **Causal only** (`scipy.signal.sosfilt`; no `filtfilt`), so the Python reference equals the streaming ESP32 filter.
- **Implementation (single shared module):** `preprocessing/audio_filter.py`, switchable via `configs/preprocessing.yaml` -> `filter.enabled` (default `false`, so frozen v1 = variant A). Called from `AudioPreprocessor.filter_audio`.
- **Pipeline position:** raw WAV -> resample 16 kHz -> mono -> **FILTER** -> peak-normalise -> 1 s windowing (50 % overlap) -> MFCC/Mel -> INT8 model. The whole continuous recording (or rodopi interval) is filtered *before* windowing, so filter state is never reset at window boundaries. On device the biquad state simply persists across the I2S stream (verified: chunked filtering with carried state == whole-signal filtering, `tests/test_audio_filter.py`). Caveat: the Python pipeline peak-normalises per recording after the filter; the device has no per-recording peak, which is a pre-existing train/deploy gap independent of the filter.

## Exact biquad coefficients (fs=16000, fc=80 Hz, a0 = 1)
```
b0 =  0.9780304792065597
b1 = -1.9560609584131194
b2 =  0.9780304792065597
a1 = -1.9555782403150352
a2 =  0.9565436765112031
```
Direct Form II Transposed (per sample x -> y; z1, z2 persist across the stream, init 0):
```c
static float z1 = 0, z2 = 0;
static inline float hp_biquad(float x) {
    const float b0=0.97803048f, b1=-1.95606096f, b2=0.97803048f, a1=-1.95557824f, a2=0.95654367f;
    float y = b0*x + z1;
    z1 = b1*x - a1*y + z2;
    z2 = b2*x - a2*y;
    return y;
}
```
Verified against `sosfilt` to 1e-9 (`test_matches_manual_df2t_biquad`). Float32 on ESP32: poles are close to the unit circle (a2 = 0.9565); float32 is adequate, but keep z1/z2 in float (not Q15) unless re-validated.

**ESP32 chain:** INMP441 (I2S, 16 kHz) -> `hp_biquad` -> same normalisation/windowing -> same MFCC/Mel (n_fft 512, hop 160, 40 mels) -> INT8 TFLite Micro (`forest_acoustic_int8.tflite`). Not built on hardware (none available).

## Validation
`tests/test_audio_filter.py` (7 tests, pass): identity when disabled; no NaN/Inf, length/sr preserved; DC removed, 1 kHz passband kept; equals manual DF2T; streaming == whole; MFCC (13,101) and Mel (40,101) shapes unchanged; INT8 model inference runs on filtered audio. Filtered set regenerated for **all 58,918 frozen v1 sample_ids** (0 missing; manifests/splits untouched) into `datasets/processed_filtered/`; features in `datasets/features_cache_filtered/` (same shapes, same ids/labels as the unfiltered cache).

## Controlled A/B
Same frozen splits and caps, same `final` architecture (1,315 params), Adam 1e-3, batch 32, 15 epochs, early stopping, class weights, augmentation; seeds 42, 1, 2 for each of A and B (`models/ab_filter_experiment.py`; artifacts in `models/ab_filter/`; `models/final` untouched). Values are mean ± sample-std over 3 seeds (raw per-seed numbers: `reports/ab_filter_results.json`, notebook 11). Note the A seed-42 re-run (val 0.629 / test 0.455) does not exactly reproduce the original v1 model (val 0.654 / test 0.561): TF training is not bit-deterministic and the model is tiny, so **run-to-run variance is large**.

| Split / metric | A no filter | B filter |
|---|---|---|
| val macro-F1 | 0.596 ± 0.047 | 0.612 ± 0.083 |
| val background F1 | 0.881 ± 0.007 | 0.870 ± 0.041 |
| val chainsaw F1 / recall | 0.570 / 0.498 | 0.587 / 0.611 |
| val gunshot F1 / recall | 0.338 / 0.809 | 0.380 / 0.772 |
| test macro-F1 | 0.464 ± 0.008 | 0.399 ± 0.072 |
| test background F1 | 0.699 ± 0.014 | 0.580 ± 0.133 |
| test chainsaw F1 / recall | 0.551 / 0.810 | 0.443 / 0.866 |
| test gunshot F1 / recall | 0.141 / 0.938 | 0.173 / 0.891 |
| external macro-F1 | 0.359 ± 0.045 | 0.404 ± 0.102 |
| external background F1 | 0.449 ± 0.096 | 0.443 ± 0.169 |
| external chainsaw F1 / recall | 0.350 / 0.910 | 0.176 / 0.405 |
| external gunshot F1 / recall | 0.277 / 0.992 | 0.592 / 0.935 |

INT8 size identical (13,072 B), 0 unsupported TFLM ops for both.

### Robustness (INT8, test_v1, existing procedure: Gaussian noise on Mel features, clean / 15 dB / 5 dB)
| Condition | A acc / macro-F1 | B acc / macro-F1 |
|---|---|---|
| clean | 0.598 / 0.468 | 0.506 / 0.408 |
| 15 dB | 0.556 / 0.306 | 0.392 / 0.244 |
| 5 dB | 0.755 / 0.323 | 0.110 / 0.067 |

Caveat: this procedure injects noise *after* the filter (in feature space), so it cannot show the filter's benefit against low-frequency rumble; it only shows how a filter-trained model copes. The 5 dB accuracy of A is high only because noisy inputs collapse to "background" (majority class), macro-F1 (0.32) is the fairer number.

## Conclusion (measured only)
The filter is **neutral on validation and in-domain test within noise, and not beneficial overall**: validation macro-F1 is +0.016 (well inside the seed std of 0.05-0.08), test macro-F1 is -0.065 (B mean below A, with B std 0.07-0.13, so partly noise), external chainsaw recall drops sharply (0.91 -> 0.41) though external gunshot F1 rises (0.28 -> 0.59), and robustness under feature-noise is worse. B is also less stable across seeds (larger std almost everywhere). With 3 seeds and a 1,315-parameter model the evidence is not strong enough to call B definitively harmful, but there is no measured gain to justify it.

**Recommendation:** do not replace `models/final` (untouched). The filter is cheap and harmless for real hardware (DC/rumble from an INMP441 is a genuine device-side concern that these offline datasets, already mostly high-passed/normalised, cannot reveal). If retained on ESP32, retrain on filtered audio; otherwise keep it disabled (`filter.enabled: false`, the default). Decide after on-device recordings are available; that requires hardware not present here.
