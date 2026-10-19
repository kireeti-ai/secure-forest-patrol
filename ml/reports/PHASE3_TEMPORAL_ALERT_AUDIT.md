# Phase 3 — Temporal Confirmation, Reject State, and Duplicate Alert Suppression

Status: **COMPLETE — diagnostic-only offline replay**  
Audit date: 2026-10-18

No frozen model, dataset, split, Phase 0–2 report, firmware, gateway behavior, MQTT schema, or production alert path was modified. Phase 4 has not started.

## Executive summary

The experiment replayed the frozen default desktop INT8 predictions chronologically within each source recording. The Phase 3 baseline matched the Phase 1 canonical test predictions exactly.

Validation supported a margin-based reject state and a duplicate-alert episode layer, but did not support temporal confirmation under the required event-recall constraint. The selected experimental configuration is therefore:

- no temporal confirmation;
- `UNCERTAIN_CHAINSAW`/`UNCERTAIN_GUNSHOT` when the uncalibrated top-two score margin is below `0.30`;
- separate same-class duplicate suppression with a 2.0-second quiet period, equivalent to four 0.5-second hops.

On the locked test comparison, this configuration reduced background false-positive windows from 536/1,781 (`0.3010`) to 374/1,781 (`0.2100`) and increased macro-F1 from `0.5760` to `0.6417`. It also suppressed 485 repeated alert candidates and left 183 windows uncertain. Chainsaw recall decreased from `0.8373` to `0.7695`; gunshot recall was unchanged at `0.8605`. These are window-level replay metrics, not false-alerts-per-hour or verified event-level metrics.

Duplicate suppression reduced emitted alert candidates from 829 to 199 in its isolated test configuration, while leaving classification metrics unchanged. Because the data does not provide reliable event boundaries for all sources, this is an episode-grouping proxy, not proof that every suppressed candidate belonged to the same real-world event.

## Replay contract

The replay input contains sample ID, source recording ID, dataset, segment index, true class, raw INT8 output values, dequantized scores, predicted class, uncalibrated margin, and derived start time. The default desktop TFLite path was regenerated for the full validation and test manifests; the test prediction IDs and classes matched `reports/phase1_diagnostics/predictions.csv` exactly.

Windows were never shuffled. State was reset at recording boundaries. Ordinary windows use `segment_index × 0.5 s`; rows with interval metadata use `interval_start + segment_index × 0.5 s`. This was necessary because two validation recordings contain local segment indices that reset for separate annotated intervals. Records with duplicate or out-of-order derived timestamps are handled deterministically and logged rather than joined silently.

The validation cache contains only a historical filtered subset, so validation features were recomputed in memory from the existing processed WAV files using the accepted Phase 2 feature implementation. No cache was rewritten. The full validation manifest was evaluated.

## Candidate mechanisms

### Temporal confirmation

Tested candidates:

| Candidate | Rule |
|---|---|
| `temporal_2_of_2` | Two same-class positive windows within two 0.5-second positions; maximum gap one position |
| `temporal_2_of_3` | Two same-class positives within three positions; maximum gap two positions |
| `temporal_3_of_4` | Three same-class positives within four positions; maximum gap two positions |

Unconfirmed event-positive windows become `UNCERTAIN_<CLASS>` operationally and are not actionable event decisions. State is separate per event class and resets at each recording.

The validation baseline event recall was chainsaw `0.4775` and gunshot `0.6667`. Candidate selection required lower background FP rate while retaining at least 80% of each baseline event recall. All temporal candidates failed that requirement, mainly because short or sparse events were suppressed. No temporal rule was selected.

### Reject state

Tested uncalibrated margin cutoffs were `0.10`, `0.20`, and `0.30`. A predicted event below the selected cutoff becomes `UNCERTAIN_CHAINSAW` or `UNCERTAIN_GUNSHOT`; uncertainty is not interpreted as environmental safety. Raw predictions remain in the replay output.

Validation selected `0.30` because it had the highest validation macro-F1 among candidates satisfying the event-recall floor and reducing background FP rate. It produced validation macro-F1 `0.5813` versus baseline `0.5483`, with background FP rate `0.0606` versus `0.0861`, while retaining chainsaw recall `0.4392` and gunshot recall `0.6111`.

The threshold is not a calibrated probability threshold. It is a validation-selected score-margin rule and requires revalidation after any model, preprocessing, runtime, or data change.

### Duplicate suppression

Tested quiet periods were 2, 4, and 6 half-second hops. The selected operational proxy is four hops, or 2.0 seconds. Separate state is maintained for chainsaw and gunshot. A same-class candidate while its episode is active is logged with suppression reason `active_same_class_episode`; each same-class candidate extends the active episode. A later candidate after the quiet period opens a new alert. State resets between source recordings.

This mechanism does not rewrite predictions or classification metrics.

## Validation comparison

| Configuration | Accuracy | Macro-F1 | Background FP rate | Chainsaw recall | Gunshot recall | Uncertain | Emitted candidates |
|---|---:|---:|---:|---:|---:|---:|---:|
| Single-window baseline | 0.8843 | 0.5483 | 0.0861 | 0.4775 | 0.6667 | 0 | 817 |
| Temporal 2/2 | 0.8993 | 0.4853 | 0.0588 | 0.3694 | 0.2037 | 254 | 563 |
| Temporal 2/3 | 0.8977 | 0.4916 | 0.0612 | 0.3761 | 0.2407 | 232 | 585 |
| Temporal 3/4 | 0.9061 | 0.4575 | 0.0457 | 0.2973 | 0.1111 | 377 | 440 |
| Reject margin 0.10 | 0.8917 | 0.5583 | 0.0775 | 0.4707 | 0.6481 | 65 | 752 |
| Reject margin 0.20 | 0.8993 | 0.5749 | 0.0688 | 0.4640 | 0.6296 | 126 | 691 |
| Reject margin 0.30 | 0.9051 | 0.5813 | 0.0606 | 0.4392 | 0.6111 | 191 | 626 |
| Duplicate quiet 2 | 0.8843 | 0.5483 | 0.0861 | 0.4775 | 0.6667 | 0 | 232 |
| Duplicate quiet 4 | 0.8843 | 0.5483 | 0.0861 | 0.4775 | 0.6667 | 0 | 212 |
| Duplicate quiet 6 | 0.8843 | 0.5483 | 0.0861 | 0.4775 | 0.6667 | 0 | 202 |

Validation values are used for selection only. They are not claims about deployment performance.

## Locked test comparison

| Configuration | Accuracy | Balanced accuracy | Macro precision | Macro recall | Macro-F1 | Background FP windows/rate | Candidate / emitted / suppressed | Uncertain |
|---|---:|---:|---:|---:|---:|---|---|---:|
| Single-window baseline | 0.7216 | 0.7989 | 0.5264 | 0.7989 | 0.5760 | 536 / 0.3010 | 829 / 829 / 0 | 0 |
| Temporal only | 0.7216 | 0.7989 | 0.5264 | 0.7989 | 0.5760 | 536 / 0.3010 | 829 / 829 / 0 | 0 |
| Reject only, margin 0.30 | 0.7886 | 0.8067 | 0.5813 | 0.8067 | 0.6417 | 374 / 0.2100 | 646 / 646 / 0 | 183 |
| Duplicate only, quiet 4 | 0.7216 | 0.7989 | 0.5264 | 0.7989 | 0.5760 | 536 / 0.3010 | 829 / 199 / 630 | 0 |
| Temporal + reject | 0.7886 | 0.8067 | 0.5813 | 0.8067 | 0.6417 | 374 / 0.2100 | 646 / 646 / 0 | 183 |
| Temporal + duplicate | 0.7216 | 0.7989 | 0.5264 | 0.7989 | 0.5760 | 536 / 0.3010 | 829 / 199 / 630 | 0 |
| All three selected components | 0.7886 | 0.8067 | 0.5813 | 0.8067 | 0.6417 | 374 / 0.2100 | 646 / 161 / 485 | 183 |

Selected-configuration per-class test results:

| Class | Precision | Recall | F1 |
|---|---:|---:|---:|
| Background | 0.9552 | 0.7900 | 0.8648 |
| Chainsaw | 0.4150 | 0.7695 | 0.5392 |
| Gunshot | 0.3737 | 0.8605 | 0.5211 |

Confusion matrix for the selected configuration, rows true and columns decision class `[background, chainsaw, gunshot]`:

```text
[[1407, 320, 54],
 [  60, 227,  8],
 [   6,   0, 37]]
```

Uncertain windows are mapped to background only for the displayed three-class confusion matrix; the replay files retain their explicit uncertain state. This convention must not be mistaken for a safe/background prediction.

## Operational and implementation cost

- Temporal confirmation: rejected for this dataset. If reconsidered, it requires per-class recent timestamps/counts and adds up to one additional 0.5-second window of confirmation delay for a 2-of-2 rule. It is incremental and needs no network or persistent storage.
- Reject state: selected. It adds one margin comparison and a state label; no additional model memory or external dependency. It can run incrementally on ESP32-S3. The threshold requires calibration/revalidation discipline.
- Duplicate suppression: selected experimentally. It adds two per-class active flags and last-candidate timestamps, plus alert log/state handling. It adds no model computation and can run incrementally on ESP32-S3. The quiet period does not establish real event separation without reliable event annotations.

RAM, flash arena, latency, power, and sustained hardware throughput were not measured. No hardware integration claim is made.

## Limitations

- The held-out test remains a window-level evaluation with 50% overlap; windows are correlated.
- Event-level precision/recall, false alerts per hour, event detection delay, and verified duplicate-event suppression are unavailable because reliable event intervals and recording-time denominators are not present for the complete replay input.
- `interval_start` metadata exists for some Rodopi interval-derived rows and was used only to prevent invalid local-index ordering. It is not treated as a universal event annotation.
- The validation and test source distributions differ; the selected margin rule improved the locked test result but should not be treated as deployment calibration.
- No audio was replayed through the ESP32-S3/INMP441 path.
- No production alert behavior, firmware, gateway, MQTT payload, or backend schema was changed.

## Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| Frozen baseline reproduced canonically | PASS | Test IDs/classes match Phase 1 exactly; metrics match |
| Temporal confirmation evaluated independently | PASS | Three validation candidates and locked comparison |
| Reject state evaluated independently | PASS | Three validation margins and locked comparison |
| Duplicate suppression evaluated independently | PASS | Three quiet periods and locked comparison |
| Combined configuration evaluated | PASS | Seven locked configurations reported |
| Validation used for selection | PASS | Margin selected only from validation; temporal rejected |
| Test locked until selection | PASS | Manifest records validation selection before locked replay |
| Recording ordering/boundaries handled | PASS | Chronological replay, interval-start correction, per-recording reset |
| Required state/edge tests | PASS | 17 deterministic unit tests passed |
| Window/event metrics distinguished | PASS | Event-level metrics explicitly unavailable |
| No unsupported event claims | PASS | Episode grouping called a replay proxy |
| Frozen artifacts unchanged | PASS | Before/after hashes in configuration manifest |
| Production/firmware untouched | PASS | Isolated experimental module only |
| Reproducible outputs | PASS | Script, configuration manifest, JSON/CSV logs |
| Deployment limitations documented | PASS | Hardware parity and resource measurements remain open |

Phase 3 stops here. Hardware testing and production integration require separate authorization.
