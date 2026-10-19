# Phase 4.2 Baseline Verification

Audit date: 2026-10-18. Counts were recomputed from `datasets/phase4_1_candidate/manifest.csv`; no Phase 4.1 artifact was overwritten.

| Measure | Result |
|---|---:|
| Candidate rows | 777 |
| Background | 722 |
| Chainsaw | 35 |
| Gunshot | 20 |
| Unique source recordings | 777 |
| Unique parent-source IDs | 777 |
| Research-only candidates | 330 |
| Quarantined-license candidates | 437 |
| Pending label review | 777 |
| Missing audio paths | 0 |
| Duplicate candidate IDs | 0 |
| Duplicate content-hash rows | 0 |
| Candidate overlap with frozen validation/test source IDs | 0 |
| Frozen exact-duplicate rows | 5,008 |
| Frozen exact-hash groups | 2,504 |

The mission references `PHASE4_DATASET_CANDIDATE_ACCEPTANCE.md`; the repository filename is `PHASE4_CANDIDATE_DATASET_ACCEPTANCE.md`. The expected and actual candidate counts match. Frozen duplicate counts describe processed-window identity and are not evidence that 5,008 independent original recordings exist.
