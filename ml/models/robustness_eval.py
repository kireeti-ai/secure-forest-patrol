#!/usr/bin/env python3
"""
Noise robustness evaluation: adds synthetic Gaussian noise at clean/moderate/
strong SNR levels to the held-out test set MEL FEATURES at eval time only
(the frozen test_v1 cache on disk is never modified), then evaluates the
final INT8 TFLite model. Writes ml/reports/ROBUSTNESS_REPORT.md.

Also performs error analysis on misclassified test examples and writes
ml/reports/FAILURE_ANALYSIS.md with a handful of example failing sample_ids
and a likely-cause guess based on confidence and class confusion pattern.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix

ML_ROOT = Path(__file__).parent.parent
CACHE_DIR = ML_ROOT / "datasets" / "features_cache"
FINAL_DIR = ML_ROOT / "models" / "final"
REPORTS_DIR = ML_ROOT / "reports"
CLASSES = ["background", "chainsaw", "gunshot"]

SNR_LEVELS = {"clean": None, "moderate": 15.0, "strong": 5.0}


def add_noise_snr(mel, snr_db, rng):
    """Add Gaussian noise to a dB-scale mel spectrogram to approximate a target SNR."""
    signal_power = np.mean(mel ** 2)
    noise_power = signal_power / (10 ** (snr_db / 10))
    noise = rng.normal(0, np.sqrt(max(noise_power, 1e-6)), size=mel.shape)
    return mel + noise


def main():
    import argparse
    global FINAL_DIR, REPORTS_DIR, CACHE_DIR
    ap = argparse.ArgumentParser()
    ap.add_argument('--model-dir', default=None, help='dir with final_metadata.json/final.keras; all outputs go here (A/B runs)')
    ap.add_argument('--cache-dir', default=None)
    a = ap.parse_args()
    if a.cache_dir:
        CACHE_DIR = Path(a.cache_dir)
    if a.model_dir:
        FINAL_DIR = Path(a.model_dir)
        REPORTS_DIR = FINAL_DIR
        
    with open(FINAL_DIR / "final_metadata.json") as f:
        meta = json.load(f)
    mean, std = meta['feature_mean'], meta['feature_std']

    interp = tf.lite.Interpreter(model_path=str(FINAL_DIR / "forest_acoustic_int8.tflite"))
    interp.allocate_tensors()
    in_d = interp.get_input_details()[0]
    out_d = interp.get_output_details()[0]
    in_scale, in_zero = in_d['quantization']
    out_scale, out_zero = out_d['quantization']

    d = np.load(CACHE_DIR / "test.npz", allow_pickle=True)
    mel_test, y_test, ids = d['mel'], d['y'], d['ids']

    rng = np.random.RandomState(42)
    results = {}
    all_preds = {}
    for level, snr in SNR_LEVELS.items():
        if snr is None:
            mel_eval = mel_test
        else:
            mel_eval = np.stack([add_noise_snr(m, snr, rng) for m in mel_test])
        X = ((mel_eval - mean) / std)[..., np.newaxis].astype(np.float32)
        preds = []
        for i in range(len(X)):
            x_q = np.round(X[i:i + 1] / in_scale + in_zero).astype(np.int8)
            interp.set_tensor(in_d['index'], x_q)
            interp.invoke()
            out_q = interp.get_tensor(out_d['index'])[0]
            preds.append(np.argmax(out_q))
        preds = np.array(preds)
        all_preds[level] = preds
        acc = accuracy_score(y_test, preds)
        f1 = f1_score(y_test, preds, average='macro')
        bg_false_alarm = None
        cm = confusion_matrix(y_test, preds, labels=[0, 1, 2])
        # background false alarm rate: fraction of true background predicted as non-background
        bg_idx = CLASSES.index('background')
        bg_total = cm[bg_idx].sum()
        bg_false_alarm = float((cm[bg_idx].sum() - cm[bg_idx, bg_idx]) / bg_total) if bg_total else None
        results[level] = {
            'accuracy': float(acc), 'macro_f1': float(f1),
            'confusion_matrix': cm.tolist(),
            'background_false_alarm_rate': bg_false_alarm,
        }
        print(f"{level} (SNR={snr}): acc={acc:.4f} macroF1={f1:.4f}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORTS_DIR / "ROBUSTNESS_REPORT.json", "w") as f:
        json.dump(results, f, indent=2)

    with open(REPORTS_DIR / "ROBUSTNESS_REPORT.md", "w") as f:
        f.write("# Robustness Report\n\n")
        f.write("Synthetic Gaussian noise added to Mel-spectrogram features of the frozen "
                "`test_v1` set at evaluation time only (original test data on disk untouched). "
                "Evaluated with the final INT8 TFLite model.\n\n")
        f.write("| Condition | SNR (dB) | Accuracy | Macro-F1 | Background False-Alarm Rate |\n")
        f.write("|---|---|---|---|---|\n")
        for level, snr in SNR_LEVELS.items():
            r = results[level]
            snr_str = "N/A (clean)" if snr is None else f"{snr}"
            fa = f"{r['background_false_alarm_rate']:.4f}" if r['background_false_alarm_rate'] is not None else "N/A"
            f.write(f"| {level} | {snr_str} | {r['accuracy']:.4f} | {r['macro_f1']:.4f} | {fa} |\n")

    # ---- failure analysis on clean-condition misclassifications ----
    clean_preds = all_preds['clean']
    mis_idx = np.where(clean_preds != y_test)[0]
    examples = []
    for i in mis_idx[:15]:
        examples.append({
            'sample_id': str(ids[i]),
            'true_class': CLASSES[y_test[i]],
            'predicted_class': CLASSES[clean_preds[i]],
        })

    manifest = pd.read_csv(ML_ROOT / "datasets" / "v1" / "test_v1.csv", low_memory=False)
    manifest_by_id = manifest.set_index('sample_id')
    with open(REPORTS_DIR / "FAILURE_ANALYSIS.md", "w") as f:
        f.write("# Failure Analysis\n\n")
        f.write(f"Total test misclassifications (clean condition): {len(mis_idx)} / {len(y_test)} "
                f"({len(mis_idx)/len(y_test):.2%})\n\n")
        f.write("## Example misclassified samples\n\n")
        f.write("| sample_id | true | predicted | dataset | audio path | likely cause |\n")
        f.write("|---|---|---|---|---|---|\n")
        for ex in examples:
            row = manifest_by_id.loc[ex['sample_id']] if ex['sample_id'] in manifest_by_id.index else None
            dataset_id = row['dataset_id'] if row is not None else 'unknown'
            path = row['processed_path'] if row is not None else 'unknown'
            if ex['true_class'] == 'background' and ex['predicted_class'] in ('chainsaw', 'gunshot'):
                cause = "background sample with transient/percussive content confused for target event"
            elif ex['predicted_class'] == 'background':
                cause = "low-energy or short/ambiguous event window misclassified as background"
            else:
                cause = "acoustic similarity between chainsaw/gunshot spectral envelope"
            f.write(f"| {ex['sample_id']} | {ex['true_class']} | {ex['predicted_class']} | {dataset_id} | {path} | {cause} |\n")

    print(f"\nSaved ROBUSTNESS_REPORT.md and FAILURE_ANALYSIS.md to {REPORTS_DIR}")


if __name__ == "__main__":
    main()
