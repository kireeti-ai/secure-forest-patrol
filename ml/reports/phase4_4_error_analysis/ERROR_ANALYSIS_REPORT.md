# Phase 4.4 — Validation Error Analysis and Next-Step Decision

Status: **Diagnostic complete — no training or acquisition started**  
Audit date: 2026-10-19

## Decision

**TARGETED_REVIEW_RECOMMENDED**

The frozen validation metrics show a specific class-recognition problem that justifies a small, bounded review of the already-defined Phase 4.3 first batch. They do not justify downloading an online dataset or manually reviewing all 777 candidates. Phase 5 remains blocked.

The recommended first action is to review the existing `BATCH_1` only: 30 background, 20 chainsaw, and 10 gunshot candidates. This is a recommendation; this audit did not mark candidates as reviewed, change labels, or change training eligibility.

## Repository and artifact audit

The frozen model metadata is `models/final/final_metadata.json`. It records the three classes in `[background, chainsaw, gunshot]` order, input shape `[40, 101, 1]`, and the frozen feature mean/std `-36.31850051879883` / `21.19044303894043`.

Existing prediction and evaluation artifacts were checked before analysis:

- Aggregate validation metrics and confusion matrix: `models/final/final_metadata.json`.
- Frozen INT8 test prediction table: `reports/phase1_diagnostics/predictions.csv`.
- Test false-positive, false-negative, source, dataset, and confidence summaries: `reports/phase1_diagnostics/`.
- Phase 1 written analysis: `reports/PHASE1_FAILURE_AUDIT.md`.
- Phase 2 contract and audit: `reports/ESP32_PREPROCESSING_CONTRACT.md` and `reports/PHASE2_PREPROCESSING_AUDIT.md`.
- Phase 3 temporal-confirmation analysis: `reports/PHASE3_TEMPORAL_ALERT_AUDIT.md` and `reports/PHASE3_DECISION.md`.
- Phase 4.3 eligibility and review state: `reports/PHASE4_3_HUMAN_REVIEW_AND_ELIGIBILITY_REPORT.md`, `datasets/phase4_3_candidate/`, and `reports/phase4_3_diagnostics/`.
- Online acquisition audit: `reports/online_dataset_alternative_audit/ONLINE_DATASET_ALTERNATIVE_AUDIT.md` and `online_dataset_audit_checks.json`.

No validation per-sample prediction CSV, validation confidence table, or validation source-level error table was found. The validation conclusions below therefore come from the frozen aggregate metadata and are not regenerated predictions.

The current decisions file was read as part of the audit. It contains 777 rows: 776 `PENDING` and one `ACCEPTED`. This differs from the older Phase 4.3 summary, which reports zero completed reviews. The explicit `ACCEPTED` row was preserved; this audit does not adjudicate whether it was entered manually. No decision file was rewritten.

## Validation results

Rows are true classes and columns are predicted classes in `[background, chainsaw, gunshot]` order:

```text
[[1811, 143, 46],
 [ 225, 217,  2],
 [  10,   7, 37]]
```

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| background | 0.8851 | 0.9055 | 0.8952 | 2,000 |
| chainsaw | 0.5913 | 0.4887 | 0.5351 | 444 |
| gunshot | 0.4353 | 0.6852 | 0.5324 | 54 |

Overall validation accuracy is **0.8267**, balanced accuracy **0.6931**, macro precision **0.6372**, macro recall **0.6931**, and macro-F1 **0.6542** over 2,498 evaluated samples.

The principal validation errors are:

- Background → chainsaw: **143**.
- Background → gunshot: **46**.
- Chainsaw → background: **225**.
- Chainsaw → gunshot: **2**.
- Gunshot → background: **10**.
- Gunshot → chainsaw: **7**.

The low chainsaw recall is the clearest validation deficiency. Gunshot recall is better but remains based on only 54 validation examples, so its estimate is comparatively uncertain. Background precision is also limited by event-like false positives, but the aggregate validation artifact does not identify their recordings or acoustic content.

## Source concentration and confidence

Validation source-level concentration cannot be established because no validation prediction table with `original_recording_id` was found. Validation confidence distributions also cannot be established because validation scores were not preserved as an artifact.

The Phase 1 test diagnostic contains useful context but was not used to select candidate IDs, tune thresholds, or change the frozen evaluation. It found 536 background false-positive windows and 45 target false-negative windows, with errors concentrated by source recording and with some high-confidence false positives. Those observations support the *categories* already represented in the Phase 4.3 queue—hard backgrounds and low-energy/partial target events—but do not prove an acoustic cause. No audio was listened to in this audit; filename, source label, waveform, or spectrogram does not establish label correctness.

Because windows overlap by 50%, window errors are correlated. A recording-level review is more informative than treating every window as an independent example.

## Data value assessment

Additional labelled data could address two specific uncertainties:

1. **Chainsaw event validity and occupancy.** The validation chainsaw recall is 0.4887, with 225 chainsaw windows predicted as background. A small review can determine whether candidate chainsaw segments actually contain an audible event, are partial/low-energy events, or have boundary/label ambiguity.
2. **Hard-background discrimination.** Validation has 143 background→chainsaw and 46 background→gunshot errors. A small review of the existing background candidates can test whether the candidate metadata represents genuinely event-free background and whether the dominant issue is label ambiguity, source/domain coverage, or model decision behaviour.
3. **Gunshot uncertainty.** Gunshot recall is 0.6852 on only 54 validation examples, with 10 misses to background and 7 confused with chainsaw. Reviewing 10 existing gunshot candidates is useful for checking event occupancy and transient/partial-event ambiguity, but does not support broad acquisition yet.

The generated `candidate_review_priority.csv` provides a diagnostic ordering of all 777 existing candidates. It preserves the queue metadata needed for provenance and license review and records that the ordering is diagnostic only. It does not mark a candidate reviewed or eligible. The first 60 are the pre-existing Phase 4.3 `BATCH_1`, not a new selection from the frozen test set.

## What cannot be established

- Validation error concentration by recording, source dataset, device, or parent group.
- Validation confidence separation between correct and incorrect predictions.
- Whether any individual candidate is correctly labelled without human review.
- Whether a threshold, reject rule, or temporal rule would improve the validation operating point; no threshold was tuned here.
- Whether the errors arise from acoustic similarity, event boundaries, label noise, domain shift, preprocessing mismatch, or quantization behaviour.
- Training benefit or eligibility of any candidate. No candidate is newly eligible as a result of this audit.

## Integrity and constraints

The audit performed no model inference, external download, training, fine-tuning, threshold change, split change, preprocessing change, firmware change, or production-code change. Frozen model, split, cache, and manifest hashes were recorded in `error_analysis_metrics.json`. The online acquisition audit remains **NO-GO**.

The next step is limited human review of the existing Phase 4.3 first batch using the repaired reviewer. After those decisions exist, reassess label quality, event occupancy, license/provenance restrictions, and source-group eligibility. If the batch does not clarify the failure pattern, investigate model score/quantization and temporal decision behaviour diagnostically on validation data before considering any training authorization.
