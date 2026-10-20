# Phase 4.8 — Fast-Track Alternative Dataset Acquisition

Audit timestamp: 2026-10-19T21:25:42.204365+00:00

## Executive summary

Two sources were acquired into isolated staging: 120 selectively downloaded IOAI WAVs and the 396,067,990-byte Vietnam benchmark clips archive, extracted to 4,365 WAV clips. No file is eligible for training yet. The final decision is **ACQUIRED_STAGING_ONLY_NO_ELIGIBLE_FILES**.

The IOAI subset contains 60 chainsaw and 60 gunshot clips. The Vietnam archive contains 690 gunshot-labelled clips and 3,675 `noise` clips; noise is retained as weakly labelled/non-verified background, not converted to the `background` class. The Vietnam `imagesvietnam_belize` branch is explicitly derived from/mixed with Belize data and is not independent.

## Investigated sources

The comparison table records Rodopi, Belize, Kenya, Sensing the Forest, Illinois, Vietnam, Outdoor Gunfire, and IOAI. Rodopi, Sensing the Forest, and Kenya were not reacquired because they are already local or quarantined. Illinois remained HTTP 403. Belize remained without authorized file-level access. Outdoor Gunfire has a documented CC BY 4.0 record but is a 1.6 GB firearm-range archive with weaker forest relevance.

## Acquisitions and validation

* IOAI: metadata CSVs downloaded from the official Hugging Face dataset; 120 class-targeted WAVs downloaded individually through public `resolve/main` URLs. Total audio bytes: 82,591,530. Files are five seconds each, PCM16, with 11.025–48 kHz and mono/stereo layouts.
* Vietnam: `clipsforzenodo.zip` downloaded from the official Zenodo API endpoint. Publisher MD5 `beaa5e5711246cea2dbad361ffb7cf02` matched. ZIP integrity passed. It contains 4,365 non-macOS WAV clips across Vietnam, Vietnam+Belize, and combined test branches.
* All acquired WAVs were decoded and measured for duration, sample rate, channels, sample count, subtype, peak, RMS, byte SHA-256, and decoded-audio hash. No resampling, normalization, segmentation, or model inference was performed.

## Provenance and eligibility

No verified original parent recordings, sessions, or devices were available for the IOAI files or the Vietnam extracted files. Therefore none is admitted as `ELIGIBLE_TRAIN_ONLY`. The 1,239 Vietnam+Belize branch clips are primary `DUPLICATE_OR_OVERLAP` dispositions because the publisher explicitly identifies mixed Belize ancestry. The remaining files are `QUARANTINED_PROVENANCE`; their labels remain publisher labels, and Vietnam `noise` remains weakly labelled rather than verified background.

## Duplicate and leakage audit

Exact byte hashes and canonical decoded-audio hashes were compared against the local raw, processed, filtered, Kenya staging, and acquired inventories. A deterministic 64-bit spectral-frame crop screen searched all 15,103 local raw WAVs with a 0.98 review threshold. Results, best paths, offsets, and limitations are in `duplicate_and_leakage_audit.csv`. Negative results do not prove source independence or absence of crop overlap.

## Eligibility summary

| disposition | count |
|---|---:|
| ELIGIBLE_TRAIN_ONLY | 0 |
| ELIGIBLE_VALIDATION_CANDIDATE | 0 |
| ELIGIBLE_INDEPENDENT_TEST_CANDIDATE | 0 |
| QUARANTINED_PROVENANCE | 3156 |
| DUPLICATE_OR_OVERLAP | 1329 |
| EXCLUDED | 0 |

Verified independent recordings: 0. Acquired files are clips, not verified independent recordings.

## Recommendation

Keep both sources isolated for research and human/provenance review. The most useful next step is to resolve file-level source grouping and licensing/attribution ancestry for the IOAI subset and the Vietnam-only branch, then review a small source-balanced sample. Do not create a training manifest or alter frozen partitions until those gates pass.

## Reproduction

```bash
python3 ml/reports/phase4_8_fasttrack_acquisition/run_fasttrack_audit.py
```
