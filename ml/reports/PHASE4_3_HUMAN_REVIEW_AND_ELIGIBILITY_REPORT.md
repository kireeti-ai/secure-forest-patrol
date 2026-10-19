# Phase 4.3 Human Review and Eligibility Report

Audit date: 2026-10-18  
Decision: **BLOCKED_BY_HUMAN_ACTION**

This phase prepared and validated the human-review workflow. No human listening occurred during this execution, so no acoustic labels or training eligibility were fabricated. No model training, threshold tuning, frozen split change, production-code change, firmware change, or Phase 4.2 overwrite was performed.

## A. Executive decision

The candidate dataset cannot proceed to Phase 5 review until a human reviewer completes the prepared queue and unresolved cases receive adjudication. The infrastructure and integrity checks are ready, but semantic label verification is not complete.

## B. Review execution

| Measure | Count |
|---|---:|
| Total candidates | 777 |
| Queued for review | 777 |
| First batch | 60 |
| First-batch background | 30 |
| First-batch chainsaw | 20 |
| First-batch gunshot | 10 |
| Actually reviewed by humans | 0 |
| Accepted | 0 |
| Relabel-required | 0 |
| Ambiguous | 0 |
| Excluded | 0 |
| Second-review-required | 0 |
| Remaining pending | 777 |

The first batch is source-balanced and uses distinct source recordings. The review queue and protocol support abstention, event boundaries, mixed-event notes, reviewer identity, timestamps, and resumable decisions. The local reviewer writes a separate decisions file and does not alter the candidate manifest.

## C. Class and source coverage

| Proposed class | Candidate rows | Distinct source recordings | Distinct parent groups | Training-eligible |
|---|---:|---:|---:|---:|
| Background | 722 | 722 | 722 | 0 |
| Chainsaw | 35 | 35 | 35 | 0 |
| Gunshot | 20 | 20 | 20 | 0 |

These are proposed-label counts, not verified acoustic counts. Raw rows are not treated as independent evidence of dataset quality.

## D. License status

| Status | Candidates |
|---|---:|
| Eligible with attribution, license-level only | 10 |
| Research-only | 330 |
| Quarantined | 437 |
| Human-verified legal-and-label eligible | 0 |

C3GD remains attribution-required; ESC-50 and RFCx remain research-only; FSC22 and Rodopi remain quarantined pending authoritative terms. A license-level status never overrides the separate human-label and provenance gates. Candidate IDs are listed in `phase4_3_diagnostics/license_audit.csv`.

## E. Dataset eligibility

Under the fail-closed policy, eligible candidates are:

- Background: 0
- Chainsaw: 0
- Gunshot: 0

All 777 candidates remain `PENDING_HUMAN_REVIEW`. A proposed metadata label is not a human-verified label, and `ACCEPTED` review status would still not automatically imply training eligibility.

## F. Label quality and adjudication

No label disagreements, confidence judgments, event boundaries, or ambiguity decisions exist yet because no human review occurred. The review protocol requires second review for proposed-label disagreement, low confidence, ambiguous impulses, mixed scenes, and uncertain boundaries. Background recordings do not require event boundaries under the documented policy; target recordings require boundaries when they are determinable.

## G. Duplicate and leakage assessment

- Frozen exact processed duplicates: 5,008 rows across 2,504 groups.
- Frozen cross-split exact-hash leakage: none observed.
- Candidate duplicate IDs: none.
- Candidate stored-hash duplicates: none.
- Candidate overlap with frozen validation/test sources: none.
- Parent/source IDs: preserved for future source-disjoint splitting.
- Near-duplicate acoustic similarity: unresolved; no fingerprint or embedding similarity was used as proof.

Processed-window duplicates are not 5,008 distinct original recordings. Frozen partitions were not modified.

## H. Integrity and testing

All deterministic checks passed for candidate IDs, manifest schema, path existence, SHA-256 consistency, WAV metadata, review-state validity, pending-review accounting, fail-closed license behavior, frozen evaluation exclusion, parent grouping, and candidate-manifest consistency. Before/after hashes for frozen models, v1 manifests, feature caches, Phase 4.1/4.2 manifests, and inspected production files are unchanged.

## I. Remaining blockers and next actions

| Blocker | Why it matters | Evidence required | Next action |
|---|---|---|---|
| Human acoustic review | Metadata cannot prove a class is audible | Reviewer decisions with IDs, timestamps, labels, confidence, and notes | Run the 60-recording batch locally using `review_tool.py` |
| Second review/adjudication | Ambiguous or disputed events can create label noise | Independent second decision and documented resolution | Escalate low-confidence, mixed, and impulse cases |
| FSC22/Rodopi licensing | Unverified terms prevent intended-use admission | Authoritative provider/license evidence | Obtain and archive source terms |
| Near-duplicate/session review | Similar recordings can inflate effective diversity | Source/session metadata or documented similarity review | Complete acoustic near-duplicate review before split design |
| Forest-domain coverage | Frozen v1 has no Sensing Forest sources | Provider-approved small subset with provenance and license | Request a targeted subset; do not download the full archive |

## J. Recommendation

Do not request Phase 5 training authorization yet. First complete human review and adjudication, resolve licensing, complete near-duplicate analysis, and preserve a source/parent-disjoint future split proposal. After those actions, issue a separate readiness review; this report itself does not authorize training.

## Artifacts

- `datasets/phase4_3_candidate/review_queue.csv`
- `datasets/phase4_3_candidate/review_decisions.csv`
- `datasets/phase4_3_candidate/manifest.csv`
- `datasets/phase4_3_candidate/review_protocol.md`
- `reports/phase4_3_diagnostics/reviewer_validation.md`
- `reports/phase4_3_diagnostics/reviewer_test_results.json`
- `reports/phase4_3_diagnostics/reviewer_usage.md`
- `reports/phase4_3_diagnostics/review_batch_1.md`
- `reports/phase4_3_diagnostics/review_progress.json`
- `reports/phase4_3_diagnostics/license_audit.csv`
- `reports/phase4_3_diagnostics/provenance_exceptions.csv`
- `reports/phase4_3_diagnostics/eligibility_audit.csv`
- `reports/phase4_3_diagnostics/class_source_coverage.json`
- `reports/phase4_3_diagnostics/duplicate_audit.csv`
- `reports/phase4_3_diagnostics/parent_source_audit.csv`
- `reports/phase4_3_diagnostics/integrity_hashes.json`
- `reports/phase4_3_diagnostics/test_results.md`

