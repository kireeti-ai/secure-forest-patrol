# Phase 1 — False-Positive and False-Negative Investigation

Status: **COMPLETE — diagnostic only**  
Audit date: 2026-10-18  
Frozen model and test data were not modified. No retraining, threshold tuning, label changes, split changes, alert-logic changes, or firmware changes were performed.

## Executive summary

The frozen INT8 test predictions were reproduced exactly on the canonical Phase 0 path: 2,119/2,119 sample IDs and labels matched the cache/manifests, all 2,119 referenced audio files were readable, and the confusion matrix matched the Phase 0 clean robustness result.

The dominant failure is background false positives, not missed gunshots:

- 536/1,781 background windows were classified as a target event: window-level false-alarm rate **0.3010**.
- 448 were background → chainsaw across 97 source recordings.
- 88 were background → gunshot across 34 source recordings.
- The errors were concentrated in `rfcx_frugalai`, `fsc22`, and `esc50_hf`; no test background errors came from `c3gd` because its test samples are gunshots.
- False positives were often high-confidence: median dequantized INT8 softmax score 0.756 and median top-two margin 0.525.
- No test error window had measurable clipping at the configured `abs(audio) >= 0.95` criterion.

Target-event false negatives were smaller but operationally important:

- 39 chainsaw → background windows across 13 recordings.
- 6 gunshot → background windows, all from one `fsc22` recording.
- Event false negatives had lower RMS energy than correct events: chainsaw FN median RMS 0.0767 versus 0.1363 for correct chainsaw windows; gunshot FN median RMS 0.0392 versus 0.0880 for correct gunshot windows.

The evidence supports a prioritized investigation of hard background negatives and recording-domain coverage, followed by event-boundary/low-energy review. It does not prove that any individual sample is mislabeled or that a particular acoustic cause is present without listening and expert annotation.

## Baseline reproduction

The canonical Phase 1 evaluator uses the default desktop `tf.lite.Interpreter`, the frozen `forest_acoustic_int8.tflite`, the training mean/std from `final_metadata.json`, and `np.argmax` on the quantized output tensor. The diagnostic script intentionally completes model inference before reading audio files so filesystem activity cannot affect the evaluation path.

| Metric | Reproduced result |
|---|---:|
| Samples | 2,119 |
| Accuracy | 0.7216 |
| Balanced accuracy | 0.7989 |
| Macro precision | 0.5264 |
| Macro recall | 0.7989 |
| Macro-F1 | 0.5760 |
| Background false positives | 536 / 1,781 |
| Background false-alarm rate | 0.3010 |
| Unreadable audio paths | 0 |

Confusion matrix, rows true and columns predicted in `[background, chainsaw, gunshot]` order:

```text
[[1245, 448,  88],
 [  39, 247,   9],
 [   6,   0,  37]]
```

Per-class results:

| Class | Precision | Recall | F1 |
|---|---:|---:|---:|
| Background | 0.9650 | 0.6990 | 0.8089 |
| Chainsaw | 0.3539 | 0.8373 | 0.4975 |
| Gunshot | 0.2721 | 0.8605 | 0.4134 |

The prediction CSV preserves every sample ID, original recording ID, class scores, predicted class, confidence, margin, source metadata, audio path, and measured audio statistics. Dequantized output scores are treated as model scores for diagnostics; they are not claimed to be calibrated probabilities of correctness.

## Background false positives

### Counts and source-level concentration

| Error | Windows | Affected recordings | Datasets |
|---|---:|---:|---|
| Background → chainsaw | 448 | 97 | fsc22 171, esc50_hf 151, rfcx_frugalai 126 |
| Background → gunshot | 88 | 34 | fsc22 51, esc50_hf 37 |
| Total background FP | 536 | 121 | fsc22, esc50_hf, rfcx_frugalai |

There are 228 background source recordings in the test split. Thirty-six affected recordings have a 100% window-level false-positive rate. Since windows overlap by 50%, these are correlated observations, not 536 independent acoustic examples. The top 20 affected recordings contribute 175/536 windows (32.6%); the top 50 contribute 349/536 (65.1%). The source-level CSV should therefore be used when prioritizing collection or review.

Dataset-specific background false-positive rates are:

| Dataset | Background windows | FP windows | Window FP rate | Affected recordings |
|---|---:|---:|---:|---:|
| rfcx_frugalai | 193 | 126 | 0.6528 | 29 |
| esc50_hf | 642 | 188 | 0.2928 | 37 |
| fsc22 | 946 | 222 | 0.2347 | 55 |

The highest measured concentration is `rfcx_frugalai` background, but its denominator is smaller. This is evidence for a dataset/domain-specific background problem, not proof that the model fails on all real forest backgrounds.

### Metadata and measurable audio patterns

The test error windows are all 1.0 seconds, 16 kHz, mono, and readable. No FP window had samples at or above 0.95 absolute amplitude. Thus clipping is not supported as the dominant explanation for this test set.

Background → chainsaw errors have median RMS 0.1285 and median peak 0.6193. Correct background windows have median RMS 0.0989 and peak 0.5824. This argues against the errors being primarily near-silent windows; many are relatively active windows.

Background → gunshot errors have median RMS 0.0702 and median peak 0.5869. Their lower RMS and transient-like visual examples are consistent with a possible percussive/transient confusion, but the claim remains a hypothesis without human listening and acoustic labels.

Source metadata is useful for dataset attribution but does not identify microphone/device fields for these error groups: `event_id`, `platform_id`, `cartridge_id`, and `mic_id` are empty for the affected `fsc22`, `esc50_hf`, and `rfcx_frugalai` samples. No device-specific causal conclusion can be made from the frozen manifest.

### Category observations

For fsc22 background false positives, the most frequent source categories are `BirdChirping` (55 total target predictions), `Insect` (39), `Wind` (28), and `Squirrel` (26). For ESC-50 background false positives, `chirping_birds` (36), `engine` (31), `insects` (29), `wind` (24), and `crow` (12) are prominent. These are source labels, not independent acoustic diagnoses. They identify useful hard-negative strata for a later controlled experiment.

The inspected representative plots show two visually distinct patterns:

- A background → chainsaw example with sustained broadband/harmonic activity across the one-second window.
- A background → gunshot example with a strong isolated transient and decaying tail.

These visual observations support the hard-negative hypothesis but do not establish the semantic identity of the sounds.

## False negatives

### Counts and distribution

| Error | Windows | Affected recordings | Datasets |
|---|---:|---:|---|
| Chainsaw → background | 39 | 13 | fsc22 26, rfcx_frugalai 11, esc50_hf 2 |
| Gunshot → background | 6 | 1 | fsc22 6 |

Chainsaw false-negative rates by dataset are 21.1% for fsc22 (26/123), 9.3% for rfcx_frugalai (11/118), and 3.7% for esc50_hf (2/54). The six gunshot false negatives are 6/36 fsc22 gunshots; all seven c3gd gunshot windows were detected.

The largest source-level chainsaw failures are:

- `fsc22_11_11166`: 7/9 chainsaw windows missed.
- `fsc22_11_11164`: 5/9 missed.
- `rfcx_rfcx_train_00154_chainsaw`: 5/5 missed.
- `fsc22_11_11101`: 4/6 missed.
- `rfcx_rfcx_train_00260_chainsaw`: 3/3 missed.

These clusters show that the 39 windows are not 39 independent failures. They are concentrated in a small number of recordings, which makes source-level review more important than simply adding all missed windows as training examples.

### Energy, boundaries, and representative inspection

Correct chainsaw windows have RMS quantiles 0.0667 / 0.1363 / 0.1794 (10th/50th/90th percentiles), while chainsaw false negatives are 0.0303 / 0.0767 / 0.1162. Correct gunshot windows have RMS 0.0441 / 0.0880 / 0.1575, while gunshot false negatives have RMS 0.0241 / 0.0392 / 0.0485.

The representative chainsaw false-negative plot has several high-energy bursts separated by a long low-energy interval; the model may be seeing only a partial or acoustically weak event in some windows. The representative gunshot false-negative plot has a strong impulse very near the beginning followed by a decaying low-energy tail. These are consistent with boundary/partial-event hypotheses, but the available manifest does not provide a verified event interval for these samples, so no label correction is justified.

## Confidence and margin analysis

Confidence is the dequantized output score of the predicted class. Margin is the predicted-class score minus the second-highest score. Neither is treated as a calibrated probability or used to make a decision in this phase.

| Group | Count | Confidence q10 / median / q90 | Margin q10 / median / q90 |
|---|---:|---:|---:|
| Correct | 1,529 | 0.563 / 0.797 / 0.957 | 0.179 / 0.633 / 0.918 |
| Background false positives | 536 | 0.531 / 0.756 / 0.938 | 0.105 / 0.525 / 0.875 |
| Target false negatives | 45 | 0.438 / 0.602 / 0.837 | 0.013 / 0.254 / 0.716 |

Incorrect predictions are not uniformly low-confidence. Background false positives are frequently confident and separated from the runner-up, especially background → chainsaw. False negatives are generally less separated, but some also have high model score. This supports future calibration/rejection investigation, but no threshold was selected or tuned here.

## Dataset and segmentation observations

The inspected preprocessing code creates 1-second windows at 16 kHz with a 0.5-second hop, using repeat/zero padding for short inputs and a final coverage rule for longer inputs. Split assignment occurs after segment creation and is grouped by `original_recording_id`; the test manifest confirms multiple windows per recording, with test `segment_index` values 0–8.

The current audit did not regenerate features or data. It used the frozen cache and manifest only. Because overlapping windows from the same recording share acoustic context, sample-level metrics overstate the amount of independent evidence. The most important observed concentration is in source recordings, not individual windows.

The test split contains no `rodopi` or `sensing_forest` background windows in the audited prediction table. The background error analysis therefore does not establish behavior on those source domains. The external test and future field recordings remain necessary for broader conclusions.

## Representative diagnostic artifacts

Fourteen plots were generated from distinct source recordings where available: up to four each for background → chainsaw, background → gunshot, and chainsaw → background, plus the single available gunshot → background source recording. Each includes waveform, log-Mel spectrogram, true/predicted class, and model score. Audio was not played; acoustic interpretations requiring listening are marked as hypotheses.

The representative index is [representative_samples.csv](./phase1_diagnostics/representative_samples.csv). All prediction-level evidence is in:

- [predictions.csv](./phase1_diagnostics/predictions.csv)
- [false_positives.csv](./phase1_diagnostics/false_positives.csv)
- [false_negatives.csv](./phase1_diagnostics/false_negatives.csv)
- [source_recording_summary.csv](./phase1_diagnostics/source_recording_summary.csv)
- [dataset_summary.csv](./phase1_diagnostics/dataset_summary.csv)
- [summary.json](./phase1_diagnostics/summary.json)

## Ranked failure taxonomy

| Rank | Category | Evidence | Confidence | Likely follow-up area |
|---:|---|---|---|---|
| 1 | Hard background negatives / domain mismatch | 536 FP windows, 121 recordings, three source datasets; rfcx background FP rate 65.3%; high-confidence errors; no clipping | High for the measured dataset pattern; low for the exact acoustic cause | Targeted background collection and raw-audio domain augmentation |
| 2 | Correlated source-recording failure clusters | 36 recordings have all test windows false-positive; top 20 sources contribute 32.6% of FP windows | High | Source-level review and recording-balanced evaluation/collection |
| 3 | Low-energy or partial chainsaw windows | 39 windows/13 recordings; event RMS median 0.0767 versus 0.1363 for correct chainsaw; clusters in fsc22 and rfcx | Medium; boundary explanation is not verified | Event-interval review, boundary-aware data audit, targeted recordings |
| 4 | Low-energy/partial fsc22 gunshot windows | 6 windows from one recording; RMS median 0.0392 versus 0.0880 for correct gunshots; impulse near boundary in inspected plot | Medium-low due to only one source recording | Manual event review and additional independent gunshot recordings |
| 5 | INT8 confidence/tie behavior | False positives can have high confidence; diagnostic required canonical `argmax` because quantized score ties can change class selection | High for the software behavior; operational impact not assessed | Canonical runtime comparison and later calibration study |

Clipping, missing files, and sample-rate/channel mismatch are not supported as explanations for the audited test errors: all 2,119 files were readable at 16 kHz mono and no measured window crossed the clipping criterion.

## Prioritized controlled follow-up experiments

These are recommendations only. None was implemented in Phase 1.

1. **Targeted hard-negative collection.** Address the measured background FP pattern in rfcx, fsc22, and ESC-50 strata, especially bird/insect/wind/engine/transient examples. Use new source recordings or source-grouped training additions, not repeated overlapping windows from the same failing recording. Evaluate on a new source-disjoint background challenge set while preserving the frozen test set. Main metric: background FP rate and recording-level false alerts. Risk: over-suppressing genuine chainsaw/gunshot recall.
2. **Source-level event and label review.** Review the clustered fsc22 and rfcx chainsaw recordings and the single fsc22 gunshot recording, including event boundaries and partial occupancy. Do not relabel automatically. Create a reviewed dataset version only after independent annotation. Main metrics: chainsaw and gunshot recall, with source-level confidence intervals. Risk: removing difficult but valid examples or introducing annotator bias.
3. **Raw-audio domain/channel augmentation.** Test gain, microphone response, background mixing, wind/engine interference, and recording-level normalization using training sources only. The current evidence is dataset/domain concentration, not clipping. Main metrics: external-test macro-F1, background FP rate, and target recall. Risk: synthetic transformations may make events less realistic or reduce event separability.
4. **Preprocessing consistency audit.** Compare the Python feature path with the eventual INMP441/ESP32 path using recorded device audio before changing the model. The present Phase 1 data cannot establish hardware mismatch. Main metric: feature/prediction agreement on paired recordings. Risk: discovering a deployment mismatch late without physical hardware.
5. **Temporal/recording-level evaluation study.** Because 50% overlap creates correlated windows and many failures cluster by source, evaluate alert aggregation on a separate validation/challenge protocol. Do not tune it against the frozen test set. Main metrics: false alerts per recording/hour and event detection delay, alongside event recall. Risk: delayed detection or suppression of short gunshots.
6. **Confidence calibration/rejection study.** Use validation data or a new calibration split to assess whether score/margin-based rejection separates hard negatives from genuine events. Do not use the Phase 1 test errors to choose a threshold. Main metrics: selective risk/coverage and target recall at fixed false-alert budgets. Risk: high-confidence false positives show that simple rejection may not be sufficient.

## Limitations and unresolved questions

- No audio playback or expert listening was performed; waveform/spectrogram interpretations require manual review.
- The diagnostic audio statistics are measured on processed 1-second WAV segments, not raw microphone captures.
- `event_id`, platform, cartridge, and microphone metadata are unavailable for the main FP/FN groups, preventing device-level causal analysis.
- Window-level counts are correlated because the segmentation hop is 0.5 seconds; operational false alerts per hour were not measured.
- The frozen test set has only 43 gunshot windows and six gunshot false negatives, all from one source recording.
- No adversarial audio, replay, field, or physical ESP32 test was performed.
- The diagnostic script is a new audit-only artifact and does not modify training, evaluation, preprocessing, firmware, model, labels, splits, or reports.

## Completion summary

Files inspected included `V1_BASELINE.md`, `V1_BASELINE_MANIFEST.json`, the historical failure/robustness/dataset/quantization reports, the frozen model files, `models/robustness_eval.py`, `models/train_cnn.py`, `preprocessing/audio_preprocess.py`, `preprocessing/create_splits.py`, and the frozen test manifest/cache.

Commands executed:

```bash
git status --short --branch
sha256sum ml/models/final/final.keras ml/models/final/forest_acoustic_int8.tflite ml/datasets/v1/*.csv ml/datasets/features_cache/*.npz
python3 ml/reports/phase1_diagnostics/run_phase1_audit.py
```

New diagnostic outputs are under `reports/phase1_diagnostics/`. Pre-existing modified and untracked repository files were preserved. The frozen model and dataset hashes remain unchanged. Phase 1 stops here; Phase 2 has not begun.
