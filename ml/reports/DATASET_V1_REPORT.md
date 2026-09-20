# Dataset V1 Report

Generated from a real run of `preprocessing/audio_preprocess.py` + `preprocessing/create_splits.py`
against the 6 raw datasets in `ml/datasets/raw/`. All counts below are measured, not estimated.

## Overview

- **Total segments (1.0s windows, 16kHz mono):** 58,918
- **Total distinct source recordings:** 1,975
- **Total audio duration represented:** 16.37 hours
- **Classes:** `background`, `chainsaw`, `gunshot`
- **Skipped/corrupt files during extraction:** 0 (after fixing an ESC-50 nested-folder path bug; see below)

## Per-class segment counts (master_v1)

| class | segments |
|---|---|
| background | 55,069 |
| chainsaw | 3,407 |
| gunshot | 442 |

Class imbalance is severe (background heavily dominant, gunshot the rarest) — this is expected
given the source datasets and is addressed at training time via `class_weight='balanced'` and
minority-class oversampling caps are NOT needed since we cap only the majority class during
feature-cache construction (`models/prepare_features.py`, `max_per_class` for background/val caps).

## Per-dataset contribution (segments / class)

| dataset_id | background | chainsaw | gunshot | recordings |
|---|---|---|---|---|
| c3gd | 0 | 0 | 100 | 100 |
| esc50_hf | 3,764 | 356 | 0 | 493 |
| fsc22 | 6,665 | 669 | 342 | 939 |
| rfcx_frugalai | 1,246 | 741 | 0 | 400 |
| rodopi | 25,056 | 1,641 | 0 | 9 |
| sensing_forest | 18,338 | 0 | 0 | 34 |

## Per-dataset labeling logic

- **c3gd**: A diversity-maximizing subset of 130 recordings was selected from the 12,112-row
  `metadata.csv`, round-robin sampled across unique `(event_id, platform_id, cartridge_id, mic_id)`
  combinations to maximize platform/cartridge/mic diversity while keeping the sample bounded
  (`subset_size: 130` in `configs/preprocessing.yaml`). All selected recordings are `gunshot`.
  100 of the 130 selected files survived the quality gate (clipping/silence checks); the rest were
  dropped. C3GD covers 4 distinct `event_id` shooting sessions.
- **fsc22**: `fsc22_metadata.csv` "Class Name" mapped explicitly: `Gunshot`→gunshot, `Chainsaw`→chainsaw,
  forest-ambient classes (`BirdChirping`, `Frog`, `Insect`, `Rain`, `Wind`, `WaterDrops`, `Thunderstorm`,
  `WolfHowl`, `Squirrel`, `WingFlaping`, `Lion`)→background. Everything else (`Fire`, `Clapping`,
  `Footsteps`, `Speaking`, `Whistling`, `WoodChop`, `Firework`, `Handsaw`, `Generator`, `Axe`,
  `VehicleEngine`, `Helicopter`, `TreeFalling`, `Silence`) was **discarded** (1,050 of 2,025 files) —
  these are non-forest-ambient or semantically ambiguous (e.g. `Handsaw` sounds acoustically close to
  chainsaw but is a different tool, so it was excluded rather than mislabeled).
- **rodopi**: 9 Praat TextGrid files parsed with `scripts/textgrid.py`. Intervals labeled `"saw"` →
  chainsaw segments; all other intervals → background (capped at 30 background intervals per recording
  file to avoid one dataset dominating). `original_recording_id` and `event_interval_id` are tracked
  per sample for provenance.
- **esc50_hf**: Joined `ESC-50-master/meta/esc50.csv` by `category`. `chainsaw`→chainsaw;
  `chirping_birds, rain, wind, crickets, insects, water_drops, frog, crow, crackling_fire, footsteps,
  thunderstorm, engine`→background. Audio was located via the per-category subfolders on disk
  (`<category>/ESC-50-master/audio/<file>.wav`) after discovering the flat `audio/` folder was
  incomplete (only 1 of 2,000 files present there).
- **rfcx_frugalai**: Folder-based labels (`audio/chainsaw`→chainsaw, `audio/environment`→background),
  resampled 12kHz→16kHz via librosa.
- **sensing_forest**: All 34 recordings labeled background (long-duration forest ambient recordings,
  hence disproportionately many segments per recording — used as external-test noise/negative source).

## Splits (grouped by original_recording_id, no leakage)

| split | segments | recordings | background | chainsaw | gunshot |
|---|---|---|---|---|---|
| train | 28,741 | 1,328 | 26,344 | 2,093 | 304 |
| validation | 6,999 | 284 | 6,501 | 444 | 54 |
| test | 2,119 | 286 | 1,781 | 295 | 43 |
| external_test | 21,059 | 77 | 20,443 | 575 | 41 |

Split ratio target was 70/15/15 by recording (applied to all recordings not carved into
`external_test`). External test set is deliberately held out from ALL of `train`/`validation`/`test`
by source: all `sensing_forest` recordings, the numerically-largest held-out `c3gd` event_id, and
2 held-out `rodopi` recordings — sources whose content never appears in the training/validation/test
pool.

## Quality gates

- `scripts/audit_dataset.py` run against `datasets/raw/`: 15,103 files audited, **0 corrupted, 0
  zero-length files**, 682 non-standard sample rates (expected — handled by resampling in
  preprocessing), 8,169 near-clipping files flagged (handled by peak normalization), 3 exact
  duplicate files (negligible, left in place). Full report: `reports/dataset_quality_report.md`.
- `scripts/validate_leakage.py` run against `datasets/v1/`: **PASSED** — no `original_recording_id`
  appears in more than one of train/validation/test/external_test.

## Known limitations

- Gunshot class is small (442 segments total, 100 recordings) — C3GD's per-event structure (only 4
  events) limits diversity of true leakage-free gunshot data; fsc22 contributes additional gunshot
  clips (342 segments from 75 distinct source recordings) to partially offset this.
- Background class dominates by design (real-world forest acoustic monitoring is background-heavy);
  this imbalance is corrected for via class weighting at training time, not by discarding data.
