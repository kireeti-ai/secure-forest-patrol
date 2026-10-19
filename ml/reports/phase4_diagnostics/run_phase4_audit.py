#!/usr/bin/env python3
"""Phase 4 read-only dataset audit and isolated candidate-manifest builder."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf

ROOT = Path(__file__).parents[2]
OUT = ROOT / "reports" / "phase4_diagnostics"
CANDIDATE_DIR = ROOT / "datasets" / "phase4_candidate"
LICENSES = {
    "c3gd": "CC BY 4.0; attribution and license URL recorded",
    "esc50_hf": "CC BY-NC 3.0; non-commercial restriction recorded",
    "rfcx_frugalai": "CC BY-NC 4.0; non-commercial restriction recorded",
    "fsc22": "Unknown; license verification required",
    "rodopi": "Unknown/likely CC BY in project metadata; verification required",
    "sensing_forest": "CC0 1.0; attribution optional, source recorded",
}
TARGET_BG_CATEGORIES = {
    "fsc22": {"BirdChirping": "bird_calls", "Insect": "insects", "Wind": "wind", "Squirrel": "animal_activity", "Rain": "rain", "WaterDrops": "water_drops", "Thunderstorm": "storm", "WingFlaping": "animal_activity"},
    "esc50_hf": {"chirping_birds": "bird_calls", "insects": "insects", "wind": "wind", "engine": "engine_like", "crow": "bird_calls", "rain": "rain", "crackling_fire": "transient_environment", "footsteps": "human_activity", "thunderstorm": "storm", "water_drops": "water_drops", "frog": "animal_activity", "crickets": "insects"},
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def split_map():
    result = {}
    for split in ("train", "validation", "test"):
        d = pd.read_csv(ROOT / "datasets/v1" / f"{split}_v1.csv", low_memory=False)
        for source in d.original_recording_id.astype(str).unique():
            result[source] = split
    return result


def audio_stats(path):
    try:
        audio, sr = sf.read(path, dtype="float32")
        audio = np.asarray(audio)
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        return {"audio_valid": True, "sample_rate": int(sr), "channels": 1 if audio.ndim == 1 else int(audio.shape[1]), "duration_s": float(len(audio) / sr), "rms": float(np.sqrt(np.mean(audio ** 2))) if len(audio) else 0.0, "peak": float(np.max(np.abs(audio))) if len(audio) else 0.0, "clipped_ge_0.95": bool(np.any(np.abs(audio) >= 0.95)), "error": ""}
    except Exception as exc:
        return {"audio_valid": False, "sample_rate": None, "channels": None, "duration_s": None, "rms": None, "peak": None, "clipped_ge_0.95": None, "error": str(exc)}


def source_failure_inventory(fp, fn, source_summary, split_membership):
    rows = []
    keys = set(fp.original_recording_id.astype(str)) | set(fn.original_recording_id.astype(str))
    for source in sorted(keys):
        f = fp[fp.original_recording_id.astype(str) == source]
        n = fn[fn.original_recording_id.astype(str) == source]
        base = (f.iloc[0] if len(f) else n.iloc[0])
        errors = []
        if len(f[f.predicted_class == "chainsaw"]): errors.append("background_to_chainsaw")
        if len(f[f.predicted_class == "gunshot"]): errors.append("background_to_gunshot")
        if len(n[n.true_class == "chainsaw"]): errors.append("chainsaw_to_background")
        if len(n[n.true_class == "gunshot"]): errors.append("gunshot_to_background")
        summary = source_summary[source_summary.original_recording_id.astype(str) == source]
        s = summary.iloc[0] if len(summary) else None
        rows.append({
            "source_recording_id": source, "dataset_id": str(base.dataset_id), "split_membership": split_membership.get(source, "not_in_frozen_v1"),
            "original_label": str(base.true_class), "total_test_windows": int(s.total_test_windows) if s is not None else len(f) + len(n),
            "background_fp_windows": int(len(f)), "background_to_chainsaw_windows": int((f.predicted_class == "chainsaw").sum()), "background_to_gunshot_windows": int((f.predicted_class == "gunshot").sum()),
            "chainsaw_fn_windows": int((n.true_class == "chainsaw").sum()), "gunshot_fn_windows": int((n.true_class == "gunshot").sum()),
            "error_types": ";".join(errors), "observed_test_coverage_s": float((s.total_test_windows * 0.5 + 0.5) if s is not None else np.nan),
            "event_timestamp_available": bool(f.event_interval_id.notna().any() or n.event_interval_id.notna().any()),
            "event_timestamp_values": ";".join(sorted(set(pd.concat([f.event_interval_id, n.event_interval_id]).dropna().astype(str)))),
            "metadata_notes": "Source-level grouping; overlapping windows are correlated. No acoustic cause inferred without review.",
        })
    return pd.DataFrame(rows)


def build_hard_candidates(fp, train, split_membership):
    rows = []
    # Test failures are evidence for review, never training candidates.
    for source, g in fp.groupby("original_recording_id", sort=True):
        dominant = "chainsaw" if (g.predicted_class == "chainsaw").sum() >= (g.predicted_class == "gunshot").sum() else "gunshot"
        subtype = str(g.fsc22_class_name.dropna().iloc[0]) if g.fsc22_class_name.notna().any() else str(g.esc50_category.dropna().iloc[0]) if g.esc50_category.notna().any() else "unresolved_background_source"
        rows.append({"candidate_id": f"fp_test_{source}", "source_recording_id": source, "source_dataset": str(g.dataset_id.iloc[0]), "proposed_background_subtype": subtype, "original_label": "background", "proposed_label": "background", "label_verification_status": "source_label_only; human acoustic review not performed", "model_failure_evidence": f"{len(g)} background FP windows; dominant prediction {dominant}", "split_membership": "test", "license_attribution_status": LICENSES.get(str(g.dataset_id.iloc[0]), "unknown"), "inclusion_recommendation": "exclude_from_candidate_training", "reason": "Frozen test overlap; retain only as review evidence", "representative_sample_id": str(g.sample_id.iloc[0]), "representative_audio_path": str(g.audio_path.iloc[0])})
    # Training-only source-level candidates from known environmental categories.
    for dataset, mapping in TARGET_BG_CATEGORIES.items():
        d = train[(train.dataset_id == dataset) & (train["class"] == "background")].copy()
        category_col = "fsc22_class_name" if dataset == "fsc22" else "esc50_category"
        d["subtype"] = d[category_col].map(mapping)
        d = d[d.subtype.notna()]
        for subtype, group in d.groupby("subtype"):
            # One representative segment per source prevents window multiplication.
            for source, source_group in group.groupby("original_recording_id"):
                row = source_group.sort_values(["segment_index", "sample_id"]).iloc[0]
                license_status = LICENSES[dataset]
                permitted = dataset in {"esc50_hf", "rfcx_frugalai"}
                rows.append({"candidate_id": f"train_bg_{row.sample_id}", "source_recording_id": source, "source_dataset": dataset, "proposed_background_subtype": subtype, "original_label": "background", "proposed_label": "background", "label_verification_status": "dataset category; acoustic verification required", "model_failure_evidence": "coverage candidate; not claimed to be a model error", "split_membership": "train", "license_attribution_status": license_status, "inclusion_recommendation": "candidate_training_research_only" if permitted else "quarantine_license_review", "reason": "One source-level representative from documented background subtype", "representative_sample_id": str(row.sample_id), "representative_audio_path": str(ROOT / row.processed_path)})
    return pd.DataFrame(rows)


def build_target_candidates(fn, train, split_membership):
    rows = []
    for source, g in fn.groupby("original_recording_id", sort=True):
        rows.append({"candidate_id": f"fn_test_{source}", "source_recording_id": source, "event_class": str(g.true_class.iloc[0]), "source_dataset": str(g.dataset_id.iloc[0]), "failure_evidence": f"{len(g)} missed target windows; median RMS {g.audio_rms_energy.median():.6f}", "rms_or_snr_information": f"median_rms={g.audio_rms_energy.median():.6f}; no SNR estimate", "event_boundary_information": "event interval unavailable" if g.event_interval_id.isna().all() else "event interval ID present; exact timing not independently reviewed", "label_confidence": "source label; manual review pending", "split_membership": "test", "recommended_action": "quarantine_review_only", "reason": "Frozen test overlap; do not add to training", "representative_sample_id": str(g.sample_id.iloc[0]), "representative_audio_path": str(g.audio_path.iloc[0])})
    # Low-energy training coverage candidates: one lowest-RMS source segment.
    target = train[train["class"].isin(["chainsaw", "gunshot"])].copy()
    for (dataset, cls), d in target.groupby(["dataset_id", "class"]):
        stats = []
        for source, sg in d.groupby("original_recording_id"):
            row = sg.iloc[0]
            path = ROOT / row.processed_path
            st = audio_stats(path)
            if st["audio_valid"]:
                stats.append((st["rms"], source, row, st))
        for rms, source, row, st in sorted(stats)[:10]:
            rows.append({"candidate_id": f"train_low_{row.sample_id}", "source_recording_id": source, "event_class": cls, "source_dataset": dataset, "failure_evidence": "low-energy coverage candidate; not a confirmed model failure", "rms_or_snr_information": f"rms={rms:.6f}; peak={st['peak']:.6f}", "event_boundary_information": "event interval metadata available" if pd.notna(row.event_interval_id) else "event interval unavailable", "label_confidence": "dataset/source label only", "split_membership": "train", "recommended_action": "candidate_training_research_only" if dataset in {"c3gd", "esc50_hf", "rfcx_frugalai"} else "quarantine_license_or_label_review", "reason": "One low-energy source-level representative; avoid overlapping-window duplication", "representative_sample_id": str(row.sample_id), "representative_audio_path": str(ROOT / row.processed_path)})
    return pd.DataFrame(rows)


def provenance_audit(candidate_frames, train, split_membership):
    all_rows = pd.concat(candidate_frames, ignore_index=True)
    train_by_source = train.set_index("sample_id")
    rows = []
    hashes = {}
    for row in all_rows.itertuples(index=False):
        sample_id = row.candidate_id.split("train_bg_")[-1] if row.candidate_id.startswith("train_bg_") else row.candidate_id.split("train_low_")[-1] if row.candidate_id.startswith("train_low_") else ""
        path = None
        representative_path = getattr(row, "representative_audio_path", "")
        if representative_path and representative_path != "nan":
            path = Path(representative_path)
        if sample_id in train_by_source.index and path is None:
            path = ROOT / str(train_by_source.loc[sample_id].processed_path)
        st = audio_stats(path) if path else {"audio_valid": None, "sample_rate": None, "channels": None, "duration_s": None, "rms": None, "peak": None, "clipped_ge_0.95": None, "error": "frozen test evidence or no source path in candidate row"}
        content_hash = sha256(path) if path and path.exists() else ""
        if content_hash:
            hashes.setdefault(content_hash, 0)
            hashes[content_hash] += 1
        rows.append({"candidate_id": row.candidate_id, "source_recording_id": row.source_recording_id, "dataset_id": getattr(row, "source_dataset", ""), "split_membership": getattr(row, "split_membership", ""), "parent_recording_id": row.source_recording_id, "source_path_or_reference": str(path) if path else "phase1_diagnostics_only", "content_sha256": content_hash, "exact_duplicate_candidate_count": "pending", "near_duplicate_analysis": "not proven; source IDs and exact hashes used; audio fingerprint review remains recommended", "audio_valid": st["audio_valid"], "sample_rate": st["sample_rate"], "channels": st["channels"], "duration_s": st["duration_s"], "rms": st["rms"], "peak": st["peak"], "clipped_ge_0.95": st["clipped_ge_0.95"], "license_status": LICENSES.get(getattr(row, "source_dataset", ""), "unknown"), "label_provenance": getattr(row, "label_verification_status", ""), "leakage_result": "PASS" if getattr(row, "split_membership", "") == "train" else "EXCLUDED_FROZEN_NONTRAIN_SPLIT", "recommended_action": getattr(row, "inclusion_recommendation", getattr(row, "recommended_action", "review"))})
    out = pd.DataFrame(rows)
    out["exact_duplicate_candidate_count"] = out["content_sha256"].map(hashes).fillna(0).astype(int)
    return out


def frozen_exact_duplicate_audit():
    rows = []
    seen_paths = set()
    for split in ("train", "validation", "test"):
        d = pd.read_csv(ROOT / "datasets/v1" / f"{split}_v1.csv", low_memory=False)
        for row in d.itertuples(index=False):
            path = ROOT / str(row.processed_path)
            if str(path) in seen_paths:
                continue
            seen_paths.add(str(path))
            rows.append({"split": split, "sample_id": str(row.sample_id), "source_recording_id": str(row.original_recording_id), "dataset_id": str(row.dataset_id), "content_sha256": sha256(path) if path.exists() else "", "audio_path": str(path)})
    out = pd.DataFrame(rows)
    if len(out):
        counts = out.content_sha256.value_counts()
        out["exact_duplicate_count"] = out.content_sha256.map(counts).fillna(0).astype(int)
        out = out[out.exact_duplicate_count > 1].sort_values(["content_sha256", "split", "sample_id"])
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    CANDIDATE_DIR.mkdir(parents=True, exist_ok=True)
    frozen = [ROOT / "models/final/final.keras", ROOT / "models/final/forest_acoustic_fp32.tflite", ROOT / "models/final/forest_acoustic_int8.tflite", ROOT / "datasets/v1/train_v1.csv", ROOT / "datasets/v1/validation_v1.csv", ROOT / "datasets/v1/test_v1.csv", ROOT / "datasets/features_cache/train.npz", ROOT / "datasets/features_cache/validation.npz", ROOT / "datasets/features_cache/test.npz"]
    hashes_before = {str(p): sha256(p) for p in frozen}
    split_membership = split_map()
    fp = pd.read_csv(ROOT / "reports/phase1_diagnostics/false_positives.csv")
    fn = pd.read_csv(ROOT / "reports/phase1_diagnostics/false_negatives.csv")
    source_summary = pd.read_csv(ROOT / "reports/phase1_diagnostics/source_recording_summary.csv")
    train = pd.read_csv(ROOT / "datasets/v1/train_v1.csv", low_memory=False)
    source_inventory = source_failure_inventory(fp, fn, source_summary, split_membership)
    hard = build_hard_candidates(fp, train, split_membership)
    target = build_target_candidates(fn, train, split_membership)
    provenance = provenance_audit([hard, target], train, split_membership)
    duplicate_groups = frozen_exact_duplicate_audit()
    source_inventory.to_csv(OUT / "failure_source_inventory.csv", index=False)
    hard.to_csv(OUT / "hard_negative_candidates.csv", index=False)
    target.to_csv(OUT / "target_event_candidates.csv", index=False)
    provenance.to_csv(OUT / "provenance_and_label_audit.csv", index=False)
    duplicate_groups.to_csv(OUT / "frozen_exact_duplicate_groups.csv", index=False)

    # Candidate manifest contains only training-source candidates, with review
    # gates preserved. Frozen validation/test evidence is intentionally omitted.
    candidate_rows = []
    for frame in (hard, target):
        for row in frame[frame.split_membership == "train"].itertuples(index=False):
            sample_id = row.candidate_id.split("train_bg_")[-1] if row.candidate_id.startswith("train_bg_") else row.candidate_id.split("train_low_")[-1]
            source_row = train[train.sample_id == sample_id].iloc[0]
            path = ROOT / source_row.processed_path
            candidate_rows.append({"candidate_id": row.candidate_id, "sample_id": sample_id, "source_recording_id": row.source_recording_id, "parent_recording_id": row.source_recording_id, "source_dataset": getattr(row, "source_dataset", ""), "original_label": source_row["class"], "verified_label": "", "label_verification_status": getattr(row, "label_verification_status", getattr(row, "label_confidence", "")), "original_split_membership": "train", "proposed_future_split_group": f"phase4_{row.source_recording_id}", "audio_path": str(path), "content_sha256": sha256(path), "license_attribution": LICENSES.get(getattr(row, "source_dataset", ""), "unknown"), "candidate_status": getattr(row, "inclusion_recommendation", getattr(row, "recommended_action", "review")), "reason": getattr(row, "reason", "")})
    candidate_manifest = pd.DataFrame(candidate_rows).drop_duplicates(subset=["sample_id"])
    if len(candidate_manifest):
        candidate_manifest["duplicate_content_count"] = candidate_manifest["content_sha256"].map(candidate_manifest["content_sha256"].value_counts())
        candidate_manifest.loc[candidate_manifest.duplicate_content_count > 1, "candidate_status"] = "quarantine_exact_duplicate"
        candidate_manifest = candidate_manifest.sort_values(["content_sha256", "candidate_id"]).drop_duplicates(subset=["content_sha256"], keep="first")
    candidate_manifest.to_csv(CANDIDATE_DIR / "manifest.csv", index=False)

    hashes_after = {str(p): sha256(p) for p in frozen}
    summary = {"phase1_verified": {"background_fp_windows": int(len(fp)), "background_fp_recordings": int(fp.original_recording_id.nunique()), "target_fn_windows": int(len(fn)), "target_fn_recordings": int(fn.original_recording_id.nunique())}, "failure_inventory_sources": int(len(source_inventory)), "hard_negative_rows": int(len(hard)), "hard_negative_training_candidate_rows": int((hard.split_membership == "train").sum()), "target_event_rows": int(len(target)), "target_training_candidate_rows": int((target.split_membership == "train").sum()), "candidate_manifest_rows": int(len(candidate_manifest)), "candidate_manifest_sources": int(candidate_manifest.source_recording_id.nunique()) if len(candidate_manifest) else 0, "candidate_status_counts": candidate_manifest.candidate_status.value_counts().to_dict() if len(candidate_manifest) else {}, "frozen_exact_duplicate_sample_rows": int(len(duplicate_groups)), "frozen_exact_duplicate_hash_groups": int(duplicate_groups.content_sha256.nunique()) if len(duplicate_groups) else 0, "license_note": "No external data acquired; unknown licenses remain quarantined and non-commercial datasets retain restrictions", "frozen_hashes_before": hashes_before, "frozen_hashes_after": hashes_after, "frozen_hashes_unchanged": hashes_before == hashes_after, "frozen_artifacts_modified": False, "retraining_performed": False, "threshold_tuning_performed": False}
    (OUT / "phase4_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
