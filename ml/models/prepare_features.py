#!/usr/bin/env python3
"""
Precompute MFCC + Mel-spectrogram feature caches for train/validation/test/external_test v1 splits.
Reused by baseline, compact CNN, and final model training scripts so features are computed once.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import soundfile as sf
from tqdm import tqdm

ML_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ML_ROOT / "preprocessing"))
from feature_extraction import get_feature_extractor  # noqa: E402

V1_DIR = ML_ROOT / "datasets" / "v1"
import argparse
_ap = argparse.ArgumentParser()
_ap.add_argument('--filtered', action='store_true',
                 help='read filtered 1 s segments from datasets/processed_filtered and write features_cache_filtered')
_ARGS, _ = _ap.parse_known_args()
FILTERED = _ARGS.filtered
CACHE_DIR = ML_ROOT / "datasets" / ("features_cache_filtered" if FILTERED else "features_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

CLASSES = ["background", "chainsaw", "gunshot"]
CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}


def build_cache(split_name: str, csv_path: Path, max_per_class: int = None):
    df = pd.read_csv(csv_path, low_memory=False)
    df = df[df['class'].isin(CLASSES)].reset_index(drop=True)

    if max_per_class is not None:
        df = df.groupby('class', group_keys=False).apply(
            lambda g: g.sample(min(len(g), max_per_class), random_state=42))
        df = df.reset_index(drop=True)

    extractor = get_feature_extractor()
    mfcc_list, mel_list, y_list, ids = [], [], [], []

    for _, row in tqdm(df.iterrows(), total=len(df), desc=split_name):
        wav_path = (ML_ROOT / "datasets" / "processed_filtered" / f"{row['sample_id']}.wav") if FILTERED \
            else ML_ROOT / row['processed_path']
        if not wav_path.exists():
            continue
        try:
            audio, sr = sf.read(wav_path, dtype='float32')
        except Exception:
            continue
        feats = extractor.extract_features(audio, sr, feature_type="both")
        mfcc = feats['mfcc']  # (13, T)
        mel = feats['mel_spectrogram']  # (40, T)
        mfcc_list.append(mfcc)
        mel_list.append(mel)
        y_list.append(CLASS_TO_IDX[row['class']])
        ids.append(row['sample_id'])

    # pad/truncate to common T
    T = min(m.shape[1] for m in mel_list)
    mfcc_arr = np.stack([m[:, :T] for m in mfcc_list]).astype(np.float32)
    mel_arr = np.stack([m[:, :T] for m in mel_list]).astype(np.float32)
    y_arr = np.array(y_list, dtype=np.int64)

    out_path = CACHE_DIR / f"{split_name}.npz"
    np.savez_compressed(out_path, mfcc=mfcc_arr, mel=mel_arr, y=y_arr, ids=np.array(ids))
    print(f"{split_name}: mfcc {mfcc_arr.shape}, mel {mel_arr.shape}, y {y_arr.shape} -> {out_path}")
    return out_path


def main():
    # Cap background for train to keep runtime bounded while staying representative;
    # keep ALL chainsaw/gunshot samples (minority classes).
    build_cache("train", V1_DIR / "train_v1.csv", max_per_class=6000)
    build_cache("validation", V1_DIR / "validation_v1.csv", max_per_class=2000)
    build_cache("test", V1_DIR / "test_v1.csv", max_per_class=None)
    build_cache("external_test", V1_DIR / "external_test_v1.csv", max_per_class=3000)


if __name__ == "__main__":
    main()
