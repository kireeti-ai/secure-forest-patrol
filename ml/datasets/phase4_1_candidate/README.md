# Phase 4.1 Candidate Dataset

This directory is an isolated, review-gated candidate manifest. It is not approved for training and contains no newly acquired external audio.

`manifest.csv` contains 777 provenance rows selected from the existing Phase 4 candidate set. All rows have `training_eligibility=not_yet_label_review`; no row is training-eligible now. The candidate preserves source IDs, parent/future split grouping, audio paths, hashes, source license disposition, and review status.

Required gates before any future training authorization:

- independent human acoustic label and event-occupancy review;
- resolution of FSC22/Rodopi licensing, and retention of attribution for permitted sources;
- parent-recording and source-level split enforcement;
- near-duplicate review beyond exact SHA-256 matching;
- preservation of the frozen v1 model, manifests, caches, and test set.

The manifest is an audit artifact only. Phase 5 training must not consume it without a separately approved acceptance decision.
