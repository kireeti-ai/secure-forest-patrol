from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.forest_node import ForestNode
from app.models.rfid import Attendance, VerificationEvent
from app.models.user import User
from app.schemas.forest_ingest import VerificationIngest
from app.services.attendance_state import MIN_SECONDS_BEFORE_EXIT, attendance_day


DUPLICATE_WINDOW = timedelta(seconds=120)


def ingest_verification(db: Session, payload: VerificationIngest) -> tuple[dict, bool]:
    """Persist one two-factor checkpoint result. Only a MATCH toggles attendance --
    a card tap alone (see app/services/rfid.py) is no longer sufficient. MISMATCH rows
    are kept so a possible proxy attempt (wrong finger for the claimed card) is visible
    to the dashboard, not just logged and forgotten.
    """
    if db.get_bind().dialect.name == "postgresql":
        db.execute(select(func.pg_advisory_xact_lock(
            func.hashtext(f"verify:{payload.node_id}:{payload.seq}:{payload.claimed_uid}"))))

    recent = datetime.now(timezone.utc) - DUPLICATE_WINDOW
    duplicate = db.scalar(select(VerificationEvent).where(
        VerificationEvent.node_id == payload.node_id, VerificationEvent.sequence == payload.seq,
        VerificationEvent.claimed_uid == payload.claimed_uid, VerificationEvent.timestamp >= recent))
    if duplicate:
        return _event_out(duplicate, duplicate=True), True

    now = datetime.now(timezone.utc)
    claimed = db.scalar(select(User).where(User.rfid_uid == payload.claimed_uid, User.is_active.is_(True)))
    actual = None
    if payload.status != "TIMEOUT":
        actual = db.scalar(select(User).where(User.fingerprint_page_id == payload.actual_page_id, User.is_active.is_(True)))

    node = db.scalar(select(ForestNode).where(ForestNode.node_id == payload.node_id))
    if node is not None:
        node.last_seen_at = now

    event = VerificationEvent(
        status=payload.status, claimed_uid=payload.claimed_uid,
        claimed_employee_id=claimed.employee_id if claimed else None,
        claimed_page_id=payload.claimed_page_id, actual_page_id=payload.actual_page_id,
        actual_employee_id=actual.employee_id if actual else None,
        score=payload.score, node_id=payload.node_id, sequence=payload.seq,
        rssi=payload.rssi, snr=payload.snr, timestamp=now)
    db.add(event)

    attendance_action = None
    if payload.status == "MATCH" and claimed and claimed.employee_id:
        today = attendance_day(now)
        row = db.scalar(select(Attendance).where(Attendance.employee_id == claimed.employee_id,
                                                 Attendance.attendance_date == today))
        if row is None:
            row = Attendance(employee_id=claimed.employee_id, attendance_date=today, entry_at=now)
            db.add(row)
            attendance_action = "ENTRY"
        elif row.exit_at is None:
            entry_at = row.entry_at if row.entry_at.tzinfo else row.entry_at.replace(tzinfo=timezone.utc)
            if (now - entry_at).total_seconds() >= MIN_SECONDS_BEFORE_EXIT:
                row.exit_at = now
                attendance_action = "EXIT"

    db.commit()
    db.refresh(event)
    return _event_out(event, claimed.full_name if claimed else None, attendance_action), False


def _event_out(event: VerificationEvent, claimed_name: str | None = None, attendance_action: str | None = None,
              duplicate: bool = False) -> dict:
    return {
        "outcome": "DUPLICATE" if duplicate else "ACCEPTED", "duplicate": duplicate, "event_id": str(event.id),
        "status": event.status, "claimed_uid": event.claimed_uid, "claimed_employee_id": event.claimed_employee_id,
        "claimed_name": claimed_name, "actual_employee_id": event.actual_employee_id,
        "claimed_page_id": event.claimed_page_id, "actual_page_id": event.actual_page_id, "score": event.score,
        "attendance_action": attendance_action, "node_id": event.node_id, "sequence": event.sequence,
        "timestamp": event.timestamp.isoformat(),
    }
