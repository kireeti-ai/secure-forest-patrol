"""Deterministic, production-independent alert decision layer.

This module consumes predictions; it never changes model outputs. It is used by
the Phase 3 offline replay only.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

CLASSES = ("background", "chainsaw", "gunshot")
EVENTS = ("chainsaw", "gunshot")


@dataclass(frozen=True)
class PredictionRecord:
    recording_id: str
    sample_id: str
    segment_index: int
    true_class: str
    predicted_class: str
    scores: Tuple[float, float, float]
    margin: float
    start_s: float


@dataclass(frozen=True)
class LayerConfig:
    temporal_enabled: bool = False
    temporal_support: int = 2
    temporal_history: int = 2
    temporal_max_gap: int = 1
    reject_enabled: bool = False
    reject_margin: float = 0.0
    duplicate_enabled: bool = False
    duplicate_quiet_windows: int = 4


@dataclass
class Decision:
    recording_id: str
    sample_id: str
    segment_index: int
    raw_class: str
    operational_state: str
    decision_class: str
    confirmed: bool
    candidate_alert: bool
    alert_emitted: bool
    suppressed: bool
    suppression_reason: str = ""
    uncertain_reason: str = ""
    transition: str = ""
    start_s: float = 0.0


class AlertDecisionLayer:
    """Stateful per-recording decision layer.

    Records must arrive in nondecreasing segment order. A duplicate segment is
    skipped deterministically; an out-of-order segment is logged as rejected.
    The caller must instantiate/reset this object at recording boundaries.
    """

    def __init__(self, config: LayerConfig):
        self.config = config
        self.reset()

    def reset(self) -> None:
        self.last_segment: Optional[int] = None
        self.last_start_s: Optional[float] = None
        self.history: Dict[str, List[int]] = {event: [] for event in EVENTS}
        self.active_alert: Dict[str, bool] = {event: False for event in EVENTS}
        self.last_alert_segment: Dict[str, Optional[int]] = {event: None for event in EVENTS}

    def process(self, record: PredictionRecord) -> Decision:
        if self.last_start_s is not None and record.start_s <= self.last_start_s:
            reason = "duplicate_timestamp" if record.start_s == self.last_start_s else "out_of_order_timestamp"
            return Decision(record.recording_id, record.sample_id, record.segment_index,
                            record.predicted_class, "UNCERTAIN", "background", False,
                            False, False, True, reason, start_s=record.start_s)
        self.last_segment = record.segment_index
        self.last_start_s = record.start_s

        raw_event = record.predicted_class if record.predicted_class in EVENTS else None
        accepted_event = raw_event
        uncertain_reason = ""
        if self.config.reject_enabled and raw_event and record.margin < self.config.reject_margin:
            accepted_event = None
            uncertain_reason = "margin_below_validation_threshold"

        confirmed = bool(accepted_event)
        if accepted_event and self.config.temporal_enabled:
            previous = self.history[accepted_event]
            previous.append(record.start_s)
            cutoff = record.start_s - (self.config.temporal_history - 1) * 0.5
            self.history[accepted_event] = [s for s in previous if s >= cutoff]
            recent = self.history[accepted_event]
            gaps_ok = len(recent) >= 2 and all((b - a) <= self.config.temporal_max_gap * 0.5 + 1e-9
                                                for a, b in zip(recent, recent[1:]))
            confirmed = len(recent) >= self.config.temporal_support and gaps_ok
        elif accepted_event:
            self.history[accepted_event].append(record.start_s)

        if raw_event and not accepted_event:
            state = "UNCERTAIN_" + raw_event.upper()
            decision_class = "uncertain"
        elif accepted_event and self.config.temporal_enabled and not confirmed:
            state = "UNCERTAIN_" + accepted_event.upper()
            decision_class = "background"
            uncertain_reason = "temporal_support_incomplete"
        elif accepted_event:
            state = "CONFIRMED_EVENT"
            decision_class = accepted_event
        else:
            state = "BACKGROUND"
            decision_class = "background"

        candidate = bool(accepted_event and (confirmed if self.config.temporal_enabled else True))
        emitted = candidate
        suppressed = False
        suppression_reason = ""
        transition = ""
        if candidate:
            if self.config.duplicate_enabled:
                last = self.last_alert_segment[accepted_event]
                if self.active_alert[accepted_event] and last is not None and record.start_s - last <= self.config.duplicate_quiet_windows * 0.5:
                    emitted = False
                    suppressed = True
                    suppression_reason = "active_same_class_episode"
                    # Extend the active episode on every same-class detection;
                    # a quiet period is measured from the latest candidate.
                    self.last_alert_segment[accepted_event] = record.start_s
                else:
                    transition = "OPEN_ALERT"
                    self.active_alert[accepted_event] = True
                    self.last_alert_segment[accepted_event] = record.start_s
                    emitted = True
            else:
                transition = "ALERT_CANDIDATE"
        else:
            for event in EVENTS:
                last = self.last_alert_segment[event]
                if self.active_alert[event] and (last is None or record.start_s - last > self.config.duplicate_quiet_windows * 0.5):
                    self.active_alert[event] = False
                    transition = "CLOSE_" + event.upper()

        return Decision(record.recording_id, record.sample_id, record.segment_index,
                        record.predicted_class, state, decision_class, confirmed,
                        candidate, emitted, suppressed, suppression_reason,
                        uncertain_reason, transition, record.start_s)


def reset_between_recordings(layer: AlertDecisionLayer) -> None:
    """Explicit helper used by replay and unit tests."""
    layer.reset()
