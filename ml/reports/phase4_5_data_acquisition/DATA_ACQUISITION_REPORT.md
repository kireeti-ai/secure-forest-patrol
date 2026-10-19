# Phase 4.5 — Source Verification and Targeted Data Acquisition

Audit date: 2026-10-19  
Decision: **METADATA_ONLY — AUDIO ACQUISITION BLOCKED**

## Executive summary

Phase 4.5 retrieved and verified small Kenya metadata artifacts from the official Zenodo record. No external audio archive was downloaded. The Kenya audio is a single 716,622,014-byte ZIP, and the publisher provides no file-level download listing or source-session manifest outside the annotation workbook. The workbook confirms 129 chainsaw clips, but those clips belong to only five filename-prefix groups; the datasheet says relationships between instances are not explicit. Therefore the requested 20–30 independent chainsaw source recordings cannot be established from the available metadata.

The Belize record was inspected without downloading audio. Its page advertises a download-all workflow, but the file tree was not available and the page exposed no individual WAV URLs, file list, archive size, or selective-download mechanism. The record’s license and collection description are documented, but file-level selection and source-group selection cannot be performed safely. Belize audio acquisition is therefore deferred.

No source passed all gates for audio acquisition. The acquisition directory contains only the two small Kenya publisher metadata files; it contains no audio, resampled audio, features, or replacement manifests. Phase 5 remains blocked.

## Kenya verification

Official record: [Zenodo 21443074](https://zenodo.org/records/21443074)  
Project documentation: [Kenya Forest Sounds Dataset README](https://github.com/SCES-Makerspace-Lab/Kenya-Forest-Sounds-Dataset/blob/live/README.md)

The official Zenodo API returned:

| File | Role | Size | Publisher checksum |
|---|---|---:|---|
| `SCES-Makerspace-Lab/Kenya-Forest-Sounds-Dataset-v1.0.1.zip` | audio archive | 716,622,014 bytes | MD5 `9789f781d9bec915bfb2e15f0c91a42a` |
| `Dataset_Description.xlsx` | labels and metadata | 159,617 bytes | MD5 `50752c1cb78cd6f939fe7454ade1b0a` |
| `KFSD_Datasheet.pdf` | methodology/datasheet | 88,374 bytes | MD5 `4baa6d389fc9329f5b1d9db2764a2525` |

Only the workbook and PDF were retrieved. The SHA-256 values of the retrieved metadata are recorded in `integrity_hashes.json`.

The workbook contains three sheets: `README`, `Human-Annotated` with 3,164 rows, and `ML-Annotated-People-Talking` with 2,336 rows. The human sheet reports 5,500 total dataset instances when combined with the ML-annotated sheet. The labels include 129 `Chainsaw`, 213 `Birds`, 231 `Wind`, 703 `Vehicle`, 3 `Crickets`, 3 `Engine`, 21 `Flowing water`, 90 `Axe`, and 7 `Cutting wood`, among others. There is no gunshot label.

The datasheet reports three collection periods, March 2024, May 2024, and January 2025, and a Zoom H2n recorder. It says each instance is an unprocessed WAV clip, 0.07–5.02 seconds, and that relationships between instances are not explicit. Filename parsing shows 98 `ZOOM` prefixes in the human-annotated sheet, but the publisher does not define those prefixes as independent sessions or parent recordings. Chainsaw clips occur under only five prefixes: `ZOOM0060`, `ZOOM0068`, `ZOOM0086`, `ZOOM0094`, and `ZOOM0228`.

This supports useful *clip-level* coverage, but not the requested independent-source count. No audio was downloaded to test whether prefixes represent devices, sessions, field trips, or merely filename groups. No event timestamps are supplied; labels are clip-level. The publisher states CC BY 4.0 and identifies the Conservation Technology Research Hub at Strathmore University as the primary collector/owner.

## Belize verification

Official record: [Mendeley Data version 3](https://data.mendeley.com/datasets/x48cwz364j/3)

The official page confirms a tropical-forest collection in Belize, AudioMoth devices, 4.09-second 8-kHz WAV clips, 749 gunshot files, more than 35,000 background files, controlled firing at 0–1,000 m, and manual listening/spectrogram extraction. It states CC BY 4.0.

The page does not provide a usable file-level manifest in the unauthenticated HTML response. Its file section remains a loading tree and its only visible action is a disabled `Download All` control. No individual WAV URLs, archive size, file hashes, device/site manifest, or selective download endpoint was exposed. The first eight filename characters are described as a Unix hexadecimal recording timestamp, but no downloaded file was available to verify whether suffixes identify crops, sensors, or event instances.

Because file-level selection is unavailable, the requested 20–30 varied gunshot source recordings and background controls cannot be selected without downloading the entire dataset. No Belize audio was downloaded.

## License and provenance audit

| Source | License evidence | Provenance evidence | Audio acquisition status |
|---|---|---|---|
| Kenya | Zenodo API `cc-by-4.0`; workbook and datasheet state CC BY 4.0 | Three forests, three collection periods, Zoom H2n, clip labels; no explicit parent/session relationships | Metadata acquired; audio blocked by monolithic archive and insufficient source grouping |
| Belize | Official Mendeley page states CC BY 4.0 | Belize sites, AudioMoth, 2017–2021, controlled firing and manual event extraction described | Audio deferred because selective file access was not available |

The license evidence is sufficient for a future attribution review, but it does not by itself establish that every derivative, crop, or underlying source has the same rights. No data was added to training or any frozen split.

## Duplicate and leakage audit

There are zero acquired audio files, so no audio SHA-256 or acoustic fingerprint comparison against the existing raw audio, processed audio, frozen manifests, or 777 Phase 4.3 candidates could be performed. This is recorded as `NOT_RUN_NO_AUDIO_ACQUIRED`, not as a clean overlap result.

Identifier-only checks found no direct `ZOOM`, Belize, TMNR, MFR, or AudioMoth source identifiers in the local manifests, but identifier absence is not evidence of audio independence. The existing frozen exact-duplicate audit remains unchanged: 5,008 duplicate rows, 2,504 groups, and zero cross-split groups. Any future acquisition must repeat exact and near-duplicate checks after audio retrieval.

## Preprocessing compatibility

No derived audio was created. The existing contract remains unchanged: 16-kHz mono, one-second windows, 0.5-second hop, repeat padding, peak normalization to -3 dB, 40 mel bins, 512-point FFT, 160-sample feature hop, power 2, and model input `[40, 101, 1]`. The publisher’s Kenya clips are already described as 16-kHz WAV filenames, but this was not independently verified from audio because the archive was not downloaded. Belize is advertised as 8 kHz and would require separate resampling after acquisition. No normalization statistics or quantization parameters were changed.

## Acquisition decision

**NO_AUDIO_ACQUISITION — BLOCKED_PENDING_SELECTIVE_ACCESS_AND_SOURCE_GROUP_VERIFICATION**

The Kenya metadata is promising for background and chainsaw coverage, but it cannot support the required independent-source count. The Belize metadata is promising for forest gunshots, but file-level selection is unavailable without a large all-data download. The correct next step is to request file manifests or a small publisher-curated subset from the maintainers, not to download either full archive speculatively.

The acquired metadata remains isolated under `ml/datasets/phase4_5_acquisition/original_metadata/`. No model training, model inference, threshold tuning, preprocessing change, firmware change, frozen-manifest change, or Phase 4.3 decision change occurred.
