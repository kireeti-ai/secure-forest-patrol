"""Forest ledger / gateway / sync-history routers.

Every value returned here is computed from persisted rows. Nothing is
hardcoded and nothing is fabricated.

No authentication: see ``docs/BACKEND.md``.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.database import get_db
from app.core.security import require_roles
from app.models.acoustic_event import AcousticEvent
from app.models.forest_gateway import Gateway
from app.models.patrol_event import PatrolEvent
from app.models.sync_record import SyncRecord
from app.services.forest_gateway_svc import gateway_online
from app.schemas.forest import GatewayResponse, LedgerResponse, SyncRecordResponse

router = APIRouter(prefix="/api/forest", tags=["forest"])


def gateway_out(g: Gateway) -> GatewayResponse:
    online = gateway_online(g)
    # Link states are the gateway's last report and only meaningful while it is
    # still reporting; once it goes quiet they read as down, not as stale "OK".
    return GatewayResponse(
        id=str(g.id), gateway_id=g.gateway_id, name=g.name, status=g.status, online=online,
        lora_status=g.lora_status if online else "NO_TRAFFIC",
        wifi_status=g.wifi_status if online else "DISCONNECTED",
        backend_status=g.backend_status if online else "UNREACHABLE",
        firmware_version=g.firmware_version,
        records_received=g.records_received or 0,
        records_forwarded=g.records_forwarded or 0,
        records_pending=g.records_pending or 0,
        last_seen_at=g.last_seen_at,
        last_successful_sync_at=g.last_successful_sync_at,
        pending_sync_queue=g.records_pending or 0)


@router.get("/ledger", response_model=list[LedgerResponse])
def list_ledger(node_id: str | None = Query(default=None),
                limit: int = Query(default=500, le=2000),
                db: Session = Depends(get_db), _: object = Depends(require_roles("ADMIN", "OPERATOR"))) -> list[LedgerResponse]:
    """Per-node hash-chain view across both event kinds (chain order preserved)."""
    out: list[LedgerResponse] = []
    p_stmt = select(PatrolEvent).order_by(PatrolEvent.node_id, PatrolEvent.sequence).limit(limit)
    a_stmt = select(AcousticEvent).order_by(AcousticEvent.node_id, AcousticEvent.sequence).limit(limit)
    if node_id:
        p_stmt = p_stmt.where(PatrolEvent.node_id == node_id)
        a_stmt = a_stmt.where(AcousticEvent.node_id == node_id)
    for e in db.scalars(p_stmt):
        out.append(LedgerResponse(
            event_kind="PATROL_EVENT", event_id=e.event_id, node_id=e.node_id,
            sequence=e.sequence, event_created_at=e.event_created_at,
            previous_hash=e.previous_hash, record_hash=e.record_hash,
            signature_status=e.signature_status, chain_status=e.chain_status,
            sync_status=e.sync_status, signature=e.signature))
    for e in db.scalars(a_stmt):
        out.append(LedgerResponse(
            event_kind="ACOUSTIC_EVENT", event_id=e.event_id, node_id=e.node_id,
            sequence=e.sequence, event_created_at=e.event_created_at,
            previous_hash=e.previous_hash, record_hash=e.record_hash,
            signature_status=e.signature_status, chain_status=e.chain_status,
            sync_status=e.sync_status, signature=e.signature))
    out.sort(key=lambda r: (r.node_id, r.sequence))
    return out[:limit]


@router.get("/gateways", response_model=list[GatewayResponse])
def list_gateways(db: Session = Depends(get_db), _: object = Depends(require_roles("ADMIN", "OPERATOR"))) -> list[GatewayResponse]:
    return [gateway_out(g) for g in db.scalars(select(Gateway).order_by(Gateway.gateway_id))]


@router.get("/gateways/{gateway_id}", response_model=GatewayResponse)
def get_gateway(gateway_id: str, db: Session = Depends(get_db), _: object = Depends(require_roles("ADMIN", "OPERATOR"))) -> GatewayResponse:
    row = db.scalar(select(Gateway).where(Gateway.gateway_id == gateway_id))
    if not row:
        raise HTTPException(status_code=404, detail="Gateway not found")
    return gateway_out(row)


_VERIFICATION_BY_SYNC_STATUS = {"VERIFIED": "PASSED", "FAILED": "FAILED"}


@router.get("/sync-history", response_model=list[SyncRecordResponse])
def list_sync(limit: int = Query(default=200, le=1000),
              db: Session = Depends(get_db), _: object = Depends(require_roles("ADMIN", "OPERATOR"))) -> list[SyncRecordResponse]:
    rows = db.scalars(select(SyncRecord).order_by(SyncRecord.created_at.desc()).limit(limit))
    return [SyncRecordResponse(
        id=str(r.id), sync_id=r.sync_id, event_id=r.event_id, node_id=r.node_id,
        gateway_id=r.gateway_id, received_at=r.received_at,
        forwarded_at=r.forwarded_at, attempt_count=r.attempt_count,
        sync_status=r.sync_status, failure_reason=r.failure_reason,
        created_at=r.created_at, updated_at=r.updated_at,
        event_timestamp=r.received_at,
        duplicate_state="DUPLICATE" if r.sync_status == "DUPLICATE" else "UNIQUE",
        verification_result=_VERIFICATION_BY_SYNC_STATUS.get(r.sync_status),
    ) for r in rows]