"""Chronological replay helpers for Phase 3 diagnostics."""
from typing import Iterable, List, Tuple

from .decision_layer import AlertDecisionLayer, Decision, PredictionRecord


def ordered_groups(records: Iterable[PredictionRecord]) -> List[Tuple[str, List[PredictionRecord]]]:
    groups = {}
    for record in records:
        groups.setdefault(record.recording_id, []).append(record)
    return [(key, sorted(value, key=lambda r: (r.start_s, r.segment_index, r.sample_id)))
            for key, value in sorted(groups.items())]


def replay(records: Iterable[PredictionRecord], layer: AlertDecisionLayer) -> List[Decision]:
    original = list(records)
    by_sample = {}
    for _, group in ordered_groups(records):
        layer.reset()
        for record in group:
            by_sample[record.sample_id] = layer.process(record)
    # Keep output aligned with input rows for audit joins while still
    # processing every recording chronologically above.
    return [by_sample[record.sample_id] for record in original]
