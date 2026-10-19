# Phase 4.1 Candidate Dataset Acceptance

Audit date: 2026-10-18  
Decision: **NOT READY FOR PHASE 5 TRAINING**

## Summary

Phase 4.1 produced an isolated candidate manifest with 777 rows from 777 source recordings: 722 background, 35 chainsaw, and 20 gunshot. Training eligibility is **0**. There are 330 research-only-license rows and 437 rows quarantined for unresolved license review; all 777 rows remain quarantined for human label review.

No new audio was acquired. A CC0 forest source was investigated, but its official record exposes a 24.4 GB archive without a justified small file-level subset. The acquisition plan records the provider-approved subset needed to close that domain gap.

## Acceptance gates

| Gate | Status | Evidence / remaining action |
|---|---|---|
| Phase 1 failure findings verified | PASS | Hard-negative and target-FN source patterns carried into the gap analysis |
| Distinct source coverage analyzed | PASS | Source-level counts and priority gaps are recorded in `data_gap_summary.json` |
| Targeted acquisition investigated | PASS | Acquisition log and plan record the investigated-but-not-acquired forest source |
| Suitable audio acquired | NOT MET | No new audio acquired; targeted provider-approved subset remains outstanding |
| License audit complete | PARTIAL | C3GD/ESC-50/RFCx dispositions recorded; FSC22/Rodopi remain unresolved |
| Independent label verification complete | NOT MET | All candidate rows are `pending_manual_review`; no human audio review was performed |
| Event occupancy/boundaries verified | NOT MET | Partial/low-energy target timing remains unresolved |
| Exact duplicate/leakage audit | PASS | 5,008 frozen rows in 2,504 exact-hash groups documented; no cross-split hash leakage observed |
| Near-duplicate audit | PARTIAL | Exact hashes checked; acoustic/near-duplicate review remains required |
| Parent/source split controls | PARTIAL | Future split groups are preserved; a future split must enforce parent-level grouping |
| Isolated candidate manifest | PASS | `ml/datasets/phase4_1_candidate/manifest.csv` created; frozen artifacts untouched |
| Frozen artifacts unchanged | PASS | Phase 4.1 before/after hashes are equal |
| Training or threshold tuning performed | PASS | Neither was performed |

## Required actions before reconsideration

1. Manually review a source-balanced subset of hard negatives and low-energy/partial targets, recording reviewer, event audibility, interval, mixed-scene status, and final label.
2. Resolve FSC22/Rodopi license terms and confirm intended use for any retained data.
3. Complete near-duplicate and parent-recording leakage review, then construct a source/parent-disjoint future split.
4. Acquire and review a small provider-approved forest-domain subset if the domain-coverage requirement remains in scope.
5. Issue a separate Phase 5 authorization only after the above gates pass and the frozen test protocol is preserved.

This report does not authorize training, relabeling, threshold changes, firmware changes, or production alert changes.
