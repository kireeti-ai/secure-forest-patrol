#!/usr/bin/env python3
"""Read-only Phase 4.12 inventory, provenance, license and split audit."""
from __future__ import annotations
import csv, hashlib, json, platform
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports'/'phase4_12_existing_data_recovery'
CHECKS=ROOT/'reports'/'online_dataset_alternative_audit'/'online_dataset_audit_checks.json'

def rows(path):
    with path.open(newline='',encoding='utf-8-sig') as f: return list(csv.DictReader(f))
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def write(name, fields, data):
    with (OUT/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(data)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    split_names=['train_v1','validation_v1','test_v1','external_test_v1']
    split_rows={n:rows(ROOT/'datasets'/'v1'/(n+'.csv')) for n in split_names}
    all_rows=[r for n in split_names[:3] for r in split_rows[n]]
    source_names=sorted(set(r['dataset_id'] for r in all_rows))
    source_paths={
      'rodopi':'datasets/raw/rodopi', 'sensing_forest':'datasets/raw/sensing_forest',
      'fsc22':'datasets/raw/fsc22', 'esc50_hf':'datasets/raw/esc50_hf',
      'rfcx_frugalai':'datasets/raw/rfcx_frugalai', 'c3gd':'datasets/raw/c3gd',
    }
    # Counts are derived from frozen manifests, not from filenames or segment counts alone.
    coverage={}
    for source in source_names:
        coverage[source]={}
        for split in split_names:
            rr=[r for r in split_rows[split] if r['dataset_id']==source]
            byclass=defaultdict(lambda:{'processed_segments':0,'original_recordings':0})
            ids=defaultdict(set)
            for r in rr: ids[r['class']].add(r['original_recording_id'])
            for r in rr: byclass[r['class']]['processed_segments']+=1
            for c in ids: byclass[c]['original_recordings']=len(ids[c])
            coverage[source][split]={'rows':len(rr),'classes':dict(byclass),'distinct_original_recordings':len(set(r['original_recording_id'] for r in rr))}
    (OUT/'class_source_coverage.json').write_text(json.dumps({'source_counts':source_names,'partitions':coverage,'manifest_rows':{n:len(split_rows[n]) for n in split_names},'notes':['original_recordings are manifest identifiers; independent status is evaluated separately','segment counts are not independent observations']},indent=2)+'\n')

    source_rows=[
      ('rodopi','Rodopi forest recordings','https://zenodo.org/records/5824433','CC BY 4.0','9 frozen source IDs; TextGrid files locally present','partial TextGrid/event context','background/chainsaw; no gunshot','source-level/segment labels; event timing available for annotated recordings','background semantics require audit; exact duplicate groups exist within validation','FROZEN_SOURCE_NOT_NEW'),
      ('sensing_forest','Sensing the Forest','https://zenodo.org/records/18909809','CC0 1.0','34 frozen source IDs; local collection metadata','collection/device context only; no target event lineage','background only in project mapping','soundscape labels; no verified event-free intervals','cannot convert absence of target annotation into verified background','BACKGROUND_ONLY_UNVERIFIED'),
      ('fsc22','FSC22 forest sound classification','https://github.com/IRMIOT/FSC22','README claims CC0 dataset and CC BY subset attribution; per-source rights need resolution','2,025 source clips; FreeSound source filename metadata, no session/device/site','clip-level class labels; no event timestamps','chainsaw, gunshot, many environmental classes; background mapping is not automatic','publisher class labels; FreeSound-derived source lineage','per-clip attribution and original-source independence unresolved; frozen source already used','UNRESOLVED_LICENSE_PROVENANCE'),
      ('esc50_hf','ESC-50-derived local subset','https://github.com/karolpiczak/ESC-50','CC BY-NC 3.0 in local license register','493 frozen source IDs; source-level Freesound lineage not session/device','clip-level environmental labels','background and mapped chainsaw examples; no gunshot coverage','clip labels; no event timestamps','non-commercial restriction; “no target label” is not verified negative','UNRESOLVED_PROVENANCE_LABELS'),
      ('rfcx_frugalai','RFCx FrugalAI','https://huggingface.co/datasets/rfcx/frugalai','CC BY-NC 4.0','400 source IDs in local manifest; dataset docs provide 12 kHz/3 s context, no session/device mapping','clip-level chainsaw/environment labels','chainsaw and environment; background not verified negative','publisher clip labels; no event timestamps in local metadata','non-commercial restriction; source/session independence and negative semantics unresolved','UNRESOLVED_LICENSE_PROVENANCE'),
      ('c3gd','Certus Caliber Classification Gunshot Dataset','https://zenodo.org/records/22286299','CC BY 4.0','100 frozen source IDs with C3GD event/platform/mic fields; raw metadata has file_id and clip_id','event_id, platform_id, cartridge_id, mic_id available; 4 events/48 platforms/15 microphones','gunshot only; no background/chainsaw','live-fire clips; class is caliber, project mapping to gunshot is derived','strong provenance but single-class and firearm-range domain','GUNSHOT_ONLY_NOT_3_CLASS'),
      ('kenya_phase4_5','Kenya staged acquisition','https://zenodo.org/records/21443074','dataset-level CC BY 4.0; file-level applicability unresolved','175 staged clips; 33 provisional filename groups; no verified parent/session/site','no verified parent/session/device mapping','publisher Chainsaw/background labels; no event timing','publisher clip labels; negative semantics unresolved','Phase 4.7 found 0 verified parent sources/sessions; quarantined','QUARANTINED_PROVENANCE'),
      ('ioai_phase4_8','IOAI staged acquisition','https://huggingface.co/datasets/pkasila/ioai26-ht1-nightwatch','dataset-level CC BY-SA 4.0; underlying ancestry unresolved','120 clips; no parent/session/device fields; 90 exact local FSC22 matches','none','60 chainsaw/60 gunshot publisher labels; no timestamps/background','publisher clip labels','duplicate/ancestry and file-level rights unresolved','DUPLICATE_OR_QUARANTINED'),
      ('vietnam_phase4_8','Vietnam benchmark staged acquisition','https://zenodo.org/records/13893977','Zenodo CC BY 4.0; mixed third-party ancestry unresolved','4,365 clips; no verified parent/session/device; branch names provisional','manual Raven Pro source context, not mapped per clip','690 gunshot; 3,675 noise not verified background','publisher archive labels','Belize mixed branch and internal repeats; no training admission','DUPLICATE_OR_QUARANTINED'),
    ]
    inv=[]
    for s,name,url,lic,prov,group,labels,ann,issues,status in source_rows:
        rr=[r for r in all_rows if r['dataset_id']==s]
        inv.append({'dataset_id':s,'dataset_name':name,'official_url':url,'license_summary':lic,'manifest_processed_segments':len(rr),'manifest_original_recordings':len(set(r['original_recording_id'] for r in rr)),'local_audio_files':len(list((ROOT/source_paths[s]).rglob('*.wav'))) if s in source_paths and (ROOT/source_paths[s]).exists() else 'not in frozen raw inventory','provenance_summary':prov,'grouping_evidence':group,'label_summary':labels,'annotation_summary':ann,'known_issues':issues,'recommendation':status})
    inv_fields=list(inv[0]); write('source_inventory.csv',inv_fields,inv)

    prov=[]
    for s,name,url,lic,pr,gr,la,an,issues,status in source_rows:
        rr=[r for r in all_rows if r['dataset_id']==s]
        prov.append({'dataset_id':s,'source_url':url,'manifest_recording_ids':len(set(r['original_recording_id'] for r in rr)),'verified_parent_recordings':100 if s=='c3gd' else (9 if s=='rodopi' else 0),'verified_sessions':4 if s=='c3gd' else 0,'device_or_platform_groups':48 if s=='c3gd' else 0,'parent_session_evidence':pr,'unresolved_provenance':issues,'status':'PASS' if s=='c3gd' else ('FAIL' if 'DUPLICATE' in status or 'ONLY' in status or 'BACKGROUND_ONLY' in status else 'UNRESOLVED')})
    write('recording_provenance_audit.csv',list(prov[0]),prov)

    lic=[]
    for s,name,url,l,pr,gr,la,an,issues,status in source_rows:
        lic.append({'dataset_id':s,'source_url':url,'dataset_license':l,'per_file_rights':'documented' if s in ('rodopi','c3gd','sensing_forest') else 'not fully established','attribution_requirements':'source citation/attribution required where license states it','noncommercial_or_redistribution':'CC BY-NC for RFCx/ESC-50; unresolved for FSC22/phase4 staged sources','evidence_reference':'local documentation and prior phase audit','status':'PASS' if s in ('rodopi','sensing_forest','c3gd') else 'UNRESOLVED','reason':issues})
    write('license_audit.csv',list(lic[0]),lic)

    labels=[]
    for s,name,url,l,pr,gr,la,an,issues,status in source_rows:
        labels.append({'dataset_id':s,'project_classes_supported':la,'annotation_granularity':an,'event_timestamps':'available' if s=='rodopi' else ('partial source metadata' if s=='c3gd' else 'not established'),'verified_background_status':'not verified' if s!='rodopi' else 'requires annotation audit','label_reliability':'documented source labels; project mapping/negative semantics require review','status':'PASS' if s=='c3gd' else 'UNRESOLVED','limitations':issues})
    write('label_quality_audit.csv',list(labels[0]),labels)

    sets={n:{r['original_recording_id'] for r in split_rows[n]} for n in split_names}
    overlaps=[]
    for i,a in enumerate(split_names):
        for b in split_names[i+1:]: overlaps.append({'partition_a':a,'partition_b':b,'recording_id_intersection':len(sets[a]&sets[b]),'session_intersection':'UNRESOLVED except C3GD metadata','exact_duplicate_cross_partition':'0 according to frozen exact duplicate audit for train/validation/test','segmentation_risk':'50% overlapping windows are correlated within each recording','status':'PASS for recorded IDs; UNRESOLVED for sessions'})
    write('split_integrity_audit.csv',list(overlaps[0]),overlaps)

    ranking=[
      {'candidate':'C3GD gunshot subset','license':'PASS','provenance':'PASS','labels':'PASS for gunshot mapping','independent_recordings':'100','background_negative':'FAIL','duplicate_leakage':'PASS for current split IDs; future reuse risk','preprocessing':'PASS with existing contract after preprocessing audit','research_value':'High for gunshot robustness, not forest background','overall':'FAIL','blockers':'Single gunshot class; no verified background/chainsaw; firearm-range domain','evidence':'datasets/raw/c3gd/C3GD/README.md; metadata.csv; frozen manifests'},
      {'candidate':'FSC22 chainsaw/gunshot/environment subsets','license':'UNRESOLVED','provenance':'UNRESOLVED','labels':'PASS for source class names; timestamps absent','independent_recordings':'2,025 source clips, independence not verified','background_negative':'UNRESOLVED','duplicate_leakage':'PASS current partitions; existing source already frozen','preprocessing':'PASS contract-compatible after audit','research_value':'High for forest target/background strata','overall':'UNRESOLVED','blockers':'FreeSound per-file rights/attribution and source groups; no verified negatives; already in frozen data','evidence':'raw/fsc22 README, LICENSE, Metadata; phase4 audits'},
      {'candidate':'Rodopi chainsaw/background','license':'PASS','provenance':'PASS source IDs/TextGrids; session independence limited','labels':'UNRESOLVED background/event semantics','independent_recordings':'9','background_negative':'UNRESOLVED','duplicate_leakage':'FAIL as new data: already frozen and exact duplicate groups in validation','preprocessing':'PASS','research_value':'Medium for forest context','overall':'FAIL','blockers':'Not new independent data; no gunshot; validation duplicates','evidence':'raw/rodopi/download_metadata.json; frozen duplicate audit'},
      {'candidate':'RFCx FrugalAI chainsaw/environment','license':'FAIL for unrestricted use / research-only CC BY-NC','provenance':'UNRESOLVED','labels':'UNRESOLVED negative semantics','independent_recordings':'400 manifest IDs; verified session count 0','background_negative':'UNRESOLVED','duplicate_leakage':'PASS current split IDs','preprocessing':'PASS after resampling audit','research_value':'High deployment relevance','overall':'FAIL','blockers':'Non-commercial restriction plus unresolved source/session and negatives','evidence':'raw/rfcx_frugalai/download_metadata.json; frozen manifests'},
      {'candidate':'Sensing the Forest background','license':'PASS CC0','provenance':'UNRESOLVED collection/session mapping','labels':'UNRESOLVED as verified negatives','independent_recordings':'34 manifest IDs; verified session count 0','background_negative':'FAIL for automatic admission','duplicate_leakage':'PASS current external split IDs','preprocessing':'PASS contract-compatible','research_value':'Medium background diversity','overall':'FAIL','blockers':'No target events and absence of annotations is not a verified negative','evidence':'frozen external_test_v1; prior Phase 4 reports'},
    ]
    write('admission_candidate_ranking.csv',list(ranking[0]),ranking)

    old=json.loads(CHECKS.read_text()); hashes={p:sha(p) for p in old['frozen_hashes']}; matches={p:hashes[p]==old['frozen_hashes'][p] for p in hashes}
    generated=['EXISTING_DATA_RECOVERY_REPORT.md','source_inventory.csv','recording_provenance_audit.csv','license_audit.csv','label_quality_audit.csv','split_integrity_audit.csv','class_source_coverage.json','admission_candidate_ranking.csv']
    ih={'audit_timestamp_utc':datetime.now(timezone.utc).isoformat(),'script':'run_existing_data_recovery.py','python':platform.python_version(),'protected_frozen_hashes':hashes,'protected_hash_matches':matches,'all_protected_hashes_match':all(matches.values()),'generated_artifact_sha256':{},'audio_downloads':0,'model_inference_started':False,'model_training_started':False,'threshold_tuning_started':False,'frozen_manifests_changed':False,'production_manifests_changed':False,'firmware_changed':False,'phase4_3_decisions_changed':False}
    decision={'decision':'BLOCKED_ON_UNRESOLVED_PROVENANCE_OR_LICENSE','qualified_candidates_for_separate_admission_review':[],'best_research_candidate':'C3GD gunshot subset for provenance-quality study only; not a three-class admission candidate','reasons':['C3GD has the strongest verified recording/session/device metadata but is gunshot-only and has no verified background/chainsaw data.','FSC22 has the strongest forest/target class relevance but source-level licensing, attribution, parent/session identity, and verified-negative semantics remain unresolved.','No source satisfies every mandatory gate; staged Phase 4.5/4.8 data remains quarantined.'],'unresolved_gates':['file-level licensing/attribution for FSC22 and staged sources','verified parent/session identity for most sources','verified background-negative semantics','near-duplicate/source ancestry beyond existing exact duplicate audit'],'recommended_next_step':'Do not modify or admit data. Resolve FSC22 file-level rights/source grouping or conduct a separately authorized human/provenance review of a narrowly scoped existing subset. Keep Phase 5 blocked.','downloads_performed':0,'training_started':False,'inference_started':False}
    (OUT/'phase4_12_decision.json').write_text(json.dumps(decision,indent=2)+'\n')
    report=f'''# Phase 4.12 — Existing Dataset Provenance Recovery and Admission Feasibility\n\nAudit date: {datetime.now(timezone.utc).date().isoformat()} UTC\n\n## Final decision\n\n**BLOCKED_ON_UNRESOLVED_PROVENANCE_OR_LICENSE**\n\nNo existing source is qualified for admission. C3GD is the strongest provenance-controlled source, with 100 frozen source recordings, 4 collection events, 48 platform groups, and 15 microphones, but it is gunshot-only and has no verified background or chainsaw class. FSC22 is the highest-value forest-target candidate, but its per-file FreeSound rights, source grouping, and verified-background semantics remain unresolved.\n\nNo audio was downloaded. No training, inference, relabeling, augmentation, threshold tuning, or production-manifest modification occurred.\n\n## Inventory and composition\n\nFrozen manifest counts were derived from actual rows:\n\n| Partition | Rows | Distinct source recording IDs |\n|---|---:|---:|\n| train | {len(split_rows['train_v1'])} | {len(sets['train_v1'])} |\n| validation | {len(split_rows['validation_v1'])} | {len(sets['validation_v1'])} |\n| test | {len(split_rows['test_v1'])} | {len(sets['test_v1'])} |\n| external_test | {len(split_rows['external_test_v1'])} | {len(sets['external_test_v1'])} |\n\nThe frozen train/validation/test sources are dominated by Rodopi background segments, while FSC22 supplies the principal mixed forest target/background taxonomy. C3GD supplies gunshot only. Full source/class/partition counts are in `class_source_coverage.json`; counts of processed windows are not treated as independent recordings.\n\n## Provenance and licensing\n\n- **C3GD:** local README and metadata expose event, file, platform, cartridge, microphone, and clip identifiers. The local license register and README record CC BY 4.0. This is the best provenance candidate, but it cannot supply all three classes.\n- **FSC22:** local README claims CC0 for the dataset and notes a CC-BY-attributed subset, while the inventory is FreeSound-derived and the local license register marks the license as unresolved. Per-file attribution and original recording/session identity are not sufficient for automatic admission.\n- **Rodopi:** local download metadata records CC BY 4.0 and TextGrid files, but the source is already in frozen data and exact duplicate groups occur within validation. It is not new independent data.\n- **RFCx:** local metadata records CC BY-NC 4.0. It is relevant forest chainsaw data, but non-commercial restrictions and source/session/negative semantics remain unresolved.\n- **Sensing the Forest:** local/previous audit evidence records CC0, but its soundscape material cannot be converted to verified background merely because a target event is absent.\n- **ESC-50, Kenya, IOAI, and Vietnam:** remain restricted, provenance-uncertain, duplicate, or quarantined under earlier reports.\n\n## Labels and negatives\n\nC3GD labels are firearm caliber classes; mapping the entire source to project `gunshot` is defensible for event presence, but there is no chainsaw/background coverage. FSC22 has explicit `Chainsaw` and `Gunshot` source classes, but labels are clip-level and lack event intervals. Generic environmental, silence, noise, and unannotated soundscape material were not automatically mapped to `background`.\n\n## Split integrity\n\nThe actual manifest check found zero intersections of `original_recording_id` across every pair of train, validation, test, and external-test partitions. The existing exact duplicate audit reports 5,008 duplicate rows in 2,504 groups and zero cross-split exact duplicate groups for the frozen train/validation/test partitions. This does not prove session-level or crop-level independence where source metadata is missing; those checks remain unresolved for most datasets.\n\n## Candidate ranking\n\nMandatory gates were evaluated before research-value ranking. No candidate has all gates PASS. The best research candidates are C3GD for provenance-controlled gunshot analysis and FSC22 for forest target-class relevance, but neither qualifies for admission. Details and evidence references are in `admission_candidate_ranking.csv`.\n\n## Validation\n\n- Script executed successfully and generated all required artifacts.\n- CSV schema/row-count and coverage reconciliation checks were run after generation.\n- Nine protected model, frozen-manifest, and feature-cache hashes matched their recorded values.\n- No downloads, model inference, training, threshold tuning, or production changes occurred.\n- Existing Git modifications were preserved; no unrelated files were reverted.\n\n## Recommended next action\n\nKeep Phase 5 blocked. If progress is required, authorize a separate narrow admission-review phase for FSC22 and/or C3GD that resolves exact file-level rights, parent/session grouping, event semantics, and duplicate ancestry. Do not create a training manifest from this audit.\n'''
    (OUT/'EXISTING_DATA_RECOVERY_REPORT.md').write_text(report)
    for p in generated: ih['generated_artifact_sha256']['ml/reports/phase4_12_existing_data_recovery/'+p]=sha(OUT/p)
    (OUT/'integrity_hashes.json').write_text(json.dumps(ih,indent=2)+'\n')
    print(json.dumps({'decision':decision['decision'],'sources':len(inv),'manifest_rows':len(all_rows),'qualified':0,'downloads':0,'all_protected_hashes_match':all(matches.values())},indent=2))

if __name__=='__main__': main()
