#!/usr/bin/env python3
"""Read-only repository checks for the online-dataset alternative audit."""
import hashlib
import json
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).parents[2]
OUT = ROOT / "reports" / "online_dataset_alternative_audit"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frozen_paths = [
        ROOT / "models/final/final.keras",
        ROOT / "models/final/forest_acoustic_fp32.tflite",
        ROOT / "models/final/forest_acoustic_int8.tflite",
        ROOT / "datasets/v1/train_v1.csv",
        ROOT / "datasets/v1/validation_v1.csv",
        ROOT / "datasets/v1/test_v1.csv",
        ROOT / "datasets/features_cache/train.npz",
        ROOT / "datasets/features_cache/validation.npz",
        ROOT / "datasets/features_cache/test.npz",
    ]
    splits = {name: pd.read_csv(ROOT / "datasets/v1" / f"{name}_v1.csv", low_memory=False) for name in ("train", "validation", "test")}
    all_sources = set().union(*(set(df.original_recording_id.astype(str)) for df in splits.values()))
    candidate = pd.read_csv(ROOT / "datasets/phase4_3_candidate/manifest.csv", low_memory=False)
    candidate_eval_sources = set(splits["validation"].original_recording_id.astype(str)) | set(splits["test"].original_recording_id.astype(str))
    exact_rows = pd.read_csv(ROOT / "reports/phase4_diagnostics/frozen_exact_duplicate_groups.csv")
    config = yaml.safe_load((ROOT / "configs/preprocessing.yaml").read_text())
    metadata = json.loads((ROOT / "models/final/final_metadata.json").read_text())

    result = {
        "audit_scope": "online source investigation only; no external audio downloaded; no training",
        "downloads_performed": 0,
        "frozen_hashes": {str(p): sha256(p) for p in frozen_paths},
        "frozen_manifest_rows": {name: int(len(df)) for name, df in splits.items()},
        "frozen_distinct_sources": int(len(all_sources)),
        "frozen_rows_by_dataset": {name: {str(k): int(v) for k, v in df.dataset_id.value_counts().items()} for name, df in splits.items()},
        "frozen_distinct_sources_by_dataset": {name: {str(k): int(v) for k, v in df.groupby("dataset_id").original_recording_id.nunique().items()} for name, df in splits.items()},
        "phase4_3_candidate_rows": int(len(candidate)),
        "phase4_3_candidate_unique_ids": int(candidate.candidate_id.nunique()),
        "phase4_3_candidate_missing_files": int((~candidate.file_exists.astype(bool)).sum()),
        "phase4_3_candidate_overlap_with_frozen_validation_test_sources": int(candidate.source_recording_id.astype(str).isin(candidate_eval_sources).sum()),
        "frozen_exact_duplicate_rows": int(len(exact_rows)),
        "frozen_exact_duplicate_groups": int(exact_rows.content_sha256.nunique()),
        "frozen_exact_duplicate_cross_split_groups": int(exact_rows.groupby("content_sha256").split.nunique().gt(1).sum()),
        "rodopi_frozen_sources": sorted(set(s for s in all_sources if s.startswith("rodopi_"))),
        "preprocessing_contract": {
            "sample_rate_hz": int(config["target_sample_rate"]),
            "channels": int(config["target_channels"]),
            "window_duration_s": float(config["window_duration"]),
            "hop_duration_s": float(config["hop_duration"]),
            "normalization": config["normalization_method"],
            "target_db": float(config["target_dB"]),
            "n_mels": int(config["mel_spectrogram"]["n_mels"]),
            "n_fft": int(config["mel_spectrogram"]["n_fft"]),
            "feature_hop_length": int(config["mel_spectrogram"]["hop_length"]),
            "power": float(config["mel_spectrogram"]["power"]),
            "filter_enabled": bool(config["filter"]["enabled"]),
        },
        "frozen_model_input_shape": metadata["input_shape"],
        "frozen_feature_mean": metadata["feature_mean"],
        "frozen_feature_std": metadata["feature_std"],
        "eligibility_policy": "No online source is eligible until license/provenance, source-group split protection, file integrity, and human label/event review pass.",
    }
    (OUT / "online_dataset_audit_checks.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
