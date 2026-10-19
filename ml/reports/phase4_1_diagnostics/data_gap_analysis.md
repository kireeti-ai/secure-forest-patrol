# Phase 4.1 Data-Gap Analysis

Audit date: 2026-10-18  
Status: diagnostic and readiness review only. No training, threshold tuning, label mutation, split mutation, or production change was performed.

## Findings

The frozen training set contains 1,328 distinct source recordings: 1,053 background, 190 chainsaw, and 90 gunshot sources. Phase 1 identified 536 background false-positive windows across 121 recordings and 45 target false-negative windows across 14 recordings. The candidate review therefore prioritizes source-level hard negatives and low-energy or partial target recordings rather than adding overlapping windows indiscriminately.

The isolated Phase 4.1 candidate contains 777 rows from 777 source IDs:

| Original label | Candidate rows |
|---|---:|
| Background | 722 |
| Chainsaw | 35 |
| Gunshot | 20 |

These counts are provenance and manifest categories, not independently verified acoustic labels. All rows remain quarantined pending human review.

## Priority gaps

1. **Authentic forest background domain:** zero `sensing_forest` sources are present in frozen v1. A targeted CC0 subset would be useful, but the authoritative record exposes a 24.4 GB archive and no justified small file-level subset was acquired in this phase.
2. **Independently verified hard negatives:** 722 candidate background sources are available from existing datasets, but none has received independent human acoustic verification in this phase. The minimum review target is 30 source recordings across at least three domains, with five reviewed per priority subtype where available.
3. **Low-energy/partial target boundaries:** 35 chainsaw and 20 gunshot candidate sources are identified, but event occupancy, boundaries, and partial-event status remain unresolved. The minimum review target is 20 chainsaw and 20 gunshot source recordings with independently reviewed occupancy/boundaries.

The subtype counts in the machine-readable summary are source labels or manifest categories only. They must not be interpreted as verified acoustic subtypes. Device metadata is also incomplete; the audit does not support a microphone-specific causal conclusion.

## Decision

Existing data is sufficient to begin a manual review workflow, but not sufficient to authorize Phase 5 training. Human review, licensing resolution for FSC22/Rodopi, parent-level split enforcement, and near-duplicate review remain gates. New acquisition is secondary to those gates.
