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
