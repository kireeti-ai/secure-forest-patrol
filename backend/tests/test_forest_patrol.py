"""Patrol ingestion tests: valid / malformed / duplicates / sync."""

from sqlalchemy import select

from app.core.security import create_access_token
from app.models.forest_node import ForestNode
from app.models.patrol_event import PatrolEvent
from tests.forest_vectors import patrol_payload, public_pem


def _register_key(db_session):
    node = db_session.scalar(select(ForestNode).where(ForestNode.node_id == "FN-001"))
    node.public_key = public_pem()
    db_session.commit()


def test_valid_patrol_accepted(client, db_session, seeded_data):
    _register_key(db_session)
    body, _, _ = patrol_payload()
    r = client.post("/api/ingest/gateway/forest-event", json=body)
    assert r.status_code == 201, r.text
    assert r.json()["outcome"] == "ACCEPTED"
    assert r.json()["signature_status"] == "VALID"
    assert r.json()["chain_status"] == "VALID"


def test_unknown_node_404(client, seeded_data):
    body, _, _ = patrol_payload(node_id="FN-UNKNOWN")
    r = client.post("/api/ingest/gateway/forest-event", json=body)
    assert r.status_code == 404


def test_malformed_422(client, seeded_data):
    r = client.post("/api/ingest/gateway/forest-event", json={"node_id": "FN-001"})
    assert r.status_code == 422


def test_duplicate_is_idempotent(client, db_session, seeded_data):
    _register_key(db_session)
    body, _, _ = patrol_payload()
    assert client.post("/api/ingest/gateway/forest-event", json=body).status_code == 201
    second = client.post("/api/ingest/gateway/forest-event", json=body)
    assert second.status_code == 200
    assert second.json()["outcome"] == "DUPLICATE"
    rows = db_session.scalars(
        select(PatrolEvent).where(PatrolEvent.node_id == "FN-001")).all()
    assert len(rows) == 1
