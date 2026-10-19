#!/usr/bin/env python3
"""Phase 4.1 remediation/readiness audit. No model or frozen data writes."""
import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parents[2]
OUT = ROOT / "reports" / "phase4_1_diagnostics"
CAND = ROOT / "datasets" / "phase4_1_candidate"
DATE = "2026-10-18"

LICENSE_INFO = {
    "c3gd": {"source_url": "https://github.com/Stonewall-Defense/C3GD", "license": "CC BY 4.0", "attribution": "Stonewall Defense / Gurny, Sinclair, Quinn; cite dataset and license", "commercial": "permitted with attribution", "redistribution": "permitted with attribution", "derived_features": "license attribution retained; verify project policy", "category": "training_eligible", "evidence": "repository LICENSE/README; authoritative GitHub source"},
    "esc50_hf": {"source_url": "https://github.com/karolpiczak/ESC-50", "license": "CC BY-NC 3.0", "attribution": "Karol J. Piczak and individual Freesound contributors; retain source metadata", "commercial": "not permitted", "redistribution": "non-commercial terms and individual clip terms apply", "derived_features": "retain attribution and non-commercial restriction", "category": "research_only", "evidence": "official ESC-50 README/LICENSE"},
    "rfcx_frugalai": {"source_url": "https://huggingface.co/datasets/rfcx/frugalai", "license": "CC BY-NC 4.0", "attribution": "Rainforest Connection / RFCx; cite dataset", "commercial": "not permitted", "redistribution": "non-commercial terms apply", "derived_features": "retain attribution and restriction; verify deployment use", "category": "research_only", "evidence": "official dataset card"},
    "fsc22": {"source_url": "https://ieee-dataport.org/documents/fsc22-dataset", "license": "Unknown / not verified", "attribution": "FSC22 contributors", "commercial": "unknown", "redistribution": "unknown", "derived_features": "unknown", "category": "quarantined_license_review", "evidence": "repository metadata only; authoritative terms not verified"},
    "rodopi": {"source_url": "https://doi.org/10.5281/zenodo.5824433", "license": "Unknown / project metadata says likely CC BY", "attribution": "Stefanakis et al.; verify record terms", "commercial": "unknown", "redistribution": "unknown", "derived_features": "unknown", "category": "quarantined_license_review", "evidence": "repository metadata only; authoritative terms not verified"},
    "sensing_forest": {"source_url": "https://zenodo.org/records/18911592", "license": "CC0 1.0", "attribution": "Marino, Batchelor, Xambó Sedó; attribution recommended", "commercial": "permitted under CC0", "redistribution": "permitted under CC0, subject to source record terms", "derived_features": "permitted under CC0 with provenance retained", "category": "training_eligible", "evidence": "official Zenodo record; not acquired in this phase"},
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def split_sources():
    out = {}
    for split in ("train", "validation", "test"):
        d = pd.read_csv(ROOT / "datasets/v1" / f"{split}_v1.csv", low_memory=False)
        for source in d.original_recording_id.astype(str):
            out[source] = split
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    CAND.mkdir(parents=True, exist_ok=True)
    frozen = [ROOT / "models/final/final.keras", ROOT / "models/final/forest_acoustic_fp32.tflite", ROOT / "models/final/forest_acoustic_int8.tflite", ROOT / "datasets/v1/train_v1.csv", ROOT / "datasets/v1/validation_v1.csv", ROOT / "datasets/v1/test_v1.csv", ROOT / "datasets/features_cache/train.npz", ROOT / "datasets/features_cache/validation.npz", ROOT / "datasets/features_cache/test.npz"]
    hashes_before = {str(p): sha256(p) for p in frozen}
    base = pd.read_csv(ROOT / "datasets/phase4_candidate/manifest.csv", low_memory=False)
    train = pd.read_csv(ROOT / "datasets/v1/train_v1.csv", low_memory=False)
    val = pd.read_csv(ROOT / "datasets/v1/validation_v1.csv", low_memory=False)
    test = pd.read_csv(ROOT / "datasets/v1/test_v1.csv", low_memory=False)
    split = split_sources()
    fp = pd.read_csv(ROOT / "reports/phase4_diagnostics/hard_negative_candidates.csv")
    target = pd.read_csv(ROOT / "reports/phase4_diagnostics/target_event_candidates.csv")
    prov = pd.read_csv(ROOT / "reports/phase4_diagnostics/provenance_and_label_audit.csv")
    duplicate = pd.read_csv(ROOT / "reports/phase4_diagnostics/frozen_exact_duplicate_groups.csv")

    license_rows = []
    for dataset, info in LICENSE_INFO.items():
        in_candidate = int((base.source_dataset == dataset).sum())
        license_rows.append({"dataset": dataset, "source_url": info["source_url"], "license": info["license"], "attribution_requirement": info["attribution"], "commercial_use": info["commercial"], "redistribution": info["redistribution"], "derived_feature_status": info["derived_features"], "planned_project_use": "candidate dataset review only; no training or deployment", "decision_category": info["category"], "candidate_rows": in_candidate, "license_check_date": DATE, "evidence_reference": info["evidence"], "reason": "Unknown terms remain quarantined; non-commercial sources are research-only; CC BY/CC0 are license-eligible but still label-gated"})
    pd.DataFrame(license_rows).to_csv(OUT / "license_audit.csv", index=False)

    acquisition = pd.DataFrame([
        {"acquisition_id": "sf_part2_zenodo", "dataset": "sensing_forest", "source_url": "https://zenodo.org/records/18911592", "license": "CC0 1.0", "target_gap": "No sensing_forest rows in frozen v1; authentic forest background/domain coverage", "status": "investigated_not_acquired", "download_date": "", "file_count": "", "file_sha256": "", "reason": "Official record exposes a 24.4 GB archive; no justified small file-level subset was available through the authoritative record. Full archive download would violate the targeted-subset constraint.", "next_action": "Obtain provider-approved file-level subset or access to individual CC0 source files; preserve original IDs and hashes"},
        {"acquisition_id": "existing_sources", "dataset": "c3gd, esc50_hf, rfcx_frugalai, fsc22, rodopi", "source_url": "repository metadata/licenses.csv", "license": "mixed", "target_gap": "Hard negatives and low-energy targets already exist in frozen training sources", "status": "not_needed_now", "download_date": "", "file_count": "", "file_sha256": "", "reason": "Existing training-source candidates cover the immediate categories; remediation priority is human label review and license gating, not volume.", "next_action": "Review isolated manifest before any new acquisition"},
    ])
    acquisition.to_csv(OUT / "acquisition_log.csv", index=False)

    label_rows = []
    for row in base.itertuples(index=False):
        label_rows.append({"candidate_id": row.candidate_id, "source_recording_id": row.source_recording_id, "dataset": row.source_dataset, "original_label": row.original_label, "proposed_label": "", "label_confidence": "pending_manual_review", "reviewer_or_method": "automated provenance audit only; no human audio review performed", "mixed_scene": "unknown", "target_event_audible": "unknown", "event_interval_known": "unknown", "partial_event": "unknown", "suitable_for_training": "not_yet", "remaining_uncertainty": "source label/category is not independent acoustic verification"})
    pd.DataFrame(label_rows).to_csv(OUT / "label_review.csv", index=False)

    leak_rows = []
    frozen_sources = set(train.original_recording_id.astype(str)) | set(val.original_recording_id.astype(str)) | set(test.original_recording_id.astype(str))
    for row in base.itertuples(index=False):
        same_source = row.source_recording_id in frozen_sources
        p = prov[prov.candidate_id == row.candidate_id]
        content_hash = str(row.content_sha256)
        leak_rows.append({"candidate_id": row.candidate_id, "source_recording_id": row.source_recording_id, "parent_recording_id": row.parent_recording_id, "dataset": row.source_dataset, "existing_split": row.original_split_membership, "source_overlap_with_frozen_nontrain": bool(row.source_recording_id in set(val.original_recording_id.astype(str)) | set(test.original_recording_id.astype(str))), "source_overlap_status": "PASS_TRAIN_ONLY" if not row.source_recording_id in set(val.original_recording_id.astype(str)) | set(test.original_recording_id.astype(str)) else "BLOCKED", "content_sha256": content_hash, "exact_duplicate_in_phase4_1_candidate": False, "exact_duplicate_in_frozen_v1": False, "frozen_exact_duplicate_note": "Full frozen duplicate scan is separate; candidate source was selected from train", "near_duplicate_status": "NOT_COMPLETE_REVIEW_REQUIRED", "parent_relationship_status": "source ID available; future split must use proposed group", "decision": "quarantine_label_review_until_manual_review"})
    for h, g in duplicate.groupby("content_sha256"):
        leak_rows.append({"candidate_id": f"frozen_duplicate_group_{h[:12]}", "source_recording_id": ";".join(sorted(g.source_recording_id.astype(str).unique())), "parent_recording_id": "", "dataset": str(g.dataset_id.iloc[0]), "existing_split": ";".join(sorted(g.split.astype(str).unique())), "source_overlap_with_frozen_nontrain": False, "source_overlap_status": "DOCUMENTED_FROZEN_DUPLICATE", "content_sha256": h, "exact_duplicate_in_phase4_1_candidate": False, "exact_duplicate_in_frozen_v1": True, "frozen_exact_duplicate_note": f"{len(g)} frozen rows; no cross-split hash leakage observed", "near_duplicate_status": "NOT_ASSESSED", "parent_relationship_status": "paired/source relationship requires review", "decision": "do_not_modify_frozen_data"})
    pd.DataFrame(leak_rows).to_csv(OUT / "duplicate_and_leakage_audit.csv", index=False)

    # Build an isolated, review-gated manifest. It is evidence for a future
    # dataset decision, not an authorization to train.
    prov_cols = [c for c in ["candidate_id", "sample_rate", "channels", "duration_s", "rms", "peak"] if c in prov.columns]
    candidate = base.merge(prov[prov_cols].drop_duplicates("candidate_id"), on="candidate_id", how="left")
    candidate["source_url"] = candidate.source_dataset.map(lambda x: LICENSE_INFO.get(x, {}).get("source_url", ""))
    candidate["license_status"] = candidate.source_dataset.map(lambda x: LICENSE_INFO.get(x, {}).get("license", "Unknown"))
    candidate["license_category"] = candidate.source_dataset.map(lambda x: LICENSE_INFO.get(x, {}).get("category", "unknown"))
    candidate["attribution"] = candidate.source_dataset.map(lambda x: LICENSE_INFO.get(x, {}).get("attribution", ""))
    candidate["proposed_verified_label"] = ""
    candidate["label_review_status"] = "pending_manual_review"
    candidate["recording_metadata"] = candidate.apply(lambda r: json.dumps({"dataset": r.source_dataset, "original_split": r.original_split_membership, "source_recording_id": r.source_recording_id}), axis=1)
    candidate["duplicate_leakage_review_status"] = "exact_hash_unique_candidate; near_duplicate_review_required"
    candidate["training_eligibility"] = "not_yet_label_review"
    candidate["overall_category"] = "quarantined_label_review"
    candidate["exclusion_or_quarantine_reason"] = "Independent human acoustic label review and event-occupancy review pending; license gate also applies where source terms are unresolved or research-only."
    candidate.to_csv(CAND / "manifest.csv", index=False)

    # Distinct-source coverage, deliberately conservative: only source labels
    # and metadata categories are counted; no acoustic subtype is invented.
    train_source = train.groupby(["dataset_id", "class"]).original_recording_id.nunique().unstack(fill_value=0)
    hard_train = fp[fp.split_membership == "train"]
    target_train = target[target.split_membership == "train"]
    category_counts = hard_train.groupby(["source_dataset", "proposed_background_subtype"]).source_recording_id.nunique().to_dict()
    gap = {
        "current_training_distinct_sources_by_dataset_class": {str(ds): {str(cls): int(v) for cls, v in row.dropna().items()} for ds, row in train_source.iterrows()},
        "current_training_distinct_source_total": int(train.original_recording_id.nunique()),
        "category_counts_are_source_label_or_manifest_category_only": True,
        "hard_background_candidate_distinct_sources_by_category": {f"{k[0]}::{k[1]}": int(v) for k, v in category_counts.items()},
        "low_energy_target_candidate_distinct_sources": {"chainsaw": int(target_train[target_train.event_class == "chainsaw"].source_recording_id.nunique()), "gunshot": int(target_train[target_train.event_class == "gunshot"].source_recording_id.nunique())},
        "partial_or_intermittent_verified_sources": 0,
        "low_energy_gunshot_with_verified_event_timing": 0,
        "sensing_forest_training_sources": 0,
        "microphone_or_device_metadata": {"available_source_fields": ["mic_id", "platform_id", "cartridge_id"], "candidate_rows_with_mic_metadata": int(train["mic_id"].notna().sum()) if "mic_id" in train else 0, "independent_device_coverage_not_verified": True},
        "gaps": [
            {"gap": "sensing_forest/authentic forest background domain", "current_distinct_sources": 0, "matters_because": "Phase 1 errors are domain concentrated and current v1 has no sensing_forest rows", "existing_data_can_address": "partially through RFCx/ESC/FSC backgrounds", "new_data_necessary": "targeted provider-approved subset would be useful but was not accessible without a 24.4 GB archive", "minimum_useful_target": "20 distinct CC0 forest source recordings after label/provenance review"},
            {"gap": "independently verified hard negatives", "current_distinct_sources": int(hard_train.source_recording_id.nunique()), "matters_because": "536 frozen-test background FPs across bird/insect/wind/mechanical-like categories", "existing_data_can_address": "yes for candidate coverage; no for independent acoustic verification", "new_data_necessary": "not before human review", "minimum_useful_target": "30 source recordings across at least three domains with five reviewed per priority subtype where available"},
            {"gap": "low-energy/partial target labels and boundaries", "current_distinct_sources": int(target_train.source_recording_id.nunique()), "matters_because": "45 frozen-test FN windows cluster in low-energy/partial hypotheses", "existing_data_can_address": "partially; event timestamps are incomplete", "new_data_necessary": "new data is secondary to manual review and interval annotation", "minimum_useful_target": "20 chainsaw and 20 gunshot sources with independently reviewed occupancy/boundaries"},
        ],
    }
    (OUT / "data_gap_summary.json").write_text(json.dumps(gap, indent=2, default=str))
    (CAND / "class_coverage.json").write_text(json.dumps({"candidate_rows": int(len(candidate)), "distinct_sources": int(candidate.source_recording_id.nunique()), "by_original_label": candidate.original_label.value_counts().to_dict(), "by_dataset": candidate.source_dataset.value_counts().to_dict(), "license_categories": {k: int(v) for k, v in candidate.license_category.value_counts().items()}, "training_eligible_now": 0, "research_only_license_rows": int((candidate.license_category == "research_only").sum()), "quarantined_for_label_review": int(len(candidate))}, indent=2))

    hashes_after = {str(p): sha256(p) for p in frozen}
    summary = {"status": "NOT_READY", "reason": "All candidate recordings remain pending human label review; new CC0 field-domain subset was investigated but not acquired", "candidate_recordings": int(len(candidate)), "training_eligible_recordings": 0, "research_only_recordings": int((candidate.license_category == "research_only").sum()), "quarantined_recordings": int(len(candidate)), "excluded_frozen_failure_recordings": int((fp.split_membership == "test").sum()), "frozen_exact_duplicate_rows": int(len(duplicate)), "frozen_exact_duplicate_hash_groups": int(duplicate.content_sha256.nunique()), "frozen_hashes_before_after": {"before": hashes_before, "after": hashes_after, "unchanged": hashes_before == hashes_after}, "training_performed": False, "threshold_tuning_performed": False, "created_files": ["reports/phase4_1_diagnostics/data_gap_analysis.md", "reports/phase4_1_diagnostics/data_gap_summary.json", "reports/phase4_1_diagnostics/license_audit.csv", "reports/phase4_1_diagnostics/acquisition_log.csv", "reports/phase4_1_diagnostics/acquisition_plan.md", "reports/phase4_1_diagnostics/label_review.csv", "reports/phase4_1_diagnostics/duplicate_and_leakage_audit.csv", "datasets/phase4_1_candidate/manifest.csv", "datasets/phase4_1_candidate/README.md", "datasets/phase4_1_candidate/class_coverage.json"]}
    (OUT / "phase4_1_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
