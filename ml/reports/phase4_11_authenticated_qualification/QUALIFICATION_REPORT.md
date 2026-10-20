# Phase 4.11 — Authenticated Candidate Qualification

Audit date: 2026-10-19 UTC

## Final decision

**NO_QUALIFIED_SOURCE_NO_DOWNLOAD**

The authenticated Hugging Face session was not needed. Public authoritative metadata was sufficient to reject qualification; no token was printed, accessed, or stored. No external audio was downloaded.

## FSD50K assessment

FSD50K remains a useful metadata lead, but it does not pass the mandatory admission gates. The official Zenodo record reports 51,197 Freesound clips, with Freesound IDs as filenames and per-clip metadata containing uploader, title, description, tags, and license. It reports the following exact rights counts:

| Set | CC0 | CC-BY | CC-BY-NC | CC Sampling+ | Total |
|---|---:|---:|---:|---:|---:|
| Development | 14,959 | 20,017 | 4,616 | 1,374 | 40,966 |
| Evaluation | 4,914 | 3,489 | 1,425 | 403 | 10,231 |

The 5,990 CC-BY-NC/Sampling+ files cannot be treated as generally admissible training data. The official record also warns that the dataset-level CC-BY label does not resolve individual clip rights and requests contact for commercial use/competitions. A future restricted subset could be considered only after exact per-file filtering, attribution preservation, and a project-level rights decision.

FSD50K labels are clip-level AudioSet ontology labels, not event timestamps. The public metadata does not provide session/device/location groups or verified event-free background recordings. Therefore a permissive-license subset would still fail provenance and background-negative gates.

The official audio archive is 24.7 GB and split across multipart archives; metadata and ground-truth archives are small, but no official selective per-file audio download mechanism was demonstrated. No audio archive was downloaded.

## Other candidates

- **ARCA23K/ARCA23K-FSD — DEFERRED_LABELS:** the official record states ARCA23K was automatically created without manual verification and reports estimated label error; the available evidence does not establish all three required classes or verified background negatives.
- **AudioSet — DEFERRED_LICENSE:** official CSVs provide YouTube video IDs and start/end times, but the official release provides metadata/features rather than authorized raw audio.
- Phase 4.7–4.10 sources retain their previous quarantine/rejection decisions and were not redownloaded.

## Pipeline and leakage compatibility

No audio was transformed or tested. The existing contract remains 16-kHz mono, -3 dB peak normalization, 1-second windows, 0.5-second hop, 40 mel bins, FFT 512, feature hop 160, power 2, and frozen mean/std. FSD50K source clips have variable durations and would require a separate, explicit preprocessing validation before any admission. Clip IDs are not session IDs; adjacent windows from one clip must not be counted as independent recordings.

Because no new audio was acquired, exact hashes, decoded hashes, near-duplicate search, and leakage checks against the local audio were not run. Their status is recorded as `NOT_RUN`/`UNRESOLVED` in `duplicate_and_leakage_audit.csv`, not as a negative result.

## Validation results

- Protected model, frozen split, and feature-cache hashes: all 9 matched.
- Candidate rows: 3.
- Qualified sources: 0.
- Audio downloads: 0.
- HF authentication used: false.
- Model inference/training/threshold tuning: not started.
- Frozen manifests, firmware, and Phase 4.3 decisions: unchanged.

## Primary evidence

- [FSD50K official Zenodo record](https://zenodo.org/records/4060432)
- [FSD50K companion site](https://fsannotator.upf.edu/fsd/release/FSD50K/)
- [ARCA23K official Zenodo record](https://zenodo.org/records/5117901)
- [AudioSet official download page](https://research.google.com/audioset/download.html)
- [Phase 4.10 discovery report](../phase4_10_source_first_discovery/SOURCE_FIRST_DISCOVERY_REPORT.md)

Phase 5 remains blocked. No source is ready for separate acquisition.
