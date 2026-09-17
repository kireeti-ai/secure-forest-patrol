"""Backend -> Dashboard WebSocket endpoint tests."""

from __future__ import annotations

import json

from sqlalchemy import select

from app.models.forest_node import ForestNode
from tests.forest_vectors import patrol_payload, public_pem


def test_ws_connects_and_receives_broadcast(client):
    import asyncio

    from app.services.ws_manager import manager

    with client.websocket_connect("/ws") as ws:
        asyncio.run(manager.broadcast("NODE_STATUS_CHANGED", {"node_id": "FN-001"}))
        message = json.loads(ws.receive_text())
        assert message["type"] == "NODE_STATUS_CHANGED"
        assert message["node_id"] == "FN-001"


def test_http_ingest_also_broadcasts(client, db_session, seeded_data):
    """The HTTP fallback path must notify the dashboard the same way MQTT
    does -- otherwise a live update silently depends on which transport an
    event arrived on."""
    node = db_session.scalar(select(ForestNode).where(ForestNode.node_id == "FN-001"))
    node.public_key = public_pem()
    db_session.commit()
    body, _, _ = patrol_payload()

    with client.websocket_connect("/ws") as ws:
        r = client.post("/api/ingest/gateway/forest-event", json=body)
        assert r.status_code == 201
        message = json.loads(ws.receive_text())
        assert message["type"] == "PATROL_EVENT_VERIFIED"
        assert message["node_id"] == "FN-001"
