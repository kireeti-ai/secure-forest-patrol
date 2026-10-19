# Human Audio Review Protocol

Review the original audio at its native format. Do not rely on the filename, source label, model prediction, waveform statistics, or spectrogram alone. Save one decision per source recording in the separate review output.

Use `ACCEPTED` only when the proposed class is clearly audible and the recording is usable. Use `RELABEL_REQUIRED` when a different class is clearly supported. Use `AMBIGUOUS` for uncertain, weak, mixed, or contaminated audio; use `EXCLUDED` for unusable audio; use `NEEDS_SECOND_REVIEW` when adjudication is required. Record event boundaries when determinable and mark unknown otherwise.

For chainsaw, distinguish engine-like chainsaw characteristics from ordinary engines or machinery. For gunshot, distinguish a firearm report from impacts, fireworks, cracking, or other impulses and record whether the decay is audible. For background, note birds, insects, wind, rain, engines, impacts, and mixed scenes that could explain false positives. Reviewers must not promote a row based only on source metadata.

Recommended review order is P1 target false-negative sources, P2 background sources linked to Phase 1 hard-negative categories, then P3 remaining candidates. The queue is source-balanced and does not include frozen validation/test failures as training candidates.
