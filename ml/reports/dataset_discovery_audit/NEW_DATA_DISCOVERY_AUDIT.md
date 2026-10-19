# SECURE-FOREST-PATROL — Existing Dataset Audit and New Data Discovery

Audit date: 2026-10-19  
Status: **Search and inventory complete; no external audio downloaded; frozen data unchanged**

## Executive conclusion

The repository already contains substantially more data than the older dataset-card text suggests. The current local inventory has six source domains, 58,918 processed segments, and 1,975 distinct `original_recording_id` values. The frozen train/validation/test manifests contain 37,859 rows from five source domains and exclude `sensing_forest` from the frozen evaluation partitions.

The principal data weaknesses remain plausible but are not all proven at source level:

- Validation chainsaw recall is 48.87% (225 chainsaw windows predicted as background).
- Validation gunshot recall is 68.52%, based on only 54 evaluated gunshot windows.
- Validation has 143 background→chainsaw and 46 background→gunshot errors.
- The available validation artifact is aggregate only; it does not contain per-window predictions or confidence scores, so validation error concentration by recording, device, geography, or environment cannot be measured.
- Phase 1 test diagnostics show source-clustered background false positives and target false negatives, but those test results were not used to select new data or tune the model.

No online source is approved for immediate acquisition. The smallest defensible next plan is conditional verification of two sources: the Kenya Forest Sounds Dataset for forest background and chainsaw diversity, and the Belize tropical-forest gunshot dataset for forest gunshots and background. Both require source-group, exact-hash, and near-duplicate checks before any data enters a future split. A full archive download is not justified at this stage.

## Existing local inventory

Counts below are computed from `ml/datasets/v1/master_v1.csv` and distinguish source recordings from derived windows.

| Local source | Original recordings | Processed segments | Classes in master manifest | Frozen partition presence | Local license/provenance status |
|---|---:|---:|---|---|---|
| Rodopi chainsaw recordings | 9 | 26,697 | background, chainsaw | train/validation; no test | CC BY reported; source overlap and RP3/RP6 duplicate known |
| Sensing the Forest | 34 | 18,338 | background | master only; no frozen train/validation/test | CC0 reported; natural soundscape, no event labels |
| FSC22 | 939 | 7,676 | background, chainsaw, gunshot | train/validation/test | source/license review retained in repository; FreeSound provenance matters |
| ESC-50 derived subset | 493 | 4,120 | background, chainsaw | train/validation/test | CC BY-NC reported; clip-level labels |
| RFCx FrugalAI | 400 | 1,987 | background, chainsaw | train/validation/test | CC BY-NC reported; 12-kHz source and forest domain |
| C3GD | 100 | 100 | gunshot | train/validation/test | CC BY reported; detailed event/device metadata |
| **Total** | **1,975** | **58,918** | | | |

The frozen partitions contain 28,741 train, 6,999 validation, and 2,119 test rows. The split manifests contain five datasets: Rodopi, FSC22, ESC-50, RFCx FrugalAI, and C3GD. `sensing_forest` is present in the master/raw inventory but not in those frozen partitions.

The current class/source distribution in the master manifest is:

| Source | Background | Chainsaw | Gunshot |
|---|---:|---:|---:|
| Rodopi | 25,056 | 1,641 | 0 |
| Sensing the Forest | 18,338 | 0 | 0 |
| FSC22 | 6,665 | 669 | 342 |
| ESC-50 subset | 3,764 | 356 | 0 |
| RFCx FrugalAI | 1,246 | 741 | 0 |
| C3GD | 0 | 0 | 100 |

The segment count is not an independent-sample count. Most ordinary source recordings yield five to nine one-second windows, while a small number of long Rodopi recordings dominate the row totals. The largest source has 14,898 rows. This is why future additions must group by original recording/session, not by window.

## Existing candidate and integrity state

The Phase 4.3 candidate pool has 777 unique candidates, all from the frozen training source side, with one-second/16-kHz compatible processed audio. Current license states are 437 `QUARANTINED`, 330 `RESEARCH_ONLY`, and 10 `ELIGIBLE_WITH_ATTRIBUTION`; all 777 remain ineligible for training pending human/eligibility review. The current decisions file contains 776 `PENDING` and one existing `ACCEPTED` row; the explicit decision was preserved.

The previous duplicate audits report 5,008 frozen duplicate rows grouped into 2,504 exact-content groups, with zero cross-split exact-duplicate groups. The known Rodopi RP3/RP6 pair has identical source content and must remain one source group. Phase 4.3 reports zero candidate source overlap with frozen validation/test sources. No new-source audio was downloaded in this audit, so external exact or near-duplicate checks remain pending for every online candidate.

## Preprocessing compatibility

The active repository contract is confirmed in `ml/configs/preprocessing.yaml`, `ml/preprocessing/audio_preprocess.py`, and the feature extraction implementation:

- resample to 16 kHz, mono;
- peak-normalize to -3 dB;
- one-second windows with a 0.5-second hop;
- repeat padding for short inputs;
- 40 mel bins, 512-point FFT, 160-sample feature hop, 0–8 kHz range, power 2;
- frozen feature mean/std `-36.31850051879883` / `21.19044303894043`;
- frozen model input `[40, 101, 1]`.

New source preparation must preserve this contract. Event timestamps must be transformed through resampling and segmentation; unlabeled intervals must not be automatically called background.

## Online source audit

### 1. Belize tropical-forest gunshot classification dataset — strongest gunshot lead

The Mendeley record describes 749 gunshot files and more than 35,000 background files, each 4.09 seconds at 8 kHz, recorded in tropical forests in Belize using AudioMoth devices. It reports controlled firing at distances from 0–1,000 m, manually extracted gunshot events, listened-to background removal, and temporally separated training/validation periods. The record states CC BY 4.0. See [Mendeley version 3](https://data.mendeley.com/datasets/x48cwz364j/3).

Assessment: **promising, conditional acquisition**. It directly addresses the missing forest gunshot/domain-distance coverage and includes original recording timestamps in filenames plus site/time partition information. It does not provide chainsaw labels. The dataset is also the source used by a later Vietnam benchmark, so that derivative must not be counted as independent. The Mendeley page exposes a download-all workflow; selective file acquisition was not demonstrated during this audit. Do not download the full archive until file-level access and metadata extraction are confirmed.

### 2. Kenya Forest Sounds Dataset — strongest background/limited chainsaw lead

The project README reports 5,500 WAV recordings from three Kenyan forests, 0.07–5.02-second clips, CC BY 4.0, 129 chainsaw clips, 213 bird clips, 231 wind clips, 703 vehicle clips, 3 crickets clips, 21 flowing-water clips, and other human/mechanical/natural categories. It reports 3,164 human-annotated sounds plus 2,336 people-talking examples validated after ML detection. See [the dataset README](https://github.com/SCES-Makerspace-Lab/Kenya-Forest-Sounds-Dataset/blob/live/README.md) and [the Zenodo record](https://zenodo.org/records/21443074).

Assessment: **promising, conditional acquisition**. It offers genuinely new geography and difficult background strata, with a small chainsaw set. It has no gunshot class. The available documentation describes clip-level labels, not event timestamps, and the Zenodo record was not machine-readable through the browser during this audit. Original session/device metadata, exact file sizes, and selective download capability require verification before acquisition. Human annotation is better than an unlabeled soundscape, but event occupancy and parent-recording grouping still require inspection.

### 3. Rodopi chainsaw dataset — reject as new data

The Zenodo record contains eight 8-kHz ARU WAV/TextGrid pairs totaling about 454 MB, with manually marked chainsaw intervals. It is already present in the repository’s raw and master inventories. The repository has the known RP3/RP6 identical-content pair. See [the Rodopi record](https://zenodo.org/records/5824433).

Assessment: **not a new source**. It is useful as an annotation/provenance reference, but reacquiring it would add leakage and duplicate risk, not independent coverage.

### 4. Sensing the Forest — reject as new data; possible background reserve only

Part 1 is a CC0 natural soundscape from a UK woodland, with a 23.5-GB archive and no event labels. The record describes fixed solar-time recordings and a microphone change during the collection period. See [the Zenodo record](https://zenodo.org/records/18909809).

Assessment: **already present locally and not event-labelled**. The repository has 34 source recordings and 18,338 processed master segments. Because no event annotation establishes that an interval is non-event, these files cannot be added as automatically labelled background. They may support a separate manually sampled hard-background study, but the archive size and annotation cost make it lower priority than Kenya.

### 5. Illinois gunshot dataset — not verified

The supplied page returned HTTP 403 during live inspection. Class coverage, files, recording identities, timestamps, license, and download size therefore remain unverified.

Assessment: **reject for this audit** until the owner or an accessible official metadata mirror supplies the missing evidence. No inference is made from the title.

### 6. IOAI 2026 Nightwatch — broad labels but weak provenance

The dataset card reports 1,283 WAV files, 29 classes, including chainsaw and gunshot, with CC BY-SA 4.0 and a total size of 2.03 GB. It gives clip-level CSV labels but no event timestamps or clear original-recording/session provenance. The card attributes the data to a Kaggle competition. See [the dataset card](https://huggingface.co/datasets/pkasila/ioai26-ht1-nightwatch).

Assessment: **low-priority verification lead, not approved**. The class coverage is attractive, but source independence, forest relevance, licensing of underlying audio, and duplicate overlap are unresolved. A derivative/aggregated benchmark must not be treated as independent merely because its repository is different.

### 7. Vietnam passive-acoustic gunshot benchmark — derivative/overlap risk

The Zenodo record contains Vietnam passive-acoustic clips plus Belize clips from Katsis et al., with WAV/JPEG pairs isolated using Raven Pro annotations. It advertises a 396.1-MB clips archive and a 484.9-MB image archive. See [the Zenodo record](https://zenodo.org/records/13893977).

Assessment: **conditional evaluation-only lead, not a new training source yet**. Vietnam clips could add geographic diversity, but the record mixes them with Belize data already available through the Mendeley lead and does not expose a simple source-group manifest in the landing page. It must be de-duplicated by original source and used only after separating Vietnam from Belize.

### 8. Gunshot/Gunfire Audio Dataset — useful acoustic control, weak forest relevance

The Zenodo record describes multi-firearm, multi-orientation recordings from an outdoor firearm range and a 1.6-GB archive with a README. The landing page does not expose a license. See [the Zenodo record](https://zenodo.org/records/7004819).

Assessment: **not preferred for forest deployment**. It may be useful as a controlled gunshot-distance/device stress set, but license and forest-domain relevance are unresolved. It should not be mixed into a forest-background training set without a documented purpose.

### 9. FSM5 / ForNet dataset — reject as independent source

The paper describes 2,258 balanced clips across animal, natural, vehicle, gunshot, and timber-cutting classes, but the source distribution includes ESC-50, UrbanSound8K, Freesound, and AudioSet. It is therefore an aggregation of public sources already represented or potentially overlapping with the current project, not an independently recorded forest collection. The paper gives a Google Drive availability link but not a clear per-file license/provenance manifest. See [the published paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC13351060/).

Assessment: **reject for new training data** unless every file is traced back to an original source and excluded when overlapping. It is not a shortcut around duplicate and license review.

## Ranked shortlist

| Rank | Source | Main value | Main blocker | Status |
|---:|---|---|---|---|
| 1 | Kenya Forest Sounds | New forest background; 129 chainsaw; CC BY 4.0 reported | No timestamps; Zenodo metadata/files and source groups need verification | Promising, conditional |
| 2 | Belize tropical-forest gunshot | 749 gunshots; >35k background; 0–1,000 m; manual extraction; CC BY 4.0 | Download-all presentation; selective access and exact provenance manifest need verification | Promising, conditional |
| 3 | Vietnam passive-acoustic benchmark | New Vietnam geography; Raven Pro-isolated clips | Mixes Belize derivative; license/source-group manifest incomplete | Evaluation-only candidate |
| 4 | IOAI Nightwatch | Chainsaw and gunshot in one card; CC BY-SA 4.0 reported | 2.03 GB; no original source/session provenance or timestamps | Verification lead only |
| 5 | Outdoor Gunshot/Gunfire | Multi-firearm/device control set | 1.6 GB; license absent; non-forest range domain | Low priority |

Rejected as new independent training sources: Rodopi, Sensing the Forest, and FSM5. Illinois remains unverified.

## Minimum viable acquisition plan

No download was performed because no candidate passed all required pre-acquisition checks and selective downloading was not demonstrated.

If acquisition is authorized after the next verification gate:

1. Obtain only the Kenya metadata workbook/manifest and a small, source-grouped subset containing approximately 20–30 chainsaw recordings plus 30–50 difficult background recordings across at least three forest sites and several background strata. Keep all source sessions together. Extract no more than needed for a first compatibility/duplicate audit.
2. Obtain a metadata/file listing for the Belize dataset before audio. If file-level selection is possible, acquire approximately 20–30 gunshot recordings spanning distance/site/time groups plus a small background control sample. If only a monolithic download is possible, defer rather than download the full archive without approval.
3. For every acquired original file, record URL, retrieval date, size, SHA-256, source recording/session/site, license, and any event interval. Resample only in a separate staging area; preserve originals.
4. Run exact SHA-256 checks against all frozen raw/processed files and the 777 Phase 4.3 candidates. Run near-duplicate fingerprints and parent/source matching. Assign future split groups before any windowing.
5. Do not label unlabeled soundscape intervals as background. Route uncertain occupancy, mixed events, and ambiguous timestamps to the existing human-review process.

Expected value is targeted source diversity, not a large segment count: Kenya addresses difficult forest background and limited chainsaw diversity; Belize addresses forest gunshot distance and site diversity. Neither source alone supplies all three classes.

## Checks performed

- Repository file and documentation discovery completed.
- Master and frozen manifest counts, source IDs, class counts, and processed sample rates inspected.
- Phase 4.3 candidate schema, license states, review decisions, and eligibility state inspected.
- Phase 4.4 error analysis and previous online audit inspected.
- Preprocessing implementation and configuration checked against the deployment contract.
- Existing exact-duplicate audit checked: 5,008 rows, 2,504 groups, zero cross-split groups.
- Existing frozen model/split/cache hashes remain those recorded in the prior integrity reports.
- Live web pages checked for the named leads and additional candidates.
- External audio downloads performed: **0**.
- Model training/inference performed: **0**.
- Frozen manifests, model files, preprocessing code, firmware, and review decisions modified: **0**.

## Remaining uncertainty

The current repository does not provide complete original-device, geographic, or event-timestamp metadata for every existing source. Validation predictions are aggregate only. New-source exact and near-duplicate tests cannot be completed until a source-specific subset is acquired or a complete file manifest with hashes is provided. This report therefore recommends conditional verification, not immediate training authorization or Phase 5.
