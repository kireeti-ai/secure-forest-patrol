"""Forest core routers: nodes / checkpoints.

The forest backend serves an internal operations network and has NO
authentication layer: there is no login, no user accounts and no RBAC.
Requests are therefore not filtered by identity. See ``docs/BACKEND.md``
for the explicit rationale and the deployment consequence.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies.database import get_db
from app.core.security import require_roles
from app.models.checkpoint import Checkpoint
from app.models.forest_node import ForestNode
from app.models.patrol_event import PatrolEvent
from app.models.rfid import RfidEvent
from app.schemas.forest import (
    CheckpointCreate,
    CheckpointResponse,
    CheckpointUpdate,
    NodeCreate,
    NodeResponse,
    NodeUpdate,
)

router = APIRouter(prefix="/api/forest", tags=["forest"])


def record_status(signature_status: str, chain_status: str, rfid_result: str, fingerprint_result: str) -> str | None:
    """Shared crypto+identity verdict for one record -- used both per-patrol-event
    (forest_patrol_api.py) and rolled up per-checkpoint (checkpoint_verification_states below)."""
    if signature_status == "INVALID":
        return "TAMPERED"
    if chain_status == "BROKEN":
        return "SUSPECTED"
    # Crypto proof (signature/chain) being intact says the record wasn't forged in transit -- it
    # says nothing about who presented the card/finger. A failed identity check must not be
    # reported as AUTHENTIC just because the bytes are unforged; see forest_checkpoints.py's
    # _officer_stats(), which already treats this combination as a mismatch for attendance stats.
    if rfid_result == "INVALID" or fingerprint_result == "NO_MATCH":
        return "MISMATCH"
    if signature_status == "VALID" and chain_status == "VALID":
        return "AUTHENTIC"
    return None


def node_out(n: ForestNode) -> NodeResponse:
    return NodeResponse(id=str(n.id), node_id=n.node_id, node_type=n.node_type,
                        checkpoint_id=n.checkpoint_id, zone_id=n.zone_id, status=n.status,
                        firmware_version=n.firmware_version, has_public_key=bool(n.public_key),
                        installed_at=n.installed_at, last_seen_at=n.last_seen_at,
                        created_at=n.created_at, updated_at=n.updated_at,
                        last_event_time=n.last_seen_at)


# The node firmware only transmits when a card is scanned (there is no
# periodic heartbeat yet), so "online" means "heard from within this window".
NODE_ONLINE_WINDOW = timedelta(minutes=15)


def checkpoint_states(db: Session, checkpoints: list[Checkpoint]) -> dict[str, tuple[str, datetime | None]]:
    """Map checkpoint_id -> (state, last activity) from the attached node.

    A checkpoint with no node, or an inactive checkpoint, is OFFLINE. Activity is
    the newest of the node's last_seen_at and its latest RFID scan.
    """
    node_ids = [c.node_id for c in checkpoints if c.node_id]
    seen = {n.node_id: n.last_seen_at for n in db.scalars(select(ForestNode).where(ForestNode.node_id.in_(node_ids)))} if node_ids else {}
    scans = {nid: ts for nid, ts in db.execute(
        select(RfidEvent.node_id, func.max(RfidEvent.timestamp))
        .where(RfidEvent.node_id.in_(node_ids)).group_by(RfidEvent.node_id))} if node_ids else {}
    now = datetime.now(timezone.utc)
    result: dict[str, tuple[str, datetime | None]] = {}
    for c in checkpoints:
        candidates = [t for t in (seen.get(c.node_id), scans.get(c.node_id)) if t is not None]
        last = max(candidates) if candidates else None
        if last is not None and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        online = bool(c.active and c.node_id and last and now - last <= NODE_ONLINE_WINDOW)
        result[c.checkpoint_id] = ("ONLINE" if online else "OFFLINE", last)
    return result


def checkpoint_verification_states(db: Session, checkpoints: list[Checkpoint]) -> dict[str, str | None]:
    """Map checkpoint_id -> record_status() of that checkpoint's most recent patrol event.

    No patrol events yet for a checkpoint -> None (honest "nothing to verify yet", not a
    fabricated PENDING). Mirrors checkpoint_states()'s per-checkpoint latest-record pattern
    and _officer_stats()'s (forest_checkpoints.py) use of the same signature/chain/rfid/
    fingerprint fields, just rolled up per checkpoint instead of per officer.
    """
    result: dict[str, str | None] = {}
    for c in checkpoints:
        latest = db.scalar(select(PatrolEvent).where(PatrolEvent.checkpoint_id == c.checkpoint_id)
                           .order_by(PatrolEvent.event_created_at.desc()).limit(1))
        result[c.checkpoint_id] = (record_status(latest.signature_status, latest.chain_status,
                                                 latest.rfid_result, latest.fingerprint_result)
                                   if latest is not None else None)
    return result


def checkpoint_out(c: Checkpoint, state: str = "OFFLINE", last_patrol_at: datetime | None = None,
                   verification_state: str | None = None) -> CheckpointResponse:
    return CheckpointResponse(
        id=str(c.id), checkpoint_id=c.checkpoint_id, name=c.name, zone_id=c.zone_id,
        latitude=float(c.latitude) if c.latitude is not None else None,
        longitude=float(c.longitude) if c.longitude is not None else None,
        node_id=c.node_id, active=c.active, state=state, last_patrol_at=last_patrol_at,
        verification_state=verification_state,
        created_at=c.created_at, updated_at=c.updated_at)


@router.get("/nodes", response_model=list[NodeResponse])
def list_nodes(db: Session = Depends(get_db), _: object = Depends(require_roles("ADMIN", "OPERATOR"))) -> list[NodeResponse]:
    return [node_out(n) for n in db.scalars(
        select(ForestNode).order_by(ForestNode.node_id))]


@router.post("/nodes", response_model=NodeResponse, status_code=status.HTTP_201_CREATED)
def create_node(payload: NodeCreate, db: Session = Depends(get_db), _: object = Depends(require_roles("ADMIN"))) -> NodeResponse:
    """Register a field node and its ECC public key (the signature trust anchor).

    Registering ``public_key`` provisions signature verification for that
    node. Until a key is registered, ingested events for the node are
    recorded with ``signature_status = PENDING`` — never claimed as valid.
    """
    if db.scalar(select(ForestNode).where(ForestNode.node_id == payload.node_id)):
        raise HTTPException(status_code=409, detail=f"Node '{payload.node_id}' already exists")
    node = ForestNode(node_id=payload.node_id, node_type=payload.node_type,
                      checkpoint_id=payload.checkpoint_id, zone_id=payload.zone_id,
                      firmware_version=payload.firmware_version, public_key=payload.public_key)
    db.add(node)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Node already exists")
    db.refresh(node)
    return node_out(node)


@router.get("/nodes/{node_id}", response_model=NodeResponse)
def get_node(node_id: str, db: Session = Depends(get_db), _: object = Depends(require_roles("ADMIN", "OPERATOR"))) -> NodeResponse:
    node = db.scalar(select(ForestNode).where(ForestNode.node_id == node_id))
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")
    return node_out(node)


@router.patch("/nodes/{node_id}", response_model=NodeResponse)
def update_node(node_id: str, payload: NodeUpdate,
                db: Session = Depends(get_db), _: object = Depends(require_roles("ADMIN"))) -> NodeResponse:
    """Update node metadata / rotate the registered public key."""
    node = db.scalar(select(ForestNode).where(ForestNode.node_id == node_id))
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(node, k, v)
    node.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(node)
    return node_out(node)


@router.get("/checkpoints", response_model=list[CheckpointResponse])
def list_checkpoints(db: Session = Depends(get_db), _: object = Depends(require_roles("ADMIN", "OPERATOR"))) -> list[CheckpointResponse]:
    rows = list(db.scalars(select(Checkpoint).order_by(Checkpoint.checkpoint_id)))
    states = checkpoint_states(db, rows)
    verification_states = checkpoint_verification_states(db, rows)
    return [checkpoint_out(c, *states[c.checkpoint_id], verification_states[c.checkpoint_id]) for c in rows]
