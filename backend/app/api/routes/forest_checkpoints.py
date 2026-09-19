"""Forest routers: checkpoint detail + patrol officer registry.

No authentication: see ``docs/BACKEND.md``.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies.database import get_db
from app.api.routes.forest_nodes import checkpoint_out
from app.core.security import require_roles
from app.models.checkpoint import Checkpoint
from app.models.officer import PatrolOfficer
from app.models.patrol_event import PatrolEvent
from app.schemas.forest import (
    CheckpointCreate,
    CheckpointResponse,
    CheckpointUpdate,
    OfficerCreate,
    OfficerResponse,
)

router = APIRouter(prefix="/api/forest", tags=["forest"])


class _OfficerStats:
    __slots__ = ("patrol_count", "mismatch_count", "last_verified_patrol")

    def __init__(self):
        self.patrol_count = 0
        self.mismatch_count = 0
        self.last_verified_patrol = None


def _officer_stats(db: Session, officer_ids: list[str]) -> dict[str, _OfficerStats]:
    """Real per-officer aggregates over patrol_events -- see OfficerResponse."""
    stats: dict[str, _OfficerStats] = {oid: _OfficerStats() for oid in officer_ids}
    if not officer_ids:
        return stats
    rows = db.execute(
        select(PatrolEvent.officer_id, PatrolEvent.rfid_result,
               PatrolEvent.fingerprint_result, PatrolEvent.signature_status,
               PatrolEvent.chain_status, PatrolEvent.event_created_at)
        .where(PatrolEvent.officer_id.in_(officer_ids))
    )
    for officer_id, rfid_result, fingerprint_result, signature_status, chain_status, event_created_at in rows:
        s = stats[officer_id]
        s.patrol_count += 1
        if rfid_result == "INVALID" or fingerprint_result == "NO_MATCH":
            s.mismatch_count += 1
        if signature_status == "VALID" and chain_status == "VALID":
            if s.last_verified_patrol is None or event_created_at > s.last_verified_patrol:
                s.last_verified_patrol = event_created_at
    return stats


def _off_out(o: PatrolOfficer, stats: _OfficerStats | None = None) -> OfficerResponse:
    stats = stats or _OfficerStats()
    return OfficerResponse(id=str(o.id), officer_id=o.officer_id, name=o.name,
                           badge_number=o.badge_number, status=o.status,
                           patrol_count=stats.patrol_count,
                           mismatch_count=stats.mismatch_count,
                           last_verified_patrol=stats.last_verified_patrol,
                           created_at=o.created_at, updated_at=o.updated_at)


@router.post("/checkpoints", response_model=CheckpointResponse,
             status_code=status.HTTP_201_CREATED)
def create_checkpoint(payload: CheckpointCreate,
                      db: Session = Depends(get_db), _: object = Depends(require_roles("ADMIN"))) -> CheckpointResponse:
    if db.scalar(select(Checkpoint).where(Checkpoint.checkpoint_id == payload.checkpoint_id)):
        raise HTTPException(status_code=409, detail="Checkpoint already exists")
    row = Checkpoint(checkpoint_id=payload.checkpoint_id, name=payload.name,
                     zone_id=payload.zone_id, latitude=payload.latitude,
                     longitude=payload.longitude, node_id=payload.node_id,
                     active=payload.active)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Checkpoint already exists")
    db.refresh(row)
    return checkpoint_out(row)


@router.get("/checkpoints/{checkpoint_id}", response_model=CheckpointResponse)
def get_checkpoint(checkpoint_id: str,
                   db: Session = Depends(get_db), _: object = Depends(require_roles("ADMIN", "OPERATOR"))) -> CheckpointResponse:
    row = db.scalar(select(Checkpoint).where(Checkpoint.checkpoint_id == checkpoint_id))
    if not row:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    return checkpoint_out(row)


@router.patch("/checkpoints/{checkpoint_id}", response_model=CheckpointResponse)
def update_checkpoint(checkpoint_id: str, payload: CheckpointUpdate,
                      db: Session = Depends(get_db), _: object = Depends(require_roles("ADMIN"))) -> CheckpointResponse:
    row = db.scalar(select(Checkpoint).where(Checkpoint.checkpoint_id == checkpoint_id))
    if not row:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return checkpoint_out(row)


@router.get("/officers", response_model=list[OfficerResponse])
def list_officers(db: Session = Depends(get_db), _: object = Depends(require_roles("ADMIN", "OPERATOR"))) -> list[OfficerResponse]:
    officers = list(db.scalars(select(PatrolOfficer).order_by(PatrolOfficer.officer_id)))
    stats = _officer_stats(db, [o.officer_id for o in officers])
    return [_off_out(o, stats.get(o.officer_id)) for o in officers]


@router.post("/officers", response_model=OfficerResponse,
             status_code=status.HTTP_201_CREATED)
def create_officer(payload: OfficerCreate,
                   db: Session = Depends(get_db), _: object = Depends(require_roles("ADMIN"))) -> OfficerResponse:
    if db.scalar(select(PatrolOfficer).where(PatrolOfficer.officer_id == payload.officer_id)):
        raise HTTPException(status_code=409, detail="Officer already exists")
    row = PatrolOfficer(officer_id=payload.officer_id, name=payload.name,
                        badge_number=payload.badge_number)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Officer already exists")
    db.refresh(row)
    return _off_out(row)