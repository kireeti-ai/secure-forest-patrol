"""Forest core routers: nodes / checkpoints.

The forest backend serves an internal operations network and has NO
authentication layer: there is no login, no user accounts and no RBAC.
Requests are therefore not filtered by identity. See ``docs/BACKEND.md``
for the explicit rationale and the deployment consequence.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies.database import get_db
from app.core.security import require_roles
from app.models.checkpoint import Checkpoint
from app.models.forest_node import ForestNode
from app.schemas.forest import (
    CheckpointCreate,
    CheckpointResponse,
    CheckpointUpdate,
    NodeCreate,
    NodeResponse,
    NodeUpdate,
)

router = APIRouter(prefix="/api/forest", tags=["forest"])


def node_out(n: ForestNode) -> NodeResponse:
    return NodeResponse(id=str(n.id), node_id=n.node_id, node_type=n.node_type,
                        checkpoint_id=n.checkpoint_id, zone_id=n.zone_id, status=n.status,
                        firmware_version=n.firmware_version, has_public_key=bool(n.public_key),
                        installed_at=n.installed_at, last_seen_at=n.last_seen_at,
                        created_at=n.created_at, updated_at=n.updated_at,
                        last_event_time=n.last_seen_at)


def checkpoint_out(c: Checkpoint) -> CheckpointResponse:
    return CheckpointResponse(
        id=str(c.id), checkpoint_id=c.checkpoint_id, name=c.name, zone_id=c.zone_id,
        latitude=float(c.latitude) if c.latitude is not None else None,
        longitude=float(c.longitude) if c.longitude is not None else None,
        node_id=c.node_id, active=c.active,
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
    return [checkpoint_out(c) for c in db.scalars(
        select(Checkpoint).order_by(Checkpoint.checkpoint_id))]
