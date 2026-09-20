from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.checkpoint import Checkpoint
from app.models.forest_node import ForestNode
from app.models.operator_checkpoint_access import OperatorCheckpointAccess
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

    # The scanning node tells us which checkpoint the officer is standing at.
    node = db.scalar(select(ForestNode).where(ForestNode.node_id == payload.node_id))
    if node is not None:
        node.last_seen_at = now
    checkpoint = db.scalar(select(Checkpoint).where(Checkpoint.node_id == payload.node_id))

    status = "UNKNOWN"
    if employee:
        status = "AUTHORIZED"
        # An officer with assigned checkpoints must scan at one of them. Officers
        # with no assignment, or scans from a node not mapped to a checkpoint, are
        # not restricted.
        assigned = set(db.scalars(select(OperatorCheckpointAccess.checkpoint_id)
                                  .where(OperatorCheckpointAccess.user_id == employee.id)))
        if checkpoint is not None and assigned and checkpoint.checkpoint_id not in assigned:
            status = "INVALID"  # registered, but tried a checkpoint they are not assigned to

    event = RfidEvent(rfid_uid=payload.uid, employee_id=employee.employee_id if employee else None,
                      node_id=payload.node_id, sequence=payload.seq, status=status,
                      rssi=payload.rssi, snr=payload.snr, timestamp=now)
    db.add(event)
    attendance_action = None
    if status == "AUTHORIZED" and employee.employee_id:
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
    body = _event_out(event, employee.full_name if employee else None, attendance_action)
    if status == "INVALID":
        body["reason"] = invalid_reason(checkpoint.checkpoint_id if checkpoint else None, sorted(assigned))
    return body, False


def invalid_reason(attempted: str | None, assigned: list[str]) -> str:
    """Human-readable reason for an INVALID scan (derived, never stored)."""
    where = attempted or "an unassigned checkpoint"
    return f"Tried to access invalid checkpoint {where}; assigned to {', '.join(sorted(assigned)) or 'none'}"


def _event_out(event: RfidEvent, employee_name: str | None = None, attendance_action: str | None = None, duplicate: bool = False) -> dict:
    return {"outcome": "DUPLICATE" if duplicate else "ACCEPTED", "duplicate": duplicate, "event_id": str(event.id),
            "status": event.status, "employee_id": event.employee_id, "employee_name": employee_name,
            "attendance_action": attendance_action, "node_id": event.node_id, "uid": event.rfid_uid,
            "sequence": event.sequence, "timestamp": event.timestamp.isoformat()}
