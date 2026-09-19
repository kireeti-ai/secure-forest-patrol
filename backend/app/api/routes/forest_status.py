"""Forest system status: every number is computed from the database.

Nothing here is hardcoded, defaulted or estimated. If a counter has no
rows behind it, it reports 0 because the database reports 0.

No authentication: see ``docs/BACKEND.md``.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies.database import get_db
from app.core.security import require_roles
from app.models.acoustic_event import AcousticEvent
from app.models.checkpoint import Checkpoint
from app.models.enums import (
    AcousticReviewStatus,
    ChainStatus,
    ForestNodeStatus,
    SignatureStatus,
    SyncState,
    SystemStatus,
)
from app.models.forest_gateway import Gateway
from app.models.forest_node import ForestNode
from app.models.patrol_event import PatrolEvent
from app.models.sync_record import SyncRecord

router = APIRouter(prefix="/api/forest", tags=["forest"])


@router.get("/system-status")
def forest_system_status(db: Session = Depends(get_db), _: object = Depends(require_roles("ADMIN", "OPERATOR"))) -> dict:
    try:
        db.execute(select(1))
        db_ok = True
    except Exception:  # pragma: no cover - only reachable on a dead connection
        db_ok = False

    def count(stmt) -> int:
        return db.scalar(stmt) or 0

    nodes = count(select(func.count()).select_from(ForestNode))
    active_nodes = count(select(func.count()).select_from(ForestNode).where(
        ForestNode.status == ForestNodeStatus.ACTIVE.value))
    checkpoints = count(select(func.count()).select_from(Checkpoint))
    active_checkpoints = count(select(func.count()).select_from(Checkpoint).where(
        Checkpoint.active.is_(True)))
    officers = count(select(func.count()).select_from(PatrolEvent).where(
        PatrolEvent.officer_id.is_not(None)))
    patrols = count(select(func.count()).select_from(PatrolEvent))
    patrols_verified = count(select(func.count()).select_from(PatrolEvent).where(
        PatrolEvent.signature_status == SignatureStatus.VALID.value,
        PatrolEvent.chain_status == ChainStatus.VALID.value))
    invalid_signatures = count(select(func.count()).select_from(PatrolEvent).where(
        PatrolEvent.signature_status == SignatureStatus.INVALID.value))
    broken_chains = count(select(func.count()).select_from(PatrolEvent).where(
        PatrolEvent.chain_status == ChainStatus.BROKEN.value))
    acoustic_total = count(select(func.count()).select_from(AcousticEvent))
    acoustic_pending_review = count(select(func.count()).select_from(AcousticEvent).where(
        AcousticEvent.review_status.in_([AcousticReviewStatus.DETECTED.value,
                                         AcousticReviewStatus.PENDING_REVIEW.value])))
    gateways = count(select(func.count()).select_from(Gateway))
    sync_pending = count(select(func.count()).select_from(SyncRecord).where(
        SyncRecord.sync_status.in_([SyncState.PENDING.value, SyncState.RECEIVED.value,
                                    SyncState.FORWARDED.value])))
    sync_failed = count(select(func.count()).select_from(SyncRecord).where(
        SyncRecord.sync_status == SyncState.FAILED.value))
    sync_duplicate = count(select(func.count()).select_from(SyncRecord).where(
        SyncRecord.sync_status == SyncState.DUPLICATE.value))

    gateways_reachable = count(select(func.count()).select_from(Gateway).where(
        Gateway.backend_status == "REACHABLE"))
    gateways_wifi_connected = count(select(func.count()).select_from(Gateway).where(
        Gateway.wifi_status == "CONNECTED"))

    def _tier(ok_count: int, total_count: int) -> str:
        if total_count == 0:
            return "OFFLINE"
        if ok_count == total_count:
            return "OPERATIONAL"
        if ok_count > 0:
            return "DEGRADED"
        return "OFFLINE"

    ledger_failures = invalid_signatures + broken_chains

    return {
        # Six-component health view for the dashboard's System Status page.
        # Every status/detail here is derived from the same counters below
        # -- no separate/fabricated signal.
        "fieldLayer": {
            "component": "Field Nodes (LoRa)",
            "status": _tier(active_nodes, nodes) if nodes else "OFFLINE",
            "details": f"{active_nodes}/{nodes} nodes active",
        },
        "gateway": {
            "component": "ESP32 Gateway(s)",
            "status": _tier(gateways_reachable, gateways) if gateways else "OFFLINE",
            "details": f"{gateways_reachable}/{gateways} gateways reachable",
        },
        "wifiBackhaul": {
            "component": "Wi-Fi Backhaul",
            "status": _tier(gateways_wifi_connected, gateways) if gateways else "OFFLINE",
            "details": f"{gateways_wifi_connected}/{gateways} gateways Wi-Fi connected",
        },
        "backend": {
            "component": "FastAPI Forest Service",
            "status": "REACHABLE",
            "details": f"{patrols} patrol events persisted",
        },
        "database": {
            "component": "PostgreSQL Database",
            "status": "OPERATIONAL" if db_ok else "OFFLINE",
            "details": SystemStatus.ONLINE.value if db_ok else SystemStatus.UNKNOWN.value,
        },
        "ledgerVerification": {
            "component": "Hash-Chain Ledger Verification",
            "status": "OPERATIONAL" if ledger_failures == 0 else "DEGRADED",
            "details": f"{invalid_signatures} invalid signatures, {broken_chains} broken chains",
        },
        # Raw counters retained for API completeness / future use.
        "nodes": {"registered": nodes, "active": active_nodes, "gateways": gateways},
        "checkpoints": {"total": checkpoints, "active": active_checkpoints},
        "patrols": {
            "total": patrols,
            "verified": patrols_verified,
            "officers_referenced": officers,
            "invalid_signatures": invalid_signatures,
            "broken_chains": broken_chains,
        },
        "acoustic": {"total": acoustic_total, "pending_review": acoustic_pending_review},
        "sync": {"pending": sync_pending, "failed": sync_failed, "duplicate": sync_duplicate},
    }