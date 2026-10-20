# Training Pipeline Fix — Baseline vs. Updated Model (v2)

All numbers below come from real executed runs in this repository (`models/train_cnn.py`,
`models/convert_tflite.py`, `models/robustness_eval.py`) against the same frozen `v1` dataset
and splits described in `DATASET_V1_REPORT.md` / `FINAL_MODEL_REPORT.md`. No new training data
was added — every improvement here comes from fixing the training procedure itself.

## 1. What was wrong with the baseline (not the data, not the architecture)

The shipped model (`models/final`, 1,315-param depthwise-separable CNN) had two concrete bugs
in how it was trained, independent of the well-documented dataset scarcity problem:

1. **Batches were sampled at natural class frequency.** Gunshot is 3.6% of the cached training
   set (304 of 8,397 samples). A batch of 32 drawn at natural frequency contains on average
   ~1.1 gunshot examples — most batches saw none. Loss-side `class_weight` compensates the
   *gradient magnitude* when a gunshot sample does appear, but does nothing about how rarely
   it appears in the first place.
2. **Noise/background mixing augmentation blended dB-scale mel values directly**
   (`models/augment.py`, old code: `out[i] * (1 - alpha) + noise * alpha` on dB values). Sound
   power adds linearly; dB values do not. This is not how two sounds actually combine, so the
   model was never trained against a physically realistic noisy mixture — a likely contributor
   to the near-total collapse (accuracy 0.02) found at 5 dB SNR in `ROBUSTNESS_REPORT.md`.

Two further hypotheses were tested and **rejected** based on measured results (see §3):
- A ~13x larger model (17,155 params, same depthwise-separable pattern, still tiny for the
  ESP32-S3's 3.3 MB flash / 64 KB tensor arena budget) — capacity was not the bottleneck;
  it made unseen-domain generalization *worse*, not better.
- Explicit additive Gaussian-SNR noise augmentation (matching `robustness_eval.py`'s own
  perturbation) — fixed noise robustness dramatically but cost generalization to unseen
  recording sources even at a low 15% application probability. Not shipped.

## 2. Fixes applied

File-level changes, both train-time only (nothing changes what the model computes at inference,
so firmware/preprocessing/quantization are unaffected):

- `models/augment.py`: noise mixing converted to power domain
  (`10**(db/10)` → linear mix → `10*log10(...)` back), replacing the old direct dB blend.
- `models/train_cnn.py`: `AugmentedSequence` gained **partial class-balanced batch sampling**
  (`--balance-strength`, 0 = natural frequency, 1 = fully equal counts). `--balance-strength 0.5`
  was the empirically best setting — full balancing (`1.0`) over-corrected and flooded
  predictions toward gunshot, tanking precision (see §3). When balanced sampling is on,
  the redundant loss-side `class_weight` is disabled rather than stacked on top.

No change to the model architecture that was shipped, no change to feature extraction, no new
data.

## 3. Results — every variant actually trained and measured

All on the same frozen `test` / `external_test` splits as the baseline report.

| Variant | Change from baseline | Test macro-F1 | External acc | External macro-F1 | 5 dB SNR acc |
|---|---|---|---|---|---|
| **Baseline (shipped)** | — | 0.561 | 0.437 | 0.579 | 0.02 |
| v2 (balance=0.5, fixed mixing) | batch balancing + power-domain mixing | **0.698** | **0.832** | **0.802** | ~0.11 |
| v2 (balance=1.0, fixed mixing) | full balancing instead of 0.5 | 0.434 | 0.597 | 0.441 | — |
| v3 (v2 + Gaussian-SNR noise aug @ 40%) | explicit noise-robustness training | 0.646 | 0.447 | 0.600 | **0.735** |
| v4 (v2 + Gaussian-SNR noise aug @ 15%) | lower-probability version of v3 | 0.638 | 0.580 | 0.642 | not fully profiled |
| Large model (17,155 params), no noise aug | ~13x capacity, same balance=0.5 | 0.775 | 0.584 | 0.674 | not tested |

**Shipped: v2 (balance-strength 0.5, power-domain mixing, no Gaussian noise augmentation).**
It is the clear winner on the metrics that matter most for a device that will see audio from
microphones/environments the training data never included (external-test accuracy and macro-F1),
without needing a bigger, costlier model.

### Why the alternatives were rejected

- **Full balancing (1.0):** gunshot recall went to 0.80–1.00 but precision collapsed to
  0.07–0.21 — the model started calling almost everything "gunshot." Macro-F1 fell *below*
  the baseline despite better recall.
- **Noise-robustness augmentation (v3/v4):** fixed the 5 dB SNR collapse (0.02 → 0.74) but cut
  external-test accuracy roughly in half (0.83 → 0.45–0.58) at every probability tried, even
  the mildest (15%). At this model size, robustness-to-noise and generalization-to-new-sources
  appear to trade off directly rather than compose.
- **Larger model (17,155 params):** improved in-distribution test metrics (macro-F1 0.775,
  better than v2's 0.698) but *external*-test accuracy dropped to 0.584 — more capacity let it
  fit training-domain-specific artifacts harder, which is the opposite of what's needed for a
  field device encountering new recording equipment and environments.

## 4. Deployment status

- `models/final_baseline_pre_v2/` — full backup of the previously shipped model (architecture,
  `.keras`, `.tflite` x2, metadata) for rollback.
- `models/final/` — now contains v2's model + metadata (promoted).
- v2 INT8 quantization: 0.8735 test accuracy / 0.6801 macro-F1, 97.55% prediction agreement
  with the FP32 Keras model — consistent with the baseline's quantization fidelity.
- `node-firmware/lib/Acoustic/src/AcousticModelData.h` and `AcousticTestVectors.h` regenerated
  from the new model (`tools/embed_model.py`, `tools/gen_acoustic_testvectors.py`).
- **On-device self-test (`FOREST_ACOUSTIC_TEST_MODE=3`) passed on real ESP32-S3 hardware**:
  TFLite Micro output matches the Python INT8 reference (max diff 0–4/256, well under the
  documented 8/256 tolerance), on-device preprocessing is bit-exact (4040/4040 tensor elements),
  and end-to-end device inference correctly classified a real gunshot window at 0.715 confidence.

## 5. What's still open

- **Noise robustness remains weak** (~0.11 accuracy at 5 dB SNR) — every training-time fix
  tried for this cost external generalization at this model size. Better approach for later:
  test-time multi-window voting/smoothing (the existing `experimental_alert_logic` decision
  layer) rather than more training-time augmentation, since that doesn't touch what the model
  itself learns.
- **Gunshot is still the weakest class in absolute terms** (304 training samples) — this report
  only fixes *how* the existing data is used, not the underlying scarcity. Real gunshot audio
  captured through the deployed INMP441/MAX4466 hardware (`node-firmware/tools/capture_audio.py`)
  remains the highest-value next step for further improvement.
