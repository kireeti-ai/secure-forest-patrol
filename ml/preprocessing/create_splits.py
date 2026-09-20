#!/usr/bin/env python3
"""
Create the frozen v1 train/validation/test/external_test splits from the
segment-level master manifest produced by audio_preprocess.py.

Grouping is done by `original_recording_id` so no segments from the same
source recording end up in more than one split (prevents leakage).

An external_test set is carved out from held-out sources that never appear
in train/val/test: sensing_forest recordings + one held-out c3gd event +
held-out rodopi recordings.
"""
import numpy as np
import pandas as pd
from pathlib import Path

RANDOM_SEED = 42
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

ML_ROOT = Path(__file__).parent.parent
MANIFESTS_DIR = ML_ROOT / "datasets" / "manifests"
V1_DIR = ML_ROOT / "datasets" / "v1"


def main():
    V1_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(MANIFESTS_DIR / "master_manifest.csv")
    print(f"Loaded {len(df)} segments from master_manifest.csv")

    rng = np.random.RandomState(RANDOM_SEED)

    # ---- external test carve-out (held-out sources, never touched by train/val/test) ----
    ext_mask = df['dataset_id'] == 'sensing_forest'
    if 'event_id' in df.columns:
        c3gd_events = sorted(df.loc[df['dataset_id'] == 'c3gd', 'event_id'].dropna().unique())
        if len(c3gd_events) > 1:
            held_out_event = c3gd_events[-1]
            ext_mask = ext_mask | ((df['dataset_id'] == 'c3gd') & (df['event_id'] == held_out_event))
    rodopi_recordings = sorted(df.loc[df['dataset_id'] == 'rodopi', 'original_recording_id'].dropna().unique())
    if len(rodopi_recordings) > 2:
        rng.shuffle(rodopi_recordings)
        held_out_rodopi = set(rodopi_recordings[:2])
        ext_mask = ext_mask | ((df['dataset_id'] == 'rodopi') & df['original_recording_id'].isin(held_out_rodopi))

    external_df = df[ext_mask].copy()
    remaining_df = df[~ext_mask].copy()

    # ---- grouped 70/15/15 split on remaining recordings ----
    unique_recordings = remaining_df['original_recording_id'].unique()
    rng.shuffle(unique_recordings)
    n = len(unique_recordings)
    n_train = int(n * TRAIN_RATIO)
    n_val = int(n * VAL_RATIO)

    train_ids = set(unique_recordings[:n_train])
    val_ids = set(unique_recordings[n_train:n_train + n_val])
    test_ids = set(unique_recordings[n_train + n_val:])

    def assign(rid):
        if rid in train_ids:
            return 'train'
        elif rid in val_ids:
            return 'validation'
        else:
            return 'test'

    remaining_df['split'] = remaining_df['original_recording_id'].apply(assign)

    train_df = remaining_df[remaining_df['split'] == 'train'].drop(columns=['split'])
    val_df = remaining_df[remaining_df['split'] == 'validation'].drop(columns=['split'])
    test_df = remaining_df[remaining_df['split'] == 'test'].drop(columns=['split'])

    # ---- leakage assertion ----
    assert not (set(train_df['original_recording_id']) & set(val_df['original_recording_id']))
    assert not (set(train_df['original_recording_id']) & set(test_df['original_recording_id']))
    assert not (set(val_df['original_recording_id']) & set(test_df['original_recording_id']))
    assert not (set(train_df['original_recording_id']) & set(external_df['original_recording_id']))
    assert not (set(val_df['original_recording_id']) & set(external_df['original_recording_id']))
    assert not (set(test_df['original_recording_id']) & set(external_df['original_recording_id']))

    # ---- save ----
    df.to_csv(V1_DIR / "master_v1.csv", index=False)
    train_df.to_csv(V1_DIR / "train_v1.csv", index=False)
    val_df.to_csv(V1_DIR / "validation_v1.csv", index=False)
    test_df.to_csv(V1_DIR / "test_v1.csv", index=False)
    external_df.to_csv(V1_DIR / "external_test_v1.csv", index=False)

    print("\n=== V1 split sizes (segments) ===")
    for name, d in [('train', train_df), ('validation', val_df), ('test', test_df), ('external_test', external_df)]:
        print(f"{name}: {len(d)} segments, {d['original_recording_id'].nunique()} recordings")
        print(d['class'].value_counts().to_dict())

    print("\nSaved v1 splits to", V1_DIR)


if __name__ == "__main__":
    main()
