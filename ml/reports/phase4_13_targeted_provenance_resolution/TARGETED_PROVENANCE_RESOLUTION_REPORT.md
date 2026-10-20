# Phase 4.13 — Targeted Provenance and License Resolution

Audit date: 2026-10-19 UTC

## Final decision

**BLOCKED_ON_UNRESOLVED_PROVENANCE_OR_LICENSE**

No candidate is ready for automatic admission. C3GD is suitable for a narrowly scoped **gunshot-only** admission review in principle, but its proposed unadmitted raw subset still requires exact/decoded/near-duplicate comparison against the frozen/local audio. It cannot satisfy the complete three-class requirement.

## Resolved findings

- **C3GD:** local metadata directly documents 12,112 raw rows, 579 `file_id` values, 4 `event_id` values, 48 platforms, 15 microphones, clip IDs, and collection metadata. The local README and license register document CC BY 4.0. These dimensions support source grouping, but they are not independent-sample counts.
- **Rodopi:** 9 raw WAVs and 9 TextGrids are present; 9 frozen source IDs are traceable. The exact RP3/RP6 duplicate relationship is preserved by the existing hash audit: 2504 exact-content hash groups contain both source IDs. Local download metadata records CC BY 4.0.
- **Sensing the Forest:** public documentation supports CC0 and collection-device context (Raspberry Pi, MEMS/RØDE microphones, Alice Holt Forest), but not per-file session identity or verified target-event absence.

## Remaining FSC22 blockers

FSC22’s local `Source File Name` field is preserved for 2,025 clips with 2,024 unique values, but it is not a Freesound URL, uploader ID, license record, session ID, device ID, or site ID. The public paper explains that FSC22 was assembled from Freesound searches and renamed source files, but the local inventory does not contain the per-recording mapping needed to establish exact license/attribution or independent parent sessions.

The dataset has 75 clips per each of 27 classes, including Chainsaw and Gunshot. Environmental labels such as Silence, Insect, and BirdChirping were not treated as verified background negatives.

## Candidate decisions

| Candidate | Scope | Decision |
|---|---|---|
| FSC22 | chainsaw/gunshot/background | BLOCKED — rights, source groups, and negative semantics unresolved |
| C3GD | gunshot-only | BLOCKED_PENDING_DUPLICATE_AUDIT — provenance/license resolved, raw-subset leakage unresolved |
| Rodopi | existing chainsaw/background | NOT_A_NEW_ADMISSION_CANDIDATE — already frozen; no new independent data |
| Sensing the Forest | background-only | BLOCKED — verified-negative and per-file grouping evidence absent |

## Independence and split findings

C3GD’s 579 raw `file_id` values are the relevant parent-like identifiers; its 4 events, 48 platforms, and 15 microphones are metadata dimensions, not 579 independent field sessions. The frozen manifest contains 100 C3GD source IDs. FSC22’s 2,024 source-file tokens are not claimed as independent recordings. Rodopi has 9 source IDs and 2504 exact duplicate hash groups containing the RP3/RP6 pair. Sensing the Forest has 34 frozen source IDs, but per-file session identity remains unresolved.

No split assignments were changed. No new audio was downloaded, so no new raw-subset duplicate or near-duplicate search was executed; that status is explicitly recorded as unresolved.

## Validation

The executable audit generated all required artifacts. CSV schemas and row counts were checked, including 5 FSC22 provenance rows, 2 FSC22 license rows, 5 C3GD rows, 4 Rodopi rows, 4 Sensing-the-Forest rows, and 4 candidate-decision rows. Protected hashes are recorded in `integrity_hashes.json`.

No training, inference, relabeling, threshold tuning, frozen-manifest, production, or firmware changes occurred. Existing user modifications were preserved.

## Recommended next action

Keep Phase 5 blocked. If a narrow follow-up is authorized, perform only the C3GD raw-subset duplicate/near-duplicate audit and preserve `file_id`/event grouping. For FSC22, obtain authoritative per-file Freesound mappings and licenses before any audio admission.

## Evidence references

- `datasets/raw/fsc22/FSC22_repo/README.md` and `LICENSE`
- `datasets/raw/fsc22/FSC22_repo/Metadata/Metadata V1.0 FSC22.csv`
- [FSC22 paper](https://www.mdpi.com/1424-8220/23/4/2032)
- `datasets/raw/c3gd/C3GD/README.md` and `metadata.csv`
- `datasets/raw/rodopi/download_metadata.json`
- [Sensing the Forest Zenodo documentation](https://zenodo.org/records/18911592)
- `reports/phase4_diagnostics/frozen_exact_duplicate_groups.csv`
