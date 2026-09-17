"""Synchronization tracking (offline-first DTN bookkeeping).

EVENT VALIDITY (signature/chain on the event row) is distinct from SYNC
STATE (transport bookkeeping here). One row per (event_id, gateway_id)
delivery attempt aggregate; retries bump ``attempt_count``.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import SyncState
from app.models.guid import GUID


class SyncRecord(Base):
    __tablename__ = "sync_records"
    __table_args__ = (
        UniqueConstraint("event_id", "gateway_id", name="uq_sync_records_event_gateway"),
        Index("ix_sync_records_node", "node_id"),
        Index("ix_sync_records_status", "sync_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    sync_id: Mapped[str] = mapped_column(String(64), nullable=False, default=lambda: uuid.uuid4().hex[:16])
    event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    gateway_id: Mapped[str] = mapped_column(String(64), nullable=False)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    forwarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    sync_status: Mapped[str] = mapped_column(String(16), nullable=False, default=SyncState.RECEIVED.value)
    failure_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
