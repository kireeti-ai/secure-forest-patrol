"""Gateway -> backend forest ingestion router (Wi-Fi/HTTPS backhaul).

The Gateway bridges the LoRa field network to IP: it extracts events off the
LoRa link and POSTs them here over Wi-Fi/GSM. This backend therefore only
ever sees an HTTP request — it never receives raw RF.

There is NO authentication on these routes (see ``docs/BACKEND.md``). The
Gateway contract is documented in ``docs/GATEWAY_BACKEND_CONTRACT.md``.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies.database import get_db
from app.schemas.forest_ingest import (
    ForestAcousticIngest,
    ForestPatrolIngest,
    GatewayStatusReport,
    IngestResult,
    RfidScanIngest,
)
from app.services.forest_acoustic import ingest_acoustic_event
from app.services.forest_gateway_svc import report_gateway_status
from app.services.forest_patrol import UnknownNodeError, ingest_patrol_event
from app.services.ws_manager import broadcast_acoustic_outcome, broadcast_gateway_status, broadcast_patrol_outcome, broadcast_rfid_scan

router = APIRouter(prefix="/api/ingest/gateway", tags=["gateway-ingestion"])


@router.post("/forest-event", response_model=IngestResult)
def ingest_forest_event(payload: ForestPatrolIngest,
                        db: Session = Depends(get_db)):
    """Accept a patrol event from a Gateway.

    Outcomes: ``ACCEPTED`` (201), ``DUPLICATE`` (200), ``INVALID_SIGNATURE``
    (202), ``BROKEN_CHAIN`` (202). Validation failures are rejected with the
    normal FastAPI 422; an unregistered node returns 404 ``UNKNOWN_NODE``.
    """
    try:
        body, http_status = ingest_patrol_event(db, payload)
    except UnknownNodeError as exc:
        return JSONResponse(status_code=404, content={"outcome": "UNKNOWN_NODE",
                                                      "duplicate": False, "detail": str(exc)})
    broadcast_patrol_outcome(body, payload.node_id, payload.checkpoint_id)
    return JSONResponse(status_code=http_status, content=body)


@router.post("/acoustic-event", response_model=IngestResult)
def ingest_acoustic(payload: ForestAcousticIngest,
                    db: Session = Depends(get_db)):
    """Accept an acoustic (TinyML) event from a Gateway.

    Ingestion records the detection only. It never marks a detection as
    confirmed: the row enters the human review workflow at
    ``review_status = PENDING_REVIEW``.
    """
    try:
        body, http_status = ingest_acoustic_event(db, payload)
    except UnknownNodeError as exc:
        return JSONResponse(status_code=404, content={"outcome": "UNKNOWN_NODE",
                                                      "duplicate": False, "detail": str(exc)})
    broadcast_acoustic_outcome(body, payload.node_id, payload.checkpoint_id)
    return JSONResponse(status_code=http_status, content=body)


@router.post("/status", response_model=dict)
def gateway_status(payload: GatewayStatusReport,
                   db: Session = Depends(get_db)):
    """Gateway health/heartbeat. Network states stay separate (LoRa/Wi-Fi/backend)."""
    result = report_gateway_status(db, payload)
    broadcast_gateway_status(result["gateway_id"])
    return result

@router.post("/rfid-scan", response_model=IngestResult)
def ingest_rfid_scan(payload: RfidScanIngest):
    """Accept an RFID scan from a Gateway."""
    broadcast_rfid_scan(payload.dict())
    return JSONResponse(status_code=202, content={"outcome": "ACCEPTED"})