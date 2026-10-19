# Phase 4 Candidate Dataset

This directory is an isolated, review-only candidate manifest for a possible future Phase 5 dataset. It does not replace `datasets/v1`, does not modify frozen train/validation/test membership, and has not been used for training.

`manifest.csv` contains one representative segment per selected training-source candidate. Selection is source-level where possible; overlapping windows from a source were not added as independent examples. The manifest preserves source recording ID, parent group, original split, source path, SHA-256, label provenance, license information, and a future split group.

The manifest contains 777 unique source rows and 777 unique content hashes after candidate-level exact-duplicate handling. It includes research-only candidates and rows requiring license, label, or review gates. “Candidate” does not mean approved for training.

Selection focuses on existing training-source hard-background categories and low-energy chainsaw/gunshot coverage. Frozen validation/test failure examples are retained only in `ml/reports/phase4_diagnostics` and are excluded from this candidate training manifest.

Source labels are not independent acoustic verification. Unknown-license FSC22/Rodopi material remains quarantined. ESC-50 and RFCx retain their non-commercial restrictions. C3GD is recorded as CC BY 4.0. Before Phase 5, a reviewer must verify intended use, labels, event occupancy, parent-recording isolation, and near-duplicate relationships.

The audio paths reference existing processed files. No audio files were copied or rewritten by Phase 4.
