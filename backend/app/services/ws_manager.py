"""Backend -> Dashboard live-update broadcaster.

PostgreSQL remains the source of truth (see ``docs/WEBSOCKET.md``); this
manager only fans out a notification after a row has already been verified
and committed. A dashboard client that misses a message, or that just
reconnected, is expected to refetch REST state -- nothing here is replayed
or persisted.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Lets synchronous callers (e.g. the HTTP ingestion routes, which
        FastAPI runs in a worker thread) schedule a broadcast without
        needing their own event loop -- see schedule_broadcast()."""
        self._loop = loop

    def schedule_broadcast(self, event_type: str, payload: dict) -> None:
        if self._loop is None or self._loop.is_closed():
            return
        asyncio.run_coroutine_threadsafe(self.broadcast(event_type, payload), self._loop)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, event_type: str, payload: dict) -> None:
        message = json.dumps({
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **payload,
        })
        async with self._lock:
            targets = list(self._connections)
        for connection in targets:
            try:
                await connection.send_text(message)
            except Exception:
                await self.disconnect(connection)


manager = ConnectionManager()


def broadcast_patrol_outcome(body: dict, node_id: str, checkpoint_id: str | None) -> None:
    """Shared by the MQTT consumer and the HTTP ingestion route so a
    dashboard live update fires the same way regardless of which transport
    an event arrived on."""
    from app.models.enums import IngestOutcome  # local import avoids a cycle

    event_type = "PATROL_EVENT_VERIFIED" if body["outcome"] == IngestOutcome.ACCEPTED.value else "PATROL_EVENT_REJECTED"
    manager.schedule_broadcast(event_type, {
        "event_id": body.get("event_id"), "node_id": node_id,
        "checkpoint_id": checkpoint_id, "status": body["outcome"]})
    if body.get("chain_status"):
        manager.schedule_broadcast("LEDGER_VERIFICATION_RESULT", {
            "event_id": body.get("event_id"), "node_id": node_id,
            "chain_status": body["chain_status"], "signature_status": body.get("signature_status")})


def broadcast_acoustic_outcome(body: dict, node_id: str, checkpoint_id: str | None) -> None:
    manager.schedule_broadcast("ACOUSTIC_EVENT_RECEIVED", {
        "event_id": body.get("event_id"), "node_id": node_id,
        "checkpoint_id": checkpoint_id, "status": body["outcome"]})


def broadcast_gateway_status(gateway_id: str) -> None:
    manager.schedule_broadcast("GATEWAY_STATUS_CHANGED", {"gateway_id": gateway_id, "status": "REPORTED"})
