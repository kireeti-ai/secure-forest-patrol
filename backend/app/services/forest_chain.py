"""Hash-chain helpers (content + record-history integrity)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.enums import ChainStatus
from app.schemas.forest_ingest import ForestAcousticIngest, ForestPatrolIngest
from app.services import crypto
from app.services.forest_verify import prev_acoustic_hash, prev_patrol_hash


def patrol_chain_status(db: Session, payload: ForestPatrolIngest) -> str:
    linkage = crypto.verify_hash_chain(
        previous_hash=payload.previous_hash,
        expected_previous=prev_patrol_hash(db, payload.node_id, payload.sequence))
    recomputed = crypto.compute_record_hash(
        node_id=payload.node_id, sequence=payload.sequence,
        event_created_at=payload.event_created_at,
        payload_digest=crypto.patrol_payload_digest(
            checkpoint_id=payload.checkpoint_id, officer_id=payload.officer_id,
            rfid_result=payload.rfid_result,
            fingerprint_result=payload.fingerprint_result),
        previous_hash=payload.previous_hash)
    ok = linkage and recomputed == payload.record_hash
    return ChainStatus.VALID.value if ok else ChainStatus.BROKEN.value


def acoustic_chain_status(db: Session, payload: ForestAcousticIngest) -> str:
    linkage = crypto.verify_hash_chain(
        previous_hash=payload.previous_hash,
        expected_previous=prev_acoustic_hash(db, payload.node_id, payload.sequence))
    recomputed = crypto.compute_record_hash(
        node_id=payload.node_id, sequence=payload.sequence,
        event_created_at=payload.event_created_at,
        payload_digest=crypto.acoustic_payload_digest(
            classification=payload.classification, confidence=payload.confidence,
            model_version=payload.model_version),
        previous_hash=payload.previous_hash)
    ok = linkage and recomputed == payload.record_hash
    return ChainStatus.VALID.value if ok else ChainStatus.BROKEN.value
