# Online Dataset Alternative Audit

Audit date: 2026-10-19  
Decision: **NO-GO FOR ACQUISITION AT THIS TIME**

This is an online-source investigation only. No external audio was downloaded, no candidate was marked human-reviewed, no model or split was changed, and Phase 5 remains blocked.

## Repository baseline

The repository checks found:

| Check | Result |
|---|---:|
| Frozen train rows | 28,741 |
| Frozen validation rows | 6,999 |
| Frozen test rows | 2,119 |
| Phase 4.3 candidate rows | 777 |
| Phase 4.3 unique candidate IDs | 777 |
| Candidate files missing | 0 |
| Candidate source overlap with frozen validation/test | 0 |
| Frozen processed exact-duplicate rows | 5,008 |
| Frozen exact-hash groups | 2,504 |
| Frozen cross-split exact-hash groups | 0 |
| External files downloaded | 0 |

The machine-readable checks are in `online_dataset_audit_checks.json`. Existing Phase 4.3 still reports zero human-reviewed and zero training-eligible candidates.

## Frozen preprocessing contract

Any future online source must use the existing contract without alteration:

- 16,000 Hz, mono;
- peak normalization to -3 dB;
- 1.0-second windows with 0.5-second hop;
- repeat padding for short recordings;
- 512-point FFT, 160-sample feature hop, 40 mel bins, power 2;
- filter disabled;
- frozen training feature normalization: mean `-36.31850051879883`, standard deviation `21.19044303894043`.

The frozen input is `[1, 40, 101, 1]`. The online audit does not propose changing any of these values.

## Source-by-source findings

### 1. Rodopi chainsaw dataset — Zenodo 5824433

**Coverage and labels.** The official record describes 8 kHz WAV recordings collected in Rodopi Mountain-Range National Park, Greece, and says chainsaw portions are marked by human listeners in companion Praat TextGrid files. This is the strongest of the requested sources for a programmatic chainsaw extraction workflow: download a WAV/TextGrid pair, parse intervals, and extract only annotated event windows plus separately identified non-event intervals. The exact number of usable one-second windows cannot be claimed without downloading and parsing the TextGrids.

**License and access.** The Zenodo record metadata reports CC BY 4.0. The record exposes individual WAV and TextGrid file links, so selective downloading is possible. The listed record is approximately 454 MB in total, with nine WAV/TextGrid pairs visible in the record; the largest WAV is approximately 230 MB. Attribution and source hashes must be retained.

**Leakage risk.** This source is not a clean new source for this project. The frozen manifests already contain `rodopi_` recordings, including the same Rodopi recording identities. The frozen duplicate audit also found identical processed windows between `rodopi_RP3_0h30_to1h20` and `rodopi_RP6_0h30_to1h20` inside validation. Downloading this record would therefore add known source overlap, not independent diversity. Estimated *new non-leaking training samples*: **0 until a source-disjoint acquisition is demonstrated**.

**Decision:** **NO-GO as an acquisition source for the current frozen experiment.** Reuse only as provenance evidence or, in a separately authorized future experiment, after excluding every source identity already present and performing source-group splitting.

### 2. Illinois Data Bank gunshot source — IDB-5664241

**Coverage and labels.** The supplied landing page could not be fetched by the audit client because it returned HTTP 403. Consequently, exact class coverage, number of files, timestamp/annotation quality, recording identity, and extractable segment counts are **unverified**. No gunshot sample count is claimed.

**License and access.** The dataset-specific license and redistribution/training terms could not be verified. Illinois Data Bank’s general policy says depositors define a license in dataset metadata and that terms may also be supplied in a `license.txt`; the repository therefore cannot infer permission from the landing-page URL alone. Selective downloading and file sizes are also unverified.

**Risk and decision:** **NO-GO pending provider confirmation.** A useful source would need an accessible metadata/license record, original recording or session IDs, explicit gunshot timestamps or event counts, and a documented file-level download path. Until then, estimated legally usable samples: **0 verified**.

### 3. Sensing the Forest natural soundscape — Zenodo 18909809

**Coverage and labels.** The official record describes natural soundscape recordings from a woodland near Alice Holt Lodge Pond, Surrey, collected at four solar-time periods, with MEMS and later RØDE microphone configurations. It is relevant to the missing forest-background domain, but it is not a chainsaw/gunshot-labelled source. The record does not provide event annotations that establish a one-second interval is background. Any background subset would require human listening or a separately documented negative-event protocol.

**License and access.** The record reports CC0 1.0 and exposes a README plus one 23.5 GB ZIP archive for Part 1. The record does not expose a small file-level subset in its file list. The linked Freesound pack may provide source-level access, but it was not treated as a verified selective acquisition path in this audit. No archive was downloaded.

**Risk and decision:** **NO-GO for immediate bulk acquisition; conditional future candidate.** It directly addresses forest-domain mismatch, but estimated *verified usable background samples now*: **0**. A provider-supported subset of at least 20 distinct source recordings, with recording IDs, microphone/date metadata, hashes, and human-reviewed non-event intervals, would be required.

### 4. Smaller multi-class alternative — IOAI 2026 Home Task 1 dataset card

The investigated Hugging Face dataset card reports 1,283 WAV files, 29 classes, 491 rows in `train.csv`, 792 rows in `fine_tune.csv`, and explicit `chainsaw` and `gunshot` classes. It also has environmental categories such as birds, rain, thunderstorm, and fire, but it is not a forest-domain dataset and the card does not establish source-recording/session groups or event timestamps. The card reports CC BY-SA 4.0 and a total size of 2.03 GB.

This is a possible metadata-level research lead, not an immediately eligible replacement: the card attributes the data to an IOAI/Kaggle competition, and underlying recording-level rights, source identity, selective file retrieval, exact per-class counts, and leakage relationship to this repository require confirmation. Estimated verified usable samples without downloading and auditing the metadata/audio: **0**.

**Decision:** **NO-GO for current training acquisition.** It could reduce class-label collection effort only after source provenance, license scope, file-level metadata, and source-disjoint split controls are independently verified.

## Estimated usable samples

| Source | Background | Chainsaw | Gunshot | Current defensible estimate |
|---|---:|---:|---:|---|
| Rodopi Zenodo 5824433 | 0 new | 0 new | 0 | Existing source overlap; TextGrid counts not recomputed |
| Illinois IDB-5664241 | 0 verified | 0 | 0 verified | Landing page/terms/metadata inaccessible to audit |
| Sensing Forest 18909809 | 0 human-verified | 0 | 0 | Natural soundscape without event labels; no archive downloaded |
| IOAI multi-class lead | 0 verified | 0 verified | 0 verified | Class names reported, but file/source/license audit incomplete |

These zeros mean “not yet verified and admitted,” not “the source contains no such sounds.”

## Minimum viable acquisition plan

1. **Do not acquire Rodopi for this frozen experiment.** It is already represented and has known duplicate/source overlap.
2. **Request an Illinois Data Bank metadata/license export** for IDB-5664241, including file list, recording/session IDs, timestamps, license, and selective-download URLs. Do not download audio before this arrives.
3. **Request a provider-supported Sensing Forest subset** of at least 20 source recordings across microphone eras and environmental conditions. Obtain IDs, hashes, metadata, and permission for derived features; then manually review selected non-event intervals.
4. **Treat the IOAI card as a secondary lead only.** Obtain underlying source/license terms and per-file metadata before considering a small class-balanced subset.
5. For any approved source, preserve original files, compute source-file SHA-256, extract only annotation-supported one-second candidates, and split by original recording/session before any future training authorization.

## Cases that still require human review

- Whether Rodopi TextGrid intervals are sufficiently audible and whether neighboring intervals are true background.
- Whether Sensing Forest intervals are genuinely non-event background rather than merely unannotated.
- Whether Illinois gunshot events are audible, timestamped, and representative of outdoor forest deployment.
- Whether IOAI labels correspond to clearly audible events and whether files share hidden source/session groups.
- Any borderline chainsaw/engine, gunshot/impact/firework, mixed scene, weak event, or partial event.

## Final recommendation

**NO-GO for dataset acquisition at this time.** The best eventual targeted path is a small, provider-approved Sensing Forest background subset plus a fully documented Illinois gunshot subset, while Rodopi should be excluded from the current acquisition because it overlaps the frozen data. The online sources do not remove the need for human review; they can reduce the queue only after provenance, license, source-group, and acoustic-label evidence is obtained.

No Phase 5 authorization is implied.
