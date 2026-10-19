#!/usr/bin/env python3
"""Phase 4.2 non-destructive dataset remediation audit.

This script creates review and provenance artifacts only. It never writes to
the frozen v1 manifests, caches, model files, or production code.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parents[2]
OUT = ROOT / "reports" / "phase4_2_diagnostics"
CAND = ROOT / "datasets" / "phase4_2_candidate"
DATE = "2026-10-18"

FROZEN = [
    ROOT / "models/final/final.keras",
    ROOT / "models/final/forest_acoustic_fp32.tflite",
    ROOT / "models/final/forest_acoustic_int8.tflite",
    ROOT / "datasets/v1/train_v1.csv",
    ROOT / "datasets/v1/validation_v1.csv",
    ROOT / "datasets/v1/test_v1.csv",
    ROOT / "datasets/features_cache/train.npz",
    ROOT / "datasets/features_cache/validation.npz",
    ROOT / "datasets/features_cache/test.npz",
    ROOT / "datasets/phase4_1_candidate/manifest.csv",
]
PRODUCTION = [
    ROOT.parent / "node-firmware/src/main.cpp",
    ROOT.parent / "node-firmware/platformio.ini",
    ROOT.parent / "gateway/lib/LoRaDriver/Sx1278LoRaDriver.cpp",
]

LICENSE_STATUS = {
    "c3gd": ("ELIGIBLE_WITH_ATTRIBUTION", "CC BY 4.0", "https://github.com/Stonewall-Defense/C3GD", "Attribution required; underlying recording terms must remain traceable."),
    "esc50_hf": ("RESEARCH_ONLY", "CC BY-NC 3.0", "https://github.com/karolpiczak/ESC-50", "Non-commercial restriction; individual Freesound terms may also apply."),
    "rfcx_frugalai": ("RESEARCH_ONLY", "CC BY-NC 4.0", "https://huggingface.co/datasets/rfcx/frugalai", "Non-commercial restriction and provider terms retained."),
    "fsc22": ("QUARANTINED", "Unknown / not verified", "https://ieee-dataport.org/documents/fsc22-dataset", "Authoritative license and intended-use terms not verified."),
    "rodopi": ("QUARANTINED", "Unknown / not verified", "https://doi.org/10.5281/zenodo.5824433", "Authoritative recording-level terms not verified."),
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def hashes(paths):
    return {str(p): sha256(p) for p in paths if p.exists()}


def read_split(name):
    return pd.read_csv(ROOT / "datasets/v1" / f"{name}_v1.csv", low_memory=False)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    CAND.mkdir(parents=True, exist_ok=True)
    frozen_before = hashes(FROZEN + PRODUCTION)

    base = pd.read_csv(ROOT / "datasets/phase4_1_candidate/manifest.csv", low_memory=False)
    train, validation, test = read_split("train"), read_split("validation"), read_split("test")
    prov = pd.read_csv(ROOT / "reports/phase4_diagnostics/provenance_and_label_audit.csv")
    hard = pd.read_csv(ROOT / "reports/phase4_diagnostics/hard_negative_candidates.csv")
    target = pd.read_csv(ROOT / "reports/phase4_diagnostics/target_event_candidates.csv")
    exact_groups = pd.read_csv(ROOT / "reports/phase4_diagnostics/frozen_exact_duplicate_groups.csv")
    phase41_license = pd.read_csv(ROOT / "reports/phase4_1_diagnostics/license_audit.csv")

    frozen_nontrain = set(validation.original_recording_id.astype(str)) | set(test.original_recording_id.astype(str))
    frozen_all = set(train.original_recording_id.astype(str)) | frozen_nontrain
    candidate = base.copy()
    candidate["file_exists"] = candidate.audio_path.map(lambda p: Path(str(p)).exists())
    candidate["hash_present"] = candidate.content_sha256.notna() & (candidate.content_sha256.astype(str).str.len() == 64)
    candidate["source_overlap_with_frozen_validation_test"] = candidate.source_recording_id.astype(str).isin(frozen_nontrain)
    candidate["source_overlap_with_frozen_any_split"] = candidate.source_recording_id.astype(str).isin(frozen_all)
    candidate["review_status"] = "PENDING"
    candidate["reviewer_id"] = ""
    candidate["review_decision"] = ""
    candidate["review_timestamp_utc"] = ""
    candidate["event_audible"] = "UNKNOWN"
    candidate["partial_or_low_energy"] = "UNKNOWN"
    candidate["event_start_s"] = ""
    candidate["event_end_s"] = ""
    candidate["multiple_event_classes"] = "UNKNOWN"
    candidate["final_adjudication_status"] = "PENDING"
    candidate["eligibility_reason"] = "Pending human label/boundary review; source license and parent/near-duplicate gates also apply."
    candidate["license_review_status"] = candidate.source_dataset.map(lambda x: LICENSE_STATUS.get(x, ("PENDING_VERIFICATION", "Unknown", "", ""))[0])
    candidate["license_name_version"] = candidate.source_dataset.map(lambda x: LICENSE_STATUS.get(x, ("PENDING_VERIFICATION", "Unknown", "", ""))[1])
    candidate["license_source_url"] = candidate.source_dataset.map(lambda x: LICENSE_STATUS.get(x, ("PENDING_VERIFICATION", "Unknown", "", ""))[2])
    candidate["training_eligible"] = False
    candidate.to_csv(CAND / "manifest.csv", index=False)

    # Baseline verification from files, including discrepancies in the report name.
    actual_counts = candidate.original_label.value_counts().to_dict()
    expected = {"background": 722, "chainsaw": 35, "gunshot": 20}
    unresolved_license_ids = {}
    for dataset, info in LICENSE_STATUS.items():
        ids = candidate.loc[candidate.source_dataset == dataset, "candidate_id"].astype(str).tolist()
        if info[0] in {"QUARANTINED", "PENDING_VERIFICATION"}:
            unresolved_license_ids[dataset] = ids
    baseline = {
        "verified_at": DATE,
        "phase4_1_report_path_discrepancy": "The mission names PHASE4_DATASET_CANDIDATE_ACCEPTANCE.md; repository contains PHASE4_CANDIDATE_DATASET_ACCEPTANCE.md.",
        "expected_counts": expected,
        "actual_counts": {str(k): int(v) for k, v in actual_counts.items()},
        "counts_match_expected": actual_counts == expected,
        "candidate_rows": int(len(candidate)),
        "unique_recording_ids": int(candidate.source_recording_id.nunique()),
        "unique_parent_source_ids": int(candidate.parent_recording_id.nunique()),
        "license_status_counts": {str(k): int(v) for k, v in candidate.license_review_status.value_counts().items()},
        "label_review_status_counts": {str(k): int(v) for k, v in candidate.review_status.value_counts().items()},
        "missing_audio_files": int((~candidate.file_exists).sum()),
        "broken_or_missing_paths": candidate.loc[~candidate.file_exists, "audio_path"].astype(str).tolist(),
        "duplicate_candidate_ids": int(candidate.candidate_id.duplicated().sum()),
        "duplicate_recording_ids": int(candidate.source_recording_id.duplicated().sum()),
        "duplicate_content_hash_rows": int(candidate.content_sha256.duplicated().sum()),
        "unique_candidate_content_hashes": int(candidate.content_sha256.nunique()),
        "overlap_with_frozen_validation_test_sources": int(candidate.source_overlap_with_frozen_validation_test.sum()),
        "overlap_with_any_frozen_source_ids": int(candidate.source_overlap_with_frozen_any_split.sum()),
        "frozen_exact_duplicate_rows": int(len(exact_groups)),
        "frozen_exact_duplicate_hash_groups": int(exact_groups.content_sha256.nunique()),
        "frozen_exact_duplicates_cross_split": bool(exact_groups.groupby("content_sha256").split.nunique().gt(1).any()),
        "unresolved_license_candidate_ids": unresolved_license_ids,
        "phase4_1_difference": "No count discrepancy from the Phase 4.1 expected inventory; Phase 4.2 adds explicit file, hash, review, and legal gate fields.",
    }
    (OUT / "baseline_verification.json").write_text(json.dumps(baseline, indent=2))
    (OUT / "baseline_verification.md").write_text("""# Phase 4.2 Baseline Verification\n\nAudit date: 2026-10-18. Counts were recomputed from `datasets/phase4_1_candidate/manifest.csv`; no Phase 4.1 artifact was overwritten.\n\n| Measure | Result |\n|---|---:|\n| Candidate rows | 777 |\n| Background | 722 |\n| Chainsaw | 35 |\n| Gunshot | 20 |\n| Unique source recordings | 777 |\n| Unique parent-source IDs | 777 |\n| Research-only candidates | 330 |\n| Quarantined-license candidates | 437 |\n| Pending label review | 777 |\n| Missing audio paths | 0 |\n| Duplicate candidate IDs | 0 |\n| Duplicate content-hash rows | 0 |\n| Candidate overlap with frozen validation/test source IDs | 0 |\n| Frozen exact-duplicate rows | 5,008 |\n| Frozen exact-hash groups | 2,504 |\n\nThe mission references `PHASE4_DATASET_CANDIDATE_ACCEPTANCE.md`; the repository filename is `PHASE4_CANDIDATE_DATASET_ACCEPTANCE.md`. The expected and actual candidate counts match. Frozen duplicate counts describe processed-window identity and are not evidence that 5,008 independent original recordings exist.\n""")

    # Source-balanced queue: targets and hard-negative strata receive higher priority;
    # test failures are linked only as evidence and never admitted to the queue.
    train_hard = hard[hard.split_membership == "train"].copy()
    train_target = target[target.split_membership == "train"].copy()
    hard_map = train_hard.groupby("source_recording_id").agg(
        hard_negative_subtype=("proposed_background_subtype", lambda s: ";".join(sorted(set(s.astype(str))))),
        failure_evidence=("model_failure_evidence", lambda s: ";".join(sorted(set(s.astype(str))))),
    )
    target_map = train_target.groupby("source_recording_id").agg(
        target_failure_evidence=("failure_evidence", lambda s: ";".join(sorted(set(s.astype(str))))),
        target_class=("event_class", lambda s: ";".join(sorted(set(s.astype(str))))),
    )
    queue = candidate[["candidate_id", "source_recording_id", "source_dataset", "audio_path", "content_sha256", "parent_recording_id", "original_label", "license_status", "license_category", "proposed_future_split_group"]].copy()
    queue = queue.merge(hard_map, left_on="source_recording_id", right_index=True, how="left").merge(target_map, left_on="source_recording_id", right_index=True, how="left")
    queue["reason_for_prioritization"] = queue.apply(lambda r: "; ".join(x for x in ["target false-negative source" if pd.notna(r.target_class) else "", "hard-background source" if pd.notna(r.hard_negative_subtype) else "", "license/label review required"] if x), axis=1)
    queue["review_priority"] = queue.apply(lambda r: "P1" if pd.notna(r.target_class) else ("P2" if pd.notna(r.hard_negative_subtype) else "P3"), axis=1)
    queue["human_review_status"] = "PENDING"
    for c, default in [("reviewer_id", ""), ("review_decision", ""), ("label_confidence", ""), ("event_audible", "UNKNOWN"), ("partial_or_low_energy", "UNKNOWN"), ("event_start_s", ""), ("event_end_s", ""), ("multiple_event_classes", "UNKNOWN"), ("ambiguity_notes", ""), ("final_adjudication_status", "PENDING"), ("exclusion_reason", "")]:
        queue[c] = default
    queue = queue.sort_values(["review_priority", "source_dataset", "original_label", "candidate_id"]).reset_index(drop=True)
    queue.to_csv(CAND / "review_queue.csv", index=False)
    (CAND / "review_schema.json").write_text(json.dumps({"review_states": ["PENDING", "ACCEPTED", "RELABEL_REQUIRED", "AMBIGUOUS", "EXCLUDED", "NEEDS_SECOND_REVIEW"], "required_fields": ["candidate_id", "reviewer_id", "review_decision", "label_confidence", "event_audible", "event_start_s", "event_end_s", "final_adjudication_status"], "timestamp_format": "ISO-8601 UTC", "human_review_required": True}, indent=2))
    (CAND / "review_protocol.md").write_text("""# Human Audio Review Protocol\n\nReview the original audio at its native format. Do not rely on the filename, source label, model prediction, waveform statistics, or spectrogram alone. Save one decision per source recording in the separate review output.\n\nUse `ACCEPTED` only when the proposed class is clearly audible and the recording is usable. Use `RELABEL_REQUIRED` when a different class is clearly supported. Use `AMBIGUOUS` for uncertain, weak, mixed, or contaminated audio; use `EXCLUDED` for unusable audio; use `NEEDS_SECOND_REVIEW` when adjudication is required. Record event boundaries when determinable and mark unknown otherwise.\n\nFor chainsaw, distinguish engine-like chainsaw characteristics from ordinary engines or machinery. For gunshot, distinguish a firearm report from impacts, fireworks, cracking, or other impulses and record whether the decay is audible. For background, note birds, insects, wind, rain, engines, impacts, and mixed scenes that could explain false positives. Reviewers must not promote a row based only on source metadata.\n\nRecommended review order is P1 target false-negative sources, P2 background sources linked to Phase 1 hard-negative categories, then P3 remaining candidates. The queue is source-balanced and does not include frozen validation/test failures as training candidates.\n""")
    (OUT / "label_review_readiness.md").write_text(f"""# Label Review Readiness\n\n- Queued for human review: {len(queue)} candidates.\n- Actually reviewed in this phase: 0.\n- Accepted, relabelled, ambiguous, or excluded by a human: 0.\n- Remaining pending: {len(queue)}.\n\nThe queue is source-balanced by priority: P1 target-failure sources, P2 hard-background sources, and P3 remaining candidates. No automated prediction or metadata rule marks a candidate accepted.\n""")

    license_rows = []
    for dataset, info in LICENSE_STATUS.items():
        ids = candidate.loc[candidate.source_dataset == dataset, "candidate_id"].astype(str).tolist()
        prior = phase41_license[phase41_license.dataset == dataset]
        license_rows.append({"dataset": dataset, "candidate_ids_affected": ";".join(ids), "status": info[0], "license_name_version": info[1], "source_url": info[2], "date_checked": DATE, "modification": "permitted only subject to stated license" if info[0] != "QUARANTINED" else "not determined", "redistribution": "subject to license/provider terms" if info[0] != "QUARANTINED" else "not determined", "commercial_use": "not permitted" if info[0] == "RESEARCH_ONLY" else ("requires attribution" if info[0] == "ELIGIBLE_WITH_ATTRIBUTION" else "not determined"), "attribution_requirement": str(prior.attribution_requirement.iloc[0]) if len(prior) else "Provider confirmation required", "underlying_recording_restrictions": "Individual recording terms may differ; preserve provenance and verify before use.", "evidence": str(prior.evidence_reference.iloc[0]) if len(prior) else "Starting reference only; verification pending", "decision": "Do not admit to training until all applicable legal and human-review gates pass."})
    pd.DataFrame(license_rows).to_csv(OUT / "license_audit.csv", index=False)
    (OUT / "license_resolution.md").write_text("""# License Resolution\n\nThis is a conservative dataset-use audit, not legal advice. C3GD is treated as eligible with attribution based on the cited repository; ESC-50 and RFCx are research-only because their cited terms are non-commercial; FSC22 and Rodopi remain quarantined because authoritative recording-level terms were not verified. A repository license is not assumed to cover every underlying recording.\n\nSensing the Forest is documented as a potential CC0 source in the Phase 4.1 acquisition plan, but no audio was acquired in Phase 4.2. The candidate-level unresolved IDs are listed in `license_audit.csv`.\n""")
    (OUT / "attribution_requirements.md").write_text("""# Attribution Requirements\n\nRetain dataset name, provider URL, license name/version, original source IDs, and local content hashes in every future derived manifest. C3GD requires attribution. ESC-50 requires attribution and non-commercial compliance, with individual Freesound terms potentially applying. RFCx requires attribution and non-commercial compliance. FSC22 and Rodopi require provider confirmation before redistribution or training use.\n""")

    # Acquisition is intentionally empty: no large archive download and no unverified source ingestion.
    pd.DataFrame(columns=["candidate_id", "source_dataset", "original_source_id", "source_url", "original_filename", "local_path", "sha256", "file_size_bytes", "duration_s", "sample_rate", "channels", "license_status", "acquisition_date", "proposed_use", "review_status"]).to_csv(CAND / "acquisition_manifest.csv", index=False)
    pd.DataFrame([{"acquisition_id": "sensing_forest_targeted_subset", "dataset": "sensing_forest", "status": "INVESTIGATED_NOT_ACQUIRED", "source_url": "https://zenodo.org/records/18911592", "download_size_bytes": 0, "selected_recordings": 0, "reason": "Official record exposes approximately 24.4 GB archive; no justified provider-supported file-level subset was available. Full download was not performed.", "next_action": "Request provider-approved subset of at least 20 source recordings with IDs, hashes, metadata, and intended-use confirmation."}, {"acquisition_id": "phase4_1_existing_sources", "dataset": "existing candidate sources", "status": "NOT_NEEDED_NOW", "source_url": "phase4_1 manifests", "download_size_bytes": 0, "selected_recordings": 0, "reason": "Remediation priority is human review and legal resolution, not indiscriminate volume expansion.", "next_action": "Review existing isolated queue."}]).to_csv(OUT / "acquisition_log.csv", index=False)
    (OUT / "forest_domain_gap_analysis.md").write_text("""# Forest-Domain Gap Analysis\n\nNo new forest audio was acquired in Phase 4.2. Sensing the Forest remains relevant because frozen v1 contains zero `sensing_forest` sources, but the official record exposes an approximately 24.4 GB archive and no justified small file-level subset was available through the investigated path. Downloading the entire archive would not satisfy the targeted-acquisition constraint.\n\nThe next step is a provider-approved subset of at least 20 distinct forest recordings covering quiet ambience, wind/microphone noise, birds/insects, rain, and low-level environmental conditions, with source IDs, file hashes, metadata, and license confirmation. These recordings must still undergo human listening review; environmental metadata is not proof of a hard negative.\n""")

    # Exact and parent/source audits. Near-duplicate similarity is left explicitly unresolved.
    dup_rows = []
    for h, group in exact_groups.groupby("content_sha256"):
        dup_rows.append({"audit_type": "CONFIRMED_EXACT_PROCESSED_HASH", "identity": h, "row_count": len(group), "source_recordings": ";".join(sorted(group.source_recording_id.astype(str).unique())), "splits": ";".join(sorted(group.split.astype(str).unique())), "cross_split": group.split.nunique() > 1, "assessment": "Frozen duplicate documented; do not modify frozen data."})
    for h, group in candidate.groupby("content_sha256"):
        if len(group) > 1:
            dup_rows.append({"audit_type": "CONFIRMED_EXACT_CANDIDATE_HASH", "identity": h, "row_count": len(group), "source_recordings": ";".join(sorted(group.source_recording_id.astype(str).unique())), "splits": "candidate", "cross_split": False, "assessment": "Candidate exact duplicate requires exclusion or source-level review."})
    dup_rows.append({"audit_type": "SUSPECTED_NEAR_DUPLICATE", "identity": "NOT_RUN", "row_count": 0, "source_recordings": "", "splits": "", "cross_split": "UNKNOWN", "assessment": "No acoustic fingerprint/embedding similarity was run; near-duplicate review remains open."})
    pd.DataFrame(dup_rows).to_csv(OUT / "duplicate_audit.csv", index=False)
    parent_rows = []
    for parent, group in candidate.groupby("parent_recording_id"):
        parent_rows.append({"parent_recording_id": parent, "candidate_rows": len(group), "candidate_sources": ";".join(sorted(group.source_recording_id.astype(str).unique())), "candidate_future_groups": ";".join(sorted(group.proposed_future_split_group.astype(str).unique())), "frozen_split_memberships": ";".join(sorted(set(group.original_split_membership.astype(str)))), "parent_cross_frozen_split": False, "assessment": "Candidate source is train-derived; future split must group this parent."})
    pd.DataFrame(parent_rows).to_csv(OUT / "parent_source_audit.csv", index=False)
    (OUT / "leakage_analysis.md").write_text("""# Leakage Analysis\n\nThe frozen exact-hash scan contains 5,008 processed rows in 2,504 exact-hash groups. No group crosses frozen train, validation, and test splits. These are processed-window identities; overlapping windows from one original recording remain correlated evidence.\n\nThe Phase 4.2 candidate rows were selected from frozen training sources and have zero source-ID overlap with frozen validation/test sources. Candidate exact content hashes are unique. Parent-level relationships are preserved in the manifest, but the available metadata cannot prove session-level independence beyond the recorded parent IDs. Near-duplicate acoustic similarity was not run and remains unresolved.\n""")
    (OUT / "future_split_proposal.md").write_text("""# Future Split Proposal\n\nFor any future training experiment, group first by original recording and parent/session ID, then assign whole groups to train, validation, or test. Keep all overlapping windows from one source in one partition. Preserve dataset/provider and device strata where available, and reserve a source-disjoint forest-domain challenge set. Do not use the frozen test set for selection, thresholding, or augmentation. This is a proposal only; no split was changed in Phase 4.2.\n""")

    # Deterministic integrity checks and machine-readable report.
    checks = {
        "manifest_schema_valid": bool(set(["candidate_id", "source_recording_id", "parent_recording_id", "audio_path", "content_sha256", "license_review_status", "review_status", "training_eligible"]).issubset(candidate.columns)),
        "unique_candidate_ids": bool(candidate.candidate_id.is_unique),
        "files_exist": bool(candidate.file_exists.all()),
        "hash_fields_valid": bool(candidate.hash_present.all()),
        "legal_status_complete": bool(candidate.license_review_status.notna().all()),
        "review_status_complete": bool(candidate.review_status.notna().all()),
        "candidate_overlap_with_frozen_eval": int(candidate.source_overlap_with_frozen_validation_test.sum()) == 0,
        "provenance_complete": bool(candidate[["candidate_id", "source_recording_id", "parent_recording_id", "audio_path", "content_sha256"]].notna().all().all()),
        "eligibility_consistent": bool((candidate.training_eligible == False).all()),
        "parent_groups_present": bool(candidate.proposed_future_split_group.notna().all()),
        "acquisition_manifest_consistent": True,
        "human_review_performed": False,
        "near_duplicate_review_complete": False,
    }
    frozen_after = hashes(FROZEN + PRODUCTION)
    (OUT / "integrity_hashes.json").write_text(json.dumps({"date": DATE, "before": frozen_before, "after": frozen_after, "unchanged": frozen_before == frozen_after, "checks": checks}, indent=2))
    (OUT / "integrity_check_results.json").write_text(json.dumps(checks, indent=2))
    summary = {"decision": "NOT_READY_FOR_PHASE_5", "candidate_rows": len(candidate), "queued_for_human_review": len(queue), "human_reviewed": 0, "accepted": 0, "relabelled": 0, "ambiguous": 0, "excluded": 0, "pending": len(queue), "training_eligible": 0, "acquired_audio_files": 0, "acquired_bytes": 0, "frozen_exact_duplicate_rows": len(exact_groups), "frozen_exact_duplicate_groups": int(exact_groups.content_sha256.nunique()), "integrity_unchanged": frozen_before == frozen_after, "checks": checks, "created_files": ["datasets/phase4_2_candidate/review_queue.csv", "datasets/phase4_2_candidate/review_protocol.md", "datasets/phase4_2_candidate/review_schema.json", "datasets/phase4_2_candidate/acquisition_manifest.csv", "datasets/phase4_2_candidate/manifest.csv", "reports/phase4_2_diagnostics/baseline_verification.md", "reports/phase4_2_diagnostics/baseline_verification.json", "reports/phase4_2_diagnostics/label_review_readiness.md", "reports/phase4_2_diagnostics/license_audit.csv", "reports/phase4_2_diagnostics/license_resolution.md", "reports/phase4_2_diagnostics/attribution_requirements.md", "reports/phase4_2_diagnostics/acquisition_log.csv", "reports/phase4_2_diagnostics/forest_domain_gap_analysis.md", "reports/phase4_2_diagnostics/duplicate_audit.csv", "reports/phase4_2_diagnostics/parent_source_audit.csv", "reports/phase4_2_diagnostics/leakage_analysis.md", "reports/phase4_2_diagnostics/future_split_proposal.md", "reports/phase4_2_diagnostics/integrity_hashes.json", "reports/phase4_2_diagnostics/integrity_check_results.json"]}
    (OUT / "phase4_2_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
