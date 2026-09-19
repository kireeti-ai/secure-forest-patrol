"""Forest patrol query routers.

No authentication: see ``docs/BACKEND.md``.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.database import get_db
from app.core.security import require_roles
from app.models.officer import PatrolOfficer
from app.models.patrol_event import PatrolEvent
from app.schemas.forest import PatrolResponse

router = APIRouter(prefix="/api/forest", tags=["forest"])


def _record_status(signature_status: str, chain_status: str) -> str | None:
    if signature_status == "INVALID":
        return "TAMPERED"
    if chain_status == "BROKEN":
        return "SUSPECTED"
    if signature_status == "VALID" and chain_status == "VALID":
        return "AUTHENTIC"
    return None


def patrol_out(e: PatrolEvent, officer_name: str | None = None) -> PatrolResponse:
    return PatrolResponse(
        id=str(e.id), event_id=e.event_id, node_id=e.node_id,
        checkpoint_id=e.checkpoint_id, officer_id=e.officer_id,
        sequence=e.sequence, event_type=e.event_type,
        rfid_result=e.rfid_result, fingerprint_result=e.fingerprint_result,
        event_created_at=e.event_created_at, gateway_received_at=e.gateway_received_at,
        backend_received_at=e.backend_received_at, previous_hash=e.previous_hash,
        record_hash=e.record_hash, signature_status=e.signature_status,
        chain_status=e.chain_status, sync_status=e.sync_status,
        created_at=e.created_at, verified_at=e.verified_at,
        officer_name=officer_name,
        record_status=_record_status(e.signature_status, e.chain_status))


def _officer_names(db: Session, officer_ids: set[str]) -> dict[str, str]:
    if not officer_ids:
        return {}
    rows = db.scalars(select(PatrolOfficer).where(PatrolOfficer.officer_id.in_(officer_ids)))
    return {o.officer_id: o.name for o in rows}


@router.get("/patrols", response_model=list[PatrolResponse])
def list_patrols(node_id: str | None = Query(default=None),
                 checkpoint_id: str | None = Query(default=None),
                 limit: int = Query(default=200, le=1000),
                 db: Session = Depends(get_db), _: object = Depends(require_roles("ADMIN", "OPERATOR"))) -> list[PatrolResponse]:
    stmt = select(PatrolEvent).order_by(
        PatrolEvent.event_created_at.desc()).limit(limit)
    if node_id:
        stmt = stmt.where(PatrolEvent.node_id == node_id)
    if checkpoint_id:
        stmt = stmt.where(PatrolEvent.checkpoint_id == checkpoint_id)
    rows = list(db.scalars(stmt))
    names = _officer_names(db, {r.officer_id for r in rows if r.officer_id})
    return [patrol_out(e, names.get(e.officer_id)) for e in rows]


@router.get("/patrols/{event_id}", response_model=PatrolResponse)
def get_patrol(event_id: str, db: Session = Depends(get_db), _: object = Depends(require_roles("ADMIN", "OPERATOR"))) -> PatrolResponse:
    row = db.scalar(select(PatrolEvent).where(PatrolEvent.event_id == event_id))
    if not row:
        raise HTTPException(status_code=404, detail="Patrol event not found")
    names = _officer_names(db, {row.officer_id} if row.officer_id else set())
    return patrol_out(row, names.get(row.officer_id))