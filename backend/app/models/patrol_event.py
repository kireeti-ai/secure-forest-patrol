"""First-class patrol event.

Answers WHO / WHERE / WHEN / WHAT / IS IT AUTHENTIC / HAS IT SYNCHRONIZED.

``event_created_at`` is the node's battery-backed RTC timestamp and is
never overwritten by gateway/backend arrival times (``gateway_received_at``
/ ``backend_received_at`` are separate columns).

Idempotency key: (node_id, sequence). One logical persisted row per key.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import ChainStatus, EventSyncStatus, FingerprintResult, RfidResult, SignatureStatus
from app.models.guid import GUID


class PatrolEvent(Base):
    __tablename__ = "patrol_events"
    __table_args__ = (
        UniqueConstraint("node_id", "sequence", name="uq_patrol_events_node_sequence"),
        UniqueConstraint("event_id", name="uq_patrol_events_event_id"),
        Index("ix_patrol_events_checkpoint", "checkpoint_id"),
        Index("ix_patrol_events_officer", "officer_id"),
        Index("ix_patrol_events_created", "event_created_at"),
        Index("ix_patrol_events_sync", "sync_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    checkpoint_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    officer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, default="PATROL_EVENT")
    rfid_result: Mapped[str | None] = mapped_column(String(16), nullable=True, default=RfidResult.VALID.value)
    fingerprint_result: Mapped[str | None] = mapped_column(String(16), nullable=True, default=FingerprintResult.MATCH.value)
    event_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    gateway_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    backend_received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    previous_hash: Mapped[str] = mapped_column(String(128), nullable=False, default="GENESIS")
    record_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    signature: Mapped[str] = mapped_column(String(2048), nullable=False)
    signature_status: Mapped[str] = mapped_column(String(16), nullable=False, default=SignatureStatus.PENDING.value)
    chain_status: Mapped[str] = mapped_column(String(16), nullable=False, default=ChainStatus.PENDING.value)
    sync_status: Mapped[str] = mapped_column(String(16), nullable=False, default=EventSyncStatus.SYNCED.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
