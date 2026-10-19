# Leakage Analysis

The frozen exact-hash scan contains 5,008 processed rows in 2,504 exact-hash groups. No group crosses frozen train, validation, and test splits. These are processed-window identities; overlapping windows from one original recording remain correlated evidence.

The Phase 4.2 candidate rows were selected from frozen training sources and have zero source-ID overlap with frozen validation/test sources. Candidate exact content hashes are unique. Parent-level relationships are preserved in the manifest, but the available metadata cannot prove session-level independence beyond the recorded parent IDs. Near-duplicate acoustic similarity was not run and remains unresolved.
