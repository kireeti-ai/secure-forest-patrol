"""LoRa gateway registry.

Network states are kept separate: LoRa activity vs Wi-Fi backhaul vs
backend reachability. They must not collapse into one "ONLINE" flag.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.guid import GUID


class Gateway(Base):
    __tablename__ = "gateways"
    __table_args__ = (
        UniqueConstraint("gateway_id", name="uq_gateways_gateway_id"),
        Index("ix_gateways_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    gateway_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    lora_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    wifi_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    backend_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    firmware_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    records_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_forwarded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_pending: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
