import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.guid import GUID


class RfidEvent(Base):
    __tablename__ = "rfid_events"
    # Not unique: a node's sequence counter restarts at 0 on every reboot, so
    # (node_id, sequence) legitimately repeats. Retries are recognised in
    # services/rfid.py by (node, sequence, uid) within a short time window.
    __table_args__ = (Index("ix_rfid_events_node_sequence", "node_id", "sequence"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    rfid_uid: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    employee_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, default="RFID_SCAN")
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    rssi: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snr: Mapped[float | None] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("employee_id", "attendance_date", name="uq_attendance_employee_day"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    entry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    exit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
