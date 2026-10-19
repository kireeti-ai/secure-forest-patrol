# Phase 4.2 Dataset Remediation Report

Audit date: 2026-10-18  
Decision: **NOT_READY_FOR_PHASE_5**

This phase was dataset remediation and validation only. No model training, fine-tuning, threshold tuning, frozen split modification, production-code modification, firmware modification, or alert-logic change was performed.

## A. Executive decision

The candidate dataset is not ready for Phase 5. The repository contains a complete source-balanced review queue and isolated candidate index, but no candidate has received human acoustic label verification. FSC22 and Rodopi licensing remains unresolved, near-duplicate review is incomplete, and no targeted forest-domain audio subset was acquired.

## B. Baseline verification

Counts were recomputed from `datasets/phase4_1_candidate/manifest.csv`, not assumed from the previous report:

| Measure | Result |
|---|---:|
| Candidate rows | 777 |
| Background | 722 |
| Chainsaw | 35 |
| Gunshot | 20 |
| Distinct source recordings | 777 |
| Distinct parent-source groups | 777 |
| Research-only candidates | 330 |
| Quarantined-license candidates | 437 |
| Missing candidate files | 0 |
| Duplicate candidate IDs | 0 |
| Duplicate candidate content hashes | 0 |
| Candidate overlap with frozen validation/test source IDs | 0 |

The mission references `PHASE4_DATASET_CANDIDATE_ACCEPTANCE.md`; the repository contains `PHASE4_CANDIDATE_DATASET_ACCEPTANCE.md`. This filename discrepancy was recorded and did not affect the counts. Frozen processed-window duplication remains 5,008 rows across 2,504 exact-hash groups, with no cross-split exact-hash leakage.

## C. Human-review status

| Status | Count |
|---|---:|
| Queued for review | 777 |
| Actually reviewed by humans | 0 |
| Accepted | 0 |
| Relabelled | 0 |
| Ambiguous | 0 |
| Excluded by human review | 0 |
| Still pending | 777 |

The queue prioritizes target false-negative sources as P1, hard-background sources as P2, and remaining candidates as P3. It is source-balanced and excludes frozen validation/test failures from candidate training. No label was accepted from metadata or model predictions.

## D. License resolution

- C3GD: `ELIGIBLE_WITH_ATTRIBUTION`, reported CC BY 4.0; attribution is required and underlying recording terms remain traceable.
- ESC-50: `RESEARCH_ONLY`, reported CC BY-NC 3.0; individual underlying recording terms may also apply.
- RFCx FrugalAI: `RESEARCH_ONLY`, reported CC BY-NC 4.0.
- FSC22: `QUARANTINED`; authoritative license and intended-use terms were not verified.
- Rodopi: `QUARANTINED`; authoritative recording-level terms were not verified.

Candidate IDs affected by unresolved licensing are listed in `phase4_2_diagnostics/license_audit.csv`. Research permission is not treated as permission for commercial deployment.

## E. Acquisition results

No audio was acquired: 0 files and 0 bytes. Sensing the Forest was investigated because frozen v1 has zero sources from that forest domain, but the official record exposes an approximately 24.4 GB archive without a justified provider-supported file-level subset. The full archive was not downloaded merely to increase dataset size.

The next action is to request a provider-approved subset of at least 20 distinct forest recordings with stable IDs, hashes, metadata, and intended-use confirmation. No acquisition manifest row was fabricated.

## F. Duplicate and leakage findings

- Confirmed frozen exact processed-hash groups: 2,504, covering 5,008 processed rows.
- Confirmed cross-split exact-hash leakage: none observed.
- Candidate exact-hash duplicates: none.
- Candidate source overlap with frozen validation/test: none.
- Parent/source grouping: parent IDs and future split groups are preserved; future splitting must group by parent/session.
- Suspected near duplicates: unresolved; no acoustic fingerprint or embedding similarity was used as proof of duplication.

The frozen duplicate rows are documented only. Frozen data was not deleted, moved, or rewritten.

## G. Candidate dataset summary

The isolated Phase 4.2 manifest contains 777 rows, but the effective training-eligible counts are:

| Class | Candidate rows | Training-eligible now | Pending human review |
|---|---:|---:|---:|
| Background | 722 | 0 | 722 |
| Chainsaw | 35 | 0 | 35 |
| Gunshot | 20 | 0 | 20 |

The class counts and source diversity are sufficient to organize a future review experiment, but not to authorize training. Raw row counts do not establish acoustic correctness, forest-domain coverage, or legal usability. Human review, licensing, parent-level split protection, and near-duplicate review must be completed first.

## H. Integrity verification

All deterministic checks passed for schema, unique IDs, file existence, hash fields, legal-status completeness, review-status completeness, provenance, eligibility consistency, parent grouping, and acquisition-manifest consistency. The before/after hashes in `phase4_2_diagnostics/integrity_hashes.json` are unchanged for the frozen model files, v1 manifests, feature caches, Phase 4.1 manifest, and sampled production files inspected.

The machine-readable results are in `phase4_2_diagnostics/integrity_check_results.json`. This passing integrity result does not prove that any candidate label is acoustically correct.

## Artifacts

- `datasets/phase4_2_candidate/manifest.csv`
- `datasets/phase4_2_candidate/review_queue.csv`
- `datasets/phase4_2_candidate/review_protocol.md`
- `datasets/phase4_2_candidate/review_schema.json`
- `reports/phase4_2_diagnostics/review_tool.py` (optional resumable macOS `afplay` reviewer; writes separate `review_results.csv`)
- `datasets/phase4_2_candidate/acquisition_manifest.csv`
- `reports/phase4_2_diagnostics/baseline_verification.md`
- `reports/phase4_2_diagnostics/label_review_readiness.md`
- `reports/phase4_2_diagnostics/license_audit.csv`
- `reports/phase4_2_diagnostics/license_resolution.md`
- `reports/phase4_2_diagnostics/attribution_requirements.md`
- `reports/phase4_2_diagnostics/acquisition_log.csv`
- `reports/phase4_2_diagnostics/forest_domain_gap_analysis.md`
- `reports/phase4_2_diagnostics/duplicate_audit.csv`
- `reports/phase4_2_diagnostics/parent_source_audit.csv`
- `reports/phase4_2_diagnostics/leakage_analysis.md`
- `reports/phase4_2_diagnostics/future_split_proposal.md`
- `reports/phase4_2_diagnostics/integrity_hashes.json`
- `reports/phase4_2_diagnostics/phase4_2_summary.json`

