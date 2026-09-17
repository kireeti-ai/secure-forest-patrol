"""Acoustic event (TinyML inference + human review).

``classification`` is an ML inference, never ground truth. Operational
truth is the separate ``review_status`` workflow:

DETECTED -> PENDING_REVIEW -> REVIEWED -> CONFIRMED / DISMISSED
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import (
    AcousticReviewStatus,
    ChainStatus,
    EventSyncStatus,
    SignatureStatus,
)
from app.models.guid import GUID


class AcousticEvent(Base):
    __tablename__ = "acoustic_events"
    __table_args__ = (
        UniqueConstraint("node_id", "sequence", name="uq_acoustic_events_node_sequence"),
        UniqueConstraint("event_id", name="uq_acoustic_events_event_id"),
        Index("ix_acoustic_events_checkpoint", "checkpoint_id"),
        Index("ix_acoustic_events_review", "review_status"),
        Index("ix_acoustic_events_created", "event_created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    checkpoint_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    zone_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    classification: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    previous_hash: Mapped[str] = mapped_column(String(128), nullable=False, default="GENESIS")
    record_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    signature: Mapped[str] = mapped_column(String(2048), nullable=False)
    signature_status: Mapped[str] = mapped_column(String(16), nullable=False, default=SignatureStatus.PENDING.value)
    chain_status: Mapped[str] = mapped_column(String(16), nullable=False, default=ChainStatus.PENDING.value)
    sync_status: Mapped[str] = mapped_column(String(16), nullable=False, default=EventSyncStatus.SYNCED.value)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default=AcousticReviewStatus.PENDING_REVIEW.value)
    gateway_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    backend_received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
