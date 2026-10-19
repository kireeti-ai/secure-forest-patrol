# Phase 4.7 — Kenya Dataset Provenance and Eligibility Resolution

Audit timestamp: 2026-10-18T19:38:04.488187+00:00

## Executive summary

The 175-file Kenya staging subset is intact and auditable, but no file is admitted for training. The dataset-level CC BY 4.0 record is authoritative for staging, while file-level parent/session/site/device lineage, event timestamps, and independent source identity remain unverified. The evidence-backed decision is **QUARANTINED_PENDING_LICENSE**.

The subset contains 129 publisher-labelled chainsaw clips and 46 publisher-labelled control clips. Controls retain their publisher labels; they are not asserted to be universal background negatives.

## Methods executed

* Recomputed byte SHA-256, decoded canonical PCM16 SHA-256, soundfile metadata, duration, and sample counts for all 175 extracted WAVs.
* Read the staged publisher workbook and datasheet; no event timestamps were fabricated.
* Preserved publisher filename prefixes as provisional groups only. `ZOOM0086` is not treated as a verified parent recording.
* Retained Phase 4.6 exact/full-file duplicate evidence.
* Searched all 15,103 local raw WAV paths with a deterministic 64-bit spectral-frame crop screen. A score of 0.98 was pre-registered as a plausible-match threshold; the maximum observed score was 0.918352, so 0 candidates were plausible matches. The screen is conservative and a negative result does not prove absence of crop overlap.
* No model inference, training, threshold tuning, preprocessing change, split change, download, or human review was performed.

## Findings

### Archive and file integrity

Archive: `ml/datasets/phase4_5_acquisition/kenya_original/Kenya-Forest-Sounds-Dataset-v1.0.1.zip`; size `716622014` bytes; SHA-256 `2e270bf4918885f8f5fe35e204f9b1ccf2cae14ecff5623fe272be1ec7a5feae`. All 175 selected extracted files were readable, 16 kHz mono PCM16, and accounted for exactly once.

### Provenance and source independence

The workbook supplies publisher labels but not verified per-file parent recording IDs, sessions, sites, or devices. The datasheet reports three forests/collection periods and Zoom H2n at dataset level, but that does not establish those fields for any particular file. There are 33 provisional filename-prefix groups. They are useful for review organization only; they must not define future split independence.

### Licensing

Zenodo reports CC BY 4.0 and the local workbook/datasheet identify the publisher and attribution context. This verifies dataset-level staging terms. It does not separately establish per-file exceptions or a file-level attribution record, so the files are primarily quarantined pending file-level license confirmation; all 175 also have a provenance blocker.

### Duplicate and crop overlap

The prior Phase 4.6 exact-hash audit found no exact matches among bounded local artifacts. This Phase 4.7 crop screen searched every local raw WAV. The result counts are in `class_source_coverage.json` and candidate-level results are in `duplicate_and_overlap_audit.csv`. Any possible match would still require manual verification; no negative result is a proof of non-overlap.

## Eligibility summary

| disposition | count |
|---|---:|
| eligible training-only | 0 |
| quarantined pending licensing (primary) | 175 |
| files also blocked by provenance | 175 |
| excluded | 0 |

Verified parent recordings: 0. Verified sessions: 0. Possible/confirmed overlap candidates: 0.

## Validation executed

* Candidate accounting: PASS — 175 unique candidates, one primary disposition each, matching all 175 staged files and metadata rows.
* Audio readability/contract check: PASS — 175/175 readable, 16 kHz mono; no crop-screen decode failures across 15,103 local raw WAVs.
* Archive and audit-artifact hashes: PASS — archive SHA-256 and every generated artifact hash in `integrity_hashes.json` recomputed successfully.
* Protected hash check: PASS — 9 model/cache/frozen-manifest hashes match the prior frozen reference.
* `unzip -t` archive integrity: PASS in Phase 4.6; current archive SHA/size still match.

## Decision and next step

**QUARANTINED_PENDING_LICENSE.** The subset has research value for a later, controlled human-review and provenance-resolution exercise, especially for chainsaw and Kenyan environmental control coverage. It is not eligible for a training manifest. The next step is to obtain curator confirmation mapping files to independent source/session groups and confirming file-level license applicability/attribution, then manually review a small, source-balanced sample before any eligibility decision.

## Reproduction

```bash
python3 ml/reports/phase4_7_provenance_resolution/run_provenance_audit.py
```

Outputs are listed in this directory. The script writes only report artifacts; source audio and protected project artifacts are read-only inputs.
