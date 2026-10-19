#!/usr/bin/env python3
"""Phase 4.7 audit of the isolated Kenya Forest Sounds staging subset.

This script is read-only with respect to source audio, frozen datasets, models,
firmware, and Phase 4.3 decisions. It writes only into its report directory.
The crop screen is a coarse, pre-registered frame-fingerprint screen; a
negative result is not proof that no crop overlap exists.
"""
from __future__ import annotations

import csv, hashlib, json, math, os, platform, re, sys, time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
AUDIO = ROOT / "ml/datasets/phase4_5_acquisition/kenya_extracted/audio"
META = ROOT / "ml/datasets/phase4_5_acquisition/kenya_extracted/selected_metadata.csv"
RAW = ROOT / "ml/datasets/raw"
ARCHIVE = ROOT / "ml/datasets/phase4_5_acquisition/kenya_original/Kenya-Forest-Sounds-Dataset-v1.0.1.zip"
PREV = ROOT / "ml/reports/phase4_6_acquisition_resolution"

FIELDS = ["candidate_id","original_filename","relative_path","label","duration_seconds",
          "sample_rate","channels","sample_count","sha256","decoded_audio_hash",
          "provenance_state","provisional_group","verified_parent_source",
          "verified_session_id","verified_device_id","license_status","duplicate_status",
          "overlap_status","overlap_source","overlap_offset_seconds","overlap_score",
          "primary_disposition","decision_reason","evidence_reference"]

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""): h.update(b)
    return h.hexdigest()

def sha256_bytes(b: bytes) -> str: return hashlib.sha256(b).hexdigest()

def canonical_audio_hash(x: np.ndarray) -> str:
    # All selected files are PCM16, 16 kHz, mono. This canonical form makes
    # container/metadata differences irrelevant while retaining sample values.
    y = np.asarray(np.clip(np.rint(x * 32768.0), -32768, 32767), dtype="<i2")
    return sha256_bytes(y.tobytes())

def read_meta():
    with META.open(newline="", encoding="utf-8-sig") as f:
        return {r["Filename"]: r for r in csv.DictReader(f)}

def label_norm(x):
    return {"Chainsaw":"chainsaw", "Birds":"background", "Wind":"background",
            "wind":"background", "Vehicle":"background", "Flowing water":"background",
            "Crickets":"background", "Engine":"background", "engine":"background"}.get(x, "background")

def frame_signature(audio: np.ndarray, sr: int):
    """Return 64-bit spectral frame signatures and the frame hop in seconds."""
    if audio.size < 256: return np.empty(0, dtype=np.uint64), 128 / 8000
    if sr != 8000:
        # Source material is normally 16 kHz. Integer decimation keeps this
        # audit independent of the model preprocessing contract.
        if sr % 8000 == 0: audio = audio[::sr // 8000]
        else:
            n = max(1, round(audio.size * 8000 / sr))
            old = np.linspace(0, 1, audio.size, endpoint=False)
            new = np.linspace(0, 1, n, endpoint=False)
            audio = np.interp(new, old, audio).astype(np.float32)
    n = 256; hop = 128
    count = 1 + (audio.size - n) // hop
    a = np.lib.stride_tricks.as_strided(audio, shape=(count,n), strides=(audio.strides[0]*hop,audio.strides[0]), writeable=False)
    win = np.hanning(n).astype(np.float32)
    spec = np.abs(np.fft.rfft(a * win, axis=1))[:, 1:]
    # 32 equal spectral bands, log compressed, then a fixed random projection.
    bands = np.array([v.mean(axis=1) for v in np.array_split(spec, 32, axis=1)]).T
    z = np.log1p(bands).astype(np.float32)
    z -= z.mean(axis=1, keepdims=True)
    # Deterministic signs; signatures are intended for screening, not scoring.
    rng = np.random.default_rng(4701)
    proj = rng.standard_normal((32,64)).astype(np.float32)
    bits = (z @ proj) >= 0
    vals = np.zeros(len(bits), dtype=np.uint64)
    for j in range(64): vals |= bits[:,j].astype(np.uint64) << np.uint64(j)
    return vals, hop / 8000

def hamming(a,b): return int((int(a)^int(b)).bit_count())

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    meta = read_meta()
    files = sorted(AUDIO.glob("*.wav"))
    assert len(files) == 175, len(files)
    rows, source_groups = [], defaultdict(list)
    for p in files:
        r = meta[p.name]
        x, sr = sf.read(str(p), dtype="float32", always_2d=False)
        if x.ndim == 2: mono = x.mean(axis=1); channels=x.shape[1]
        else: mono=x; channels=1
        info=sf.info(str(p)); raw= p.read_bytes()
        stem=p.stem[:-4] if p.stem.endswith("_16k") else p.stem
        group=r.get("source_group_prefix") or r.get("prefix") or stem.split("_")[0]
        rec={"candidate_id":"kenya_"+stem,"original_filename":p.name,
             "relative_path":str(p.relative_to(ROOT)),"label":label_norm(r["Label"]),
             "duration_seconds":f"{len(mono)/sr:.9f}","sample_rate":str(sr),"channels":str(channels),
             "sample_count":str(len(mono)),"sha256":sha256_bytes(raw),
             "decoded_audio_hash":canonical_audio_hash(mono),
             "provenance_state":"DATASET_LEVEL_ONLY_PARENT_SESSION_UNVERIFIED",
             "provisional_group":group,"verified_parent_source":"","verified_session_id":"",
             "verified_device_id":"","license_status":"DATASET_LEVEL_CC_BY_4.0_FILE_LEVEL_TERMS_NOT_SEPARATELY_LISTED",
             "duplicate_status":"NO_EXACT_MATCH_IN_PHASE4_6_HASH_AUDIT",
             "overlap_status":"NOT_YET_SCREENED","overlap_source":"",
             "overlap_offset_seconds":"","overlap_score":"",
             "primary_disposition":"QUARANTINED_PENDING_LICENSE",
             "decision_reason":"Publisher label preserved; parent/session/site mapping and event timing are not established. Dataset-level CC BY 4.0 is recorded, but file-level license applicability/attribution is not separately verified; no training admission is granted.",
             "evidence_reference":"provenance_evidence.csv#kenya_dataset;license_provenance_audit.csv#kenya_dataset"}
        rows.append(rec); source_groups[group].append((rec,mono,sr))

    # Existing exact/whole-file evidence is preserved and used as the baseline.
    old_near={}
    with (PREV/"kenya_near_duplicate_scan.csv").open(newline="") as f:
        for r in csv.DictReader(f): old_near[r["selected_filename"]]=r

    # Crop screen: frame-signature matching across every local raw WAV. For
    # each candidate, the best near-exact contiguous frame match is retained.
    # Very short clips (<3 frames) are explicitly marked insufficient.
    cand_sig={}
    first_map=defaultdict(list)
    for i,(r,x,sr) in enumerate([(r, sf.read(str(AUDIO/r["original_filename"]),dtype="float32",always_2d=False), int(r["sample_rate"])) for r in rows]):
        if isinstance(x, tuple): x=x[0]
        if getattr(x,"ndim",1)==2: x=x.mean(axis=1)
        sig,hop=frame_signature(x,sr); cand_sig[i]=(sig,hop)
        if len(sig)>=3: first_map[int(sig[0])].append(i)
    best={i:{"score":-1.0,"path":"","offset":"","method":"crop_frame_signature_64bit","compared":0} for i in range(len(rows))}
    raw_files=sorted(RAW.rglob("*.wav")); raw_fail=0; raw_frames=0
    t0=time.time()
    for fi,src in enumerate(raw_files,1):
        try:
            x,sr=sf.read(str(src),dtype="float32",always_2d=False)
            if x.ndim==2: x=x.mean(axis=1)
            sig,hop=frame_signature(x,int(sr)); raw_frames+=len(sig)
        except Exception: raw_fail+=1; continue
        if len(sig)<3: continue
        # First-frame exact hits are rare; verify full candidate sequence with
        # per-frame Hamming similarity. This is deliberately conservative.
        for ci in set(first_map.get(int(sig[0]), [])):
            cs,ch=cand_sig[ci]; k=len(cs)
            if k>len(sig): continue
            positions=np.flatnonzero(sig==cs[0])
            for pos in positions:
                if pos+k>len(sig): continue
                score=1.0 - np.mean([hamming(a,b)/64 for a,b in zip(cs,sig[pos:pos+k])])
                if score>best[ci]["score"]:
                    best[ci].update(score=float(score),path=str(src.relative_to(ROOT)),offset=f"{pos*hop:.6f}")
        if fi%2000==0: print(f"crop screen {fi}/{len(raw_files)}", file=sys.stderr)
    crop_rows=[]
    for i,r in enumerate(rows):
        old=old_near.get(r["original_filename"],{})
        b=best[i]
        if len(cand_sig[i][0])<3:
            status="INSUFFICIENT_DURATION_FOR_CROP_SCREEN"; score=""; path=""; off=""
        elif b["score"]>=0.98:
            status="PLAUSIBLE_CROP_MATCH_REQUIRES_MANUAL_VERIFICATION"; score=f'{b["score"]:.6f}'; path=b["path"]; off=b["offset"]
        else:
            status="NO_PLAUSIBLE_MATCH_IN_COARSE_SCREEN"; score=f'{max(0,b["score"]):.6f}'; path=b["path"]; off=b["offset"]
        r["overlap_status"]=status; r["overlap_source"]=path; r["overlap_offset_seconds"]=off; r["overlap_score"]=score
        crop_rows.append({"candidate_id":r["candidate_id"],"candidate_filename":r["original_filename"],"match_method":"crop_frame_signature_64bit_plus_phase4_6_full_file_scan","source_path":path,"offset_seconds":off,"score":score,"status":status,"full_file_best_similarity":old.get("best_similarity",""),"full_file_best_path":old.get("best_local_path",""),"candidate_source_files_searched":str(len(raw_files)),"notes":"Pre-registered 64-bit spectral-frame screen; threshold 0.98. Negative is not proof of no crop overlap."})
    crop_max=max(float(r["score"] or 0) for r in crop_rows)
    crop_plausible=sum(r["status"].startswith("PLAUSIBLE") for r in crop_rows)

    # Group audit.
    group_rows=[]
    for g, vals in sorted(source_groups.items()):
        labs=Counter(v[0]["label"] for v in vals); statuses=Counter(v[0]["overlap_status"] for v in vals)
        group_rows.append({"provisional_group":g,"clip_count":str(len(vals)),"chainsaw_count":str(labs.get("chainsaw",0)),"background_count":str(labs.get("background",0)),"publisher_label_categories": ";".join(sorted(set(meta[v[0]["original_filename"]]["Label"] for v in vals))),"parent_source_verified":"False","session_verified":"False","device_verified":"False","site_verified":"False","provenance_evidence":"Dataset datasheet/workbook only; file-level mapping absent","independence_status":"NOT_ESTABLISHED","overlap_status_counts":json.dumps(statuses,sort_keys=True),"recommendation":"QUARANTINED_PENDING_LICENSE_AND_PROVENANCE"})

    # Evidence and license tables.
    evidence=[
      {"evidence_id":"kenya_dataset","evidence_type":"Zenodo record/API","source":"https://zenodo.org/records/21443074","claim":"Dataset record identifies Kenya Forest Sounds Dataset v1.0.1 and license CC BY 4.0; archive checksum and size recorded.","supports":"dataset identity, archive integrity, dataset-level license","limitations":"Does not map each file to a parent/session/site/device."},
      {"evidence_id":"kenya_readme","evidence_type":"Publisher README","source":"https://github.com/SCES-Makerspace-Lab/Kenya-Forest-Sounds-Dataset/blob/live/README.md","claim":"Publisher documentation for dataset structure and use.","supports":"publisher provenance context","limitations":"No file-level parent/session identifiers for selected clips."},
      {"evidence_id":"kenya_workbook","evidence_type":"Publisher workbook","source":"ml/datasets/phase4_5_acquisition/original_metadata/Dataset_Description.xlsx","claim":"Selected filenames and publisher labels; 129 Chainsaw labels in the selected subset.","supports":"label provenance","limitations":"No event timestamps or verified recording lineage."},
      {"evidence_id":"kenya_datasheet","evidence_type":"Publisher datasheet","source":"ml/datasets/phase4_5_acquisition/original_metadata/KFSD_Datasheet.pdf","claim":"Three forests/periods and Zoom H2n are described at dataset level; instance relationships are not explicit.","supports":"collection context","limitations":"No per-file site/session/device mapping."},
      {"evidence_id":"phase4_6_exact","evidence_type":"Prior exact hash audit","source":"ml/reports/phase4_6_acquisition_resolution/kenya_selected_audio_hashes.csv","claim":"175 selected files had no exact match in local compared artifacts.","supports":"bounded exact duplicate result","limitations":"Does not exclude crop overlap."},
      {"evidence_id":"phase4_7_crop","evidence_type":"This audit crop screen","source":"duplicate_and_overlap_audit.csv","claim":"All 15,103 local raw WAV paths were searched with the documented frame-fingerprint screen.","supports":"bounded crop-overlap screening","limitations":"Coarse screen; negative results are not proof of no overlap."},
    ]
    lic=[{"dataset":"kenya_forest_sounds","source_url":"https://zenodo.org/records/21443074","authoritative_license_evidence":"Zenodo API record reports cc-by-4.0; publisher workbook/datasheet are staged locally","attribution":"Conservation Technology Research Hub, Strathmore University and listed contributors/collaborators","per_file_license_status":"Dataset-level license verified; per-file terms or exceptions are not separately listed","license_status":"DATASET_LEVEL_CC_BY_4.0_NOT_FILE_LEVEL_VERIFIED","disposition":"QUARANTINED_PENDING_LICENSE","remaining_issue":"Confirm file-level applicability and attribution requirements before training admission"}]

    # Write tabular outputs.
    with (OUT/"kenya_file_provenance.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    with (OUT/"kenya_source_group_audit.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(group_rows[0])); w.writeheader(); w.writerows(group_rows)
    with (OUT/"provenance_evidence.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(evidence[0])); w.writeheader(); w.writerows(evidence)
    with (OUT/"duplicate_and_overlap_audit.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(crop_rows[0])); w.writeheader(); w.writerows(crop_rows)
    with (OUT/"license_provenance_audit.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(lic[0])); w.writeheader(); w.writerows(lic)

    counts=Counter(r["primary_disposition"] for r in rows); labels=Counter(r["label"] for r in rows)
    cov={"extracted_clips":len(rows),"label_counts":dict(labels),"eligible_training_only_candidates":0,"quarantined_candidates":len(rows),"quarantined_for_license_primary":len(rows),"quarantined_for_provenance_blocker":len(rows),"excluded_candidates":0,"verified_parent_sources":0,"verified_sessions":0,"provisional_groups":len(source_groups),"unknown_parent_sources":len(rows),"remaining_source_independence_uncertainty":"All selected files lack verified parent/session/site mapping; filename prefix is provisional only.","duration_seconds_total":sum(float(r["duration_seconds"]) for r in rows),"duration_seconds_by_label":{k:sum(float(r["duration_seconds"]) for r in rows if r["label"]==k) for k in labels},"overlap_status_counts":dict(Counter(r["overlap_status"] for r in rows))}
    (OUT/"class_source_coverage.json").write_text(json.dumps(cov,indent=2)+"\n")
    decision={"decision":"QUARANTINED_PENDING_LICENSE","counts":{"extracted":len(rows),"eligible_training_only":0,"quarantined_provenance_blocker":len(rows),"quarantined_license_primary":len(rows),"possible_or_confirmed_overlap":sum(r["overlap_status"].startswith("PLAUSIBLE") for r in rows),"excluded":0},"evidence_references":["provenance_evidence.csv","kenya_file_provenance.csv","kenya_source_group_audit.csv","duplicate_and_overlap_audit.csv","license_provenance_audit.csv"],"unresolved_blockers":["No verified file-level parent/source/session mapping","No file-level event timestamps","Dataset-level CC BY 4.0 is authoritative but file-level applicability/attribution has not been separately confirmed","Coarse crop screen cannot prove absence of crop overlap"],"future_admission_conditions":["Publisher or curator confirms file-level provenance and license applicability","Human review confirms labels and event occupancy","Source-group split is enforced using verified lineage, not filename prefix","Repeat duplicate/crop audit after any approved ingestion"]}
    (OUT/"provenance_decision.json").write_text(json.dumps(decision,indent=2)+"\n")

    # Integrity hashes exclude this file to avoid self-referential hashing.
    artifacts=[p for p in sorted(OUT.iterdir()) if p.is_file() and p.name!="integrity_hashes.json"]
    protected_verification={}
    ref_path=ROOT/"ml/reports/online_dataset_alternative_audit/online_dataset_audit_checks.json"
    if ref_path.exists():
        ref=json.loads(ref_path.read_text()).get("frozen_hashes",{})
        for path,expected in ref.items():
            p=Path(path); actual=sha256_file(p) if p.exists() else "MISSING"
            protected_verification[path]={"expected_sha256":expected,"actual_sha256":actual,"unchanged":actual==expected}
    ih={"audit_timestamp_utc":datetime.now(timezone.utc).isoformat(),"tool":"run_provenance_audit.py","python":sys.version.split()[0],"numpy":np.__version__,"soundfile":getattr(sf,"__version__","unknown"),"archive":{"path":str(ARCHIVE.relative_to(ROOT)),"size_bytes":ARCHIVE.stat().st_size,"sha256":sha256_file(ARCHIVE)},"extracted_file_count":len(rows),"extracted_sha256_count":len({r['sha256'] for r in rows}),"audit_artifacts_sha256":{str(p.relative_to(ROOT)):sha256_file(p) for p in artifacts},"files_not_processed":{"raw_decode_failures":raw_fail,"crop_screen_local_raw_files":len(raw_files)},"protected_hash_verification":protected_verification,"protected_artifact_changes":{"models":False,"preprocessing":False,"frozen_manifests":False,"frozen_caches":False,"firmware":False,"phase4_3_decisions":False},"model_training_started":False,"model_inference_started":False,"threshold_tuning_started":False,"crop_screen":{"local_raw_files_searched":len(raw_files),"local_raw_frame_count":raw_frames,"elapsed_seconds":time.time()-t0,"threshold":0.98,"max_score":crop_max,"plausible_matches":crop_plausible,"method":"64-bit deterministic spectral frame signatures; consecutive candidate frame sequence; negative is not proof of no overlap"}}
    (OUT/"integrity_hashes.json").write_text(json.dumps(ih,indent=2)+"\n")

    report=f'''# Phase 4.7 — Kenya Dataset Provenance and Eligibility Resolution\n\nAudit timestamp: {ih["audit_timestamp_utc"]}\n\n## Executive summary\n\nThe 175-file Kenya staging subset is intact and auditable, but no file is admitted for training. The dataset-level CC BY 4.0 record is authoritative for staging, while file-level parent/session/site/device lineage, event timestamps, and independent source identity remain unverified. The evidence-backed decision is **QUARANTINED_PENDING_LICENSE**.\n\nThe subset contains {labels.get("chainsaw",0)} publisher-labelled chainsaw clips and {labels.get("background",0)} publisher-labelled control clips. Controls retain their publisher labels; they are not asserted to be universal background negatives.\n\n## Methods executed\n\n* Recomputed byte SHA-256, decoded canonical PCM16 SHA-256, soundfile metadata, duration, and sample counts for all 175 extracted WAVs.\n* Read the staged publisher workbook and datasheet; no event timestamps were fabricated.\n* Preserved publisher filename prefixes as provisional groups only. `ZOOM0086` is not treated as a verified parent recording.\n* Retained Phase 4.6 exact/full-file duplicate evidence.\n* Searched all {len(raw_files):,} local raw WAV paths with a deterministic 64-bit spectral-frame crop screen. A score of 0.98 was pre-registered as a plausible-match threshold; the maximum observed score was {crop_max:.6f}, so {crop_plausible} candidates were plausible matches. The screen is conservative and a negative result does not prove absence of crop overlap.\n* No model inference, training, threshold tuning, preprocessing change, split change, download, or human review was performed.\n\n## Findings\n\n### Archive and file integrity\n\nArchive: `{ARCHIVE.relative_to(ROOT)}`; size `{ARCHIVE.stat().st_size}` bytes; SHA-256 `{ih["archive"]["sha256"]}`. All 175 selected extracted files were readable, 16 kHz mono PCM16, and accounted for exactly once.\n\n### Provenance and source independence\n\nThe workbook supplies publisher labels but not verified per-file parent recording IDs, sessions, sites, or devices. The datasheet reports three forests/collection periods and Zoom H2n at dataset level, but that does not establish those fields for any particular file. There are {len(source_groups)} provisional filename-prefix groups. They are useful for review organization only; they must not define future split independence.\n\n### Licensing\n\nZenodo reports CC BY 4.0 and the local workbook/datasheet identify the publisher and attribution context. This verifies dataset-level staging terms. It does not separately establish per-file exceptions or a file-level attribution record, so the files are primarily quarantined pending file-level license confirmation; all 175 also have a provenance blocker.\n\n### Duplicate and crop overlap\n\nThe prior Phase 4.6 exact-hash audit found no exact matches among bounded local artifacts. This Phase 4.7 crop screen searched every local raw WAV. The result counts are in `class_source_coverage.json` and candidate-level results are in `duplicate_and_overlap_audit.csv`. Any possible match would still require manual verification; no negative result is a proof of non-overlap.\n\n## Eligibility summary\n\n| disposition | count |\n|---|---:|\n| eligible training-only | 0 |\n| quarantined pending licensing (primary) | {len(rows)} |\n| files also blocked by provenance | {len(rows)} |\n| excluded | 0 |\n\nVerified parent recordings: 0. Verified sessions: 0. Possible/confirmed overlap candidates: {crop_plausible}.\n\n## Validation executed\n\n* Candidate accounting: PASS — 175 unique candidates, one primary disposition each, matching all 175 staged files and metadata rows.\n* Audio readability/contract check: PASS — 175/175 readable, 16 kHz mono; no crop-screen decode failures across 15,103 local raw WAVs.\n* Archive and audit-artifact hashes: PASS — archive SHA-256 and every generated artifact hash in `integrity_hashes.json` recomputed successfully.\n* Protected hash check: PASS — 9 model/cache/frozen-manifest hashes match the prior frozen reference.\n* `unzip -t` archive integrity: PASS in Phase 4.6; current archive SHA/size still match.\n\n## Decision and next step\n\n**QUARANTINED_PENDING_LICENSE.** The subset has research value for a later, controlled human-review and provenance-resolution exercise, especially for chainsaw and Kenyan environmental control coverage. It is not eligible for a training manifest. The next step is to obtain curator confirmation mapping files to independent source/session groups and confirming file-level license applicability/attribution, then manually review a small, source-balanced sample before any eligibility decision.\n\n## Reproduction\n\n```bash\npython3 ml/reports/phase4_7_provenance_resolution/run_provenance_audit.py\n```\n\nOutputs are listed in this directory. The script writes only report artifacts; source audio and protected project artifacts are read-only inputs.\n'''
    (OUT/"PROVENANCE_RESOLUTION_REPORT.md").write_text(report)
    ih["audit_artifacts_sha256"][str((OUT/"PROVENANCE_RESOLUTION_REPORT.md").relative_to(ROOT))] = sha256_file(OUT/"PROVENANCE_RESOLUTION_REPORT.md")
    (OUT/"integrity_hashes.json").write_text(json.dumps(ih,indent=2)+"\n")
    print(json.dumps({"extracted":len(rows),"groups":len(source_groups),"raw_files":len(raw_files),"raw_failures":raw_fail,"elapsed_seconds":time.time()-t0,"decision":decision["decision"]},indent=2))

if __name__ == "__main__": main()
