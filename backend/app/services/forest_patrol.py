"""Forest patrol-event ingestion (idempotent on node_id + sequence)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.enums import ChainStatus, EventSyncStatus, IngestOutcome, SignatureStatus, SyncState
from app.models.forest_node import ForestNode
from app.models.patrol_event import PatrolEvent
from app.schemas.forest_ingest import ForestPatrolIngest
from app.services.errors import ResourceNotFoundError
from app.services.forest_chain import patrol_chain_status
from app.services.forest_verify import gateway_id_of, patrol_sig_status, record_sync, touch_gateway


class UnknownNodeError(ResourceNotFoundError):
    pass


def _outcome(sig: str, chain: str) -> tuple[str, int, str]:
    if sig == SignatureStatus.INVALID.value:
        return IngestOutcome.INVALID_SIGNATURE.value, 202, EventSyncStatus.FAILED.value
    if chain == ChainStatus.BROKEN.value:
        return IngestOutcome.BROKEN_CHAIN.value, 202, EventSyncStatus.FAILED.value
    return IngestOutcome.ACCEPTED.value, 201, EventSyncStatus.SYNCED.value


def ingest_patrol_event(db: Session, payload: ForestPatrolIngest) -> tuple[dict, int]:
    now = datetime.now(timezone.utc)
    node = db.scalar(select(ForestNode).where(ForestNode.node_id == payload.node_id))
    if node is None:
        raise UnknownNodeError(f"Unknown node '{payload.node_id}'")
    if (node.status or "ACTIVE") != "ACTIVE":
        return ({"outcome": IngestOutcome.INVALID_REQUEST.value,
                 "detail": f"Node '{payload.node_id}' is not active", "duplicate": False}, 422)
    gid = gateway_id_of(payload.gateway)
    gw_received = payload.gateway.received_at if payload.gateway and payload.gateway.received_at else now
    existing = db.scalar(select(PatrolEvent).where(
        PatrolEvent.node_id == payload.node_id, PatrolEvent.sequence == payload.sequence))
    if existing is not None:
        touch_gateway(db, gid, now=now)
        record_sync(db, event_id=existing.event_id, node_id=payload.node_id,
                    gateway_id=gid, now=now, status=SyncState.DUPLICATE.value, bump=True)
        db.commit()
        return ({"outcome": IngestOutcome.DUPLICATE.value, "event_id": existing.event_id,
                 "duplicate": True, "signature_status": existing.signature_status,
                 "chain_status": existing.chain_status}, 200)
    event_id = payload.event_id or f"{payload.node_id}-{payload.sequence:06d}"
    sig = patrol_sig_status(node, payload)
    chain = patrol_chain_status(db, payload)
    outcome, http_status, sync_status = _outcome(sig, chain)
    row = PatrolEvent(
        event_id=event_id, node_id=payload.node_id,
        checkpoint_id=payload.checkpoint_id or node.checkpoint_id,
        officer_id=payload.officer_id, sequence=payload.sequence,
        event_type=payload.event_type or "PATROL_EVENT",
        rfid_result=payload.rfid_result, fingerprint_result=payload.fingerprint_result,
        event_created_at=payload.event_created_at, gateway_received_at=gw_received,
        backend_received_at=now, previous_hash=payload.previous_hash,
        record_hash=payload.record_hash, signature=payload.signature,
        signature_status=sig, chain_status=chain, sync_status=sync_status, verified_at=now)
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        dupe = db.scalar(select(PatrolEvent).where(
            PatrolEvent.node_id == payload.node_id, PatrolEvent.sequence == payload.sequence))
        if dupe is not None:
            touch_gateway(db, gid, now=now)
            db.commit()
            return ({"outcome": IngestOutcome.DUPLICATE.value, "event_id": dupe.event_id,
                     "duplicate": True, "signature_status": dupe.signature_status,
                     "chain_status": dupe.chain_status}, 200)
        raise
    node.last_seen_at = now
    touch_gateway(db, gid, now=now)
    record_sync(db, event_id=event_id, node_id=payload.node_id, gateway_id=gid, now=now,
                status=SyncState.VERIFIED.value if outcome == IngestOutcome.ACCEPTED.value else SyncState.FAILED.value,
                failure_reason=None if outcome == IngestOutcome.ACCEPTED.value else outcome)
    db.commit()
    db.refresh(row)
    return ({"outcome": outcome, "event_id": row.event_id, "duplicate": False,
             "signature_status": row.signature_status, "chain_status": row.chain_status}, http_status)
