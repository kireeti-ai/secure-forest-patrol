#!/usr/bin/env python3
"""
A/B experiment: A = unfiltered features (datasets/features_cache), B = filtered (features_cache_filtered).
Same frozen v1 splits, same final architecture/hyperparameters, seeds 42/1/2. Everything is written to
models/ab_filter/{A,B}_seed{N}/ -- models/final and the v1 caches are never touched.
For each run: train -> INT8 convert -> robustness (clean/15dB/5dB). Then summarise to reports/ab_filter_results.json.
"""
import json
import subprocess
import sys
from pathlib import Path

ML = Path(__file__).parent.parent
PY = sys.executable
SEEDS = [42, 1, 2]
CACHES = {"A": ML / "datasets/features_cache", "B": ML / "datasets/features_cache_filtered"}


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-2000:])
        raise SystemExit(f"failed: {cmd}")


def main():
    results = {}
    for v, cache in CACHES.items():
        for s in SEEDS:
            out = ML / "models/ab_filter" / f"{v}_seed{s}"
            if not (out / "QUANTIZATION_REPORT.json").exists():
                run([PY, str(ML / "models/train_cnn.py"), "--variant", "final", "--seed", str(s),
                     "--cache-dir", str(cache), "--out-dir", str(out)])
                run([PY, str(ML / "models/convert_tflite.py"), "--model-dir", str(out), "--cache-dir", str(cache)])
                run([PY, str(ML / "models/robustness_eval.py"), "--model-dir", str(out), "--cache-dir", str(cache)])
            m = json.load(open(out / "final_metadata.json"))
            q = json.load(open(out / "QUANTIZATION_REPORT.json"))
            rob = json.load(open(out / "ROBUSTNESS_REPORT.json"))
            results[f"{v}_seed{s}"] = {
                "val": m["validation_metrics"], "test": m["test_metrics"], "external": m["external_test_metrics"],
                "int8_test_acc": q["int8_tflite_test_accuracy"], "int8_test_macro_f1": q["int8_tflite_test_macro_f1"],
                "int8_bytes": q["int8_tflite_bytes"], "unsupported_ops": q["unsupported_tflm_ops"],
                "robustness": rob, "epochs_ran": m["epochs_ran"]}
            print(v, s, "val F1", round(m["validation_metrics"]["macro_f1"], 4),
                  "test F1", round(m["test_metrics"]["macro_f1"], 4), flush=True)
    json.dump(results, open(ML / "reports/ab_filter_results.json", "w"), indent=2, default=str)


if __name__ == "__main__":
    main()
