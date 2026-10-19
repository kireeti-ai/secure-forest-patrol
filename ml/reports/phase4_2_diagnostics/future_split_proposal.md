# Future Split Proposal

For any future training experiment, group first by original recording and parent/session ID, then assign whole groups to train, validation, or test. Keep all overlapping windows from one source in one partition. Preserve dataset/provider and device strata where available, and reserve a source-disjoint forest-domain challenge set. Do not use the frozen test set for selection, thresholding, or augmentation. This is a proposal only; no split was changed in Phase 4.2.
