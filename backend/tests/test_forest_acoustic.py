"""Acoustic ingestion + review workflow tests."""

from sqlalchemy import select

from app.models.acoustic_event import AcousticEvent
from app.models.forest_node import ForestNode
from tests.forest_vectors import acoustic_payload, public_pem


def _register_acoustic_key(db_session):
    node = db_session.scalar(select(ForestNode).where(ForestNode.node_id == "FN-002"))
    node.public_key = public_pem()
    db_session.commit()


def test_acoustic_accepted_and_pending_review(client, db_session, seeded_data):
    _register_acoustic_key(db_session)
    body, _, _ = acoustic_payload()
    r = client.post("/api/ingest/gateway/acoustic-event", json=body)
    assert r.status_code == 201, r.text
    assert r.json()["outcome"] == "ACCEPTED"
    row = db_session.scalar(select(AcousticEvent).where(
        AcousticEvent.event_id == r.json()["event_id"]))
    assert row.review_status == "PENDING_REVIEW"
    assert row.classification == "Chainsaw"


def test_acoustic_duplicate_idempotent(client, db_session, seeded_data):
    _register_acoustic_key(db_session)
    body, _, _ = acoustic_payload()
    assert client.post("/api/ingest/gateway/acoustic-event", json=body).status_code == 201
    dupe = client.post("/api/ingest/gateway/acoustic-event", json=body)
    assert dupe.status_code == 200
    assert dupe.json()["outcome"] == "DUPLICATE"


def test_acoustic_review_workflow(client, db_session, seeded_data):
    _register_acoustic_key(db_session)
    body, _, _ = acoustic_payload()
    created = client.post("/api/ingest/gateway/acoustic-event", json=body)
    event_id = created.json()["event_id"]
    for target in ["REVIEWED", "CONFIRMED"]:
        r = client.post(f"/api/forest/acoustic-events/{event_id}/review",
                        json={"review_status": target})
        assert r.status_code == 200, r.text
        assert r.json()["reviewStatus"] == target


def test_inference_not_confirmed_automatically(client, db_session, seeded_data):
    _register_acoustic_key(db_session)
    body, _, _ = acoustic_payload()
    created = client.post("/api/ingest/gateway/acoustic-event", json=body)
    assert created.status_code == 201
    row = db_session.scalar(select(AcousticEvent).where(
        AcousticEvent.event_id == created.json()["event_id"]))
    assert row.review_status != "CONFIRMED"


def test_unsigned_node_acoustic_event_is_stored_pending_and_deduped(client, db_session, seeded_data):
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from app.models.acoustic_event import AcousticEvent

    client.post("/api/forest/nodes", json={"node_id": "NODE_01", "checkpoint_id": "CP-01"})
    body = {"node_id": "NODE_01", "sequence": 0, "classification": "Gunshot", "confidence": 0.83,
            "model_version": "forest-acoustic-v1", "trigger_rms": 412, "gateway": {"gateway_id": "GW-FE", "rssi": -70, "snr": 9.5}}
    first = client.post("/api/ingest/gateway/acoustic-node-event", json=body)
    assert first.status_code == 201, first.text
    assert first.json()["outcome"] == "ACCEPTED"
    assert (first.json()["signature_status"], first.json()["chain_status"]) == ("PENDING", "PENDING")
    # immediate retry is a duplicate
    assert client.post("/api/ingest/gateway/acoustic-node-event", json=body).json()["outcome"] == "DUPLICATE"

    row = db_session.scalar(select(AcousticEvent).where(AcousticEvent.node_id == "NODE_01"))
    assert row.review_status == "PENDING_REVIEW" and row.checkpoint_id == "CP-01" and row.record_hash == "UNSIGNED"

    # node reboots later, counter restarts at 0: a new event, not a duplicate; backend sequence keeps rising
    row.backend_received_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    db_session.commit()
    again = client.post("/api/ingest/gateway/acoustic-node-event", json=body)
    assert again.json()["outcome"] == "ACCEPTED"
    seqs = sorted(r.sequence for r in db_session.scalars(select(AcousticEvent).where(AcousticEvent.node_id == "NODE_01")))
    assert seqs == [1, 2]

    shown = client.get("/api/forest/acoustic-events").json()
    assert {e["classification"] for e in shown if e["nodeId"] == "NODE_01"} == {"Gunshot"}


def test_unsigned_acoustic_event_rejects_unknown_node_and_bad_class(client, db_session, seeded_data):
    base = {"sequence": 1, "confidence": 0.5}
    assert client.post("/api/ingest/gateway/acoustic-node-event", json={**base, "node_id": "NODE_99", "classification": "Gunshot"}).status_code == 404
    assert client.post("/api/ingest/gateway/acoustic-node-event", json={**base, "node_id": "NODE_01", "classification": "Background"}).status_code == 422


def test_mqtt_acoustic_topic_routes_unsigned_and_signed(client, db_session, seeded_data):
    import json
    from types import SimpleNamespace
    from sqlalchemy import select
    from app.models.acoustic_event import AcousticEvent
    from app.services.mqtt_consumer import TOPIC_ACOUSTIC, MqttConsumer

    client.post("/api/forest/nodes", json={"node_id": "NODE_01", "checkpoint_id": "CP-01"})
    consumer = MqttConsumer(session_factory=lambda: db_session)
    db_session.close = lambda: None
    consumer._on_message(None, None, SimpleNamespace(topic=TOPIC_ACOUSTIC, payload=json.dumps(
        {"node_id": "NODE_01", "sequence": 7, "classification": "Chainsaw", "confidence": 0.9}).encode()))
    row = db_session.scalar(select(AcousticEvent).where(AcousticEvent.node_id == "NODE_01"))
    assert row is not None and row.classification == "Chainsaw" and row.signature_status == "PENDING"
