# Phase 4.12 — Existing Dataset Provenance Recovery and Admission Feasibility

Audit date: 2026-10-19 UTC

## Final decision

**BLOCKED_ON_UNRESOLVED_PROVENANCE_OR_LICENSE**

No existing source is qualified for admission. C3GD is the strongest provenance-controlled source, with 100 frozen source recordings, 4 collection events, 48 platform groups, and 15 microphones, but it is gunshot-only and has no verified background or chainsaw class. FSC22 is the highest-value forest-target candidate, but its per-file FreeSound rights, source grouping, and verified-background semantics remain unresolved.

No audio was downloaded. No training, inference, relabeling, augmentation, threshold tuning, or production-manifest modification occurred.

## Inventory and composition

Frozen manifest counts were derived from actual rows:

| Partition | Rows | Distinct source recording IDs |
|---|---:|---:|
| train | 28741 | 1328 |
| validation | 6999 | 284 |
| test | 2119 | 286 |
| external_test | 21059 | 77 |

The frozen train/validation/test sources are dominated by Rodopi background segments, while FSC22 supplies the principal mixed forest target/background taxonomy. C3GD supplies gunshot only. Full source/class/partition counts are in `class_source_coverage.json`; counts of processed windows are not treated as independent recordings.

## Provenance and licensing

- **C3GD:** local README and metadata expose event, file, platform, cartridge, microphone, and clip identifiers. The local license register and README record CC BY 4.0. This is the best provenance candidate, but it cannot supply all three classes.
- **FSC22:** local README claims CC0 for the dataset and notes a CC-BY-attributed subset, while the inventory is FreeSound-derived and the local license register marks the license as unresolved. Per-file attribution and original recording/session identity are not sufficient for automatic admission.
- **Rodopi:** local download metadata records CC BY 4.0 and TextGrid files, but the source is already in frozen data and exact duplicate groups occur within validation. It is not new independent data.
- **RFCx:** local metadata records CC BY-NC 4.0. It is relevant forest chainsaw data, but non-commercial restrictions and source/session/negative semantics remain unresolved.
- **Sensing the Forest:** local/previous audit evidence records CC0, but its soundscape material cannot be converted to verified background merely because a target event is absent.
- **ESC-50, Kenya, IOAI, and Vietnam:** remain restricted, provenance-uncertain, duplicate, or quarantined under earlier reports.

## Labels and negatives

C3GD labels are firearm caliber classes; mapping the entire source to project `gunshot` is defensible for event presence, but there is no chainsaw/background coverage. FSC22 has explicit `Chainsaw` and `Gunshot` source classes, but labels are clip-level and lack event intervals. Generic environmental, silence, noise, and unannotated soundscape material were not automatically mapped to `background`.

## Split integrity

The actual manifest check found zero intersections of `original_recording_id` across every pair of train, validation, test, and external-test partitions. The existing exact duplicate audit reports 5,008 duplicate rows in 2,504 groups and zero cross-split exact duplicate groups for the frozen train/validation/test partitions. This does not prove session-level or crop-level independence where source metadata is missing; those checks remain unresolved for most datasets.

## Candidate ranking

Mandatory gates were evaluated before research-value ranking. No candidate has all gates PASS. The best research candidates are C3GD for provenance-controlled gunshot analysis and FSC22 for forest target-class relevance, but neither qualifies for admission. Details and evidence references are in `admission_candidate_ranking.csv`.

## Validation

- Script executed successfully and generated all required artifacts.
- CSV schema/row-count and coverage reconciliation checks were run after generation.
- Nine protected model, frozen-manifest, and feature-cache hashes matched their recorded values.
- No downloads, model inference, training, threshold tuning, or production changes occurred.
- Existing Git modifications were preserved; no unrelated files were reverted.

## Recommended next action

Keep Phase 5 blocked. If progress is required, authorize a separate narrow admission-review phase for FSC22 and/or C3GD that resolves exact file-level rights, parent/session grouping, event semantics, and duplicate ancestry. Do not create a training manifest from this audit.
