"""Metrics for classification and alert-proxy replay outputs."""
from collections import Counter
from typing import Dict, Iterable, Sequence

import numpy as np
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score, precision_score, recall_score

CLASSES = ["background", "chainsaw", "gunshot"]


def summarize(records, decisions) -> Dict:
    y_true = [r.true_class for r in records]
    y_pred = [d.decision_class if d.decision_class in CLASSES else "background" for d in decisions]
    cm = confusion_matrix(y_true, y_pred, labels=CLASSES)
    candidate = sum(d.candidate_alert for d in decisions)
    emitted = sum(d.alert_emitted for d in decisions)
    uncertain = sum(d.operational_state.startswith("UNCERTAIN") for d in decisions)
    suppressed = sum(d.suppressed for d in decisions)
    fp = sum(t == "background" and p != "background" for t, p in zip(y_true, y_pred))
    bg_total = sum(t == "background" for t in y_true)
    rec_ids = {r.recording_id for r in records}
    fp_recordings = {r.recording_id for r, d in zip(records, decisions) if r.true_class == "background" and d.decision_class != "background"}
    event_pred_recordings = {r.recording_id for r, d in zip(records, decisions) if d.decision_class in ("chainsaw", "gunshot")}
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "macro_precision": float(precision_score(y_true, y_pred, labels=CLASSES, average="macro", zero_division=0)),
        "macro_recall": float(recall_score(y_true, y_pred, labels=CLASSES, average="macro", zero_division=0)),
        "macro_f1": float(f1_score(y_true, y_pred, labels=CLASSES, average="macro", zero_division=0)),
        "per_class_precision": dict(zip(CLASSES, precision_score(y_true, y_pred, labels=CLASSES, average=None, zero_division=0).tolist())),
        "per_class_recall": dict(zip(CLASSES, recall_score(y_true, y_pred, labels=CLASSES, average=None, zero_division=0).tolist())),
        "per_class_f1": dict(zip(CLASSES, f1_score(y_true, y_pred, labels=CLASSES, average=None, zero_division=0).tolist())),
        "confusion_matrix": cm.tolist(),
        "background_false_positive_windows": int(fp),
        "background_false_positive_rate": float(fp / bg_total) if bg_total else None,
        "candidate_alerts": int(candidate),
        "confirmed_alerts": int(emitted),
        "uncertain_windows": int(uncertain),
        "suppressed_duplicate_candidates": int(suppressed),
        "recordings": int(len(rec_ids)),
        "recordings_with_background_false_positive": int(len(fp_recordings)),
        "recordings_with_event_positive_decision": int(len(event_pred_recordings)),
        "event_level_metrics": "unavailable: frozen manifests lack reliable event intervals/time denominators for this replay",
    }
