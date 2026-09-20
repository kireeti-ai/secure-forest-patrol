"""Gateway status bookkeeping (separate LoRa / Wi-Fi / backend states)."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.forest_gateway import Gateway
from app.schemas.forest_ingest import GatewayStatusReport


# The gateway reports every 30 s; treat it as offline after three missed reports.
GATEWAY_ONLINE_WINDOW = timedelta(seconds=90)


def gateway_online(gateway: Gateway, now: datetime | None = None) -> bool:
    """A stored 'REACHABLE'/'CONNECTED' status is only its last report, not a live
    signal. The gateway counts as online only while it keeps reporting."""
    seen = gateway.last_seen_at
    if seen is None:
        return False
    if seen.tzinfo is None:
        seen = seen.replace(tzinfo=timezone.utc)
    return (now or datetime.now(timezone.utc)) - seen <= GATEWAY_ONLINE_WINDOW


def report_gateway_status(db: Session, payload: GatewayStatusReport) -> dict:
    now = datetime.now(timezone.utc)
    gateway = db.scalar(select(Gateway).where(Gateway.gateway_id == payload.gateway_id))
    if gateway is None:
        gateway = Gateway(gateway_id=payload.gateway_id, name=payload.name or payload.gateway_id)
        db.add(gateway)
        db.flush()
    if payload.name is not None:
        gateway.name = payload.name
    if payload.lora_status is not None:
        gateway.lora_status = payload.lora_status
    if payload.wifi_status is not None:
        gateway.wifi_status = payload.wifi_status
    if payload.backend_status is not None:
        gateway.backend_status = payload.backend_status
    if payload.firmware_version is not None:
        gateway.firmware_version = payload.firmware_version
    if payload.records_received is not None:
        gateway.records_received = payload.records_received
    if payload.records_forwarded is not None:
        gateway.records_forwarded = payload.records_forwarded
    if payload.records_pending is not None:
        gateway.records_pending = payload.records_pending
    gateway.last_seen_at = now
    gateway.last_successful_sync_at = now
    db.commit()
    db.refresh(gateway)
    return {"gateway_id": gateway.gateway_id, "last_seen_at": now.isoformat()}
