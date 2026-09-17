"""Forest acoustic-event ingestion (idempotent on node_id + sequence)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.acoustic_event import AcousticEvent
from app.models.enums import (
    AcousticReviewStatus,
    ChainStatus,
    EventSyncStatus,
    IngestOutcome,
    SignatureStatus,
    SyncState,
)
from app.models.forest_node import ForestNode
from app.schemas.forest_ingest import ForestAcousticIngest
from app.services.forest_chain import acoustic_chain_status
from app.services.forest_patrol import UnknownNodeError
from app.services.forest_verify import acoustic_sig_status, gateway_id_of, record_sync, touch_gateway


def ingest_acoustic_event(db: Session, payload: ForestAcousticIngest) -> tuple[dict, int]:
    now = datetime.now(timezone.utc)
    node = db.scalar(select(ForestNode).where(ForestNode.node_id == payload.node_id))
    if node is None:
        raise UnknownNodeError(f"Unknown node '{payload.node_id}'")
    if (node.status or "ACTIVE") != "ACTIVE":
        return ({"outcome": IngestOutcome.INVALID_REQUEST.value,
                 "detail": f"Node '{payload.node_id}' is not active", "duplicate": False}, 422)
    gid = gateway_id_of(payload.gateway)
    gw_received = payload.gateway.received_at if payload.gateway and payload.gateway.received_at else now
    existing = db.scalar(select(AcousticEvent).where(
        AcousticEvent.node_id == payload.node_id, AcousticEvent.sequence == payload.sequence))
    if existing is not None:
        touch_gateway(db, gid, now=now)
        record_sync(db, event_id=existing.event_id, node_id=payload.node_id,
                    gateway_id=gid, now=now, status=SyncState.DUPLICATE.value, bump=True)
        db.commit()
        return ({"outcome": IngestOutcome.DUPLICATE.value, "event_id": existing.event_id,
                 "duplicate": True, "signature_status": existing.signature_status,
                 "chain_status": existing.chain_status}, 200)
    event_id = payload.event_id or f"{payload.node_id}-A{payload.sequence:06d}"
    sig = acoustic_sig_status(node, payload)
    chain = acoustic_chain_status(db, payload)
    if sig == SignatureStatus.INVALID.value:
        outcome, http_status = IngestOutcome.INVALID_SIGNATURE.value, 202
        sync_status = EventSyncStatus.FAILED.value
    elif chain == ChainStatus.BROKEN.value:
        outcome, http_status = IngestOutcome.BROKEN_CHAIN.value, 202
        sync_status = EventSyncStatus.FAILED.value
    else:
        outcome, http_status = IngestOutcome.ACCEPTED.value, 201
        sync_status = EventSyncStatus.SYNCED.value
    row = AcousticEvent(
        event_id=event_id, node_id=payload.node_id,
        checkpoint_id=payload.checkpoint_id or node.checkpoint_id,
        zone_id=payload.zone_id or node.zone_id, sequence=payload.sequence,
        event_created_at=payload.event_created_at, classification=payload.classification,
        confidence=payload.confidence, model_version=payload.model_version,
        previous_hash=payload.previous_hash, record_hash=payload.record_hash,
        signature=payload.signature, signature_status=sig, chain_status=chain,
        sync_status=sync_status, review_status=AcousticReviewStatus.PENDING_REVIEW.value,
        gateway_received_at=gw_received, backend_received_at=now)
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        dupe = db.scalar(select(AcousticEvent).where(
            AcousticEvent.node_id == payload.node_id, AcousticEvent.sequence == payload.sequence))
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
