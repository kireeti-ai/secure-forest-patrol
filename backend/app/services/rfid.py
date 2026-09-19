from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rfid import Attendance, RfidEvent
from app.models.user import User
from app.schemas.forest_ingest import RfidScanIngest


def ingest_rfid_scan(db: Session, payload: RfidScanIngest) -> tuple[dict, bool]:
    """Persist exactly one gateway scan and toggle the employee's daily attendance."""
    duplicate = db.scalar(select(RfidEvent).where(RfidEvent.node_id == payload.node_id, RfidEvent.sequence == payload.seq))
    if duplicate:
        return _event_out(duplicate, duplicate=True), True

    now = datetime.now(timezone.utc)
    employee = db.scalar(select(User).where(User.rfid_uid == payload.uid, User.is_active.is_(True)))
    event = RfidEvent(rfid_uid=payload.uid, employee_id=employee.employee_id if employee else None,
                      node_id=payload.node_id, sequence=payload.seq, status="AUTHORIZED" if employee else "UNKNOWN",
                      rssi=payload.rssi, snr=payload.snr, timestamp=now)
    db.add(event)
    attendance_action = None
    if employee and employee.employee_id:
        row = db.scalar(select(Attendance).where(Attendance.employee_id == employee.employee_id,
                                                 Attendance.attendance_date == now.date()))
        if row is None:
            row = Attendance(employee_id=employee.employee_id, attendance_date=now.date(), entry_at=now)
            db.add(row)
            attendance_action = "ENTRY"
        elif row.exit_at is None:
            row.exit_at = now
            attendance_action = "EXIT"
    db.commit()
    db.refresh(event)
    return _event_out(event, employee.full_name if employee else None, attendance_action), False


def _event_out(event: RfidEvent, employee_name: str | None = None, attendance_action: str | None = None, duplicate: bool = False) -> dict:
    return {"outcome": "DUPLICATE" if duplicate else "ACCEPTED", "duplicate": duplicate, "event_id": str(event.id),
            "status": event.status, "employee_id": event.employee_id, "employee_name": employee_name,
            "attendance_action": attendance_action, "node_id": event.node_id, "uid": event.rfid_uid,
            "sequence": event.sequence, "timestamp": event.timestamp.isoformat()}
