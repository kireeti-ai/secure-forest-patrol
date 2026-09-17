"""Verification helpers: signature + hash-chain + sync bookkeeping."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.acoustic_event import AcousticEvent
from app.models.enums import ChainStatus, SignatureStatus
from app.models.forest_gateway import Gateway
from app.models.forest_node import ForestNode
from app.models.patrol_event import PatrolEvent
from app.models.sync_record import SyncRecord
from app.schemas.forest_ingest import ForestAcousticIngest, ForestPatrolIngest
from app.services import crypto


def gateway_id_of(payload_gateway, fallback: str = "UNKNOWN") -> str:
    gid = getattr(payload_gateway, "gateway_id", None) if payload_gateway is not None else None
    return gid or fallback


def touch_gateway(db: Session, gateway_id: str, *, now: datetime) -> Gateway:
    gateway = db.scalar(select(Gateway).where(Gateway.gateway_id == gateway_id))
    if gateway is None:
        gateway = Gateway(gateway_id=gateway_id, name=gateway_id, status="ACTIVE")
        db.add(gateway)
        db.flush()
    gateway.last_seen_at = now
    gateway.last_successful_sync_at = now
    gateway.records_received = (gateway.records_received or 0) + 1
    gateway.records_forwarded = (gateway.records_forwarded or 0) + 1
    return gateway


def record_sync(db: Session, *, event_id: str, node_id: str, gateway_id: str,
                now: datetime, status: str, failure_reason: str | None = None,
                bump: bool = False) -> SyncRecord:
    existing = db.scalar(select(SyncRecord).where(
        SyncRecord.event_id == event_id, SyncRecord.gateway_id == gateway_id))
    if existing is not None:
        if bump:
            existing.attempt_count = (existing.attempt_count or 1) + 1
        existing.sync_status = status
        existing.forwarded_at = now
        if failure_reason is not None:
            existing.failure_reason = failure_reason
        return existing
    row = SyncRecord(event_id=event_id, node_id=node_id, gateway_id=gateway_id,
                     received_at=now, forwarded_at=now, attempt_count=1,
                     sync_status=status, failure_reason=failure_reason)
    db.add(row)
    return row


def prev_patrol_hash(db: Session, node_id: str, sequence: int) -> str | None:
    prior = db.scalar(select(PatrolEvent).where(
        PatrolEvent.node_id == node_id, PatrolEvent.sequence < sequence
    ).order_by(PatrolEvent.sequence.desc()))
    return prior.record_hash if prior is not None else None


def prev_acoustic_hash(db: Session, node_id: str, sequence: int) -> str | None:
    prior = db.scalar(select(AcousticEvent).where(
        AcousticEvent.node_id == node_id, AcousticEvent.sequence < sequence
    ).order_by(AcousticEvent.sequence.desc()))
    return prior.record_hash if prior is not None else None


def patrol_sig_status(node: ForestNode, payload: ForestPatrolIngest) -> str:
    if not node.public_key:
        return SignatureStatus.PENDING.value
    message = crypto.patrol_signing_bytes(
        node_id=payload.node_id, sequence=payload.sequence,
        event_created_at=payload.event_created_at, checkpoint_id=payload.checkpoint_id,
        officer_id=payload.officer_id, rfid_result=payload.rfid_result,
        fingerprint_result=payload.fingerprint_result,
        previous_hash=payload.previous_hash, record_hash=payload.record_hash)
    ok = crypto.verify_signature(public_key=node.public_key, message=message,
                                 signature_b64=payload.signature)
    return SignatureStatus.VALID.value if ok else SignatureStatus.INVALID.value


def acoustic_sig_status(node: ForestNode, payload: ForestAcousticIngest) -> str:
    if not node.public_key:
        return SignatureStatus.PENDING.value
    message = crypto.acoustic_signing_bytes(
        node_id=payload.node_id, sequence=payload.sequence,
        event_created_at=payload.event_created_at, checkpoint_id=payload.checkpoint_id,
        zone_id=payload.zone_id, classification=payload.classification,
        confidence=payload.confidence, model_version=payload.model_version,
        previous_hash=payload.previous_hash, record_hash=payload.record_hash)
    ok = crypto.verify_signature(public_key=node.public_key, message=message,
                                 signature_b64=payload.signature)
    return SignatureStatus.VALID.value if ok else SignatureStatus.INVALID.value
