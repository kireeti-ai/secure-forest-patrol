"""Forest field-node registry.

Fixed installed nodes (checkpoint scanners / acoustic sensors).
The node's configured checkpoint comes from the manifest columns
(``checkpoint_id`` / ``zone_id``). ``public_key`` holds the device's
ECC secp256r1 public key (PEM or raw hex). Device private keys are
NEVER stored in this database.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import ForestNodeStatus, ForestNodeType
from app.models.guid import GUID


class ForestNode(Base):
    __tablename__ = "forest_nodes"
    __table_args__ = (
        UniqueConstraint("node_id", name="uq_forest_nodes_node_id"),
        Index("ix_forest_nodes_status", "status"),
        Index("ix_forest_nodes_checkpoint", "checkpoint_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    node_type: Mapped[str] = mapped_column(String(32), nullable=False, default=ForestNodeType.CHECKPOINT_NODE.value)
    checkpoint_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    zone_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=ForestNodeStatus.ACTIVE.value)
    firmware_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    public_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    installed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
