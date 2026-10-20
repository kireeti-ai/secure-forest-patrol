# Phase 4.9 — Source Provenance Recovery

Audit timestamp: 2026-10-19T21:39:14.803152+00:00

## Executive summary

All 4,485 staged clips were reconciled without downloading new data. The final decision is **QUARANTINED_PROVENANCE**: 0 files are eligible for future training-only consideration, 2425 remain provenance-quarantined, and 2060 are duplicate/overlap dispositions.

### IOAI

The selected 120 files reconcile to 60 chainsaw and 60 gunshot labels. Exactly 90 are byte-exact matches to local FSC22 WAVs, with source paths recorded; 30 have no byte-exact FSC22 match. The 90 matches resolve to 90 local FSC22 parent recording IDs, but this maps duplication rather than the original IOAI ancestry. No IOAI parent/session/device metadata was found.

### Vietnam

The extracted archive reconciles to 4,365 WAVs: 729 `imagesvietnamunbalanced_clips`, 1,239 `imagesvietnam_belize_clips`, and 2,397 `testdatacombined_clips`. It contains 690 gunshot-labelled and 3,675 noise-labelled clips. The publisher explicitly describes the mixed branch as Vietnam plus Belize, so those 1,239 clips are not independent Vietnam evidence. A decoded-hash reconciliation found 733 repeated clip rows across the acquired Vietnam branches; these are marked overlap duplicates while representatives remain quarantined.

## Methods executed

* Inspected Phase 4.8 manifests, duplicate audit, license audit, archive, extracted paths, IOAI CSV metadata, and the prior Phase 4.7 report.
* Used the IOAI dataset card/API metadata and commit metadata; no original recording/session/device fields were present in the selected CSV schema.
* Inspected the Zenodo record/API, archive directory structure, filenames, and publication description. The record states Vietnam passive-monitoring clips plus Belize data, Raven Pro manual clip isolation, and three branches.
* Reused Phase 4.8 exact/decoded-match results and performed a decoded-hash grouping across the already-acquired Vietnam files. No expensive new local audio similarity scan was run.
* No model inference, training, threshold tuning, preprocessing change, download, curator contact, or source-file modification occurred.

## License and attribution

IOAI reports CC BY-SA 4.0 on its dataset card and attributes source material to IOAI/Kaggle. The card does not establish rights for each underlying recording. Vietnam reports CC BY 4.0 on Zenodo and cites Vu et al. plus the Belize Katsis et al. dataset. The archive-level license does not establish identical file-level rights for third-party Belize material. Both sources therefore remain blocked for file-level provenance/licensing admission.

## Label semantics

IOAI labels are clip-level CSV categories with no event timestamps or event-occupancy annotations. Vietnam gunshot clips are described as manually isolated/annotated using Raven Pro, but the extracted WAV archive contains no per-file event intervals. Vietnam `noise` is an archive folder label, not a verified negative control, and is not mapped to project `background`.

## Source grouping and duplicate ancestry

The only verified parent IDs are 90 local FSC22 parents used to trace exact IOAI duplication. Vietnam branch directories are provisional groups, not original recording identities. No verified Vietnam parent recordings or sessions were found. Different filenames/hashes were not treated as independence.

## Eligibility

| primary disposition | count |
|---|---:|
| ELIGIBLE_TRAIN_ONLY | 0 |
| QUARANTINED_PROVENANCE | 2425 |
| QUARANTINED_LICENSE | 0 |
| DUPLICATE_OR_OVERLAP | 2060 |
| QUARANTINED_LABEL | 0 |
| EXCLUDED_AUDIO_INVALID | 0 |

No verified negatives were found. No production or future-training manifest was created.

## Recommended next step

Do not admit these files. The single most useful next step is to obtain or locate source-level metadata for the 30 non-duplicate IOAI clips and the Vietnam-only representatives, including original recording/session/device identifiers and file-level rights. Until then, preserve the staging data and keep Phase 5 blocked.

## Reproduction

```bash
python3 ml/reports/phase4_9_source_provenance/run_provenance_recovery.py
```
