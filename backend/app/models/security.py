"""

Audit trail only. Operator identity is intentionally NOT authenticated by this
backend: there is no login, no user account table and no RBAC. ``actor_id`` is
therefore an optional free-form reference supplied by the caller and is
deliberately not a foreign key, so the audit trail never depends on an
identity subsystem that does not exist.

The audit trail records WHAT changed and WHEN, which is what the forest
verification objective actually requires.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.guid import GUID


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_created_at", "created_at"), Index("ix_audit_logs_actor_id", "actor_id"))

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    target_type: Mapped[str] = mapped_column(String, nullable=False)
    target_id: Mapped[str | None] = mapped_column(String, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
