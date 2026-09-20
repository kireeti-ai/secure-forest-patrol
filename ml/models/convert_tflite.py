#!/usr/bin/env python3
"""
Convert the selected FP32 Keras model to TFLite (FP32 verification) and then
to a fully INT8-quantized TFLite model using a representative dataset sampled
ONLY from training data. Evaluates FP32 vs INT8 on the frozen test_v1 set,
inspects the operator list for TFLite Micro compatibility, and saves the
final artifacts.
"""
import json
from pathlib import Path

import numpy as np
import tensorflow as tf
from sklearn.metrics import f1_score, accuracy_score, confusion_matrix, classification_report

ML_ROOT = Path(__file__).parent.parent
CACHE_DIR = ML_ROOT / "datasets" / "features_cache"
FINAL_DIR = ML_ROOT / "models" / "final"
FP32_DIR = ML_ROOT / "models" / "forest_acoustic_fp32"
REPORTS_DIR = ML_ROOT / "reports"
CLASSES = ["background", "chainsaw", "gunshot"]

# TFLite Micro commonly-supported ops (used for the manual cross-check)
TFLM_SUPPORTED_OPS = {
    "CONV_2D", "DEPTHWISE_CONV_2D", "FULLY_CONNECTED", "AVERAGE_POOL_2D",
    "MAX_POOL_2D", "SOFTMAX", "RESHAPE", "QUANTIZE", "DEQUANTIZE", "MEAN",
    "ADD", "MUL", "RELU", "RELU6", "PAD", "CONCATENATION", "LOGISTIC",
}


def load_split(name):
    d = np.load(CACHE_DIR / f"{name}.npz", allow_pickle=True)
    return d['mel'], d['y']


def main():
    import argparse
    global FINAL_DIR, FP32_DIR, REPORTS_DIR, CACHE_DIR
    ap = argparse.ArgumentParser()
    ap.add_argument('--model-dir', default=None, help='dir with final_metadata.json/final.keras; all outputs go here (A/B runs)')
    ap.add_argument('--cache-dir', default=None)
    a = ap.parse_args()
    if a.cache_dir:
        CACHE_DIR = Path(a.cache_dir)
    if a.model_dir:
        FINAL_DIR = Path(a.model_dir)
        REPORTS_DIR = FINAL_DIR
        FP32_DIR = FINAL_DIR / 'fp32_copy'
    with open(FINAL_DIR / "final_metadata.json") as f:
        meta = json.load(f)
    mean, std = meta['feature_mean'], meta['feature_std']

    model = tf.keras.models.load_model(FINAL_DIR / "final.keras")

    mel_train, y_train = load_split("train")
    mel_test, y_test = load_split("test")

    def norm(mel):
        return ((mel - mean) / std)[..., np.newaxis].astype(np.float32)

    X_train = norm(mel_train)
    X_test = norm(mel_test)

    # ---- save FP32 SavedModel + metadata ----
    FP32_DIR.mkdir(parents=True, exist_ok=True)
    model.save(FP32_DIR / "model.keras")
    with open(FP32_DIR / "metadata.json", "w") as f:
        json.dump({
            'architecture': 'final depthwise-separable compact CNN',
            'input_shape': meta['input_shape'],
            'classes': CLASSES,
            'n_params': meta['n_params'],
            'weights_size_bytes': meta['weights_size_bytes'],
            'validation_metrics': meta['validation_metrics'],
        }, f, indent=2, default=str)

    # ---- FP32 TFLite conversion + numerical check ----
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_fp32 = converter.convert()
    fp32_path = FINAL_DIR / "forest_acoustic_fp32.tflite"
    fp32_path.write_bytes(tflite_fp32)

    interp_fp32 = tf.lite.Interpreter(model_content=tflite_fp32)
    interp_fp32.allocate_tensors()
    in_detail = interp_fp32.get_input_details()[0]
    out_detail = interp_fp32.get_output_details()[0]

    keras_probs = model.predict(X_test[:50], verbose=0)
    tflite_fp32_probs = []
    for i in range(50):
        interp_fp32.set_tensor(in_detail['index'], X_test[i:i + 1])
        interp_fp32.invoke()
        tflite_fp32_probs.append(interp_fp32.get_tensor(out_detail['index'])[0])
    tflite_fp32_probs = np.array(tflite_fp32_probs)
    max_abs_diff = float(np.max(np.abs(keras_probs - tflite_fp32_probs)))
    argmax_match = float(np.mean(np.argmax(keras_probs, 1) == np.argmax(tflite_fp32_probs, 1)))
    print(f"FP32 Keras vs FP32 TFLite: max_abs_diff={max_abs_diff:.6f}, argmax_match={argmax_match:.3f}")

    # ---- INT8 quantization (representative dataset from TRAIN only) ----
    rng = np.random.RandomState(42)
    rep_idx = rng.choice(len(X_train), size=min(300, len(X_train)), replace=False)

    def representative_dataset():
        for i in rep_idx:
            yield [X_train[i:i + 1]]

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative_dataset
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8
    tflite_int8 = converter.convert()

    int8_path = FINAL_DIR / "forest_acoustic_int8.tflite"
    int8_path.write_bytes(tflite_int8)

    # ---- Inspect ops (disable XNNPACK/default delegates so the op list reflects
    #      the actual ops baked into the .tflite flatbuffer, not runtime delegate wrapping) ----
    interp_int8 = tf.lite.Interpreter(
        model_content=tflite_int8,
        experimental_op_resolver_type=tf.lite.experimental.OpResolverType.BUILTIN_WITHOUT_DEFAULT_DELEGATES)
    interp_int8.allocate_tensors()
    in_d = interp_int8.get_input_details()[0]
    out_d = interp_int8.get_output_details()[0]

    ops_used = set()
    try:
        for op in interp_int8._get_ops_details():  # noqa
            ops_used.add(op['op_name'])
    except Exception:
        pass

    unsupported = ops_used - TFLM_SUPPORTED_OPS
    tensor_count = interp_int8.get_tensor_details()

    # ---- Evaluate FP32 (Keras) vs INT8 (TFLite Interpreter) on frozen test set ----
    keras_pred = np.argmax(model.predict(X_test, verbose=0), axis=1)

    in_scale, in_zero = in_d['quantization']
    int8_preds = []
    for i in range(len(X_test)):
        x = X_test[i:i + 1]
        x_q = np.round(x / in_scale + in_zero).astype(np.int8)
        interp_int8.set_tensor(in_d['index'], x_q)
        interp_int8.invoke()
        out_q = interp_int8.get_tensor(out_d['index'])[0]
        int8_preds.append(np.argmax(out_q))
    int8_preds = np.array(int8_preds)

    fp32_acc = accuracy_score(y_test, keras_pred)
    fp32_f1 = f1_score(y_test, keras_pred, average='macro')
    int8_acc = accuracy_score(y_test, int8_preds)
    int8_f1 = f1_score(y_test, int8_preds, average='macro')
    keras_vs_int8_agreement = float(np.mean(keras_pred == int8_preds))

    quant_report = {
        'fp32_keras_test_accuracy': float(fp32_acc),
        'fp32_keras_test_macro_f1': float(fp32_f1),
        'int8_tflite_test_accuracy': float(int8_acc),
        'int8_tflite_test_macro_f1': float(int8_f1),
        'keras_fp32_vs_int8_tflite_prediction_agreement': keras_vs_int8_agreement,
        'fp32_vs_fp32tflite_max_abs_diff_first50': max_abs_diff,
        'fp32_vs_fp32tflite_argmax_match_first50': argmax_match,
        'int8_confusion_matrix': confusion_matrix(y_test, int8_preds, labels=[0, 1, 2]).tolist(),
        'int8_classification_report': classification_report(y_test, int8_preds, labels=[0, 1, 2], target_names=CLASSES, zero_division=0),
        'fp32_keras_weights_bytes': meta['weights_size_bytes'],
        'fp32_tflite_bytes': len(tflite_fp32),
        'int8_tflite_bytes': len(tflite_int8),
        'ops_used': sorted(ops_used),
        'unsupported_tflm_ops': sorted(unsupported),
        'tensor_count': len(tensor_details_list := tensor_count),
        'input_shape': in_d['shape'].tolist(),
        'input_dtype': str(in_d['dtype']),
        'output_shape': out_d['shape'].tolist(),
        'output_dtype': str(out_d['dtype']),
        'input_quantization_scale_zero_point': [float(in_scale), int(in_zero)],
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORTS_DIR / "QUANTIZATION_REPORT.json", "w") as f:
        json.dump(quant_report, f, indent=2, default=str)

    # ---- labels + metadata ----
    (FINAL_DIR / "labels.txt").write_text("\n".join(CLASSES) + "\n")
    model_metadata = {
        'version': 'forest-acoustic-v1',
        'classes': CLASSES,
        'input_shape': meta['input_shape'],
        'sample_rate': 16000,
        'window_length_s': 1.0,
        'feature': 'mel_spectrogram',
        'n_mels': int(meta['input_shape'][0]),
        'n_fft': 512, 'hop_length': 160,
        'quantization': 'int8_full_integer',
        'input_scale_zero_point': [float(in_scale), int(in_zero)],
        'dataset_version': 'v1',
        'fp32_tflite_bytes': len(tflite_fp32),
        'int8_tflite_bytes': len(tflite_int8),
        'unsupported_tflm_ops': sorted(unsupported),
    }
    with open(FINAL_DIR / "model_metadata.json", "w") as f:
        json.dump(model_metadata, f, indent=2)

    print("\n=== QUANTIZATION SUMMARY ===")
    print(f"FP32 Keras weights: {meta['weights_size_bytes']/1024:.1f} KB")
    print(f"FP32 TFLite: {len(tflite_fp32)/1024:.1f} KB")
    print(f"INT8 TFLite: {len(tflite_int8)/1024:.1f} KB")
    print(f"FP32 test acc/macroF1: {fp32_acc:.4f}/{fp32_f1:.4f}")
    print(f"INT8 test acc/macroF1: {int8_acc:.4f}/{int8_f1:.4f}")
    print(f"Keras FP32 vs INT8 TFLite prediction agreement: {keras_vs_int8_agreement:.4f}")
    print(f"Ops used: {sorted(ops_used)}")
    print(f"Unsupported TFLM ops: {sorted(unsupported) if unsupported else 'NONE - all ops supported'}")


if __name__ == "__main__":
    main()
