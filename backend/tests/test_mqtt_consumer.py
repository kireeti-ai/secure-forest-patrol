"""MQTT consumer tests: transport is exercised directly (no live broker),
routed through the same verification/persistence services the HTTP
ingestion routes use. See docs/MQTT.md."""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import select

from app.models.forest_node import ForestNode
from app.models.patrol_event import PatrolEvent
from app.services.mqtt_consumer import MqttConsumer
from tests.forest_vectors import acoustic_payload, patrol_payload, public_pem


def _register_key(db_session, node_id="FN-001"):
    node = db_session.scalar(select(ForestNode).where(ForestNode.node_id == node_id))
    node.public_key = public_pem()
    db_session.commit()


@pytest.fixture()
def mqtt_consumer(db_session):
    return MqttConsumer(session_factory=lambda: db_session)


def test_valid_patrol_accepted_via_mqtt(mqtt_consumer, db_session, seeded_data):
    _register_key(db_session)
    body, _, _ = patrol_payload()
    mqtt_consumer._handle_patrol(body)
    row = db_session.scalar(select(PatrolEvent).where(PatrolEvent.node_id == "FN-001"))
    assert row is not None
    assert row.signature_status == "VALID"
    assert row.chain_status == "VALID"


def test_duplicate_patrol_is_idempotent_via_mqtt(mqtt_consumer, db_session, seeded_data):
    _register_key(db_session)
    body, _, _ = patrol_payload()
    mqtt_consumer._handle_patrol(body)
    mqtt_consumer._handle_patrol(body)
    rows = db_session.scalars(select(PatrolEvent).where(PatrolEvent.node_id == "FN-001")).all()
    assert len(rows) == 1


def test_invalid_signature_rejected_via_mqtt(mqtt_consumer, db_session, seeded_data):
    _register_key(db_session)
    body, _, _ = patrol_payload()
    body["signature"] = body["signature"][::-1]
    mqtt_consumer._handle_patrol(body)
    row = db_session.scalar(select(PatrolEvent).where(PatrolEvent.node_id == "FN-001"))
    assert row.signature_status == "INVALID"


def test_unknown_node_does_not_raise(mqtt_consumer, db_session, seeded_data):
    body, _, _ = patrol_payload(node_id="FN-UNKNOWN")
    mqtt_consumer._handle_patrol(body)  # must not raise UnknownNodeError out of the handler


def test_malformed_patrol_payload_dropped(mqtt_consumer, db_session, seeded_data):
    mqtt_consumer._handle_patrol({"node_id": "FN-001"})  # missing required fields
    row = db_session.scalar(select(PatrolEvent).where(PatrolEvent.node_id == "FN-001"))
    assert row is None


def test_valid_acoustic_event_recorded_via_mqtt(mqtt_consumer, db_session, seeded_data):
    _register_key(db_session, node_id="FN-002")
    body, _, _ = acoustic_payload()
    mqtt_consumer._handle_acoustic(body)
    from app.models.acoustic_event import AcousticEvent
    row = db_session.scalar(select(AcousticEvent).where(AcousticEvent.node_id == "FN-002"))
    assert row is not None
    assert row.review_status == "PENDING_REVIEW"


def test_broadcast_fires_on_valid_patrol(db_session, seeded_data):
    _register_key(db_session)
    received: list[str] = []

    class _FakeSocket:
        async def send_text(self, message: str) -> None:
            received.append(message)

    from app.services import ws_manager as ws_mod

    async def run():
        loop = asyncio.get_running_loop()
        ws_mod.manager._connections.add(_FakeSocket())
        ws_mod.manager.bind_loop(loop)
        consumer = MqttConsumer(session_factory=lambda: db_session)
        body, _, _ = patrol_payload()
        consumer._handle_patrol(body)
        await asyncio.sleep(0.05)  # let run_coroutine_threadsafe's callback land

    try:
        asyncio.run(run())
        assert any("PATROL_EVENT_VERIFIED" in m for m in received)
    finally:
        ws_mod.manager._connections.clear()
        ws_mod.manager._loop = None
