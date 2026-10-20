# Phase 4.10 — Source-First Dataset Discovery and Admission

Audit date: 2026-10-19 (UTC)

## Decision

**NO QUALIFIED SOURCE — NO DOWNLOAD.** No investigated source passed all three mandatory gates: usable license, defensible original-recording/source grouping, and labels suitable for the requested class decision. The acquisition manifest is intentionally header-only.

No external audio was downloaded in this phase. No model inference, training, threshold tuning, preprocessing change, frozen-split change, Phase 4.3 decision change, or firmware change was performed.

## Findings

| Source | Status | Main blocker |
|---|---|---|
| Kenya forest audio | DEFERRED_PROVENANCE | Phase 4.7 found zero verified parent/session/site groups and unresolved primary licensing. |
| IOAI26 HT1 Nightwatch | REJECTED_DUPLICATE_SOURCE | Phase 4.8/4.9 already acquired it; substantial exact overlap and no source groups. |
| Vietnam forest gunshot benchmark | REJECTED_DUPLICATE_SOURCE | Already acquired; ancestry overlap, repeated clips, and noise is not verified background. |
| Belize forest gunshots/background | ACCESS_UNAVAILABLE | Previously investigated; file-level access remains unavailable and no new access evidence was found. |
| Sensing the Forest natural soundscape | REJECTED_DUPLICATE_SOURCE | Already local and not a verified source of background intervals; do not auto-label negatives. |
| Rodopi forest soundscape | REJECTED_DUPLICATE_SOURCE | Already part of the frozen/local source inventory; reacquisition would create leakage risk. |
| Outdoor Gunfire | DEFERRED_LABELS | Firearm-range domain is weakly relevant to forest deployment and event timing/background eligibility is not established. |
| Illinois gunshot dataset | ACCESS_UNAVAILABLE | Official page was not accessible in the prior audit; no legitimate alternate access was identified. |
| FSD50K / Freesound Dataset 50K | DEFERRED_LICENSE | Useful provenance and labels, but mixed file-level rights, no verified background negatives, no session/device groups, and full acquisition is multi-GB without a demonstrated selective path. |
| ARCA23K / ARCA23K-FSD | DEFERRED_LABELS | Official record reports no manual verification and estimated 46.4% training-label error; it covers gunshot/gunfire but not an exact chainsaw class or verified background. |
| AudioSet | DEFERRED_LICENSE | Excellent timestamp/source-ID structure, but official release does not provide raw audio and source-platform rights/availability are unresolved; not a lawful selective audio acquisition path. |

### New candidates

**FSD50K** is the strongest research lead, not an acquisition approval. The official records describe 51,197 Freesound clips with Freesound IDs and human-labeled AudioSet-ontology classes. However, audio has mixed per-clip CC rights, source/session/device grouping is not available, the labels are clip-level rather than event timestamps, verified background negatives are absent, and the full archive is multi-gigabyte with no selective official file-download path demonstrated. It remains **DEFERRED_LICENSE**.

**ARCA23K/ARCA23K-FSD** has source URLs and an explicit gunshot/gunfire class, but the official record says ARCA23K was automatically created with no manual verification and estimates 46.4% of training examples are incorrectly labelled. It has no verified background class and no exact chainsaw class in the listed taxonomy. It remains **DEFERRED_LABELS**.

**AudioSet** has the best metadata structure: YouTube video IDs, start/end seconds, and multi-label human annotations. The official release provides CSV metadata and precomputed features, not raw source audio. Retrieving raw audio would depend on third-party platform availability and rights outside the release; therefore it is not a lawful qualified audio acquisition path. It remains **DEFERRED_LICENSE**.

Previously investigated sources were not redownloaded. Kenya, IOAI, Vietnam, Rodopi, Sensing the Forest, Belize, Illinois, and Outdoor Gunfire retain their Phase 4.7–4.9 dispositions; no automatic admission or relabeling was performed.

## Gate and ranking summary

The ranking rubric uses seven 0–3 criteria: licensing, recording-level provenance, label quality, environmental relevance, likely independent-recording coverage, accessibility/size, and overlap risk (higher is safer). Scores and evidence are in `candidate_ranking.csv`. No source reached `QUALIFIED_FOR_DOWNLOAD`.

## Data and leakage risks

No new audio means no new hashes or near-duplicate comparisons were possible. Existing Phase 4.9 evidence remains authoritative for the staged IOAI/Vietnam material: 90 IOAI files matched local FSC22, Vietnam includes a mixed Belize branch and internal repeats, and no staged file was eligible. Any future source must be grouped by original recording/session before splitting; adjacent windows must not be treated as independent recordings.

## Existing contract preserved

The frozen preprocessing contract remains 16 kHz mono, peak normalization to -3 dB, 1.0-second windows, 0.5-second hop, 40 mel bins, FFT 512, feature hop 160, power 2, and frozen feature mean/std. No new pipeline was proposed or executed.

## Validation

`run_source_first_discovery.py` recomputed all nine protected frozen hashes from `online_dataset_audit_checks.json`; `integrity_hashes.json` records the actual results. It also confirms zero downloads and zero model/training activity.

## Primary evidence

- [FSD50K/ARCA23K Zenodo record](https://zenodo.org/records/5117901)
- [Freesound dataset index](https://labs.freesound.org/datasets/)
- [AudioSet official download and license page](https://research.google.com/audioset/download.html)
- [Phase 4.9 provenance report](../phase4_9_source_provenance/SOURCE_PROVENANCE_REPORT.md)
- [Phase 4.8 acquisition report](../phase4_8_fasttrack_acquisition/ACQUISITION_REPORT.md)

## Remaining action

Keep all candidates quarantined. If the project wants to revisit FSD50K, first obtain an exact per-file permissive-license subset and a defensible source-group policy from its metadata; this is a new admission review, not a reason to download the full archive. Phase 5 remains blocked.
