#!/usr/bin/env python3
"""
Baseline model: MFCC statistical features (mean+std over time per coefficient)
-> Logistic Regression (scikit-learn).

Trains on train_v1 cache, selects nothing to tune (single fixed config given
time budget), evaluates on validation, and reports test + external_test metrics.
"""
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, f1_score, precision_score, recall_score,
                              balanced_accuracy_score, confusion_matrix, classification_report)

ML_ROOT = Path(__file__).parent.parent.parent
CACHE_DIR = ML_ROOT / "datasets" / "features_cache"
OUT_DIR = Path(__file__).parent
CLASSES = ["background", "chainsaw", "gunshot"]

SEED = 42


def mfcc_stats(mfcc_arr):
    # mfcc_arr: (N, 13, T) -> (N, 26) mean+std per coefficient
    mean = mfcc_arr.mean(axis=2)
    std = mfcc_arr.std(axis=2)
    return np.concatenate([mean, std], axis=1)


def load_split(name):
    d = np.load(CACHE_DIR / f"{name}.npz", allow_pickle=True)
    X = mfcc_stats(d['mfcc'])
    y = d['y']
    return X, y


def evaluate(model, X, y, name):
    pred = model.predict(X)
    metrics = {
        'accuracy': accuracy_score(y, pred),
        'balanced_accuracy': balanced_accuracy_score(y, pred),
        'macro_f1': f1_score(y, pred, average='macro'),
        'macro_precision': precision_score(y, pred, average='macro', zero_division=0),
        'macro_recall': recall_score(y, pred, average='macro', zero_division=0),
        'per_class_f1': dict(zip(CLASSES, f1_score(y, pred, average=None, labels=[0, 1, 2], zero_division=0).tolist())),
        'confusion_matrix': confusion_matrix(y, pred, labels=[0, 1, 2]).tolist(),
        'classification_report': classification_report(y, pred, labels=[0, 1, 2], target_names=CLASSES, zero_division=0),
    }
    print(f"\n=== {name} ===")
    print(f"Accuracy: {metrics['accuracy']:.4f}  Macro-F1: {metrics['macro_f1']:.4f}  Balanced Acc: {metrics['balanced_accuracy']:.4f}")
    print(metrics['classification_report'])
    return metrics


def main():
    X_train, y_train = load_split("train")
    X_val, y_val = load_split("validation")
    X_test, y_test = load_split("test")
    X_ext, y_ext = load_split("external_test")

    print(f"Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}, External: {X_ext.shape}")

    # standardize using train stats
    mean, std = X_train.mean(axis=0), X_train.std(axis=0) + 1e-8
    X_train_n = (X_train - mean) / std
    X_val_n = (X_val - mean) / std
    X_test_n = (X_test - mean) / std
    X_ext_n = (X_ext - mean) / std

    model = LogisticRegression(max_iter=2000, class_weight='balanced', random_state=SEED, multi_class='multinomial')
    model.fit(X_train_n, y_train)

    val_metrics = evaluate(model, X_val_n, y_val, "validation")
    test_metrics = evaluate(model, X_test_n, y_test, "test")
    ext_metrics = evaluate(model, X_ext_n, y_ext, "external_test")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = {'validation': val_metrics, 'test': test_metrics, 'external_test': ext_metrics}
    with open(OUT_DIR / "baseline_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    import joblib
    joblib.dump({'model': model, 'mean': mean, 'std': std}, OUT_DIR / "baseline_model.joblib")
    print(f"\nSaved baseline model + results to {OUT_DIR}")


if __name__ == "__main__":
    main()
