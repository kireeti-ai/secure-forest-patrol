#!/usr/bin/env python3
"""Phase 4.8 staging audit for the selectively acquired IOAI and Vietnam data.

Writes only under ml/reports/phase4_8_fasttrack_acquisition. Source audio and
all frozen project artifacts are read-only inputs. No model code is imported.
"""
from __future__ import annotations
import csv, hashlib, json, platform, sys, time, zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import soundfile as sf

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
IOAI_AUDIO=ROOT/'ml/datasets/phase4_8_fasttrack/source_ioai'
IOAI_META=ROOT/'ml/datasets/phase4_8_fasttrack/metadata'
VIET=ROOT/'ml/datasets/phase4_8_fasttrack/extracted_vietnam'
VIET_ZIP=ROOT/'ml/datasets/phase4_8_fasttrack/source_vietnam/clipsforzenodo.zip'
RAW=ROOT/'ml/datasets/raw'
KENYA=ROOT/'ml/datasets/phase4_5_acquisition/kenya_extracted/audio'

def hfile(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()
def hbytes(b): return hashlib.sha256(b).hexdigest()
def decoded_hash(x):
    a=np.asarray(x)
    if a.ndim==1: a=a[:,None]
    y=np.asarray(np.clip(np.rint(a*32768),-32768,32767),dtype='<i2')
    return hbytes(y.tobytes())

# Reuse the Phase 4.7 deterministic crop-screen implementation.
import importlib.util
spec=importlib.util.spec_from_file_location('p47',ROOT/'ml/reports/phase4_7_provenance_resolution/run_provenance_audit.py')
p47=importlib.util.module_from_spec(spec); spec.loader.exec_module(p47)

def metadata():
    m={}
    for n in ('train.csv','fine_tune.csv'):
        with (IOAI_META/n).open(newline='') as f:
            for r in csv.DictReader(f): m[Path(r['path']).name]=r
    return m

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    ioai=metadata()
    files=[]
    for p in sorted(IOAI_AUDIO.glob('*.wav')):
        r=ioai[p.name]; files.append((p,'ioai',r['category'],r['path'],r['split']))
    for p in sorted(VIET.rglob('*.wav')):
        if '__MACOSX' in str(p): continue
        rel=p.relative_to(VIET).as_posix(); category=p.parent.name
        files.append((p,'vietnam',category,rel,''))
    assert len(files)==4485,(len(files))
    manifest=[]; specs=[]; duplicate_rows=[]
    seen_sha=defaultdict(list); seen_dec=defaultdict(list)
    for p,ds,cat,source_rel,split in files:
        x,sr=sf.read(str(p),dtype='float32',always_2d=False)
        info=sf.info(str(p)); channels=info.channels
        if x.ndim==1: mono=x
        else: mono=x.mean(axis=1)
        source_group=''
        ancestry=''
        if ds=='ioai':
            label='chainsaw' if cat=='Chainsaw' else 'gunshot'
            label_gran='publisher clip-level class label'
            license_name='CC BY-SA 4.0'
            attribution='IOAI 2026 Home Task 1 / source attribution to Kaggle competition as documented on dataset card'
            disposition='QUARANTINED_PROVENANCE'
            reason='Dataset-level license is documented, but original recording/session/device ancestry and source-group independence are not provided.'
            cid='phase4_8_ioai_'+p.stem
            source_url='https://huggingface.co/datasets/pkasila/ioai26-ht1-nightwatch'
        else:
            label='gunshot' if cat=='gunshot' else 'noise_unverified'
            label_gran='publisher folder label; noise is not a verified negative'
            license_name='CC BY 4.0'
            attribution='Vu, Phan, Le, and Clink; cite Zenodo record 13893977'
            if 'imagesvietnam_belize_clips' in source_rel:
                disposition='DUPLICATE_OR_OVERLAP'
                reason='Publisher explicitly states this branch combines Vietnam and Belize audio; ancestry overlap prevents independent-source admission.'
                ancestry='Vietnam plus Belize-derived branch (publisher-stated)'
            else:
                disposition='QUARANTINED_PROVENANCE'
                reason='Publisher labels are present, but per-file parent/session/device identity is not supplied; noise is not a verified background negative.'
                ancestry='Vietnam-labelled branch; independent parent identity unverified'
            label_gran='publisher folder/clip label; Raven Pro extraction described at dataset level'
            cid='phase4_8_vietnam_'+hbytes(source_rel.encode())[:16]
            source_url='https://zenodo.org/records/13893977'
        sha=hfile(p); dh=decoded_hash(x)
        rec={'candidate_id':cid,'source_dataset':ds,'source_url':source_url,'original_filename':p.name,'relative_path':str(p.relative_to(ROOT)),'source_relative_path':source_rel,'sha256':sha,'decoded_audio_hash':dh,'label':label,'label_granularity':label_gran,'duration_seconds':f'{info.frames/info.samplerate:.9f}','sample_rate':str(info.samplerate),'channels':str(channels),'sample_count':str(info.frames),'subtype':info.subtype,'peak':f'{float(np.max(np.abs(mono))):.9f}','rms':f'{float(np.sqrt(np.mean(mono*mono))):.9f}','parent_recording_id':'','session_id':'','device_id':'','license':license_name,'attribution':attribution,'provenance_group':source_group,'ancestry':ancestry,'duplicate_status':'NOT_YET_SCREENED','overlap_status':'NOT_YET_SCREENED','intended_use':'future training-only research candidate','eligibility_status':disposition,'decision_reason':reason}
        manifest.append(rec); specs.append((p,x,sr,rec)); seen_sha[sha].append(rec); seen_dec[dh].append(rec)

    # Exact/decoded duplicate matches within the acquired set.
    for recs in list(seen_sha.values())+list(seen_dec.values()):
        if len(recs)>1:
            for r in recs: r['duplicate_status']='ACQUIRED_SET_EXACT_OR_DECODED_DUPLICATE'
    # Build the directly available local comparison inventory. Byte hashes are
    # sufficient to catch container-identical overlap; decoded hashes catch
    # metadata/container variation at the same sample representation.
    raw_paths=sorted(RAW.rglob('*.wav'))
    local_paths=sorted(set(raw_paths)|set((ROOT/'ml/datasets/processed').rglob('*.wav'))|set((ROOT/'ml/datasets/processed_filtered').rglob('*.wav'))|set(KENYA.glob('*.wav')))
    local_sha=defaultdict(list); local_dec=defaultdict(list); local_fail=0
    t0=time.time()
    for i,p in enumerate(local_paths,1):
        try:
            local_sha[hfile(p)].append(str(p.relative_to(ROOT)))
            x,_=sf.read(str(p),dtype='float32',always_2d=False)
            local_dec[decoded_hash(x)].append(str(p.relative_to(ROOT)))
        except Exception: local_fail+=1
        if i%10000==0: print('local inventory',i,'/',len(local_paths),file=sys.stderr)
    for r in manifest:
        hits=local_sha.get(r['sha256'],[])+local_dec.get(r['decoded_audio_hash'],[])
        if hits:
            r['duplicate_status']='MATCH_IN_LOCAL_AUDIO'; r['overlap_status']='EXACT_OR_DECODED_MATCH'; r['eligibility_status']='DUPLICATE_OR_OVERLAP'; r['decision_reason']=r['decision_reason']+' Exact or decoded-audio match found in the local inventory.'
        else:
            r['duplicate_status']='NO_EXACT_OR_DECODED_MATCH_IN_LOCAL_INVENTORY'
            r['overlap_status']='CROP_SCREEN_PENDING'

    # Coarse crop screen against local raw WAVs only. Match uses the Phase 4.7
    # 64-bit spectral frame sequence; >=.98 is a review-required hit.
    candidate_sig=[]; first=defaultdict(list)
    for i,(p,x,sr,r) in enumerate(specs):
        a=x.mean(axis=1) if getattr(x,'ndim',1)==2 else x
        sig,hop=p47.frame_signature(a,int(sr)); candidate_sig.append((sig,hop))
        if len(sig)>=3: first[int(sig[0])].append(i)
    best=[(-1.0,'','') for _ in manifest]; raw_frames=0
    for j,src in enumerate(raw_paths,1):
        try:
            x,sr=sf.read(str(src),dtype='float32',always_2d=False); x=x.mean(axis=1) if x.ndim==2 else x
            sig,hop=p47.frame_signature(x,int(sr)); raw_frames+=len(sig)
        except Exception: continue
        if len(sig)<3: continue
        for i in set(first.get(int(sig[0]),[])):
            cs,_=candidate_sig[i]; k=len(cs)
            if k>len(sig): continue
            for pos in np.flatnonzero(sig==cs[0]):
                if pos+k>len(sig): continue
                score=1.0-np.mean([p47.hamming(a,b)/64 for a,b in zip(cs,sig[pos:pos+k])])
                if score>best[i][0]: best[i]=(float(score),str(src.relative_to(ROOT)),f'{pos*hop:.6f}')
        if j%3000==0: print('crop screen',j,'/',len(raw_paths),file=sys.stderr)
    dup_rows=[]
    for i,r in enumerate(manifest):
        score,path,offset=best[i]
        if score>=.98:
            r['overlap_status']='PLAUSIBLE_CROP_MATCH_REQUIRES_MANUAL_VERIFICATION'; r['overlap_source']=path
            r['overlap_score']=f'{score:.6f}'; r['overlap_offset_seconds']=offset
        elif r['overlap_status']=='CROP_SCREEN_PENDING':
            r['overlap_status']='NO_PLAUSIBLE_MATCH_IN_COARSE_SCREEN'; r['overlap_source']=path; r['overlap_score']=f'{max(0,score):.6f}'; r['overlap_offset_seconds']=offset
        dup_rows.append({'candidate_id':r['candidate_id'],'source_dataset':r['source_dataset'],'source_path':path,'offset_seconds':offset,'score':f'{max(0,score):.6f}','status':r['overlap_status'],'method':'exact_sha256+decoded_hash+64bit_spectral_crop_screen','local_raw_files_searched':str(len(raw_paths)),'notes':'Negative crop result does not prove source independence; threshold 0.98 pre-registered.'})

    mf=[k for k in manifest[0]]+['overlap_source','overlap_offset_seconds','overlap_score']
    with (OUT/'acquisition_manifest.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=mf); w.writeheader()
        for r in manifest:
            for k in ('overlap_source','overlap_offset_seconds','overlap_score'): r.setdefault(k,'')
            w.writerow(r)
    with (OUT/'duplicate_and_leakage_audit.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dup_rows[0])); w.writeheader(); w.writerows(dup_rows)

    license_rows=[
      {'source_dataset':'ioai','source_url':'https://huggingface.co/datasets/pkasila/ioai26-ht1-nightwatch','license_evidence':'Official dataset card reports CC-BY-SA 4.0; labels and 1,283-file count documented there.','attribution_requirements':'Preserve attribution and share-alike obligations; card attributes IOAI/Kaggle competition.','provenance_evidence':'Dataset card supplies class/file metadata but no original recording/session/device/source-group mapping.','license_status':'DATASET_LEVEL_VERIFIED_FILE_LEVEL_ANCESTRY_UNRESOLVED','disposition':'QUARANTINED_PROVENANCE','unresolved_issue':'Underlying source recordings and independent source groups are not documented.'},
      {'source_dataset':'vietnam_benchmark','source_url':'https://zenodo.org/records/13893977','license_evidence':'Zenodo API record reports CC BY 4.0; archive MD5 verified against record.','attribution_requirements':'Cite Vu, Phan, Le, Clink (2024) and Zenodo DOI 10.5281/zenodo.13893977.','provenance_evidence':'Record states Vietnam passive-monitoring data plus open Belize dataset; clips isolated using Raven Pro.','license_status':'DATASET_LEVEL_VERIFIED_FILE_LEVEL_ANCESTRY_PARTLY_EXPLICIT','disposition':'QUARANTINED_PROVENANCE','unresolved_issue':'Belize-derived branch is not independent; per-file parent/session/device mapping is absent.'},
      {'source_dataset':'kenya_quarantined','source_url':'https://zenodo.org/records/21443074','license_evidence':'Phase 4.7 verified dataset-level CC BY 4.0.','attribution_requirements':'See Phase 4.7 license audit.','provenance_evidence':'Phase 4.7 found 175 staged clips with unresolved file-level lineage.','license_status':'NOT_REACQUIRED','disposition':'NOT_INVESTIGATED_PHASE4_8','unresolved_issue':'Explicitly excluded from Phase 4.8 acquisition.'},
      {'source_dataset':'belize','source_url':'https://data.mendeley.com/datasets/x48cwz364j/3','license_evidence':'Official page reports CC BY 4.0.','attribution_requirements':'See prior Mendeley audit.','provenance_evidence':'File-level access unavailable without authorized credentials; no audio acquired.','license_status':'LICENSE_DOCUMENTED_AUDIO_NOT_ACQUIRED','disposition':'NOT_ACQUIRED','unresolved_issue':'No public file manifest or selective endpoint demonstrated.'},
      {'source_dataset':'illinois','source_url':'https://databank.illinois.edu/datasets/IDB-5664241','license_evidence':'Not verified; official landing page returned HTTP 403.','attribution_requirements':'Unknown.','provenance_evidence':'Not assessed due access block.','license_status':'UNVERIFIED','disposition':'NOT_ACQUIRED','unresolved_issue':'403 access block; no bypass attempted.'},
      {'source_dataset':'sensing_forest','source_url':'https://zenodo.org/records/18909809','license_evidence':'Zenodo API reports CC0 1.0.','attribution_requirements':'No CC attribution requirement, citation still appropriate.','provenance_evidence':'Natural soundscape record has device/period context but no verified event-negative intervals.','license_status':'DOCUMENTED_NOT_REACQUIRED','disposition':'NOT_ACQUIRED','unresolved_issue':'23.5 GB archive and no verified negative intervals; already locally present.'},
      {'source_dataset':'rodopi','source_url':'https://zenodo.org/records/5824433','license_evidence':'Phase 4 prior audit reports CC BY 4.0.','attribution_requirements':'See existing Rodopi audit.','provenance_evidence':'Already present locally and overlaps frozen Rodopi sources.','license_status':'EXISTING_LOCAL_SOURCE','disposition':'NOT_REACQUIRED','unresolved_issue':'Known source overlap; no new acquisition.'},
      {'source_dataset':'outdoor_gunfire','source_url':'https://zenodo.org/records/7004819','license_evidence':'Zenodo API reports CC BY 4.0.','attribution_requirements':'Cite Florida Institute of Technology authors/record.','provenance_evidence':'Outdoor firearm range, multiple devices; source is not forest-domain and archive is 1.6 GB.','license_status':'DOCUMENTED_NOT_ACQUIRED','disposition':'NOT_ACQUIRED','unresolved_issue':'Large archive and range-domain mismatch; not needed after targeted acquisition.'},
    ]
    with (OUT/'license_provenance_audit.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(license_rows[0])); w.writeheader(); w.writerows(license_rows)
    comparisons=[
      {'source_dataset':'ioai','source_url':'https://huggingface.co/datasets/pkasila/ioai26-ht1-nightwatch','class_coverage':'chainsaw 60; gunshot 60 in selected subset; environmental classes in full card','license':'CC BY-SA 4.0','access_status':'SELECTIVE ACCESS DEMONSTRATED','size':'2.03 GB full dataset; 82,591,530 bytes selected audio','recordings':'1,283 files documented; original recording groups not documented','provenance_quality':'LOW / source ancestry unresolved','environmental_relevance':'General environmental audio, not specifically forest','blockers':'90/120 selected files exact or decoded matches to local FSC22; remaining 30 lack source groups/device/session metadata','final_decision':'ACQUIRED_STAGING_ONLY_QUARANTINED'},
      {'source_dataset':'vietnam_benchmark','source_url':'https://zenodo.org/records/13893977','class_coverage':'690 gunshot; 3,675 noise-labelled clips','license':'CC BY 4.0 via Zenodo API','access_status':'ARCHIVE DOWNLOADED AND VERIFIED','size':'396,067,990 bytes compressed; 4,365 WAVs extracted','recordings':'Clip files; original source-group count not established','provenance_quality':'PARTIAL; Vietnam and Belize ancestry explicitly separated/mixed in branches','environmental_relevance':'Strong passive-acoustic protected-area relevance for Vietnam; Belize derivative branch','blockers':'1,239 Vietnam+Belize branch files overlap/ancestry-duplicate; no per-file parent/session/device mapping; noise not verified negative','final_decision':'ACQUIRED_STAGING_ONLY_QUARANTINED'},
      {'source_dataset':'belize','source_url':'https://data.mendeley.com/datasets/x48cwz364j/3','class_coverage':'749 gunshot; >35,000 background','license':'CC BY 4.0','access_status':'NOT ACQUIRED; no authorized file manifest/selective endpoint demonstrated','size':'Unknown from public file response','recordings':'20 AudioMoth sites; file-level groups unavailable','provenance_quality':'Promising metadata, inaccessible file-level selection','environmental_relevance':'Very strong tropical forest relevance','blockers':'Public file tree unavailable; unauthenticated API returned 401 in prior audit','final_decision':'NOT_ACQUIRED'},
      {'source_dataset':'kenya','source_url':'https://zenodo.org/records/21443074','class_coverage':'129 chainsaw; natural/mechanical controls','license':'CC BY 4.0 dataset-level','access_status':'NOT_REACQUIRED; remains Phase 4.7 quarantine','size':'716,622,014 bytes already staged','recordings':'175 staged clips; parent/session mapping unresolved','provenance_quality':'PARTIAL / quarantined','environmental_relevance':'Strong Kenyan forest relevance','blockers':'File-level license/provenance and source independence unresolved','final_decision':'NOT_REACQUIRED'},
      {'source_dataset':'sensing_forest','source_url':'https://zenodo.org/records/18909809','class_coverage':'Natural soundscape; no verified target labels','license':'CC0 1.0','access_status':'NOT ACQUIRED; already local / archive 23.5 GB','size':'23.5 GB Part 1','recordings':'Long soundscape recordings; source context documented','provenance_quality':'Good collection context; no verified negative intervals','environmental_relevance':'Strong woodland background relevance','blockers':'No event-negative proof; large archive; already present locally','final_decision':'NOT_ACQUIRED'},
      {'source_dataset':'rodopi','source_url':'https://zenodo.org/records/5824433','class_coverage':'Chainsaw TextGrid events','license':'CC BY 4.0 reported in existing audit','access_status':'NOT REACQUIRED; already local','size':'Existing local source','recordings':'Known local Rodopi sources','provenance_quality':'Documented but overlaps frozen source groups','environmental_relevance':'Strong forest chainsaw relevance','blockers':'Known source overlap and duplicate RP3/RP6','final_decision':'NOT_REACQUIRED'},
      {'source_dataset':'outdoor_gunfire','source_url':'https://zenodo.org/records/7004819','class_coverage':'Outdoor gunshot/gunfire','license':'CC BY 4.0 via Zenodo API','access_status':'NOT ACQUIRED','size':'1.6 GB archive','recordings':'Multi-firearm/multi-device range recordings; exact count unverified','provenance_quality':'Moderate collection context','environmental_relevance':'Outdoor range, not forest','blockers':'Large archive and domain mismatch; no need to acquire in this pass','final_decision':'NOT_ACQUIRED'},
      {'source_dataset':'illinois','source_url':'https://databank.illinois.edu/datasets/IDB-5664241','class_coverage':'Unverified gunshot','license':'Unverified','access_status':'HTTP 403','size':'Unknown','recordings':'Unknown','provenance_quality':'Unknown','environmental_relevance':'Unknown','blockers':'Official landing page inaccessible; no bypass attempted','final_decision':'NOT_ACQUIRED'},
    ]
    with (OUT/'dataset_candidate_comparison.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(comparisons[0])); w.writeheader(); w.writerows(comparisons)
    cov={'acquired_files':len(manifest),'acquired_archives':1,'datasets_acquired':2,'class_counts':dict(Counter(r['label'] for r in manifest)),'publisher_labelled_target_counts':{'chainsaw':60,'gunshot':750,'background_verified':0},'training_eligible_counts':{'chainsaw':0,'gunshot':0,'background':0},'weakly_labelled_noise':sum(r['label']=='noise_unverified' for r in manifest),'files_by_dataset':dict(Counter(r['source_dataset'] for r in manifest)),'files_by_disposition':dict(Counter(r['eligibility_status'] for r in manifest)),'verified_original_recordings':0,'verified_parent_groups':0,'verified_sessions':0,'derived_clips':len(manifest),'total_duration_seconds':sum(float(r['duration_seconds']) for r in manifest),'crop_plausible_matches':sum(r['overlap_status'].startswith('PLAUSIBLE') for r in manifest),'local_raw_files_searched':len(raw_paths),'ancestry_note':'Vietnam archive explicitly contains a Vietnam+Belize branch; IOAI and Vietnam parent/session/device identities are not supplied at file level.'}
    (OUT/'class_source_coverage.json').write_text(json.dumps(cov,indent=2)+'\n')
    decision={'decision':'ACQUIRED_STAGING_ONLY_NO_ELIGIBLE_FILES','acquired_source_count':2,'acquired_file_count':len(manifest),'eligible_file_count':0,'quarantined_file_count':sum(r['eligibility_status'].startswith('QUARANTINED') for r in manifest),'duplicate_or_overlap_count':sum(r['eligibility_status']=='DUPLICATE_OR_OVERLAP' for r in manifest),'excluded_file_count':0,'blockers':['No verified original recording/session/device groups for IOAI or Vietnam files','Vietnam imagesvietnam_belize branch is explicitly derivative/ancestry-overlapping','Noise labels are not verified background negatives','No file was admitted to frozen or future training manifests'],'proposed_training_manifest_generated':False}
    (OUT/'acquisition_decision.json').write_text(json.dumps(decision,indent=2)+'\n')
    # Integrity after report generation is completed below; this list excludes itself.
    artifacts=[]
    report=f'''# Phase 4.8 — Fast-Track Alternative Dataset Acquisition\n\nAudit timestamp: {datetime.now(timezone.utc).isoformat()}\n\n## Executive summary\n\nTwo sources were acquired into isolated staging: 120 selectively downloaded IOAI WAVs and the 396,067,990-byte Vietnam benchmark clips archive, extracted to 4,365 WAV clips. No file is eligible for training yet. The final decision is **ACQUIRED_STAGING_ONLY_NO_ELIGIBLE_FILES**.\n\nThe IOAI subset contains 60 chainsaw and 60 gunshot clips. The Vietnam archive contains 690 gunshot-labelled clips and 3,675 `noise` clips; noise is retained as weakly labelled/non-verified background, not converted to the `background` class. The Vietnam `imagesvietnam_belize` branch is explicitly derived from/mixed with Belize data and is not independent.\n\n## Investigated sources\n\nThe comparison table records Rodopi, Belize, Kenya, Sensing the Forest, Illinois, Vietnam, Outdoor Gunfire, and IOAI. Rodopi, Sensing the Forest, and Kenya were not reacquired because they are already local or quarantined. Illinois remained HTTP 403. Belize remained without authorized file-level access. Outdoor Gunfire has a documented CC BY 4.0 record but is a 1.6 GB firearm-range archive with weaker forest relevance.\n\n## Acquisitions and validation\n\n* IOAI: metadata CSVs downloaded from the official Hugging Face dataset; 120 class-targeted WAVs downloaded individually through public `resolve/main` URLs. Total audio bytes: 82,591,530. Files are five seconds each, PCM16, with 11.025–48 kHz and mono/stereo layouts.\n* Vietnam: `clipsforzenodo.zip` downloaded from the official Zenodo API endpoint. Publisher MD5 `beaa5e5711246cea2dbad361ffb7cf02` matched. ZIP integrity passed. It contains 4,365 non-macOS WAV clips across Vietnam, Vietnam+Belize, and combined test branches.\n* All acquired WAVs were decoded and measured for duration, sample rate, channels, sample count, subtype, peak, RMS, byte SHA-256, and decoded-audio hash. No resampling, normalization, segmentation, or model inference was performed.\n\n## Provenance and eligibility\n\nNo verified original parent recordings, sessions, or devices were available for the IOAI files or the Vietnam extracted files. Therefore none is admitted as `ELIGIBLE_TRAIN_ONLY`. The 1,239 Vietnam+Belize branch clips are primary `DUPLICATE_OR_OVERLAP` dispositions because the publisher explicitly identifies mixed Belize ancestry. The remaining files are `QUARANTINED_PROVENANCE`; their labels remain publisher labels, and Vietnam `noise` remains weakly labelled rather than verified background.\n\n## Duplicate and leakage audit\n\nExact byte hashes and canonical decoded-audio hashes were compared against the local raw, processed, filtered, Kenya staging, and acquired inventories. A deterministic 64-bit spectral-frame crop screen searched all {len(raw_paths):,} local raw WAVs with a 0.98 review threshold. Results, best paths, offsets, and limitations are in `duplicate_and_leakage_audit.csv`. Negative results do not prove source independence or absence of crop overlap.\n\n## Eligibility summary\n\n| disposition | count |\n|---|---:|\n| ELIGIBLE_TRAIN_ONLY | 0 |\n| ELIGIBLE_VALIDATION_CANDIDATE | 0 |\n| ELIGIBLE_INDEPENDENT_TEST_CANDIDATE | 0 |\n| QUARANTINED_PROVENANCE | {sum(r['eligibility_status']=='QUARANTINED_PROVENANCE' for r in manifest)} |\n| DUPLICATE_OR_OVERLAP | {sum(r['eligibility_status']=='DUPLICATE_OR_OVERLAP' for r in manifest)} |\n| EXCLUDED | 0 |\n\nVerified independent recordings: 0. Acquired files are clips, not verified independent recordings.\n\n## Recommendation\n\nKeep both sources isolated for research and human/provenance review. The most useful next step is to resolve file-level source grouping and licensing/attribution ancestry for the IOAI subset and the Vietnam-only branch, then review a small source-balanced sample. Do not create a training manifest or alter frozen partitions until those gates pass.\n\n## Reproduction\n\n```bash\npython3 ml/reports/phase4_8_fasttrack_acquisition/run_fasttrack_audit.py\n```\n'''
    (OUT/'ACQUISITION_REPORT.md').write_text(report)
    artifacts=[p for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='integrity_hashes.json']
    ih={'audit_timestamp_utc':datetime.now(timezone.utc).isoformat(),'tool':'run_fasttrack_audit.py','python':sys.version.split()[0],'numpy':np.__version__,'soundfile':getattr(sf,'__version__','unknown'),'archives':{'vietnam_zip':{'path':str(VIET_ZIP.relative_to(ROOT)),'size_bytes':VIET_ZIP.stat().st_size,'sha256':hfile(VIET_ZIP),'publisher_md5':'beaa5e5711246cea2dbad361ffb7cf02'},'ioai_selective_audio_bytes':sum(p.stat().st_size for p in IOAI_AUDIO.glob('*.wav'))},'acquired_file_count':len(manifest),'acquired_file_sha256_count':len({r['sha256'] for r in manifest}),'audit_artifacts_sha256':{str(p.relative_to(ROOT)):hfile(p) for p in artifacts},'local_inventory':{'files_searched':len(local_paths),'decode_failures':local_fail,'raw_crop_files_searched':len(list(RAW.rglob('*.wav'))),'raw_crop_frame_count':raw_frames},'protected_artifacts_changed':False,'model_training_started':False,'model_inference_started':False,'threshold_tuning_started':False,'frozen_manifests_changed':False,'phase4_3_decisions_changed':False,'preprocessing_changed':False,'firmware_changed':False}
    (OUT/'integrity_hashes.json').write_text(json.dumps(ih,indent=2)+'\n')
    print(json.dumps({'acquired_files':len(manifest),'ioai_files':sum(r['source_dataset']=='ioai' for r in manifest),'vietnam_files':sum(r['source_dataset']=='vietnam' for r in manifest),'local_files':len(local_paths),'crop_plausible':sum(r['overlap_status'].startswith('PLAUSIBLE') for r in manifest),'decision':decision['decision']},indent=2))

if __name__=='__main__': main()
