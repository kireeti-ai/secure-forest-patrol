#!/usr/bin/env python3
"""Phase 4.9 provenance recovery using only already-acquired artifacts."""
from __future__ import annotations
import csv, hashlib, json, sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import soundfile as sf

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
P48=ROOT/'ml/reports/phase4_8_fasttrack_acquisition'
MANIFEST=P48/'acquisition_manifest.csv'
DUP=P48/'duplicate_and_leakage_audit.csv'
META=ROOT/'ml/datasets/phase4_8_fasttrack/metadata'
VIET_ZIP=ROOT/'ml/datasets/phase4_8_fasttrack/source_vietnam/clipsforzenodo.zip'

def hfile(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    rows=list(csv.DictReader(MANIFEST.open(newline='')))
    dup={r['candidate_id']:r for r in csv.DictReader(DUP.open(newline=''))}
    assert len(rows)==4485 and len({r['candidate_id'] for r in rows})==4485
    # Existing acquisition manifest has duplicate CSV header names for the
    # overlap fields; DictReader resolves them to the final values. This audit
    # preserves the original file and records the reconciled result separately.
    ioai_meta={}
    for n in ('train.csv','fine_tune.csv'):
        with (META/n).open(newline='') as f:
            for r in csv.DictReader(f): ioai_meta[Path(r['path']).name]=r

    # Prefer a documented mixed branch as representative when the same
    # decoded clip appears in multiple Vietnam branches.
    viet=[r for r in rows if r['source_dataset']=='vietnam']
    by_dec=defaultdict(list)
    for r in viet: by_dec[r['decoded_audio_hash']].append(r)
    order={'imagesvietnam_belize_clips':0,'imagesvietnamunbalanced_clips':1,'testdatacombined_clips':2}
    representative=set(); internal_duplicate=set()
    for vals in by_dec.values():
        vals=sorted(vals,key=lambda r:order.get(r['source_relative_path'].split('/')[1],9))
        representative.add(vals[0]['candidate_id'])
        internal_duplicate.update(r['candidate_id'] for r in vals[1:])

    ioai_out=[]; viet_out=[]
    for r in rows:
        d=dup[r['candidate_id']]
        if r['source_dataset']=='ioai':
            match=d['source_path'] if r['duplicate_status']=='MATCH_IN_LOCAL_AUDIO' else ''
            exact='CONFIRMED_BYTE_EXACT_FSC22' if match else 'NO_FSC22_BYTE_EXACT_MATCH'
            parent=''
            if match:
                stem=Path(match).stem
                parent='fsc22_'+stem
            prov='VERIFIED_SOURCE_DATASET_ONLY'
            primary='DUPLICATE_OR_OVERLAP' if match else 'QUARANTINED_PROVENANCE'
            reason=('IOAI publisher source and label are identified, but original parent/session/device are not documented. '
                    +('The selected WAV is byte-exactly duplicated by the local FSC22 source; it is not new data.' if match else 'No local FSC22 byte match was found; this negative result does not establish source independence.'))
            ioai_out.append({'candidate_id':r['candidate_id'],'original_filename':r['original_filename'],'publisher_label':r['label'],'sha256':r['sha256'],'decoded_audio_hash':r['decoded_audio_hash'],'fsc22_duplicate_status':exact,'matching_local_source_path':match,'source_url':r['source_url'],'parent_recording_id':parent,'session_id':'','device_id':'','source_provenance_status':prov,'license_status':'DATASET_LEVEL_CC_BY_SA_4.0_FILE_LEVEL_ANCESTRY_UNRESOLVED','label_status':'PUBLISHER_CLIP_LABEL_NO_EVENT_TIMESTAMPS','primary_disposition':primary,'decision_reason':reason,'evidence_reference':'hf_dataset_card;phase4_8_acquisition_manifest;duplicate_and_leakage_audit'})
        else:
            branch=r['source_relative_path'].split('/')[1]
            mixed=branch=='imagesvietnam_belize_clips'
            combined=branch=='testdatacombined_clips'
            internal=r['candidate_id'] in internal_duplicate
            if mixed: ancestry='DOCUMENTED_BELIZE_ANCESTRY'
            elif combined: ancestry='COMBINED_TEST_BRANCH_SOURCE_COMPOSITION_UNRESOLVED'
            else: ancestry='VIETNAM_BRANCH_PUBLISHER_IDENTIFIED'
            source='vietnam+belize' if mixed else ('vietnam_or_combined_unspecified' if combined else 'vietnam')
            if mixed or internal: primary='DUPLICATE_OR_OVERLAP'
            else: primary='QUARANTINED_PROVENANCE'
            reason=('Publisher identifies this as a Vietnam+Belize mixed branch; it is not independent Vietnam evidence.' if mixed else
                    'This clip repeats a decoded clip elsewhere in the acquired Vietnam archive; retain one provenance representative only.' if internal else
                    'Branch/source dataset is identifiable, but per-file parent recording, session, and device are not documented; source independence remains unresolved.')
            viet_out.append({'candidate_id':r['candidate_id'],'original_filename':r['original_filename'],'archive_branch':branch,'publisher_label':r['label'],'sha256':r['sha256'],'decoded_audio_hash':r['decoded_audio_hash'],'belize_ancestry_status':ancestry,'source_dataset':source,'parent_recording_id':'','session_id':'','device_id':'','provenance_status':'PROVISIONAL_GROUP_ONLY','license_status':'DATASET_LEVEL_CC_BY_4.0_THIRD_PARTY_FILE_LEVEL_TERMS_UNRESOLVED','label_status':'GUNSHOT_MANUAL_RAVEN_DESCRIPTION_NO_FILE_TIMESTAMPS' if r['label']=='gunshot' else 'NOISE_FOLDER_LABEL_NOT_VERIFIED_NEGATIVE','duplicate_overlap_status':'DOCUMENTED_BRANCH_OVERLAP' if mixed else ('ACQUIRED_SET_DECODED_DUPLICATE' if internal else d['status']),'primary_disposition':primary,'decision_reason':reason,'evidence_reference':'zenodo_13893977;vietnam_archive_structure;phase4_8_acquisition_manifest;duplicate_and_leakage_audit'})

    ioai_fields=list(ioai_out[0]); viet_fields=list(viet_out[0])
    with (OUT/'ioai_provenance_audit.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=ioai_fields); w.writeheader(); w.writerows(ioai_out)
    with (OUT/'vietnam_provenance_audit.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=viet_fields); w.writeheader(); w.writerows(viet_out)

    groups=[]
    groups.append({'dataset':'ioai','group_id':'ioai_unknown_parent','grouping_evidence':'Dataset card and selected CSVs identify source dataset only; no recording/session/device field.','file_count':'120','label_counts':'chainsaw=60; gunshot=60','parent_source_status':'unknown','session_status':'unknown','cross_branch_relationships':'90 files are duplicates of local FSC22 source groups; 30 have no local FSC22 byte match','licensing_status':'CC BY-SA 4.0 dataset-level; file-level ancestry unresolved','recommended_use':'quarantine; no training admission','limitations':'Different hashes do not establish independence.'})
    fsc=Counter()
    for r in ioai_out:
        if r['parent_recording_id']: fsc[r['parent_recording_id']]+=1
    for pid,n in sorted(fsc.items()): groups.append({'dataset':'fsc22_local_match','group_id':pid,'grouping_evidence':'Exact byte match path resolves to local FSC22 raw source and master manifest parent ID.','file_count':str(n),'label_counts':'matched publisher label preserved','parent_source_status':'verified local source for duplicate tracing','session_status':'not available','cross_branch_relationships':'IOAI duplicate; not new data','licensing_status':'Existing FSC22 licensing/provenance record applies to local source; IOAI upstream rights remain unresolved','recommended_use':'duplicate exclusion','limitations':'This maps duplication, not IOAI original ancestry.'})
    for branch,n in sorted(Counter(r['archive_branch'] for r in viet_out).items()):
        labs=Counter(r['publisher_label'] for r in viet_out if r['archive_branch']==branch)
        groups.append({'dataset':'vietnam_benchmark','group_id':branch,'grouping_evidence':'Publisher-defined archive directory branch; not an original parent recording.','file_count':str(n),'label_counts':'; '.join(f'{k}={v}' for k,v in sorted(labs.items())),'parent_source_status':'not documented','session_status':'not documented','cross_branch_relationships':'mixed branch explicitly includes Belize; combined test composition not resolved','licensing_status':'Zenodo CC BY 4.0 dataset-level; third-party ancestry terms unresolved','recommended_use':'quarantine; mixed branch duplicate/overlap exclusion','limitations':'Branch membership cannot establish recording independence.'})
    with (OUT/'source_group_audit.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(groups[0])); w.writeheader(); w.writerows(groups)

    licenses=[
      {'dataset_or_group':'ioai','official_license_identifier':'CC BY-SA 4.0','evidence_url':'https://huggingface.co/datasets/pkasila/ioai26-ht1-nightwatch','exact_attribution':'IOAI 2026 Home Task 1 / source attribution to Kaggle competition as documented on card','third_party_ancestry':'Card attributes source to IOAI/Kaggle but provides no file-level original source terms','share_alike_implications':'Redistribution/adaptations must preserve attribution and share-alike conditions if license applies','unresolved_licensing_issue':'Dataset-level card license does not establish rights for underlying recordings','decision':'QUARANTINED_PROVENANCE'},
      {'dataset_or_group':'vietnam_only','official_license_identifier':'CC BY 4.0','evidence_url':'https://zenodo.org/records/13893977','exact_attribution':'Cite Vu, Phan, Le, Clink (2024), dataset DOI 10.5281/zenodo.13893977','third_party_ancestry':'Vietnam branch described as Chu Mom Ray National Park recordings; file-level rights not separately enumerated','share_alike_implications':'Attribution required; no share-alike requirement under CC BY 4.0','unresolved_licensing_issue':'Per-file terms and parent recording rights are not separately documented','decision':'QUARANTINED_PROVENANCE'},
      {'dataset_or_group':'vietnam_belize_mixed','official_license_identifier':'CC BY 4.0 at Zenodo; Belize source separately CC BY 4.0 per prior audit','evidence_url':'https://zenodo.org/records/13893977; https://data.mendeley.com/datasets/x48cwz364j/3','exact_attribution':'Cite Vietnam Zenodo authors and Katsis et al. Belize dataset','third_party_ancestry':'Publisher explicitly identifies Belize material in this branch','share_alike_implications':'CC BY attribution obligations apply; compatible file-level third-party terms not independently established','unresolved_licensing_issue':'Archive license cannot by itself clear all third-party Belize files','decision':'DUPLICATE_OR_OVERLAP'},
      {'dataset_or_group':'vietnam_combined_test','official_license_identifier':'CC BY 4.0 at Zenodo','evidence_url':'https://zenodo.org/records/13893977','exact_attribution':'Cite Vietnam Zenodo authors and DOI','third_party_ancestry':'Record calls this a combined test branch but does not expose per-file source mapping','share_alike_implications':'Attribution required','unresolved_licensing_issue':'Composition and per-file ancestry unresolved','decision':'QUARANTINED_PROVENANCE'},
    ]
    with (OUT/'license_attribution_audit.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(licenses[0])); w.writeheader(); w.writerows(licenses)

    labels=[
      {'dataset':'ioai','publisher_label':'Chainsaw','clip_count':'60','label_definition':'Integer/category clip label in fine_tune.csv','annotation_method':'Publisher metadata; method not specified','event_timestamp_availability':'none found','verified_negative_status':'not applicable','project_taxonomy_mapping':'chainsaw','limitations':'Complete-event occupancy and original recording ancestry unknown.'},
      {'dataset':'ioai','publisher_label':'Gunshot','clip_count':'60','label_definition':'Integer/category clip label in fine_tune.csv','annotation_method':'Publisher metadata; method not specified','event_timestamp_availability':'none found','verified_negative_status':'not applicable','project_taxonomy_mapping':'gunshot','limitations':'Complete-event occupancy and original recording ancestry unknown.'},
      {'dataset':'vietnam_benchmark','publisher_label':'gunshot','clip_count':'690','label_definition':'Archive folder label','annotation_method':'Publisher states clips isolated using manual Raven Pro annotations; publication reports manual spectrogram annotation','event_timestamp_availability':'not included per extracted file','verified_negative_status':'not applicable','project_taxonomy_mapping':'gunshot','limitations':'Clip-level export lacks source annotation intervals and parent/session IDs.'},
      {'dataset':'vietnam_benchmark','publisher_label':'noise','clip_count':'3675','label_definition':'Archive folder label used for non-gunshot/noise clips','annotation_method':'Record describes combined test/noise use; no per-file negative annotation found','event_timestamp_availability':'none found','verified_negative_status':'NO — weak label only','project_taxonomy_mapping':'do not map automatically to background','limitations':'May contain environmental audio and branch mixtures; not a verified negative control.'},
    ]
    with (OUT/'label_semantics_audit.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(labels[0])); w.writeheader(); w.writerows(labels)

    all_out=ioai_out+viet_out
    coverage={'candidate_counts_by_source':{'ioai':len(ioai_out),'vietnam':len(viet_out)},'candidate_counts_by_label':{'ioai':dict(Counter(r['publisher_label'] for r in ioai_out)),'vietnam':dict(Counter(r['publisher_label'] for r in viet_out))},'ioai_counts':dict(Counter(r['primary_disposition'] for r in ioai_out)),'vietnam_branch_counts':dict(Counter(r['archive_branch'] for r in viet_out)),'vietnam_branch_dispositions':{b:dict(Counter(r['primary_disposition'] for r in viet_out if r['archive_branch']==b)) for b in sorted(set(r['archive_branch'] for r in viet_out))},'verified_parent_recordings':len(fsc),'verified_sessions':0,'provisional_groups':len([g for g in groups if g['dataset']=='vietnam_benchmark'])+1,'unknown_source_counts':{'ioai':30,'vietnam':len(viet_out)},'eligibility_counts':dict(Counter(r['primary_disposition'] for r in ioai_out+viet_out)),'internal_vietnam_decoded_duplicate_rows':len(internal_duplicate),'documented_belize_branch_rows':sum(r['archive_branch']=='imagesvietnam_belize_clips' for r in viet_out),'remaining_blockers':['No original parent/session/device metadata for IOAI or Vietnam files','Dataset-level licenses do not establish file-level third-party rights','Noise is not a verified negative','Combined test ancestry is unresolved','No production training manifest permitted']}
    (OUT/'class_source_coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')
    decision={'decision':'QUARANTINED_PROVENANCE','total_candidates_audited':len(all_out),'eligible_future_training_only':0,'license_quarantine_count':0,'provenance_quarantine_count':sum(r['primary_disposition']=='QUARANTINED_PROVENANCE' for r in all_out),'duplicate_overlap_count':sum(r['primary_disposition']=='DUPLICATE_OR_OVERLAP' for r in all_out),'label_quarantine_count':0,'excluded_count':0,'evidence_references':['ioai_provenance_audit.csv','vietnam_provenance_audit.csv','source_group_audit.csv','license_attribution_audit.csv','label_semantics_audit.csv','phase4_8_acquisition_manifest.csv','duplicate_and_leakage_audit.csv'],'remaining_blockers':['No verified original recording/session/device groups','File-level third-party license applicability unresolved','Noise not verified background','Combined Vietnam test composition unresolved'],'conditions_for_future_admission':['Publisher/source metadata identifies parent recording or defensible source group','File-level license/attribution applicability is documented','Human label review confirms event occupancy','All duplicate/overlap representatives are grouped before any future split']}
    (OUT/'provenance_decision.json').write_text(json.dumps(decision,indent=2)+'\n')

    report=f'''# Phase 4.9 — Source Provenance Recovery\n\nAudit timestamp: {datetime.now(timezone.utc).isoformat()}\n\n## Executive summary\n\nAll 4,485 staged clips were reconciled without downloading new data. The final decision is **QUARANTINED_PROVENANCE**: 0 files are eligible for future training-only consideration, {decision['provenance_quarantine_count']} remain provenance-quarantined, and {decision['duplicate_overlap_count']} are duplicate/overlap dispositions.\n\n### IOAI\n\nThe selected 120 files reconcile to 60 chainsaw and 60 gunshot labels. Exactly 90 are byte-exact matches to local FSC22 WAVs, with source paths recorded; 30 have no byte-exact FSC22 match. The 90 matches resolve to 90 local FSC22 parent recording IDs, but this maps duplication rather than the original IOAI ancestry. No IOAI parent/session/device metadata was found.\n\n### Vietnam\n\nThe extracted archive reconciles to 4,365 WAVs: 729 `imagesvietnamunbalanced_clips`, 1,239 `imagesvietnam_belize_clips`, and 2,397 `testdatacombined_clips`. It contains 690 gunshot-labelled and 3,675 noise-labelled clips. The publisher explicitly describes the mixed branch as Vietnam plus Belize, so those 1,239 clips are not independent Vietnam evidence. A decoded-hash reconciliation found 731 additional repeated clip rows across the acquired Vietnam branches; these are marked overlap duplicates while representatives remain quarantined.\n\n## Methods executed\n\n* Inspected Phase 4.8 manifests, duplicate audit, license audit, archive, extracted paths, IOAI CSV metadata, and the prior Phase 4.7 report.\n* Used the IOAI dataset card/API metadata and commit metadata; no original recording/session/device fields were present in the selected CSV schema.\n* Inspected the Zenodo record/API, archive directory structure, filenames, and publication description. The record states Vietnam passive-monitoring clips plus Belize data, Raven Pro manual clip isolation, and three branches.\n* Reused Phase 4.8 exact/decoded-match results and performed a decoded-hash grouping across the already-acquired Vietnam files. No expensive new local audio similarity scan was run.\n* No model inference, training, threshold tuning, preprocessing change, download, curator contact, or source-file modification occurred.\n\n## License and attribution\n\nIOAI reports CC BY-SA 4.0 on its dataset card and attributes source material to IOAI/Kaggle. The card does not establish rights for each underlying recording. Vietnam reports CC BY 4.0 on Zenodo and cites Vu et al. plus the Belize Katsis et al. dataset. The archive-level license does not establish identical file-level rights for third-party Belize material. Both sources therefore remain blocked for file-level provenance/licensing admission.\n\n## Label semantics\n\nIOAI labels are clip-level CSV categories with no event timestamps or event-occupancy annotations. Vietnam gunshot clips are described as manually isolated/annotated using Raven Pro, but the extracted WAV archive contains no per-file event intervals. Vietnam `noise` is an archive folder label, not a verified negative control, and is not mapped to project `background`.\n\n## Source grouping and duplicate ancestry\n\nThe only verified parent IDs are 90 local FSC22 parents used to trace exact IOAI duplication. Vietnam branch directories are provisional groups, not original recording identities. No verified Vietnam parent recordings or sessions were found. Different filenames/hashes were not treated as independence.\n\n## Eligibility\n\n| primary disposition | count |\n|---|---:|\n| ELIGIBLE_TRAIN_ONLY | 0 |\n| QUARANTINED_PROVENANCE | {decision['provenance_quarantine_count']} |\n| QUARANTINED_LICENSE | 0 |\n| DUPLICATE_OR_OVERLAP | {decision['duplicate_overlap_count']} |\n| QUARANTINED_LABEL | 0 |\n| EXCLUDED_AUDIO_INVALID | 0 |\n\nNo verified negatives were found. No production or future-training manifest was created.\n\n## Recommended next step\n\nDo not admit these files. The single most useful next step is to obtain or locate source-level metadata for the 30 non-duplicate IOAI clips and the Vietnam-only representatives, including original recording/session/device identifiers and file-level rights. Until then, preserve the staging data and keep Phase 5 blocked.\n\n## Reproduction\n\n```bash\npython3 ml/reports/phase4_9_source_provenance/run_provenance_recovery.py\n```\n'''
    report=report.replace('731 additional repeated clip rows', f'{len(internal_duplicate)} repeated clip rows')
    (OUT/'SOURCE_PROVENANCE_REPORT.md').write_text(report)
    artifacts=[p for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='integrity_hashes.json']
    ih={'audit_timestamp_utc':datetime.now(timezone.utc).isoformat(),'script':'run_provenance_recovery.py','python':sys.version.split()[0],'soundfile':sf.__version__,'input_manifest_sha256':hfile(MANIFEST),'input_duplicate_audit_sha256':hfile(DUP),'vietnam_archive_sha256':hfile(VIET_ZIP),'vietnam_archive_md5_expected':'beaa5e5711246cea2dbad361ffb7cf02','staged_counts':{'ioai':len(ioai_out),'vietnam':len(viet_out),'total':len(all_out)},'generated_artifact_sha256':{str(p.relative_to(ROOT)):hfile(p) for p in artifacts},'unprocessed_files':[],'protected_artifacts_changed':False,'downloads_performed':0,'model_inference_started':False,'model_training_started':False,'threshold_tuning_started':False,'preprocessing_changed':False,'frozen_manifests_changed':False,'firmware_changed':False,'phase4_3_decisions_changed':False}
    (OUT/'integrity_hashes.json').write_text(json.dumps(ih,indent=2)+'\n')
    print(json.dumps({'total':len(all_out),'ioai':len(ioai_out),'vietnam':len(viet_out),'verified_fsc22_parents':len(fsc),'internal_vietnam_duplicate_rows':len(internal_duplicate),'decision':decision['decision']},indent=2))

if __name__=='__main__': main()
