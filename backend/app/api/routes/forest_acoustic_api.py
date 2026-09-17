"""Forest acoustic routers (classification is inference, not ground truth).

No authentication: see ``docs/BACKEND.md``.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.database import get_db
from app.models.acoustic_event import AcousticEvent
from app.schemas.forest import AcousticResponse, AcousticReviewUpdate

router = APIRouter(prefix="/api/forest", tags=["forest"])


def acoustic_out(e: AcousticEvent) -> AcousticResponse:
    return AcousticResponse(
        id=str(e.id), event_id=e.event_id, node_id=e.node_id,
        checkpoint_id=e.checkpoint_id, zone_id=e.zone_id, sequence=e.sequence,
        event_created_at=e.event_created_at, classification=e.classification,
        confidence=e.confidence, model_version=e.model_version,
        previous_hash=e.previous_hash, record_hash=e.record_hash,
        signature_status=e.signature_status, chain_status=e.chain_status,
        sync_status=e.sync_status, review_status=e.review_status,
        gateway_received_at=e.gateway_received_at,
        backend_received_at=e.backend_received_at, created_at=e.created_at,
        reviewed_at=e.reviewed_at)


@router.get("/acoustic-events", response_model=list[AcousticResponse])
def list_acoustic(review_status: str | None = Query(default=None),
                  limit: int = Query(default=200, le=1000),
                  db: Session = Depends(get_db)) -> list[AcousticResponse]:
    stmt = select(AcousticEvent).order_by(
        AcousticEvent.event_created_at.desc()).limit(limit)
    if review_status:
        stmt = stmt.where(AcousticEvent.review_status == review_status)
    return [acoustic_out(e) for e in db.scalars(stmt)]


@router.get("/acoustic-events/{event_id}", response_model=AcousticResponse)
def get_acoustic(event_id: str, db: Session = Depends(get_db)) -> AcousticResponse:
    row = db.scalar(select(AcousticEvent).where(AcousticEvent.event_id == event_id))
    if not row:
        raise HTTPException(status_code=404, detail="Acoustic event not found")
    return acoustic_out(row)


@router.post("/acoustic-events/{event_id}/review", response_model=AcousticResponse)
def review_acoustic(event_id: str, payload: AcousticReviewUpdate,
                    db: Session = Depends(get_db)) -> AcousticResponse:
    """Move an ML detection through the human review workflow.

    ``review_status`` is the operational truth; the ML ``classification`` on
    the row is never overwritten by this transition.
    """
    row = db.scalar(select(AcousticEvent).where(AcousticEvent.event_id == event_id))
    if not row:
        raise HTTPException(status_code=404, detail="Acoustic event not found")
    row.review_status = payload.review_status
    row.reviewed_at = datetime.now(timezone.utc)
    row.reviewed_by = payload.reviewed_by or "OPERATIONS"
    db.commit()
    db.refresh(row)
    return acoustic_out(row)