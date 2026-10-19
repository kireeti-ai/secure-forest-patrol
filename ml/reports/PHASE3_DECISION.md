# Phase 3 Decision Record

Date: 2026-10-18  
Status: **Diagnostic recommendation only — not production approval**

## Decision

- **Temporal confirmation:** Not justified by this replay. Every tested rule reduced event recall below the validation selection floor, particularly for short gunshot/partial-event windows.
- **Reject state:** Justified for further controlled testing. Validation selected an uncalibrated margin cutoff of `0.30`; locked test background FP rate decreased from `0.3010` to `0.2100`, with 183 uncertain windows and chainsaw recall decreasing from `0.8373` to `0.7695`.
- **Duplicate suppression:** Justified as an alert-volume mechanism, not as verified event deduplication. A 2.0-second quiet period reduced test emitted candidates from 829 to 199 without changing window classification metrics.
- **Selected experimental configuration:** reject margin `0.30` plus same-class duplicate suppression with a 2.0-second quiet period. Temporal confirmation is disabled because validation did not support it.

## Known failure cases

- Low-energy/partial chainsaw windows can be rejected or remain uncertain.
- A margin rule is not calibrated probability and may suppress real events near the cutoff.
- A continuous event with a gap longer than the configured quiet period may be split into multiple alert episodes.
- Two distinct real-world events closer than the quiet period may be grouped.
- The replay dataset cannot verify event identity for every suppressed candidate.

## Further testing suitability

The isolated logic is suitable for a future hardware-parity experiment, not deployment. Before integration, collect paired ESP32-S3/INMP441 traces, verify preprocessing/model output parity, measure alert latency and memory, and evaluate on recordings with reliable event intervals and duration denominators.

Claims that remain unverified: false alerts per hour, event-level recall, true duplicate-event suppression, hardware timing/RAM/power, and production operator impact.
