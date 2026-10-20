"""Forest patrol-event ingestion (idempotent on node_id + sequence)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.enums import ChainStatus, EventSyncStatus, FingerprintResult, IngestOutcome, RfidResult, SignatureStatus, SyncState
from app.models.forest_node import ForestNode
from app.models.patrol_event import PatrolEvent
from app.models.user import User
from app.schemas.forest_ingest import ForestPatrolIngest
from app.services.attendance_state import hex_uid_key, record_attendance_match
from app.services.errors import ResourceNotFoundError
from app.services.forest_chain import patrol_chain_status
from app.services.forest_verify import gateway_id_of, patrol_sig_status, record_sync, touch_gateway


class UnknownNodeError(ResourceNotFoundError):
    pass


def _outcome(sig: str, chain: str) -> tuple[str, int, str]:
    # Phase 3 (docs/TAMPER_EVIDENCE_SECURITY_PLAN.md): once a node HAS a registered public key,
    # a bad signature or a broken hash chain is a hard rejection (4xx), not a 202 "flagged but
    # stored anyway". A node with NO key yet (PENDING) has nothing to verify against - that is
    # not tampering, so it is still accepted and stored, but marked UNVERIFIABLE rather than
    # silently conflated with a cryptographically ACCEPTED event.
    if sig == SignatureStatus.PENDING.value:
        return IngestOutcome.UNVERIFIABLE.value, 202, EventSyncStatus.PENDING.value
    if sig == SignatureStatus.INVALID.value:
        return IngestOutcome.INVALID_SIGNATURE.value, 401, EventSyncStatus.FAILED.value
    if chain == ChainStatus.BROKEN.value:
        return IngestOutcome.BROKEN_CHAIN.value, 409, EventSyncStatus.FAILED.value
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

    # A signed patrol event is this node's normal path once it has identity/clock (see
    # node-firmware's sendVerificationEvent) -- the legacy unsigned 'V' path in
    # app/services/verification.py is the only other place attendance gets marked, and a
    # node past Phase 2 never sends that anymore. Mirror it here: a real two-factor match
    # (valid card + matching finger) on an accepted (non-tampered, chain-intact) event marks
    # today's entry/exit, same as the legacy path.
    if (outcome == IngestOutcome.ACCEPTED.value and payload.officer_id
            and payload.rfid_result == RfidResult.VALID.value
            and payload.fingerprint_result == FingerprintResult.MATCH.value):
        officer_key = hex_uid_key(payload.officer_id)
        claimed = next((u for u in db.scalars(select(User).where(User.is_active.is_(True), User.rfid_uid.is_not(None)))
                        if hex_uid_key(u.rfid_uid) == officer_key), None)
        if claimed and claimed.employee_id:
            record_attendance_match(db, claimed.employee_id, now)

    touch_gateway(db, gid, now=now)
    record_sync(db, event_id=event_id, node_id=payload.node_id, gateway_id=gid, now=now,
                status=SyncState.VERIFIED.value if outcome == IngestOutcome.ACCEPTED.value else SyncState.FAILED.value,
                failure_reason=None if outcome == IngestOutcome.ACCEPTED.value else outcome)
    db.commit()
    db.refresh(row)
    return ({"outcome": outcome, "event_id": row.event_id, "duplicate": False,
             "signature_status": row.signature_status, "chain_status": row.chain_status}, http_status)
