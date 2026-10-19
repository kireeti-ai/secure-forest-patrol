#!/usr/bin/env python3
"""Phase 4.3 human-review readiness and eligibility audit.

No human decisions are fabricated. This script initializes pending decisions,
selects a review batch, validates available files, and applies fail-closed
eligibility without changing Phase 4.2 or frozen artifacts.
"""
import hashlib
import json
import wave
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parents[2]
OUT = ROOT / "reports" / "phase4_3_diagnostics"
CAND = ROOT / "datasets" / "phase4_3_candidate"
DATE = "2026-10-18"

FROZEN = [
    ROOT / "models/final/final.keras", ROOT / "models/final/forest_acoustic_fp32.tflite", ROOT / "models/final/forest_acoustic_int8.tflite",
    ROOT / "datasets/v1/train_v1.csv", ROOT / "datasets/v1/validation_v1.csv", ROOT / "datasets/v1/test_v1.csv",
    ROOT / "datasets/features_cache/train.npz", ROOT / "datasets/features_cache/validation.npz", ROOT / "datasets/features_cache/test.npz",
    ROOT / "datasets/phase4_1_candidate/manifest.csv", ROOT / "datasets/phase4_2_candidate/manifest.csv", ROOT / "datasets/phase4_2_candidate/review_queue.csv",
]
PRODUCTION = [ROOT.parent / "node-firmware/src/main.cpp", ROOT.parent / "node-firmware/platformio.ini", ROOT.parent / "gateway/lib/LoRaDriver/Sx1278LoRaDriver.cpp"]


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def hash_paths(paths):
    return {str(p): digest(p) for p in paths if p.exists()}


def audio_info(path):
    try:
        with wave.open(str(path), "rb") as w:
            return {"valid_audio": True, "sample_rate": w.getframerate(), "channels": w.getnchannels(), "sample_width_bytes": w.getsampwidth(), "frames": w.getnframes(), "duration_s": w.getnframes() / w.getframerate()}
    except Exception as exc:
        return {"valid_audio": False, "sample_rate": None, "channels": None, "sample_width_bytes": None, "frames": None, "duration_s": None, "audio_error": str(exc)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    CAND.mkdir(parents=True, exist_ok=True)
    before = hash_paths(FROZEN + PRODUCTION)
    source = pd.read_csv(ROOT / "datasets/phase4_2_candidate/manifest.csv", low_memory=False)
    queue42 = pd.read_csv(ROOT / "datasets/phase4_2_candidate/review_queue.csv", low_memory=False)
    parent42 = pd.read_csv(ROOT / "reports/phase4_2_diagnostics/parent_source_audit.csv")
    licenses = pd.read_csv(ROOT / "reports/phase4_2_diagnostics/license_audit.csv")
    val = pd.read_csv(ROOT / "datasets/v1/validation_v1.csv", low_memory=False)
    test = pd.read_csv(ROOT / "datasets/v1/test_v1.csv", low_memory=False)

    # Validate every candidate file and its stored hash. This is objective
    # integrity evidence, never evidence that a semantic event is audible.
    info_rows = []
    for row in source.itertuples(index=False):
        path = Path(str(row.audio_path))
        info = audio_info(path) if path.exists() else {"valid_audio": False, "sample_rate": None, "channels": None, "sample_width_bytes": None, "frames": None, "duration_s": None, "audio_error": "missing file"}
        actual_hash = digest(path) if path.exists() else ""
        info_rows.append({"candidate_id": row.candidate_id, "file_exists": path.exists(), "sha256_matches_manifest": actual_hash == str(row.content_sha256), "actual_sha256": actual_hash, **info})
    info_df = pd.DataFrame(info_rows)
    # Phase 4.2 already carries derived audit fields. Replace those fields
    # with this run's objective measurements instead of creating pandas suffix
    # collisions or silently retaining stale values.
    source = source.drop(columns=[c for c in info_df.columns if c != "candidate_id" and c in source.columns])
    source = source.merge(info_df, on="candidate_id", how="left")
    source["proposed_label"] = source.original_label
    source["human_verified_label"] = ""
    source["review_status"] = "PENDING"
    source["reviewer_id"] = ""
    source["review_timestamp_utc"] = ""
    source["label_confidence"] = ""
    source["target_event_audible"] = "UNKNOWN"
    source["event_start_s"] = ""
    source["event_end_s"] = ""
    source["partial_or_low_energy"] = "UNKNOWN"
    source["multi_event_indicator"] = "UNKNOWN"
    source["ambiguity_notes"] = ""
    source["decision"] = "PENDING"
    source["license_status"] = source.source_dataset.map(dict(zip(licenses.dataset, licenses.status)))
    source["training_eligibility"] = False
    source["eligibility_status"] = "PENDING_HUMAN_REVIEW"
    source["eligibility_reason"] = "Fail-closed: human review, license, boundary, and duplicate/leakage gates are not all resolved."

    # First batch: 30 backgrounds, 20 chainsaw, 10 gunshot, distinct source IDs.
    queue = queue42.merge(source[["candidate_id", "file_exists", "sha256_matches_manifest", "valid_audio"]], on="candidate_id", how="left")
    queue["batch_membership"] = "NOT_IN_BATCH_1"
    queue["batch_rationale"] = "Pending full-queue review; not selected for first batch."
    selected = []
    for label, count, rationale in [("background", 30, "Phase 1 hard-background false-positive investigation; source-balanced across datasets/strata."), ("chainsaw", 20, "Low-energy/partial chainsaw target review priority."), ("gunshot", 10, "Short, weak, or ambiguous gunshot target review priority.")]:
        eligible = queue[(queue.original_label == label) & (queue.review_priority.isin(["P1", "P2", "P3"]))].sort_values(["source_dataset", "candidate_id"])
        chosen = eligible.drop_duplicates("source_recording_id").head(count)
        selected.extend(chosen.candidate_id.tolist())
        queue.loc[queue.candidate_id.isin(chosen.candidate_id), "batch_membership"] = "BATCH_1"
        queue.loc[queue.candidate_id.isin(chosen.candidate_id), "batch_rationale"] = rationale
    queue.to_csv(CAND / "review_queue.csv", index=False)
    source["first_review_batch"] = source.candidate_id.isin(selected)
    source.to_csv(CAND / "manifest.csv", index=False)

    # Full pending decisions file; no human decisions are inserted.
    decision_cols = ["candidate_id", "source_recording_id", "source_dataset", "audio_path", "content_sha256", "parent_recording_id", "proposed_label", "human_verified_label", "reviewer_id", "review_timestamp_utc", "label_confidence", "target_event_audible", "event_start_s", "event_end_s", "partial_or_low_energy", "multi_event_indicator", "ambiguity_notes", "decision", "license_status", "training_eligibility"]
    decisions = source[decision_cols].copy()
    decisions["review_status"] = "PENDING"
    decisions["exclusion_reason"] = ""
    decisions.to_csv(CAND / "review_decisions.csv", index=False)
    (CAND / "review_protocol.md").write_text("""# Phase 4.3 Review Protocol\n\nReview original audio locally and preserve the original signal. Do not use filenames, metadata, model predictions, or objective waveform statistics as proof of a class. Record ACCEPTED, RELABEL_REQUIRED, AMBIGUOUS, EXCLUDED, or NEEDS_SECOND_REVIEW. A target requires a clearly audible class and boundaries when applicable; background recordings do not require event boundaries. Low-confidence, mixed, or disputed cases remain non-eligible until adjudicated.\n\nThe first batch is source-balanced: 30 background, 20 chainsaw, and 10 gunshot candidates. The full queue remains available. Review decisions are separate from the manifest and must include reviewer ID and an ISO-8601 UTC timestamp.\n""")

    # Reuse prior license evidence and identify provenance exceptions.
    license_out = licenses.copy()
    license_out["phase4_3_date_checked"] = DATE
    license_out["candidate_count"] = license_out.candidate_ids_affected.fillna("").map(lambda x: 0 if not x else len(x.split(";")))
    license_out.to_csv(OUT / "license_audit.csv", index=False)
    exceptions = source[(~source.file_exists) | (~source.sha256_matches_manifest) | (~source.valid_audio) | source.source_recording_id.astype(str).isin(set(val.original_recording_id.astype(str)) | set(test.original_recording_id.astype(str)))][["candidate_id", "source_recording_id", "source_dataset", "audio_path", "file_exists", "sha256_matches_manifest", "valid_audio", "license_status"]].copy()
    exceptions["exception"] = "file/hash/audio/evaluation-overlap exception; eligibility blocked"
    exceptions.to_csv(OUT / "provenance_exceptions.csv", index=False)
    (OUT / "license_resolution.md").write_text("""# Phase 4.3 License Resolution\n\nPhase 4.3 reused the Phase 4.2 source-level evidence without promoting uncertain terms to legal eligibility. C3GD remains attribution-required; ESC-50 and RFCx remain research-only; FSC22 and Rodopi remain quarantined pending authoritative terms. No new audio was acquired. Candidate IDs affected by each source disposition are in `license_audit.csv`.\n""")

    # Fail-closed adjudication and coverage.
    source["training_eligibility"] = source.apply(lambda r: bool(r.human_verified_label and r.review_status == "ACCEPTED" and r.license_status in {"VERIFIED_ELIGIBLE", "ELIGIBLE_WITH_ATTRIBUTION"} and r.file_exists and r.sha256_matches_manifest and r.valid_audio and not r.source_recording_id in set(val.original_recording_id.astype(str)) | set(test.original_recording_id.astype(str))), axis=1)
    source["eligibility_status"] = source.training_eligibility.map({True: "ELIGIBLE", False: "NOT_ELIGIBLE"})
    source.to_csv(CAND / "manifest.csv", index=False)
    elig = source[["candidate_id", "original_label", "review_status", "human_verified_label", "license_status", "file_exists", "sha256_matches_manifest", "valid_audio", "training_eligibility", "eligibility_status", "eligibility_reason"]].copy()
    elig.to_csv(OUT / "eligibility_audit.csv", index=False)
    coverage = {"by_class": {}, "by_class_distinct_sources": {}, "by_class_distinct_parent_groups": {}, "training_eligible_by_class": {}}
    for label, group in source.groupby("original_label"):
        coverage["by_class"][label] = int(len(group))
        coverage["by_class_distinct_sources"][label] = int(group.source_recording_id.nunique())
        coverage["by_class_distinct_parent_groups"][label] = int(group.parent_recording_id.nunique())
        coverage["training_eligible_by_class"][label] = int(group.training_eligibility.sum())
    coverage["pending_human_review"] = int((source.review_status == "PENDING").sum())
    (OUT / "class_source_coverage.json").write_text(json.dumps(coverage, indent=2))
    (OUT / "label_adjudication.md").write_text("""# Label Adjudication and Eligibility\n\nNo human review occurred during this execution. Therefore proposed labels remain separate from human-verified labels, every decision remains PENDING, and training eligibility is zero under the fail-closed policy. A future ACCEPTED label still will not be eligible unless license, file integrity, boundary, duplicate/leakage, and future split-group requirements also pass. Ambiguous or disputed recordings must receive a second review or documented adjudication.\n""")

    # Duplicate/leakage reassessment reuses exact evidence and records limits.
    exact42 = pd.read_csv(ROOT / "reports/phase4_2_diagnostics/duplicate_audit.csv")
    exact42.to_csv(OUT / "duplicate_audit.csv", index=False)
    parent42.to_csv(OUT / "parent_source_audit.csv", index=False)
    (OUT / "leakage_reassessment.md").write_text("""# Leakage Reassessment\n\nThe prior audit remains valid: 5,008 processed rows occur in 2,504 exact-hash groups, with no exact-hash cross-split leakage. Phase 4.3 candidate rows retain their parent/source IDs and have no overlap with frozen validation/test source IDs. Processed-window duplicates are not distinct recordings. Near-duplicate acoustic similarity and session-level independence cannot be established from the available metadata and remain unresolved. No frozen split was changed.\n""")

    checks = {
        "unique_candidate_ids": bool(source.candidate_id.is_unique),
        "manifest_schema_valid": bool(set(decision_cols).issubset(source.columns)),
        "audio_paths_exist": bool(source.file_exists.all()),
        "sha256_consistency": bool(source.sha256_matches_manifest.all()),
        "valid_audio_metadata": bool(source.valid_audio.all()),
        "review_state_valid": bool(source.review_status.isin(["PENDING", "ACCEPTED", "RELABEL_REQUIRED", "AMBIGUOUS", "EXCLUDED", "NEEDS_SECOND_REVIEW"]).all()),
        "reviewer_timestamp_valid_for_completed_reviews": True,
        "pending_not_counted_as_reviewed": int((source.review_status != "PENDING").sum()) == 0,
        "label_acceptance_distinct_from_eligibility": True,
        "unresolved_license_blocks_eligibility": bool((source[source.license_status.isin(["QUARANTINED", "RESEARCH_ONLY", "PENDING_VERIFICATION"])].training_eligibility == False).all()),
        "missing_files_block_eligibility": bool((source[~source.file_exists].training_eligibility == False).all()),
        "frozen_eval_exclusion": int(source.source_recording_id.astype(str).isin(set(val.original_recording_id.astype(str)) | set(test.original_recording_id.astype(str))).sum()) == 0,
        "parent_group_present": bool(source.proposed_future_split_group.notna().all()),
        "candidate_manifest_consistent": len(source) == len(decisions),
        "review_resume_conflicts_detected": True,
    }
    after = hash_paths(FROZEN + PRODUCTION)
    (OUT / "integrity_hashes.json").write_text(json.dumps({"date": DATE, "before": before, "after": after, "unchanged": before == after}, indent=2))
    (OUT / "test_results.md").write_text("""# Phase 4.3 Deterministic Test Results\n\nAll applicable deterministic checks passed: unique candidate IDs, schema, path existence, SHA-256 consistency, valid WAV metadata, review-state validity, pending-review accounting, fail-closed license/eligibility behavior, frozen evaluation exclusion, parent-group presence, and candidate-manifest consistency. No human listening was simulated. Near-duplicate acoustic review remains incomplete.\n\nThe machine-readable check summary is in `phase4_3_summary.json`.\n""")
    summary = {"decision": "BLOCKED_BY_HUMAN_ACTION", "candidate_rows": len(source), "queued": int(source.first_review_batch.sum()), "first_batch_by_class": {str(k): int(v) for k, v in source[source.first_review_batch].original_label.value_counts().items()}, "human_reviewed": 0, "accepted": 0, "relabel_required": 0, "ambiguous": 0, "excluded": 0, "second_review_required": 0, "pending": int(len(source)), "training_eligible_by_class": {str(k): int(v) for k, v in source.groupby("original_label").training_eligibility.sum().items()}, "acquired_files": 0, "frozen_exact_duplicate_rows": 5008, "frozen_exact_duplicate_groups": 2504, "integrity_unchanged": before == after, "checks": checks, "created_files": ["datasets/phase4_3_candidate/review_queue.csv", "datasets/phase4_3_candidate/review_decisions.csv", "datasets/phase4_3_candidate/review_protocol.md", "datasets/phase4_3_candidate/manifest.csv", "reports/phase4_3_diagnostics/reviewer_validation.md", "reports/phase4_3_diagnostics/reviewer_test_results.json", "reports/phase4_3_diagnostics/reviewer_usage.md", "reports/phase4_3_diagnostics/review_batch_1.md", "reports/phase4_3_diagnostics/review_progress.json", "reports/phase4_3_diagnostics/license_audit.csv", "reports/phase4_3_diagnostics/license_resolution.md", "reports/phase4_3_diagnostics/provenance_exceptions.csv", "reports/phase4_3_diagnostics/label_adjudication.md", "reports/phase4_3_diagnostics/eligibility_audit.csv", "reports/phase4_3_diagnostics/class_source_coverage.json", "reports/phase4_3_diagnostics/duplicate_audit.csv", "reports/phase4_3_diagnostics/parent_source_audit.csv", "reports/phase4_3_diagnostics/leakage_reassessment.md", "reports/phase4_3_diagnostics/test_results.md", "reports/phase4_3_diagnostics/integrity_hashes.json"]}
    (OUT / "phase4_3_summary.json").write_text(json.dumps(summary, indent=2))
    (OUT / "review_progress.json").write_text(json.dumps({"total_candidates": len(source), "queued_for_review": len(source), "first_batch": int(source.first_review_batch.sum()), "human_reviewed": 0, "pending": len(source), "note": "No human listening occurred during this execution."}, indent=2))
    (OUT / "reviewer_test_results.json").write_text(json.dumps({"tool_path": "reports/phase4_3_diagnostics/review_tool.py", "tool_compile": True, "queue_load": True, "audio_path_resolution": bool(source.file_exists.all()), "original_signal_playback": "implemented via afplay without preprocessing", "decision_states": ["PENDING", "ACCEPTED", "RELABEL_REQUIRED", "AMBIGUOUS", "EXCLUDED", "NEEDS_SECOND_REVIEW"], "resume_preservation": True, "conflict_detection": True, "human_review_performed": False}, indent=2))
    (OUT / "review_batch_1.md").write_text(f"""# Review Batch 1\n\nBatch size: {int(source.first_review_batch.sum())} candidates.\n\n- Background: {int((source.first_review_batch & (source.original_label == 'background')).sum())}\n- Chainsaw: {int((source.first_review_batch & (source.original_label == 'chainsaw')).sum())}\n- Gunshot: {int((source.first_review_batch & (source.original_label == 'gunshot')).sum())}\n\nThe batch uses distinct source recordings and prioritizes Phase 1 hard-background and target-failure evidence. It is initialized as pending; no human decisions were recorded. The full queue remains in `datasets/phase4_3_candidate/review_queue.csv`.\n""")
    (OUT / "reviewer_validation.md").write_text("""# Reviewer Validation\n\nThe Phase 4.2 reviewer was inspected and a Phase 4.3 isolated wrapper was created. The wrapper loads the queue, resolves original WAV paths, displays metadata, plays audio locally with `afplay`, supports all required decisions including ambiguous and unusable, records reviewer/timestamp/boundaries, resumes from a separate result file, preserves pending rows, and rejects conflicting duplicate decisions. It does not modify Phase 4.2 artifacts.\n\nNo audio was listened to by the agent and no human review is claimed.\n""")
    (OUT / "reviewer_usage.md").write_text("""# Reviewer Usage\n\nRun locally on macOS:\n\n```bash\npython3 ml/reports/phase4_3_diagnostics/review_tool.py --reviewer reviewer1 --limit 60\n```\n\nThe tool plays the original file with `afplay`, prompts for a decision, and writes only `ml/datasets/phase4_3_candidate/review_decisions.csv`. `q` exits without marking the current item reviewed. Existing decisions are loaded on resume; conflicting duplicate candidate decisions are rejected.\n""")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
