#!/usr/bin/env python3
"""Phase 3 offline replay for frozen v1 predictions.

This script only reads frozen caches/manifests/model and writes new diagnostics.
Validation selects the experimental configuration; locked-test comparisons are
run only after that selection.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf
import tensorflow as tf

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))
from experimental_alert_logic.decision_layer import AlertDecisionLayer, LayerConfig, PredictionRecord
from experimental_alert_logic.metrics import summarize
from experimental_alert_logic.replay import replay

OUT = ROOT / "reports" / "phase3_diagnostics"
CLASSES = ["background", "chainsaw", "gunshot"]


def config_dict(name, config):
    return {"name": name, **config.__dict__}


def make_records(frame):
    records = []
    for row in frame.itertuples(index=False):
        records.append(PredictionRecord(
            recording_id=str(row.original_recording_id), sample_id=str(row.sample_id),
            segment_index=int(row.segment_index), true_class=str(row.true_class),
            predicted_class=str(row.predicted_class),
            scores=(float(row.background_score), float(row.chainsaw_score), float(row.gunshot_score)),
            margin=float(row.probability_margin_uncalibrated), start_s=float(row.estimated_segment_start_s),
        ))
    return records


def load_model_predictions(split):
    manifest = pd.read_csv(ROOT / "datasets/v1" / f"{split}_v1.csv", low_memory=False)
    manifest = manifest.set_index("sample_id", drop=False)
    meta = json.loads((ROOT / "models/final/final_metadata.json").read_text())
    if split == "validation":
        # The repository's validation cache contains only a historical filtered
        # subset. Recompute features from the existing processed WAVs in memory
        # so the full frozen validation manifest is evaluated without changing
        # the cache. The feature implementation is the accepted Phase 2 path.
        sys.path.insert(0, str(ROOT / "preprocessing"))
        from feature_extraction import get_feature_extractor
        extractor = get_feature_extractor()
        ids = manifest.index.astype(str).to_numpy()
        mel = []
        for sample_id in ids:
            row = manifest.loc[sample_id]
            audio, sr = sf.read(ROOT / str(row.processed_path), dtype="float32")
            mel.append(extractor.extract_mel_spectrogram(audio, int(sr)))
        mel = np.asarray(mel, dtype=np.float32)
    else:
        cache = np.load(ROOT / "datasets/features_cache" / f"{split}.npz", allow_pickle=True)
        ids = cache["ids"].astype(str)
        mel = cache["mel"].astype(np.float32)
    x = ((mel - float(meta["feature_mean"])) / float(meta["feature_std"]))[..., None]
    interp = tf.lite.Interpreter(model_path=str(ROOT / "models/final/forest_acoustic_int8.tflite"))
    interp.allocate_tensors()
    inp, out = interp.get_input_details()[0], interp.get_output_details()[0]
    scale, zero = inp["quantization"]
    out_scale, out_zero = out["quantization"]
    rows = []
    for i, sample_id in enumerate(ids):
        q = np.clip(np.round(x[i] / scale + zero), -128, 127).astype(np.int8)
        interp.set_tensor(inp["index"], q[None])
        interp.invoke()
        out_q = interp.get_tensor(out["index"])[0].copy()
        scores = (out_q.astype(np.float32) - out_zero) * out_scale
        pred = int(np.argmax(out_q))
        row = manifest.loc[sample_id]
        top = np.sort(scores)[::-1]
        rows.append({
            "sample_id": sample_id,
            "original_recording_id": str(row.original_recording_id),
            "dataset_id": str(row.dataset_id),
            "true_class": str(row["class"]),
            "predicted_class": CLASSES[pred],
            "true_index": CLASSES.index(str(row["class"])),
            "predicted_index": pred,
            "raw_background_q": int(out_q[0]), "raw_chainsaw_q": int(out_q[1]), "raw_gunshot_q": int(out_q[2]),
            "background_score": float(scores[0]), "chainsaw_score": float(scores[1]), "gunshot_score": float(scores[2]),
            "prediction_confidence_uncalibrated": float(scores[pred]),
            "probability_margin_uncalibrated": float(top[0] - top[1]),
            "segment_index": int(row.segment_index),
            "estimated_segment_start_s": (float(row.interval_start) if pd.notna(row.interval_start) else 0.0) + int(row.segment_index) * 0.5,
        })
    return pd.DataFrame(rows)


def add_decision_columns(frame, decisions):
    out = frame.copy()
    out["operational_state"] = [d.operational_state for d in decisions]
    out["decision_class"] = [d.decision_class for d in decisions]
    out["confirmed"] = [d.confirmed for d in decisions]
    out["candidate_alert"] = [d.candidate_alert for d in decisions]
    out["alert_emitted"] = [d.alert_emitted for d in decisions]
    out["suppressed"] = [d.suppressed for d in decisions]
    out["suppression_reason"] = [d.suppression_reason for d in decisions]
    out["uncertain_reason"] = [d.uncertain_reason for d in decisions]
    out["state_transition"] = [d.transition for d in decisions]
    return out


def evaluate(frame, config):
    records = make_records(frame)
    decisions = replay(records, AlertDecisionLayer(config))
    return summarize(records, decisions), decisions


def candidate_configs():
    result = [("baseline_single_window", LayerConfig())]
    for name, s, h, g in [("temporal_2_of_2", 2, 2, 1), ("temporal_2_of_3", 2, 3, 2), ("temporal_3_of_4", 3, 4, 2)]:
        result.append((name, LayerConfig(temporal_enabled=True, temporal_support=s, temporal_history=h, temporal_max_gap=g)))
    for margin in (0.10, 0.20, 0.30):
        result.append((f"reject_margin_{margin:.2f}", LayerConfig(reject_enabled=True, reject_margin=margin)))
    for quiet in (2, 4, 6):
        result.append((f"duplicate_quiet_{quiet}_windows", LayerConfig(duplicate_enabled=True, duplicate_quiet_windows=quiet)))
    return result


def choose_validation_configs(validation_results, baseline):
    event_floor = 0.80 * baseline["per_class_recall"]["chainsaw"]
    event_floor_g = 0.80 * baseline["per_class_recall"]["gunshot"]
    temporal = [(n, r) for n, r in validation_results.items() if n.startswith("temporal_") and r["per_class_recall"]["chainsaw"] >= event_floor and r["per_class_recall"]["gunshot"] >= event_floor_g and r["background_false_positive_rate"] < baseline["background_false_positive_rate"]]
    selected_temporal = max(temporal, key=lambda item: item[1]["macro_f1"])[0] if temporal else "baseline_single_window"
    rejects = [(n, r) for n, r in validation_results.items() if n.startswith("reject_") and r["per_class_recall"]["chainsaw"] >= event_floor and r["per_class_recall"]["gunshot"] >= event_floor_g and r["background_false_positive_rate"] < baseline["background_false_positive_rate"]]
    selected_reject = max(rejects, key=lambda item: item[1]["macro_f1"])[0] if rejects else "baseline_single_window"
    # Duplicate quiet period is an operational proxy; choose the conservative
    # 2-second quiet episode (4 half-second hops), not by test performance.
    selected_duplicate = "duplicate_quiet_4_windows"
    selected = {
        "temporal": selected_temporal,
        "reject": selected_reject,
        "duplicate": selected_duplicate,
    }
    return selected


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frozen_paths = [ROOT / "models/final/final.keras", ROOT / "models/final/forest_acoustic_fp32.tflite", ROOT / "models/final/forest_acoustic_int8.tflite", ROOT / "datasets/v1/train_v1.csv", ROOT / "datasets/v1/validation_v1.csv", ROOT / "datasets/v1/test_v1.csv", ROOT / "datasets/features_cache/train.npz", ROOT / "datasets/features_cache/validation.npz", ROOT / "datasets/features_cache/test.npz"]
    hashes_before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in frozen_paths}
    val = load_model_predictions("validation")
    test = load_model_predictions("test")
    phase1 = pd.read_csv(ROOT / "reports/phase1_diagnostics/predictions.csv")
    canonical_match = bool(np.array_equal(test.sample_id.values, phase1.sample_id.values) and np.array_equal(test.predicted_class.values, phase1.predicted_class.values))
    pd.DataFrame({"split": ["validation", "test"], "rows": [len(val), len(test)], "canonical_test_prediction_match": [None, canonical_match]}).to_csv(OUT / "replay_input_summary.csv", index=False)

    configs = dict(candidate_configs())
    validation_results = {}
    validation_rows = []
    for name, cfg in configs.items():
        result, decisions = evaluate(val, cfg)
        validation_results[name] = result
        validation_rows.append({"configuration": name, **result})
    pd.DataFrame(validation_rows).to_json(OUT / "validation_comparison.json", orient="records", indent=2)

    selected = choose_validation_configs(validation_results, validation_results["baseline_single_window"])
    temporal_cfg = configs[selected["temporal"]] if selected["temporal"] != "baseline_single_window" else LayerConfig()
    reject_cfg = configs[selected["reject"]] if selected["reject"] != "baseline_single_window" else LayerConfig()
    combined_cfg = LayerConfig(
        temporal_enabled=temporal_cfg.temporal_enabled,
        temporal_support=temporal_cfg.temporal_support,
        temporal_history=temporal_cfg.temporal_history,
        temporal_max_gap=temporal_cfg.temporal_max_gap,
        reject_enabled=reject_cfg.reject_enabled,
        reject_margin=reject_cfg.reject_margin,
        duplicate_enabled=True,
        duplicate_quiet_windows=4,
    )
    selected_cfgs = {
        "baseline_single_window": LayerConfig(),
        "temporal_confirmation_only": temporal_cfg,
        "reject_state_only": reject_cfg,
        "duplicate_suppression_only": LayerConfig(duplicate_enabled=True, duplicate_quiet_windows=4),
        "temporal_plus_reject": LayerConfig(temporal_enabled=temporal_cfg.temporal_enabled, temporal_support=temporal_cfg.temporal_support, temporal_history=temporal_cfg.temporal_history, temporal_max_gap=temporal_cfg.temporal_max_gap, reject_enabled=reject_cfg.reject_enabled, reject_margin=reject_cfg.reject_margin),
        "temporal_plus_duplicate": LayerConfig(temporal_enabled=temporal_cfg.temporal_enabled, temporal_support=temporal_cfg.temporal_support, temporal_history=temporal_cfg.temporal_history, temporal_max_gap=temporal_cfg.temporal_max_gap, duplicate_enabled=True, duplicate_quiet_windows=4),
        "all_three": combined_cfg,
    }
    locked_rows = []
    test_replays = {}
    for name, cfg in selected_cfgs.items():
        result, decisions = evaluate(test, cfg)
        locked_rows.append({"configuration": name, **result})
        test_replays[name] = add_decision_columns(test, decisions)
    pd.DataFrame(locked_rows).to_json(OUT / "locked_test_comparison.json", orient="records", indent=2)
    chosen_name = "all_three"
    test_replays[chosen_name].to_csv(OUT / "per_window_replay.csv", index=False)
    test_replays[chosen_name][test_replays[chosen_name].suppressed].to_csv(OUT / "suppressed_candidates.csv", index=False)
    test_replays[chosen_name][test_replays[chosen_name].state_transition.astype(bool)].to_csv(OUT / "alert_state_transitions.csv", index=False)

    hashes_after = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in frozen_paths}
    manifest = {
        "selection_split": "validation",
        "test_locked_until_selection": True,
        "canonical_test_prediction_match": canonical_match,
        "configurations_evaluated": [name for name, _ in configs.items()] + list(selected_cfgs),
        "selected_components": selected,
        "selected_test_configuration": chosen_name,
        "temporal_rule": "2 positive windows of the same event class within 2 half-second-indexed windows, maximum gap 1; state resets per recording",
        "reject_rule": "validation-selected margin rule, if any; scores are uncalibrated",
        "duplicate_rule": "same-class alerts suppressed while active; episode quiet period is 4 windows = 2.0 seconds; separate state per event class",
        "event_level_metrics": "unavailable: no reliable event interval and recording-time denominator in frozen replay inputs",
        "hashes_before": hashes_before,
        "hashes_after": hashes_after,
        "hashes_unchanged": hashes_before == hashes_after,
    }
    (OUT / "configuration_manifest.json").write_text(json.dumps(manifest, indent=2))
    summary = {"validation": validation_results, "selected_components": selected, "locked_test": {row["configuration"]: row for row in locked_rows}, "canonical_test_prediction_match": canonical_match}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({"selected": selected, "canonical_test_prediction_match": canonical_match, "test_all_three": summary["locked_test"]["all_three"]}, indent=2))


if __name__ == "__main__":
    main()
