"""Patrol officer registry.

Only identity metadata is stored. The reference architecture matches
fingerprints locally on the field node and transmits MATCH/NO_MATCH —
raw biometric templates are never sent to or stored by the backend.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import OfficerStatus
from app.models.guid import GUID


class PatrolOfficer(Base):
    __tablename__ = "patrol_officers"
    __table_args__ = (
        UniqueConstraint("officer_id", name="uq_patrol_officers_officer_id"),
        Index("ix_patrol_officers_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    officer_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    badge_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=OfficerStatus.ACTIVE.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
