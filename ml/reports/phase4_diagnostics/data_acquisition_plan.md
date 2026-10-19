# Phase 4 Data Acquisition Plan

## Decision

No external data was acquired in Phase 4. The current repository already contains useful candidate source domains and documented hard-background categories, so downloading more files before label/provenance review would increase volume without resolving the measured failure modes.

## Immediate candidate work

Use the isolated `datasets/phase4_candidate/manifest.csv` for review only. Prioritize:

1. Source-disjoint hard backgrounds from RFCx, ESC-50, and FSC22-like forest categories, with special attention to the Phase 1 FP domains and bird/insect/wind/engine/transient strata.
2. Low-energy chainsaw sources from RFCx and ESC-50, keeping one or a small number of source-level representatives rather than overlapping-window expansion.
3. Gunshot coverage from C3GD, with explicit review of low-energy and boundary cases before inclusion.

## External acquisition gates

External acquisition is justified only if the review confirms that the existing sources cannot supply a required gap. Any future acquisition must record the authoritative source URL, license URL, citation, permitted use, file hashes, original recording ID, and parent/crop relationship before processing under the accepted Phase 2 contract.

Repository license records currently identify:

- C3GD: CC BY 4.0 — attribution required.
- ESC-50: CC BY-NC 3.0 — non-commercial restriction.
- RFCx FrugalAI: CC BY-NC 4.0 — non-commercial restriction.
- Sensing the Forest: CC0 1.0, but it has no frozen v1 training rows in the audited manifest.
- FSC22 and Rodopi: license verification remains required before redistribution or commercial use.

No arbitrary web scraping, full-dataset download, or unlicensed acquisition is authorized by this plan.
