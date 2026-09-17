"""Patrol crypto + chain tests with deterministic vectors."""

from datetime import datetime, timezone

from sqlalchemy import select

from app.models.forest_node import ForestNode
from app.models.patrol_event import PatrolEvent
from tests.forest_vectors import patrol_payload, public_pem, wrong_public_pem


def _register_key(db_session, pem=None):
    node = db_session.scalar(select(ForestNode).where(ForestNode.node_id == "FN-001"))
    node.public_key = pem or public_pem()
    db_session.commit()


def test_invalid_signature_recorded(client, db_session, seeded_data):
    _register_key(db_session)
    body, _, _ = patrol_payload()
    body["signature"] = body["signature"][::-1]
    r = client.post("/api/ingest/gateway/forest-event", json=body)
    assert r.status_code == 202
    assert r.json()["outcome"] == "INVALID_SIGNATURE"


def test_wrong_public_key_invalid(client, db_session, seeded_data):
    _register_key(db_session, wrong_public_pem())
    body, _, _ = patrol_payload()
    r = client.post("/api/ingest/gateway/forest-event", json=body)
    assert r.status_code == 202
    assert r.json()["outcome"] == "INVALID_SIGNATURE"


def test_modified_payload_rejected(client, db_session, seeded_data):
    _register_key(db_session)
    body, _, _ = patrol_payload()
    body["rfid_result"] = "INVALID"
    r = client.post("/api/ingest/gateway/forest-event", json=body)
    assert r.status_code == 202
    assert r.json()["outcome"] in ("INVALID_SIGNATURE", "BROKEN_CHAIN")


def test_broken_chain_recorded(client, db_session, seeded_data):
    _register_key(db_session)
    body, _, _ = patrol_payload(sequence=2, previous_hash="WRONG-HASH")
    r = client.post("/api/ingest/gateway/forest-event", json=body)
    assert r.status_code == 202
    assert r.json()["outcome"] == "BROKEN_CHAIN"


def test_chain_links_two_events(client, db_session, seeded_data):
    _register_key(db_session)
    first_body, _, first_hash = patrol_payload(sequence=1)
    assert client.post("/api/ingest/gateway/forest-event", json=first_body).status_code == 201
    second_body, _, _ = patrol_payload(sequence=2, previous_hash=first_hash)
    r = client.post("/api/ingest/gateway/forest-event", json=second_body)
    assert r.status_code == 201
    assert r.json()["chain_status"] == "VALID"


def test_delayed_event_keeps_node_timestamp(client, db_session, seeded_data):
    _register_key(db_session)
    body, created, _ = patrol_payload()
    r = client.post("/api/ingest/gateway/forest-event", json=body)
    assert r.status_code == 201
    row = db_session.scalar(select(PatrolEvent).where(
        PatrolEvent.event_id == r.json()["event_id"]))
    # SQLite (test backend) drops tzinfo on read; normalize before comparing
    # instants. PostgreSQL stores/returns tz-aware timestamps unchanged.
    stored = row.event_created_at
    if stored.tzinfo is None:
        stored = stored.replace(tzinfo=timezone.utc)
    assert stored == created
    assert row.gateway_received_at is not None
    received = row.gateway_received_at
    if received.tzinfo is None:
        received = received.replace(tzinfo=timezone.utc)
    assert received == datetime(2026, 9, 17, 13, 27, 11, tzinfo=timezone.utc)
