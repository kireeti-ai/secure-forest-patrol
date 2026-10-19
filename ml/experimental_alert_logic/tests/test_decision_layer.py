import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from experimental_alert_logic.decision_layer import AlertDecisionLayer, LayerConfig, PredictionRecord


def rec(i, cls="background", margin=.8, rid="r"):
    return PredictionRecord(rid, f"{rid}_{i}", i, "background", cls, (0., 0., 0.), margin, i * .5)


def test_confirmation_and_reset():
    layer = AlertDecisionLayer(LayerConfig(temporal_enabled=True, temporal_support=2, temporal_history=2, temporal_max_gap=1))
    assert layer.process(rec(0, "chainsaw")).confirmed is False
    assert layer.process(rec(1, "chainsaw")).confirmed is True
    layer.reset()
    assert layer.process(rec(0, "chainsaw", rid="other")).confirmed is False


def test_reject_is_class_specific_and_not_safe():
    d = AlertDecisionLayer(LayerConfig(reject_enabled=True, reject_margin=.3)).process(rec(0, "gunshot", .1))
    assert d.operational_state == "UNCERTAIN_GUNSHOT"
    assert d.decision_class == "uncertain"


def test_duplicate_suppression_and_quiet_reopen():
    layer = AlertDecisionLayer(LayerConfig(duplicate_enabled=True, duplicate_quiet_windows=2))
    assert layer.process(rec(0, "chainsaw")).alert_emitted
    assert layer.process(rec(1, "chainsaw")).suppressed
    layer.process(rec(4, "background"))
    assert layer.process(rec(5, "chainsaw")).alert_emitted


def test_duplicate_and_out_of_order_are_deterministic():
    layer = AlertDecisionLayer(LayerConfig())
    assert layer.process(rec(2)).suppressed is False
    assert layer.process(rec(2)).suppression_reason == "duplicate_timestamp"
    assert layer.process(rec(1)).suppression_reason == "out_of_order_timestamp"


def test_isolated_chainsaw_does_not_confirm():
    layer = AlertDecisionLayer(LayerConfig(temporal_enabled=True))
    d = layer.process(rec(0, "chainsaw"))
    assert d.operational_state == "UNCERTAIN_CHAINSAW"


def test_isolated_gunshot_does_not_confirm():
    layer = AlertDecisionLayer(LayerConfig(temporal_enabled=True))
    assert layer.process(rec(0, "gunshot")).confirmed is False


def test_repeated_gunshot_confirms():
    layer = AlertDecisionLayer(LayerConfig(temporal_enabled=True))
    layer.process(rec(0, "gunshot"))
    assert layer.process(rec(1, "gunshot")).confirmed


def test_alternating_classes_do_not_cross_confirm():
    layer = AlertDecisionLayer(LayerConfig(temporal_enabled=True))
    layer.process(rec(0, "chainsaw"))
    assert layer.process(rec(1, "gunshot")).confirmed is False


def test_ambiguous_margin_rejects():
    d = AlertDecisionLayer(LayerConfig(reject_enabled=True, reject_margin=.2)).process(rec(0, "chainsaw", .19))
    assert d.decision_class == "uncertain"


def test_stable_predictions_need_required_support():
    layer = AlertDecisionLayer(LayerConfig(temporal_enabled=True, temporal_support=3, temporal_history=4))
    assert [layer.process(rec(i, "chainsaw")).confirmed for i in range(2)] == [False, False]


def test_long_background_stays_background():
    layer = AlertDecisionLayer(LayerConfig(temporal_enabled=True))
    assert all(layer.process(rec(i)).decision_class == "background" for i in range(20))


def test_quiet_period_allows_new_event():
    layer = AlertDecisionLayer(LayerConfig(duplicate_enabled=True, duplicate_quiet_windows=2))
    assert layer.process(rec(0, "chainsaw")).alert_emitted
    assert layer.process(rec(1, "chainsaw")).suppressed
    layer.process(rec(4, "background"))
    assert layer.process(rec(5, "chainsaw")).alert_emitted


def test_extended_episode_does_not_reopen_each_window():
    layer = AlertDecisionLayer(LayerConfig(duplicate_enabled=True, duplicate_quiet_windows=2))
    assert layer.process(rec(0, "gunshot")).alert_emitted
    for i in range(1, 10):
        assert layer.process(rec(i, "gunshot")).suppressed


def test_recording_boundary_resets_state():
    layer = AlertDecisionLayer(LayerConfig(temporal_enabled=True))
    layer.process(rec(0, "chainsaw", rid="a"))
    layer.reset()
    assert layer.process(rec(1, "chainsaw", rid="b")).confirmed is False


def test_missing_gap_fails_confirmation():
    layer = AlertDecisionLayer(LayerConfig(temporal_enabled=True, temporal_support=2, temporal_history=3, temporal_max_gap=1))
    layer.process(rec(0, "chainsaw"))
    assert layer.process(rec(3, "chainsaw")).confirmed is False


def test_end_of_recording_does_not_emit_without_candidate():
    layer = AlertDecisionLayer(LayerConfig(duplicate_enabled=True))
    d = layer.process(rec(0, "background"))
    assert d.alert_emitted is False and d.transition == ""


def test_new_event_after_suppressed_episode_emits():
    layer = AlertDecisionLayer(LayerConfig(duplicate_enabled=True, duplicate_quiet_windows=2))
    layer.process(rec(0, "chainsaw"))
    layer.process(rec(1, "chainsaw"))
    layer.process(rec(5, "background"))
    assert layer.process(rec(6, "chainsaw")).alert_emitted
