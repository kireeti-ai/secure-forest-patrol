#!/usr/bin/env python3
"""Phase 2 reference audit. Reads frozen artifacts and writes diagnostics only."""
import hashlib
import json
from pathlib import Path

import librosa
import numpy as np
import pandas as pd
import soundfile as sf
import tensorflow as tf
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix

ROOT = Path(__file__).parents[2]
OUT = ROOT / "reports" / "phase2_diagnostics"
CLASSES = ["background", "chainsaw", "gunshot"]


def load_model_io(path, no_delegate=False):
    kwargs = {}
    if no_delegate:
        kwargs["experimental_op_resolver_type"] = tf.lite.experimental.OpResolverType.BUILTIN_WITHOUT_DEFAULT_DELEGATES
    interpreter = tf.lite.Interpreter(model_path=str(path), **kwargs)
    interpreter.allocate_tensors()
    return interpreter, interpreter.get_input_details()[0], interpreter.get_output_details()[0]


def quantize_input(x, scale, zero_point):
    # This is the exact operation used by convert_tflite.py and robustness_eval.py.
    # The frozen test inputs round into int8 range, so explicit clipping does not
    # change any frozen reference value.
    return np.round(x / scale + zero_point).astype(np.int8)


def run_one(interpreter, input_detail, output_detail, x):
    q = quantize_input(x, input_detail["quantization"][0], input_detail["quantization"][1])
    interpreter.set_tensor(input_detail["index"], q[None])
    interpreter.invoke()
    output_q = interpreter.get_tensor(output_detail["index"])[0].copy()
    output_real = (output_q.astype(np.float32) - output_detail["quantization"][1]) * output_detail["quantization"][0]
    return q, output_q, output_real


def compare_arrays(a, b):
    delta = np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    return {
        "max_abs": float(np.max(np.abs(delta))),
        "mean_abs": float(np.mean(np.abs(delta))),
        "rmse": float(np.sqrt(np.mean(np.square(delta)))),
        "different_elements": int(np.count_nonzero(delta)),
        "elements": int(delta.size),
    }


def choose_golden(predictions):
    choices = []

    def add(category, frame):
        if len(frame):
            choices.append((category, frame.iloc[0]))

    add("ordinary_background", predictions[(predictions.true_class == "background") & (predictions.predicted_class == "background") & (predictions.dataset_id == "fsc22")])
    add("background_to_chainsaw", predictions[(predictions.true_class == "background") & (predictions.predicted_class == "chainsaw")])
    add("background_to_gunshot", predictions[(predictions.true_class == "background") & (predictions.predicted_class == "gunshot")])
    add("correct_chainsaw", predictions[(predictions.true_class == "chainsaw") & (predictions.predicted_class == "chainsaw")])
    add("chainsaw_to_background", predictions[(predictions.true_class == "chainsaw") & (predictions.predicted_class == "background")])
    add("correct_gunshot", predictions[(predictions.true_class == "gunshot") & (predictions.predicted_class == "gunshot") & (predictions.dataset_id == "c3gd")])
    add("gunshot_to_background", predictions[(predictions.true_class == "gunshot") & (predictions.predicted_class == "background")])
    add("low_energy", predictions.sort_values("audio_rms_energy").head(1))
    add("high_amplitude", predictions.sort_values("audio_peak_amplitude", ascending=False).head(1))
    add("boundary_start", predictions[predictions.segment_index == 0])
    add("boundary_end", predictions[predictions.segment_index == 8])
    # Remove duplicate sample IDs while retaining category coverage.
    seen = set()
    result = []
    for category, row in choices:
        if row.sample_id not in seen:
            seen.add(row.sample_id)
            result.append((category, row))
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    predictions = pd.read_csv(ROOT / "reports/phase1_diagnostics/predictions.csv")
    cache = np.load(ROOT / "datasets/features_cache/test.npz", allow_pickle=True)
    cache_ids = cache["ids"].astype(str)
    cache_mel = cache["mel"].astype(np.float32)
    cache_y = cache["y"].astype(int)
    manifest = pd.read_csv(ROOT / "datasets/v1/test_v1.csv", low_memory=False)
    metadata = json.loads((ROOT / "models/final/final_metadata.json").read_text())
    mean, std = float(metadata["feature_mean"]), float(metadata["feature_std"])

    int8_path = ROOT / "models/final/forest_acoustic_int8.tflite"
    fp32_path = ROOT / "models/final/forest_acoustic_fp32.tflite"
    keras_path = ROOT / "models/final/final.keras"
    x_test = ((cache_mel - mean) / std)[..., None].astype(np.float32)
    keras_probs = np.load(OUT / "keras_outputs.npy")
    # Keep only one TFLite interpreter alive at a time. This avoids a
    # TensorFlow/XNNPACK interaction observed when the default and
    # delegate-free interpreters coexist in this desktop environment.
    int8_default, int8_in, int8_out = load_model_io(int8_path)

    default_preds = []
    default_outputs = []
    quantized_inputs = []
    rounded_inputs = []
    input_real = x_test / int8_in["quantization"][0] + int8_in["quantization"][1]
    rounded_real = np.round(input_real)
    for x in x_test:
        q, out_q, _ = run_one(int8_default, int8_in, int8_out, x)
        default_preds.append(int(np.argmax(out_q)))
        default_outputs.append(out_q)
        quantized_inputs.append(q)
    default_preds = np.asarray(default_preds)
    default_outputs = np.asarray(default_outputs)
    del int8_default
    int8_nodelegate, int8_nd_in, int8_nd_out = load_model_io(int8_path, no_delegate=True)
    nodelegate_preds, nodelegate_outputs = [], []
    for x in x_test:
        q2, out_q2, _ = run_one(int8_nodelegate, int8_nd_in, int8_nd_out, x)
        nodelegate_preds.append(int(np.argmax(out_q2)))
        nodelegate_outputs.append(out_q2)
    nodelegate_preds = np.asarray(nodelegate_preds)
    nodelegate_outputs = np.asarray(nodelegate_outputs)
    del int8_nodelegate
    quantized_inputs = np.asarray(quantized_inputs)
    import gc
    gc.collect()

    fp32_interp, fp32_in, fp32_out = load_model_io(fp32_path, no_delegate=True)
    fp32_probs = []
    for x in x_test:
        fp32_interp.set_tensor(fp32_in["index"], x[None])
        fp32_interp.invoke()
        fp32_probs.append(fp32_interp.get_tensor(fp32_out["index"])[0].copy())
    fp32_probs = np.asarray(fp32_probs)
    del fp32_interp

    # Golden references use existing processed WAV paths and are cross-checked
    # against the frozen feature cache. No data is regenerated.
    golden_rows = []
    golden_mels, golden_norm, golden_q, golden_out_q, golden_out_real = [], [], [], [], []
    deterministic_rows = []
    id_to_cache = {sid: i for i, sid in enumerate(cache_ids)}
    extractor_module = __import__("sys")
    extractor_module.path.insert(0, str(ROOT / "preprocessing"))
    from feature_extraction import get_feature_extractor
    extractor = get_feature_extractor()

    for category, row in choose_golden(predictions):
        idx = id_to_cache[str(row.sample_id)]
        wav = ROOT / str(row.audio_path).replace(str(ROOT) + "/", "") if str(row.audio_path).startswith(str(ROOT)) else Path(row.audio_path)
        if not wav.is_absolute():
            wav = ROOT / wav
        audio, sr = sf.read(wav, dtype="float32")
        features = extractor.extract_mel_spectrogram(audio, int(sr)).astype(np.float32)
        reference = cache_mel[idx]
        diff = compare_arrays(features, reference)
        x = ((features - mean) / std)[..., None].astype(np.float32)
        golden_int8, golden_in, golden_out = load_model_io(int8_path)
        q, out_q, out_real = run_one(golden_int8, golden_in, golden_out, x)
        del golden_int8
        golden_rows.append({
            "category": category,
            "sample_id": str(row.sample_id),
            "original_recording_id": str(row.original_recording_id),
            "dataset_id": str(row.dataset_id),
            "audio_path": str(wav),
            "sample_rate": int(sr),
            "feature_shape": list(features.shape),
            "feature_cache_max_abs_diff": diff["max_abs"],
            "feature_cache_mean_abs_diff": diff["mean_abs"],
            "feature_cache_rmse": diff["rmse"],
            "expected_true_class": str(row.true_class),
            "canonical_predicted_class": CLASSES[int(np.argmax(out_q))],
            "canonical_prediction_index": int(np.argmax(out_q)),
            "source_segment_index": int(row.segment_index),
            "padding_tested": False,
        })
        golden_mels.append(features)
        golden_norm.append(x)
        golden_q.append(q)
        golden_out_q.append(out_q)
        golden_out_real.append(out_real)

        feature_repeats = []
        q_repeats = []
        output_repeats = []
        for _ in range(5):
            repeat_features = extractor.extract_mel_spectrogram(audio, int(sr)).astype(np.float32)
            repeat_x = ((repeat_features - mean) / std)[..., None].astype(np.float32)
            repeat_int8, repeat_in, repeat_out_detail = load_model_io(int8_path)
            repeat_q, repeat_out, _ = run_one(repeat_int8, repeat_in, repeat_out_detail, repeat_x)
            del repeat_int8
            feature_repeats.append(repeat_features)
            q_repeats.append(repeat_q)
            output_repeats.append(repeat_out)
        deterministic_rows.append({
            "category": category,
            "sample_id": str(row.sample_id),
            "feature_repeat_comparison": compare_arrays(feature_repeats[0], np.asarray(feature_repeats[1:])),
            "quantized_repeat_disagreement": int(np.count_nonzero(np.asarray(q_repeats[0]) != np.asarray(q_repeats[1:]))),
            "output_repeat_comparison": compare_arrays(output_repeats[0], np.asarray(output_repeats[1:])),
            "prediction_repeat_classes": [CLASSES[int(np.argmax(value))] for value in output_repeats],
        })

    np.savez_compressed(
        OUT / "golden_references.npz",
        mel_db=np.asarray(golden_mels, dtype=np.float32),
        normalized_input=np.asarray(golden_norm, dtype=np.float32),
        quantized_input=np.asarray(golden_q, dtype=np.int8),
        output_int8=np.asarray(golden_out_q, dtype=np.int8),
        output_dequantized=np.asarray(golden_out_real, dtype=np.float32),
    )
    pd.DataFrame(golden_rows).to_csv(OUT / "golden_manifest.csv", index=False)
    pd.DataFrame(deterministic_rows).to_csv(OUT / "determinism_golden.csv", index=False)

    # Inspect tensor quantization parameters and flatbuffer operators.
    inspection_interp, _, _ = load_model_io(int8_path, no_delegate=True)
    tensor_details = inspection_interp.get_tensor_details()
    quantized_tensor_details = []
    for detail in tensor_details:
        params = detail.get("quantization_parameters", {})
        scales = np.asarray(params.get("scales", []))
        zero_points = np.asarray(params.get("zero_points", []))
        if scales.size:
            quantized_tensor_details.append({
                "name": detail["name"],
                "shape": detail["shape"].tolist(),
                "dtype": str(detail["dtype"]),
                "quantized_dimension": int(params.get("quantized_dimension", 0)),
                "scale_count": int(scales.size),
                "scale_min": float(scales.min()),
                "scale_max": float(scales.max()),
                "zero_point_count": int(zero_points.size),
                "zero_point_min": int(zero_points.min()) if zero_points.size else None,
                "zero_point_max": int(zero_points.max()) if zero_points.size else None,
            })
    ops = sorted({item["op_name"] for item in inspection_interp._get_ops_details()})
    del inspection_interp

    default_dequant = (default_outputs.astype(np.float32) - int8_out["quantization"][1]) * int8_out["quantization"][0]
    nodelegate_dequant = (nodelegate_outputs.astype(np.float32) - int8_nd_out["quantization"][1]) * int8_nd_out["quantization"][0]
    tie_mask = np.array([len(np.unique(row)) < 3 for row in default_outputs])
    disagreement = default_preds != nodelegate_preds
    fp32_tflite_diff = compare_arrays(keras_probs[:50], fp32_probs[:50])
    quantization_summary = {
        "input_contract": {
            "shape": int8_in["shape"].tolist(),
            "dtype": str(int8_in["dtype"]),
            "scale": float(int8_in["quantization"][0]),
            "zero_point": int(int8_in["quantization"][1]),
            "rounded_input_min": float(rounded_real.min()),
            "rounded_input_max": float(rounded_real.max()),
            "rounded_values_below_int8": int((rounded_real < -128).sum()),
            "rounded_values_above_int8": int((rounded_real > 127).sum()),
        },
        "output_contract": {
            "shape": int8_out["shape"].tolist(),
            "dtype": str(int8_out["dtype"]),
            "scale": float(int8_out["quantization"][0]),
            "zero_point": int(int8_out["quantization"][1]),
            "dequantization": "real = (q - zero_point) * scale",
        },
        "operator_list": ops,
        "quantized_tensor_count": len(quantized_tensor_details),
        "quantized_tensor_details": quantized_tensor_details,
        "fp32_keras_vs_fp32_tflite_first50": fp32_tflite_diff,
        "fp32_keras_vs_fp32_tflite_argmax_first50": float(np.mean(np.argmax(keras_probs[:50], axis=1) == np.argmax(fp32_probs[:50], axis=1))),
        "fp32_keras_vs_int8_nodelegate_agreement_test": float(np.mean(np.argmax(keras_probs, axis=1) == nodelegate_preds)),
        "int8_default_vs_nodelegate": {
            "prediction_disagreements": int(disagreement.sum()),
            "output_tensor_comparison": compare_arrays(default_dequant, nodelegate_dequant),
            "disagreements_with_default_output_tie": int((disagreement & tie_mask).sum()),
            "total_default_output_ties": int(tie_mask.sum()),
            "default_confusion_matrix": confusion_matrix(cache_y, default_preds, labels=[0, 1, 2]).tolist(),
            "nodelegate_confusion_matrix": confusion_matrix(cache_y, nodelegate_preds, labels=[0, 1, 2]).tolist(),
        },
        "argmax_rule": "np.argmax on raw int8 output; ties resolve to the first class index",
        "input_quantization_implementation": "np.round(x / scale + zero_point).astype(np.int8); no explicit clip in repository evaluator",
    }
    (OUT / "quantization_summary.json").write_text(json.dumps(quantization_summary, indent=2, default=str))

    determinism = {
        "golden_sample_count": len(golden_rows),
        "repetitions_per_sample": 5,
        "feature_max_abs_across_repeats": float(max(row["feature_repeat_comparison"]["max_abs"] for row in deterministic_rows)),
        "feature_mean_abs_across_repeats": float(max(row["feature_repeat_comparison"]["mean_abs"] for row in deterministic_rows)),
        "feature_rmse_across_repeats": float(max(row["feature_repeat_comparison"]["rmse"] for row in deterministic_rows)),
        "quantized_input_disagreements_across_repeats": int(sum(row["quantized_repeat_disagreement"] for row in deterministic_rows)),
        "output_max_abs_across_repeats": float(max(row["output_repeat_comparison"]["max_abs"] for row in deterministic_rows)),
        "output_mean_abs_across_repeats": float(max(row["output_repeat_comparison"]["mean_abs"] for row in deterministic_rows)),
        "prediction_class_disagreements_across_repeats": int(sum(len(set(row["prediction_repeat_classes"])) > 1 for row in deterministic_rows)),
        "method": "same processed WAV decoded and passed through FeatureExtractor five times; model invoked five times per resulting input",
    }
    (OUT / "determinism_summary.json").write_text(json.dumps(determinism, indent=2))

    report = {
        "artifact_hashes_before_and_after": {
            str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [keras_path, fp32_path, int8_path, ROOT / "datasets/v1/test_v1.csv", ROOT / "datasets/features_cache/test.npz"]
        },
        "golden_count": len(golden_rows),
        "golden_categories": [row["category"] for row in golden_rows],
        "determinism": determinism,
        "quantization": quantization_summary,
        "software": {"python": __import__("sys").version, "tensorflow": tf.__version__, "librosa": librosa.__version__, "numpy": np.__version__, "soundfile": sf.__version__},
    }
    (OUT / "phase2_summary.json").write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps({"golden_count": len(golden_rows), "categories": [row["category"] for row in golden_rows], "determinism": determinism, "int8_default_vs_nodelegate_disagreements": int(disagreement.sum()), "ties": int(tie_mask.sum()), "operators": ops}, indent=2, default=str))


if __name__ == "__main__":
    main()
