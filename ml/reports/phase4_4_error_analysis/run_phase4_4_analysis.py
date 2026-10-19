#!/usr/bin/env python3
"""Read-only Phase 4.4 error analysis.

This script consumes frozen metadata and existing diagnostics. It does not run
model inference, download data, change review state, or alter any dataset.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "phase4_4_error_analysis"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def precision_recall_f1(matrix: list[list[int]], index: int) -> tuple[float, float, float]:
    tp = matrix[index][index]
    predicted = sum(row[index] for row in matrix)
    actual = sum(matrix[index])
    precision = tp / predicted if predicted else 0.0
    recall = tp / actual if actual else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def main() -> None:
    metadata = json.loads((ROOT / "models/final/final_metadata.json").read_text())
    validation = metadata["validation_metrics"]
    matrix = validation["confusion_matrix"]
    classes = metadata["classes"]
    per_class = {}
    for i, name in enumerate(classes):
        precision, recall, f1 = precision_recall_f1(matrix, i)
        per_class[name] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": sum(matrix[i]),
        }

    phase1 = json.loads((ROOT / "reports/phase1_diagnostics/summary.json").read_text())
    queue_path = ROOT / "datasets/phase4_3_candidate/review_queue.csv"
    decisions_path = ROOT / "datasets/phase4_3_candidate/review_decisions.csv"
    queue = read_csv(queue_path)
    decisions = read_csv(decisions_path)

    valid_decisions = {
        "ACCEPTED",
        "RELABEL_REQUIRED",
        "AMBIGUOUS",
        "EXCLUDED",
        "NEEDS_SECOND_REVIEW",
    }
    decision_counts = Counter(row.get("decision", "").strip() for row in decisions)
    completed = sum(value for key, value in decision_counts.items() if key in valid_decisions)
    pending_or_unresolved = len(decisions) - completed

    # This is a deterministic diagnostic ordering only. It does not change
    # queue state, eligibility, labels, or the decisions file.
    def rank_key(row: dict[str, str]) -> tuple[int, int, str]:
        batch = 0 if row.get("batch_membership") == "BATCH_1" else 1
        target = row.get("target_class", "")
        if target == "chainsaw":
            category = 0
        elif target == "gunshot":
            category = 1
        elif row.get("original_label") == "background" and row.get("hard_negative_subtype"):
            category = 2
        else:
            category = 3
        return batch, category, row.get("candidate_id", "")

    ranked = sorted(queue, key=rank_key)
    priority_path = OUT / "candidate_review_priority.csv"
    fields = [
        "review_rank", "candidate_id", "source_recording_id", "source_dataset",
        "original_label", "target_class", "hard_negative_subtype", "batch_membership",
        "review_priority", "human_review_status", "review_decision",
        "license_status", "proposed_future_split_group", "selection_basis",
    ]
    with priority_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for rank, row in enumerate(ranked, 1):
            if row.get("batch_membership") == "BATCH_1":
                basis = "Existing Phase 4.3 first batch; preserve current queue ordering"
            elif row.get("target_class") in {"chainsaw", "gunshot"}:
                basis = "Target-class validation recall deficiency; diagnostic priority only"
            elif row.get("hard_negative_subtype"):
                basis = "Background hard-negative metadata; diagnostic priority only"
            else:
                basis = "Remaining candidate; no stronger validated grouping available"
            writer.writerow({
                "review_rank": rank,
                **{key: row.get(key, "") for key in fields[1:-1]},
                "selection_basis": basis,
            })

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

    metrics = {
        "analysis_scope": "Phase 4.4 validation diagnostics; Phase 1 test artifacts are context only",
        "inference_run": False,
        "external_downloads": 0,
        "training_started": False,
        "validation": {
            "source": "models/final/final_metadata.json validation_metrics",
            "sample_count": sum(sum(row) for row in matrix),
            "classes": classes,
            "confusion_matrix_rows_true_columns_predicted": matrix,
            "accuracy": validation["accuracy"],
            "balanced_accuracy": validation["balanced_accuracy"],
            "macro_precision": validation["macro_precision"],
            "macro_recall": validation["macro_recall"],
            "macro_f1": validation["macro_f1"],
            "per_class": per_class,
            "prediction_table_available": False,
            "source_group_error_analysis_available": False,
            "confidence_distribution_available": False,
        },
        "validation_error_counts": {
            "background_to_chainsaw": matrix[0][1],
            "background_to_gunshot": matrix[0][2],
            "chainsaw_to_background": matrix[1][0],
            "chainsaw_to_gunshot": matrix[1][2],
            "gunshot_to_background": matrix[2][0],
            "gunshot_to_chainsaw": matrix[2][1],
        },
        "phase1_test_context_not_used_for_selection": {
            "source": "reports/phase1_diagnostics/summary.json",
            "background_false_alarm_count": phase1["background_false_alarm_count"],
            "background_false_alarm_rate": phase1["background_false_alarm_rate"],
            "failure_groups": phase1["failure_groups"],
            "use": "context and limitation only; no candidate or threshold selection",
        },
        "phase4_3_review_state_observed": {
            "queue_rows": len(queue),
            "decision_rows": len(decisions),
            "decision_counts": dict(sorted(decision_counts.items())),
            "valid_completed_decisions": completed,
            "unresolved_or_pending_decisions": pending_or_unresolved,
            "training_eligible_candidates": 0,
            "note": "Existing decisions are preserved; this analysis writes no review decisions.",
        },
        "candidate_priority_output": str(priority_path.relative_to(ROOT)),
        "frozen_artifact_sha256": {str(path.relative_to(ROOT)): sha256(path) for path in frozen_paths},
    }
    (OUT / "error_analysis_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")

    decision = {
        "decision": "TARGETED_REVIEW_RECOMMENDED",
        "basis": [
            "Validation chainsaw recall is 0.4887 and gunshot recall is 0.6852, with 225 and 10 false negatives to background respectively.",
            "Validation background errors include 143 background-to-chainsaw and 46 background-to-gunshot windows.",
            "A small existing Phase 4.3 first batch is already defined as 30 background, 20 chainsaw, and 10 gunshot candidates.",
            "The evidence supports a bounded human review to resolve label/event uncertainty before any training decision; it does not justify online acquisition or review of all 777 candidates.",
        ],
        "recommended_scope": {
            "candidate_count": 60,
            "existing_batch": "BATCH_1",
            "by_class": {"background": 30, "chainsaw": 20, "gunshot": 10},
            "status": "recommendation_only; no candidates marked reviewed or training eligible",
        },
        "next_action": "Review the existing Phase 4.3 BATCH_1 with the repaired reviewer, then reassess label quality, event occupancy, and eligibility. Keep model investigation diagnostic-only until those observations exist.",
        "online_acquisition": "NO-GO",
        "phase5": "BLOCKED",
        "limitations": [
            "No validation per-sample prediction CSV or validation confidence scores were found, so validation source concentration and confidence separation cannot be measured.",
            "Phase 1 per-source and confidence evidence is from the frozen test diagnostic and is not used to tune thresholds or select candidate IDs here.",
            "No audio was listened to in this audit; acoustic causes and label correctness remain unverified.",
            "No candidate has been marked human-reviewed or training-eligible by this analysis.",
        ],
    }
    (OUT / "next_step_decision.json").write_text(json.dumps(decision, indent=2) + "\n")
    print(json.dumps({"validation_samples": metrics["validation"]["sample_count"], "queue_rows": len(queue), "decision_counts": dict(decision_counts), "decision": decision["decision"]}, indent=2))


if __name__ == "__main__":
    main()
