#!/usr/bin/env python3
"""Non-mutating Phase 1 audit of the frozen v1 test artifacts."""
import hashlib
import json
from pathlib import Path

import librosa
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import soundfile as sf
import tensorflow as tf
from sklearn.metrics import (accuracy_score, balanced_accuracy_score,
                             confusion_matrix, f1_score, precision_score,
                             recall_score)

ROOT = Path(__file__).parents[2]
OUT = ROOT / "reports" / "phase1_diagnostics"
CLASSES = ["background", "chainsaw", "gunshot"]
IDX = {name: i for i, name in enumerate(CLASSES)}


def read_audio(path):
    if not path.exists():
        return None, None, None, "missing_file"
    try:
        audio, sr = sf.read(path, always_2d=False, dtype="float32")
        audio = np.asarray(audio)
        if audio.ndim == 1:
            channels, mono = 1, audio
        else:
            channels, mono = audio.shape[1], audio.mean(axis=1)
        stats = {
            "duration_s": float(len(mono) / sr),
            "sample_rate": int(sr),
            "channels": int(channels),
            "peak_amplitude": float(np.max(np.abs(mono))) if len(mono) else 0.0,
            "rms_energy": float(np.sqrt(np.mean(np.square(mono)))) if len(mono) else 0.0,
            "clip_ratio_ge_0.95": float(np.mean(np.abs(mono) >= 0.95)) if len(mono) else 0.0,
        }
        return mono, sr, stats, ""
    except Exception as exc:  # record, do not silently skip
        return None, None, None, repr(exc)


def error_stats(sub):
    return {
        "windows": int(len(sub)),
        "recordings": int(sub.original_recording_id.nunique()),
        "datasets": sub.dataset_id.value_counts().to_dict(),
        "mean_confidence": float(sub.prediction_confidence.mean()) if len(sub) else None,
        "median_confidence": float(sub.prediction_confidence.median()) if len(sub) else None,
        "mean_margin": float(sub.probability_margin.mean()) if len(sub) else None,
        "median_margin": float(sub.probability_margin.median()) if len(sub) else None,
        "rms_median": float(sub.audio_rms_energy.median()) if sub.audio_rms_energy.notna().any() else None,
        "peak_median": float(sub.audio_peak_amplitude.median()) if sub.audio_peak_amplitude.notna().any() else None,
        "clipped_windows": int((sub["audio_clip_ratio_ge_0.95"] > 0).sum()) if sub["audio_clip_ratio_ge_0.95"].notna().any() else None,
    }


def distribution_stats(sub):
    if not len(sub):
        return {"count": 0}
    return {
        "count": int(len(sub)),
        "confidence_q10_q50_q90": [float(x) for x in sub.prediction_confidence.quantile([0.1, 0.5, 0.9]).tolist()],
        "margin_q10_q50_q90": [float(x) for x in sub.probability_margin.quantile([0.1, 0.5, 0.9]).tolist()],
        "rms_q10_q50_q90": [float(x) for x in sub.audio_rms_energy.quantile([0.1, 0.5, 0.9]).tolist()],
        "peak_q10_q50_q90": [float(x) for x in sub.audio_peak_amplitude.quantile([0.1, 0.5, 0.9]).tolist()],
    }


def source_summary(df):
    rows = []
    for (recording_id, dataset_id), group in df.groupby(
        ["original_recording_id", "dataset_id"], sort=True
    ):
        bg = int((group.true_class == "background").sum())
        chainsaw = int((group.true_class == "chainsaw").sum())
        gunshot = int((group.true_class == "gunshot").sum())
        bg_fp = (group.true_class == "background") & (group.predicted_class != "background")
        rows.append({
            "original_recording_id": recording_id,
            "dataset_id": dataset_id,
            "total_test_windows": int(len(group)),
            "background_windows": bg,
            "chainsaw_windows": chainsaw,
            "gunshot_windows": gunshot,
            "background_fp_windows": int(bg_fp.sum()),
            "background_to_chainsaw": int(((group.true_class == "background") & (group.predicted_class == "chainsaw")).sum()),
            "background_to_gunshot": int(((group.true_class == "background") & (group.predicted_class == "gunshot")).sum()),
            "chainsaw_fn_to_background": int(((group.true_class == "chainsaw") & (group.predicted_class == "background")).sum()),
            "gunshot_fn_to_background": int(((group.true_class == "gunshot") & (group.predicted_class == "background")).sum()),
            "background_fp_rate": float(bg_fp.sum() / bg) if bg else None,
            "chainsaw_fn_rate": float(((group.true_class == "chainsaw") & (group.predicted_class == "background")).sum() / chainsaw) if chainsaw else None,
            "gunshot_fn_rate": float(((group.true_class == "gunshot") & (group.predicted_class == "background")).sum() / gunshot) if gunshot else None,
        "mean_rms": float(group.audio_rms_energy.mean()) if group.audio_rms_energy.notna().any() else None,
        "mean_peak": float(group.audio_peak_amplitude.mean()) if group.audio_peak_amplitude.notna().any() else None,
        })
    return pd.DataFrame(rows)


def representative_plots(df, failures):
    reps = []
    categories = {
        "background_to_chainsaw": (df.true_class == "background") & (df.predicted_class == "chainsaw"),
        "background_to_gunshot": (df.true_class == "background") & (df.predicted_class == "gunshot"),
        "chainsaw_to_background": (df.true_class == "chainsaw") & (df.predicted_class == "background"),
        "gunshot_to_background": (df.true_class == "gunshot") & (df.predicted_class == "background"),
    }
    for category, mask in categories.items():
        chosen = []
        for _, row in df[mask].sort_values("prediction_confidence", ascending=False).iterrows():
            if row.original_recording_id not in {item.original_recording_id for item in chosen}:
                chosen.append(row)
            if len(chosen) == 4:
                break
        for row in chosen:
            reps.append({
                "category": category,
                "sample_id": row.sample_id,
                "original_recording_id": row.original_recording_id,
                "dataset_id": row.dataset_id,
                "audio_path": row.audio_path,
                "predicted_class": row.predicted_class,
                "prediction_confidence": row.prediction_confidence,
            })
            audio, sr, _, error = read_audio(Path(row.audio_path))
            if error:
                failures.append({"sample_id": row.sample_id, "audio_path": row.audio_path, "error": error, "stage": "plot"})
                continue
            try:
                mel = librosa.feature.melspectrogram(
                    y=audio, sr=sr, n_fft=512, hop_length=160, n_mels=40,
                    fmax=min(8000, sr / 2), power=2.0,
                )
                mel_db = librosa.power_to_db(mel, ref=np.max)
                fig, (ax_wave, ax_mel) = plt.subplots(2, 1, figsize=(10, 6), constrained_layout=True)
                time = np.arange(len(audio)) / sr
                ax_wave.plot(time, audio, linewidth=0.5)
                ax_wave.set_title(f"{category} | {row.sample_id} | true={row.true_class}, pred={row.predicted_class}, score={row.prediction_confidence:.3f}")
                ax_wave.set_xlabel("seconds")
                ax_wave.set_ylabel("amplitude")
                ax_wave.grid(alpha=0.2)
                image = ax_mel.imshow(mel_db, origin="lower", aspect="auto", extent=[0, len(audio) / sr, 0, 40])
                ax_mel.set_title("log-Mel spectrogram")
                ax_mel.set_xlabel("seconds")
                ax_mel.set_ylabel("Mel bin")
                fig.colorbar(image, ax=ax_mel, label="dB")
                safe_name = f"{category}__{row.sample_id}".replace("/", "_")
                fig.savefig(OUT / f"{safe_name}.png", dpi=120)
                plt.close(fig)
            except Exception as exc:
                failures.append({"sample_id": row.sample_id, "audio_path": row.audio_path, "error": repr(exc), "stage": "plot"})
    pd.DataFrame(reps).to_csv(OUT / "representative_samples.csv", index=False)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = pd.read_csv(ROOT / "datasets/v1/test_v1.csv", low_memory=False)
    cache = np.load(ROOT / "datasets/features_cache/test.npz", allow_pickle=True)
    mel = cache["mel"].astype(np.float32)
    labels = cache["y"].astype(int)
    sample_ids = cache["ids"].astype(str)
    assert len(manifest) == len(labels) == len(sample_ids) == 2119
    assert manifest.sample_id.astype(str).tolist() == sample_ids.tolist(), "sample ID order mismatch"
    assert manifest["class"].map(IDX).to_numpy().tolist() == labels.tolist(), "label order mismatch"

    metadata = json.loads((ROOT / "models/final/final_metadata.json").read_text())
    mean, std = float(metadata["feature_mean"]), float(metadata["feature_std"])
    interpreter = tf.lite.Interpreter(model_path=str(ROOT / "models/final/forest_acoustic_int8.tflite"))
    interpreter.allocate_tensors()
    input_detail = interpreter.get_input_details()[0]
    output_detail = interpreter.get_output_details()[0]
    input_scale, input_zero = input_detail["quantization"]
    output_scale, output_zero = output_detail["quantization"]

    rows, failures = [], []
    for i, (sample_id, true_index) in enumerate(zip(sample_ids, labels)):
        features = ((mel[i] - mean) / std)[..., None]
        quantized = np.round(features / input_scale + input_zero).astype(np.int8)
        interpreter.set_tensor(input_detail["index"], quantized[None])
        interpreter.invoke()
        output_q = interpreter.get_tensor(output_detail["index"])[0].astype(np.float32)
        scores = (output_q - output_zero) * output_scale
        # Match the canonical evaluator exactly: np.argmax resolves equal
        # quantized output values in favor of the first class.
        predicted_index = int(np.argmax(output_q))
        order = np.argsort(scores)[::-1]
        row = manifest.iloc[i]
        audio_path = Path(str(row.processed_path))
        if not audio_path.is_absolute():
            audio_path = ROOT / audio_path
        rows.append({
            "sample_id": str(sample_id),
            "original_recording_id": str(row.original_recording_id),
            "dataset_id": str(row.dataset_id),
            "audio_path": str(audio_path),
            "true_class": CLASSES[int(true_index)],
            "predicted_class": CLASSES[predicted_index],
            "true_index": int(true_index),
            "predicted_index": predicted_index,
            "background_score": float(scores[0]),
            "chainsaw_score": float(scores[1]),
            "gunshot_score": float(scores[2]),
            "prediction_confidence": float(scores[predicted_index]),
            "probability_margin": float(scores[order[0]] - scores[order[1]]),
            "manifest_duration_s": float(row.duration),
            "manifest_sample_rate": int(row.sample_rate),
            "manifest_channels": int(row.channels),
            "segment_index": int(row.segment_index) if pd.notna(row.segment_index) else None,
            "estimated_segment_start_s": float(row.segment_index * 0.5) if pd.notna(row.segment_index) else None,
            "audio_path_verified": audio_path.exists(),
            "event_id": str(row.event_id) if pd.notna(row.event_id) else "",
            "platform_id": str(row.platform_id) if pd.notna(row.platform_id) else "",
            "cartridge_id": str(row.cartridge_id) if pd.notna(row.cartridge_id) else "",
            "mic_id": str(row.mic_id) if pd.notna(row.mic_id) else "",
            "event_interval_id": str(row.event_interval_id) if pd.notna(row.event_interval_id) else "",
            "fsc22_class_name": str(row.fsc22_class_name) if pd.notna(row.fsc22_class_name) else "",
            "esc50_category": str(row.esc50_category) if pd.notna(row.esc50_category) else "",
        })

    # Read audio only after the complete inference pass. This keeps the canonical
    # TFLite evaluation path isolated from filesystem/audio-decoder activity.
    for row in rows:
        _, _, audio_stats, read_error = read_audio(Path(row["audio_path"]))
        if read_error:
            failures.append({"sample_id": row["sample_id"], "audio_path": row["audio_path"], "error": read_error, "stage": "read"})
        audio_stats = audio_stats or {"duration_s": None, "sample_rate": None, "channels": None, "peak_amplitude": None, "rms_energy": None, "clip_ratio_ge_0.95": None}
        row["audio_readable"] = not bool(read_error)
        row["audio_read_error"] = read_error
        row.update({f"audio_{key}": value for key, value in audio_stats.items()})

    predictions = pd.DataFrame(rows)
    predictions.to_csv(OUT / "predictions.csv", index=False)
    false_positives = predictions[(predictions.true_class == "background") & (predictions.predicted_class != "background")]
    false_negatives = predictions[(predictions.true_class != "background") & (predictions.predicted_class == "background")]
    false_positives.to_csv(OUT / "false_positives.csv", index=False)
    false_negatives.to_csv(OUT / "false_negatives.csv", index=False)
    sources = source_summary(predictions)
    sources.to_csv(OUT / "source_recording_summary.csv", index=False)
    dataset_rows = []
    for dataset_id, group in predictions.groupby("dataset_id", sort=True):
        background = group.true_class == "background"
        chainsaw = group.true_class == "chainsaw"
        gunshot = group.true_class == "gunshot"
        dataset_rows.append({
            "dataset_id": dataset_id,
            "test_windows": int(len(group)),
            "test_recordings": int(group.original_recording_id.nunique()),
            "background_windows": int(background.sum()),
            "background_fp_windows": int((background & (group.predicted_class != "background")).sum()),
            "background_fp_rate": float((background & (group.predicted_class != "background")).sum() / background.sum()) if background.sum() else None,
            "chainsaw_windows": int(chainsaw.sum()),
            "chainsaw_fn_to_background": int((chainsaw & (group.predicted_class == "background")).sum()),
            "gunshot_windows": int(gunshot.sum()),
            "gunshot_fn_to_background": int((gunshot & (group.predicted_class == "background")).sum()),
        })
    pd.DataFrame(dataset_rows).to_csv(OUT / "dataset_summary.csv", index=False)

    predicted = predictions.predicted_class.map(IDX).to_numpy()
    cm = confusion_matrix(labels, predicted, labels=[0, 1, 2])
    summary = {
        "evaluation_path": "default desktop tf.lite.Interpreter, matching ROBUSTNESS_REPORT clean run",
        "sample_count": int(len(predictions)),
        "sample_id_order_verified": True,
        "label_order_verified": True,
        "audio_files_readable": int(predictions.audio_readable.sum()),
        "audio_files_unreadable": int((~predictions.audio_readable).sum()),
        "accuracy": float(accuracy_score(labels, predicted)),
        "balanced_accuracy": float(balanced_accuracy_score(labels, predicted)),
        "macro_f1": float(f1_score(labels, predicted, average="macro")),
        "macro_precision": float(precision_score(labels, predicted, average="macro", zero_division=0)),
        "macro_recall": float(recall_score(labels, predicted, average="macro", zero_division=0)),
        "confusion_matrix": cm.tolist(),
        "per_class_precision": dict(zip(CLASSES, precision_score(labels, predicted, average=None, labels=[0, 1, 2], zero_division=0).tolist())),
        "per_class_recall": dict(zip(CLASSES, recall_score(labels, predicted, average=None, labels=[0, 1, 2], zero_division=0).tolist())),
        "per_class_f1": dict(zip(CLASSES, f1_score(labels, predicted, average=None, labels=[0, 1, 2], zero_division=0).tolist())),
        "background_false_alarm_count": int(len(false_positives)),
        "background_false_alarm_rate": float(len(false_positives) / (labels == 0).sum()),
        "failure_groups": {
            "background_to_chainsaw": error_stats(predictions[(predictions.true_class == "background") & (predictions.predicted_class == "chainsaw")]),
            "background_to_gunshot": error_stats(predictions[(predictions.true_class == "background") & (predictions.predicted_class == "gunshot")]),
            "chainsaw_to_background": error_stats(predictions[(predictions.true_class == "chainsaw") & (predictions.predicted_class == "background")]),
            "gunshot_to_background": error_stats(predictions[(predictions.true_class == "gunshot") & (predictions.predicted_class == "background")]),
        },
        "confidence_groups": {
            "correct": distribution_stats(predictions[predictions.true_class == predictions.predicted_class]),
            "false_positives": distribution_stats(false_positives),
            "false_negatives": distribution_stats(false_negatives),
            "background_to_chainsaw": distribution_stats(predictions[(predictions.true_class == "background") & (predictions.predicted_class == "chainsaw")]),
            "background_to_gunshot": distribution_stats(predictions[(predictions.true_class == "background") & (predictions.predicted_class == "gunshot")]),
            "chainsaw_to_background": distribution_stats(predictions[(predictions.true_class == "chainsaw") & (predictions.predicted_class == "background")]),
            "gunshot_to_background": distribution_stats(predictions[(predictions.true_class == "gunshot") & (predictions.predicted_class == "background")]),
        },
        "top_false_positive_recordings": sources[sources.background_fp_windows > 0].sort_values(["background_fp_windows", "background_fp_rate"], ascending=False).head(20).to_dict(orient="records"),
        "top_false_negative_recordings": sources[(sources.chainsaw_fn_to_background > 0) | (sources.gunshot_fn_to_background > 0)].sort_values(["chainsaw_fn_to_background", "gunshot_fn_to_background"], ascending=False).head(20).to_dict(orient="records"),
        "read_failures": failures,
        "artifact_hashes": {
            str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [ROOT / "models/final/forest_acoustic_int8.tflite", ROOT / "datasets/v1/test_v1.csv", ROOT / "datasets/features_cache/test.npz"]
        },
    }
    representative_plots(predictions, failures)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps({"summary": summary, "false_positives": len(false_positives), "false_negatives": len(false_negatives), "recordings_with_fp": int((sources.background_fp_windows > 0).sum()), "recordings_with_fn": int(((sources.chainsaw_fn_to_background > 0) | (sources.gunshot_fn_to_background > 0)).sum())}, indent=2, default=str))


if __name__ == "__main__":
    main()
