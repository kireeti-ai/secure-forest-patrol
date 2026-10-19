# Phase 4.6 — Acquisition Blocker Resolution

Audit date: 2026-10-19  
Decision: **KENYA_ACQUIRED_FOR_STAGING_ONLY_BELIZE_DEFERRED**

## Summary

The Kenya archive was downloaded into the isolated Phase 4.5 acquisition area, verified, and inspected. The Belize source was investigated through its public record and documented API route, but no audio was downloaded because authorized file-level selection was not available.

The Kenya archive is intact and useful for a controlled staging audit, but its clips cannot be treated as independent source recordings. All 129 publisher-labelled chainsaw clips were extracted, along with 46 labelled background controls. The extracted subset remains outside the frozen dataset, has not been human-reviewed, and is not training-eligible.

## Kenya archive result

Source: [Zenodo record 21443074](https://zenodo.org/records/21443074)

| Check | Result |
|---|---|
| Archive | `Kenya-Forest-Sounds-Dataset-v1.0.1.zip` |
| Actual size | 716,622,014 bytes |
| Publisher MD5 | `9789f781d9bec915bfb2e15f0c91a42a` |
| Local SHA-256 | `2e270bf4918885f8f5fe35e204f9b1ccf2cae14ecff5623fe272be1ec7a5feae` |
| ZIP integrity | PASS; `unzip -t` reported no errors |
| ZIP members | 5,500 WAV files; no embedded annotation files |
| Audio properties | 175/175 extracted files are 16-kHz, mono, PCM-16 WAV |
| Extracted subset | 129 Chainsaw + 46 publisher-labelled background controls |
| Extracted audio duration | 850.4176875 seconds total; Chainsaw 638.9728125 seconds; controls 211.444875 seconds |
| Staging storage | 744,106,121 bytes including archive, metadata, and extracted subset |

The full archive listing is in `kenya_archive_inventory.csv`. The archive contains only WAV members under one dataset directory. The publisher workbook and datasheet remain separately preserved under `ml/datasets/phase4_5_acquisition/original_metadata/`.

### Source-group structure

The 129 chainsaw clips occur in five filename-prefix groups:

| Provisional prefix | Chainsaw clips |
|---|---:|
| `ZOOM0060` | 2 |
| `ZOOM0068` | 1 |
| `ZOOM0086` | 104 |
| `ZOOM0094` | 20 |
| `ZOOM0228` | 2 |

The publisher datasheet reports a Zoom H2n recorder, three collection periods, and three forests, but explicitly says relationships between instances are not made explicit. The ZIP filenames do not establish whether a prefix is a session, device, field trip, source recording, or merely a naming convention. The most defensible grouping is therefore **provisional filename prefix**, not independent original recording. In particular, 104/129 chainsaw clips share `ZOOM0086`; the data must not be counted as 129 independent chainsaw recordings.

The extracted background controls preserve their publisher labels: Birds, Wind/wind, Vehicle, Flowing water, Crickets, and Engine/engine. They are not automatically relabelled to `background`, and no event timestamps are claimed.

## Duplicate and leakage checks

Exact SHA-256 checks were run on all 175 extracted WAVs against the local raw WAV inventory, processed WAV inventory, and Phase 4.3 candidate WAVs. There were zero exact matches; a same-size prefilter found zero local candidates.

A bounded audio-level scan compared normalized 256-sample full-file fingerprints against 15,058 local raw WAV files with duration within 0.12 seconds. There were zero matches at or above 0.95 similarity. This is evidence against same-length full-file duplicates, not proof that a Kenya clip is not a crop of a longer local recording. Parent/crop relationships remain unresolved because the external source does not provide parent IDs.

No direct `ZOOM` identifiers occur in the local manifests or candidate pool. This identifier result is not a substitute for audio-level provenance. The frozen duplicate audit remains unchanged: 5,008 duplicate rows, 2,504 groups, and zero cross-split groups.

No frozen train, validation, or test manifest was modified. The acquired files are not assigned to a future split.

## Belize access result

Source: [Mendeley Data version 3](https://data.mendeley.com/datasets/x48cwz364j/3)

The public page confirms the described Belize forest gunshot/background collection, 4.09-second 8-kHz WAVs, manual extraction/listening, and CC BY 4.0. It does not expose an accessible file manifest or individual WAV endpoints in the public response. The visible file tree remained in a loading state and the `Download All` control was disabled.

Mendeley’s documented dataset/file APIs require an OAuth bearer token. An unauthenticated request returned HTTP 401. No credentials were available and no access controls were bypassed. Since filenames, archive size, source-group fields, and individual file hashes could not be retrieved, no Belize audio was downloaded.

The exact access investigation is in `belize_access_investigation.md`. The appropriate next route is a publisher-provided file manifest or small source-grouped subset, not an unaudited full archive.

## Preprocessing compatibility

No repository preprocessing code was changed and no model inference was run. A read-only compatibility check on the extracted subset found:

- 175/175 files at 16 kHz;
- 175/175 files mono;
- durations from 0.0696875 to 5.0155 seconds;
- representative one-second, peak-normalized segments produced mel shape `[40, 101]` using the existing 512-point FFT, 160-sample hop, 40 mel bins, 0–8 kHz range, and power 2;
- the frozen feature mean/std and quantization parameters were not changed.

Short clips still require the repository’s repeat-padding behavior if they are ever prepared for a future experiment. No features or resampled replacements were added to the frozen cache.

## Eligibility and next action

The Kenya subset is **staging-only**. It can be considered for a future training-only addition only after:

1. the publisher clarifies whether filename prefixes map to recording sessions or another parent group;
2. source-group split assignments are created before windowing;
3. labels and event occupancy receive human review;
4. license attribution is recorded at the final file level; and
5. exact and crop/near-duplicate review is completed against the full local corpus.

The Belize source remains deferred pending authorized file-level metadata. Phase 5 remains blocked. No model, threshold, split, preprocessing code, firmware, or Phase 4.3 decision was changed.
