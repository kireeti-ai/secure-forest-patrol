# Phase 4 — Targeted Dataset Improvement and Data Quality Audit

Status: **COMPLETE — investigation and isolated candidate-manifest preparation only**  
Audit date: 2026-10-18

No model retraining, fine-tuning, recalibration, threshold selection, frozen split change, frozen cache regeneration, firmware change, gateway change, backend change, or production alert change was performed.

## Executive summary

The Phase 1 error counts were independently reproduced from the diagnostic CSVs:

- 536 background false-positive windows across 121 source recordings.
- 448 background→chainsaw windows and 88 background→gunshot windows.
- 45 target false-negative windows across 14 source recordings: 39 chainsaw and 6 gunshot.
- The errors were grouped into a 135-source failure inventory; these are source-level clusters, not independent examples.

The highest-value improvement is targeted source-level coverage, not indiscriminate window multiplication. Existing training data contains relevant hard-background categories and low-energy target sources, so no external data was acquired. The isolated candidate manifest contains 777 source-level training candidates with provenance and exact hashes. It is not approved for training: 340 are research-only candidates and 437 remain quarantined for license, label, or review reasons.

## Recording-level failure inventory

The machine-readable inventory is `phase4_diagnostics/failure_source_inventory.csv`. It preserves dataset, split, original label, error counts, observed test coverage, and available interval identifiers without inferring missing acoustic metadata.

The main source-domain pattern is:

| Dataset | Background windows | FP windows | FP rate | Chainsaw FN | Gunshot FN |
|---|---:|---:|---:|---:|---:|
| RFCx FrugalAI | 193 | 126 | 0.6528 | 11 | 0 |
| ESC-50 HF | 642 | 188 | 0.2928 | 2 | 0 |
| FSC22 | 946 | 222 | 0.2347 | 26 | 6 |
| C3GD | 0 | 0 | unavailable | 0 | 0 |

The largest repeated background clusters include all-window-failure recordings in ESC-50, FSC22, and RFCx. The largest target clusters remain the Phase 1 examples: `fsc22_11_11166`, `fsc22_11_11164`, `rfcx_rfcx_train_00154_chainsaw`, `fsc22_11_11101`, and `rfcx_rfcx_train_00260_chainsaw`. The single gunshot false-negative source is `fsc22_15_11563`.

These clusters justify source-level review and collection. They do not prove mislabeling, acoustic identity, or event-boundary error.

## Hard-background opportunities

`hard_negative_candidates.csv` contains 843 rows: 121 frozen-test review-only candidates and 722 training-source coverage candidates. Categories are preserved as source labels or mapped source categories, not asserted acoustic diagnoses.

The existing training data contains bird, insect, wind, animal, rain, storm, water, engine-like, human-activity, and transient-environment examples across FSC22 and ESC-50, plus background source coverage in other datasets. The most valuable additions are source-disjoint representatives from those categories, especially in RFCx/ESC-50 deployment-like domains. FSC22 candidates remain license-review gated.

The Phase 1 false positives themselves are marked `exclude_from_candidate_training` because they come from the frozen test split. They should be listened to and independently annotated before any future use.

## Low-energy and partial target opportunities

`target_event_candidates.csv` contains 69 rows: 14 frozen-test failure-source review candidates and 55 training-source low-energy coverage candidates. The Phase 1 evidence supports low-energy/partial-event hypotheses for chainsaw and gunshot misses, but no causal explanation is assigned where event timestamps or SNR are unavailable.

Training candidates use one low-RMS representative per source where readable. They do not expand a single recording into many overlapping “independent” examples. C3GD gunshot candidates have a recorded CC BY 4.0 source; RFCx and ESC-50 candidates retain non-commercial restrictions; Rodopi candidates remain license/label review gated.

## Label and provenance audit

`provenance_and_label_audit.csv` records source path, SHA-256, audio readability, sample rate, channel count, duration, RMS, peak, clipping flag, label provenance, split/leakage result, and license status for all candidate/review rows.

An exact SHA-256 scan over the frozen train/validation/test processed files found 5,008 rows in 2,504 exact-duplicate hash groups. These duplicates are within validation and correspond to paired Rodopi source IDs; no exact duplicate hash crossed frozen train/validation/test split boundaries. The finding still reduces effective validation diversity and should be considered in future source-level evaluation. Candidate-level hashes are unique after isolation/deduplication. Near-duplicate audio fingerprinting was not claimed as complete and remains a review item.

No candidate was silently relabeled. Source categories are retained as provenance clues, and uncertain material is quarantined.

## Acquisition recommendation

No new data is necessary before review. The present data already supplies candidate background strata and low-energy target sources. External acquisition should wait until license review, manual audio review, and a gap analysis show that a required domain is absent. The acquisition plan is [data_acquisition_plan.md](./phase4_diagnostics/data_acquisition_plan.md).

## Candidate dataset summary

The isolated candidate manifest is [datasets/phase4_candidate/manifest.csv](../datasets/phase4_candidate/manifest.csv). It contains only rows from the frozen training partition, proposed future split groups, source paths, content hashes, license status, and review gates. Frozen validation/test failure evidence is kept only in diagnostics, not in the candidate training manifest.

The candidate dataset is not approved for Phase 5. The formal gates are in [PHASE4_CANDIDATE_DATASET_ACCEPTANCE.md](./PHASE4_CANDIDATE_DATASET_ACCEPTANCE.md).

## Acceptance status

| Criterion | Status |
|---|---|
| Phase 1 patterns verified | PASS |
| Recording inventory created | PASS |
| Hard-negative candidates justified | PASS/PARTIAL — source labels require review |
| Low-energy/partial candidates investigated | PARTIAL — timing/SNR gaps remain |
| Label/provenance audit completed | PASS/PARTIAL — manual review remains |
| Exact duplicates handled | PASS for candidate set; broader v1 duplicates documented |
| Near-duplicates handled | PARTIAL |
| Source leakage checked | PASS for candidate frozen split membership |
| License/attribution documented | PARTIAL |
| Candidate isolated from frozen baseline | PASS |
| Uncertain labels quarantined | PASS |
| Candidate acceptance criteria established | PASS |
| Frozen artifacts unchanged | PASS |
| No training or threshold tuning | PASS |
| Reproducible/traceable candidate data | PASS/PARTIAL — external license and manual review gates remain |
| Remaining blockers documented | PASS |

Phase 4 stops here. Phase 5 has not started.
