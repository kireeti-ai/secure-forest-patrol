# Phase 4 Candidate Dataset Acceptance Criteria

This document defines review gates before any separate Phase 5 training authorization. The candidate manifest is not yet approved for training.

## Mandatory criteria

| Criterion | Status | Evidence / remaining action |
|---|---|---|
| Candidate sources are traceable to stable IDs and paths | PASS | `manifest.csv` includes source, parent, path, and SHA-256 |
| No candidate source overlaps frozen validation/test | PASS | Candidate manifest rows are from frozen `train` only; source split checked |
| Frozen manifests and caches remain unchanged | PASS | Phase 4 summary hashes recorded; no writes to v1 artifacts |
| Candidate content hashes are unique | PASS | 777 candidate rows, 777 unique hashes after candidate-level deduplication |
| Candidate audio is readable and compatible | PASS | Candidate provenance audit found readable processed audio; 16-kHz/mono contract checked |
| Labels have independent verification or explicit quarantine | PARTIAL | Source labels are preserved; manual acoustic review is still required |
| License and attribution permit intended use | PARTIAL | 340 research-only rows have recorded restrictions; 437 rows remain quarantined for license/label review |
| Parent recordings/crops cannot cross future splits | PARTIAL | Proposed future group is recorded; a future split must enforce parent-level grouping |
| Event occupancy/boundaries are supported | PARTIAL | Many candidates lack reliable event intervals; do not invent frame labels |
| Near-duplicate review is complete | PARTIAL | Exact hashes were checked; candidate near-duplicate fingerprint review remains |

## Recommended coverage targets

These are review targets, not claims that the current dataset meets them:

- At least 30 distinct hard-background source recordings across at least three source domains, with at least 10 each from bird/insect/wind-or-mechanical/transient strata where available.
- At least 20 distinct chainsaw source recordings spanning continuous, intermittent, low-energy, and partial-operation conditions.
- At least 20 distinct gunshot source recordings spanning source/device conditions and boundary/decay cases.
- At least five independently reviewed recordings per priority subtype before using that subtype as a label-quality correction set.
- Zero source, parent-recording, or exact-content overlap across any future train/validation/test proposal.

The targets are based on the Phase 1 source clusters, the current training source counts, and the need to avoid treating 50%-overlapping windows as independent examples. They must be revised only with an explicit source-availability justification.

## Known gaps

- Phase 1 hard-negative evidence is concentrated in frozen test recordings, so those examples are review evidence and cannot become candidate training data.
- FSC22 and Rodopi license status is unresolved.
- Source labels do not prove that every segment contains the named event.
- Full event-level timing and SNR metadata are incomplete.
- Candidate near-duplicate review beyond exact SHA-256 matching is not complete.
- No new field recordings from the target ESP32-S3/INMP441 path are included.

The candidate dataset is **not ready for Phase 5 authorization** until the partial criteria are resolved or explicitly accepted by review.
