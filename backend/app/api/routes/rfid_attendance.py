from datetime import date, datetime, timedelta, timezone

import re

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.api.dependencies.database import get_db
from app.core.security import hash_password, require_roles
from app.models.checkpoint import Checkpoint
from app.models.operator_checkpoint_access import OperatorCheckpointAccess
from app.models.patrol_event import PatrolEvent
from app.models.rfid import Attendance, RfidEvent, VerificationEvent
from app.models.user import User
from app.services.attendance_state import absent_after, attendance_day, attendance_timezone, presence_state
from app.services.rfid import invalid_reason

router = APIRouter(prefix="/api", tags=["rfid-attendance"])
_OFFICER_ROLES = ("OFFICER", "ADMIN")  # ADMIN retains access to legacy forest records.


class EmployeeCreate(BaseModel):
    employee_id: str = Field(min_length=1, max_length=64)
    full_name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=12, max_length=256)
    rfid_uid: str | None = Field(default=None, max_length=32)
    role: str = "EMPLOYEE"

    @field_validator("role")
    @classmethod
    def only_supported_roles(cls, value: str) -> str:
        if value not in {"OFFICER", "EMPLOYEE"}:
            raise ValueError("role must be OFFICER or EMPLOYEE")
        return value

    @field_validator("rfid_uid")
    @classmethod
    def normalize_rfid_uid(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = value.strip().upper().replace("-", ":")
        if not re.fullmatch(r"[0-9A-F]{2}(?::[0-9A-F]{2}){3,9}", normalized):
            raise ValueError("rfid_uid must be colon-separated hexadecimal bytes")
        return normalized


class RfidAssignment(BaseModel):
    rfid_uid: str | None = Field(default=None, max_length=32)

    @field_validator("rfid_uid")
    @classmethod
    def normalize_rfid_uid(cls, value: str | None) -> str | None:
        return EmployeeCreate.normalize_rfid_uid(value)


class FingerprintAssignment(BaseModel):
    fingerprint_page_id: int | None = Field(default=None, ge=0, le=65535)


class CheckpointAssignment(BaseModel):
    checkpoint_ids: list[str] = Field(max_length=100)


def _checkpoints_of(user: User) -> list[str]:
    return sorted(access.checkpoint_id for access in user.checkpoint_access)


def _employee_out(user: User) -> dict:
    return {"id": str(user.id), "employee_id": user.employee_id, "name": user.full_name,
            "email": user.email, "role": user.role, "rfid_uid": user.rfid_uid,
            "fingerprint_page_id": user.fingerprint_page_id, "active": user.is_active,
            "checkpoints": _checkpoints_of(user)}


@router.get("/employees")
def list_employees(db: Session = Depends(get_db), _: User = Depends(require_roles(*_OFFICER_ROLES))) -> list[dict]:
    return [_employee_out(user) for user in db.scalars(select(User).order_by(User.employee_id))]


@router.post("/employees", status_code=status.HTTP_201_CREATED)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db), _: User = Depends(require_roles(*_OFFICER_ROLES))) -> dict:
    user = User(employee_id=payload.employee_id.strip(), full_name=payload.full_name.strip(), email=payload.email.strip().lower(),
                password_hash=hash_password(payload.password), role=payload.role, rfid_uid=payload.rfid_uid)
    db.add(user)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="employee ID, email, or RFID UID is already registered") from exc
    db.refresh(user)
    return _employee_out(user)


def _find_employee(employee_id: str, db: Session) -> User:
    employee = db.scalar(select(User).where(User.employee_id == employee_id))
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.put("/employees/{employee_id}/rfid")
def assign_rfid(employee_id: str, payload: RfidAssignment, db: Session = Depends(get_db), _: User = Depends(require_roles(*_OFFICER_ROLES))) -> dict:
    """Assign, replace, or clear an employee's RFID card without exposing passwords."""
    employee = _find_employee(employee_id, db)
    employee.rfid_uid = payload.rfid_uid
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="RFID UID is already registered") from exc
    db.refresh(employee)
    return _employee_out(employee)


@router.put("/employees/{employee_id}/fingerprint")
def assign_fingerprint(employee_id: str, payload: FingerprintAssignment, db: Session = Depends(get_db),
                       _: User = Depends(require_roles(*_OFFICER_ROLES))) -> dict:
    """Assign, replace, or clear an employee's enrolled R307S fingerprint template id.

    This must match the page id enrolled into node-firmware's kAllowedCards[] for the
    checkpoint(s) this officer uses -- see node-firmware/src/fingerprint_enroll_diagnostic.cpp.
    """
    employee = _find_employee(employee_id, db)
    employee.fingerprint_page_id = payload.fingerprint_page_id
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Fingerprint page id is already registered") from exc
    db.refresh(employee)
    return _employee_out(employee)


@router.put("/employees/{employee_id}/checkpoints")
def assign_checkpoints(employee_id: str, payload: CheckpointAssignment, db: Session = Depends(get_db),
                       _: User = Depends(require_roles(*_OFFICER_ROLES))) -> dict:
    """Replace the set of checkpoints an employee is assigned to."""
    employee = _find_employee(employee_id, db)
    wanted = list(dict.fromkeys(payload.checkpoint_ids))
    known = set(db.scalars(select(Checkpoint.checkpoint_id).where(Checkpoint.checkpoint_id.in_(wanted))))
    missing = [cid for cid in wanted if cid not in known]
    if missing:
        raise HTTPException(status_code=404, detail=f"Unknown checkpoint(s): {', '.join(missing)}")
    # Delete first: SQLAlchemy would otherwise INSERT new rows before removing the old
    # ones and trip the (user, checkpoint) unique constraint on overlapping sets.
    employee.checkpoint_access.clear()
    db.flush()
    employee.checkpoint_access.extend(OperatorCheckpointAccess(checkpoint_id=cid) for cid in wanted)
    db.commit()
    db.refresh(employee)
    return _employee_out(employee)


@router.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_employee(employee_id: str, db: Session = Depends(get_db), _: User = Depends(require_roles(*_OFFICER_ROLES))) -> Response:
    employee = _find_employee(employee_id, db)
    db.delete(employee)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


_VERIFY_WINDOW = timedelta(seconds=20)  # matches the node's own "PLACE FINGER NOW" countdown


def _fingerprint_result_for(row: RfidEvent, patrol_candidates: list[PatrolEvent],
                            verification_candidates: list[VerificationEvent]) -> str | None:
    """The second factor that followed this card tap, if any.

    A card tap (RfidEvent) and its fingerprint outcome are two separate records with no shared
    key -- correlated here by (node_id, uid) plus the fingerprint result landing within the
    node's own verification window right after the tap. Signed nodes report MATCH/NO_MATCH
    directly on the patrol event; older/legacy nodes still produce a VerificationEvent
    (MATCH/MISMATCH/TIMEOUT) -- normalized to the same MATCH/NO_MATCH/TIMEOUT vocabulary here.
    """
    uid_key = _hex_uid_key(row.rfid_uid)
    best: tuple[float, str] | None = None
    for p in patrol_candidates:
        if p.node_id != row.node_id or _hex_uid_key(p.officer_id) != uid_key:
            continue
        delta = (p.event_created_at - row.timestamp).total_seconds()
        if 0 <= delta <= _VERIFY_WINDOW.total_seconds() and (best is None or delta < best[0]):
            best = (delta, "MATCH" if p.fingerprint_result == "MATCH" else "NO_MATCH")
    for v in verification_candidates:
        if v.node_id != row.node_id or _hex_uid_key(v.claimed_uid) != uid_key:
            continue
        delta = (v.timestamp - row.timestamp).total_seconds()
        if 0 <= delta <= _VERIFY_WINDOW.total_seconds() and (best is None or delta < best[0]):
            best = (delta, "NO_MATCH" if v.status == "MISMATCH" else v.status)
    return best[1] if best else None


@router.get("/rfid-events")
def list_rfid_events(db: Session = Depends(get_db), _: User = Depends(require_roles(*_OFFICER_ROLES))) -> list[dict]:
    rows = list(db.scalars(select(RfidEvent).order_by(RfidEvent.timestamp.desc()).limit(200)))
    checkpoint_by_node = {nid: cid for nid, cid in db.execute(
        select(Checkpoint.node_id, Checkpoint.checkpoint_id).where(Checkpoint.node_id.is_not(None)))}
    assigned_by_employee: dict[str, list[str]] = {}
    for employee_id, checkpoint_id in db.execute(
            select(User.employee_id, OperatorCheckpointAccess.checkpoint_id)
            .join(OperatorCheckpointAccess, OperatorCheckpointAccess.user_id == User.id)
            .where(User.employee_id.is_not(None))):
        assigned_by_employee.setdefault(employee_id, []).append(checkpoint_id)

    oldest = min((r.timestamp for r in rows), default=datetime.now(timezone.utc))
    window_end = datetime.now(timezone.utc) + _VERIFY_WINDOW
    patrol_candidates = list(db.scalars(select(PatrolEvent).where(
        PatrolEvent.event_created_at >= oldest, PatrolEvent.event_created_at <= window_end)))
    verification_candidates = list(db.scalars(select(VerificationEvent).where(
        VerificationEvent.timestamp >= oldest, VerificationEvent.timestamp <= window_end)))

    result = []
    for row in rows:
        checkpoint_id = checkpoint_by_node.get(row.node_id)
        result.append({
            "id": str(row.id), "checkpoint_id": checkpoint_id, "uid": row.rfid_uid,
            "employee_id": row.employee_id, "node_id": row.node_id, "sequence": row.sequence,
            "status": row.status, "rssi": row.rssi, "snr": row.snr, "timestamp": row.timestamp.isoformat(),
            "reason": invalid_reason(checkpoint_id, assigned_by_employee.get(row.employee_id, [])) if row.status == "INVALID" else None,
            "fingerprint_result": _fingerprint_result_for(row, patrol_candidates, verification_candidates),
        })
    return result


def _hex_uid_key(uid: str | None) -> str:
    return re.sub(r"[^0-9a-f]", "", (uid or "").lower())


@router.get("/verification-events")
def list_verification_events(status: str | None = None, db: Session = Depends(get_db),
                             _: User = Depends(require_roles(*_OFFICER_ROLES))) -> list[dict]:
    """Two-factor checkpoint results (card + fingerprint). Pass ``status=MISMATCH`` to see
    only possible proxy attempts (fingerprint did not match the claimed card's officer).

    Two sources feed this, because node firmware stopped sending the legacy unsigned 'V'
    packet once a node has an identity/clock and signs patrol events instead (see
    node-firmware/src/main.cpp::sendVerificationEvent and docs/TAMPER_EVIDENCE_SECURITY_PLAN.md):
    older/legacy rows in ``verification_events`` (richer: carries actual_page_id/score, who the
    finger actually belonged to), and signed ``patrol_events`` rows with
    ``fingerprint_result == 'NO_MATCH'`` (the only record of a mismatch a signed node produces
    today -- the signed wire payload is a MATCH/NO_MATCH flag only, so actual_page_id/score are
    not available for these and come back null).
    """
    query = select(VerificationEvent).order_by(VerificationEvent.timestamp.desc()).limit(200)
    if status:
        query = query.where(VerificationEvent.status == status)
    names_by_employee = {employee_id: name for employee_id, name in
                         db.execute(select(User.employee_id, User.full_name).where(User.employee_id.is_not(None)))}
    checkpoint_by_node = {nid: cid for nid, cid in db.execute(
        select(Checkpoint.node_id, Checkpoint.checkpoint_id).where(Checkpoint.node_id.is_not(None)))}
    users_by_uid_key = {_hex_uid_key(uid): (employee_id, name) for uid, employee_id, name in
                        db.execute(select(User.rfid_uid, User.employee_id, User.full_name)
                                   .where(User.rfid_uid.is_not(None)))}
    result = []
    for row in db.scalars(query):
        result.append({
            "id": str(row.id), "status": row.status, "checkpoint_id": checkpoint_by_node.get(row.node_id),
            "claimed_uid": row.claimed_uid, "claimed_employee_id": row.claimed_employee_id,
            "claimed_name": names_by_employee.get(row.claimed_employee_id),
            "claimed_page_id": row.claimed_page_id, "actual_page_id": row.actual_page_id,
            "actual_employee_id": row.actual_employee_id,
            "actual_name": names_by_employee.get(row.actual_employee_id),
            "score": row.score, "node_id": row.node_id, "sequence": row.sequence,
            "timestamp": row.timestamp.isoformat(),
        })
    if status is None or status == "MISMATCH":
        patrol_query = (select(PatrolEvent).where(PatrolEvent.fingerprint_result == "NO_MATCH")
                        .order_by(PatrolEvent.event_created_at.desc()).limit(200))
        for row in db.scalars(patrol_query):
            claimed_employee_id, claimed_name = users_by_uid_key.get(_hex_uid_key(row.officer_id), (None, None))
            result.append({
                "id": f"patrol:{row.id}", "status": "MISMATCH", "checkpoint_id": row.checkpoint_id,
                "claimed_uid": row.officer_id, "claimed_employee_id": claimed_employee_id,
                "claimed_name": claimed_name,
                "claimed_page_id": None, "actual_page_id": None,
                "actual_employee_id": None, "actual_name": None,
                "score": None, "node_id": row.node_id, "sequence": row.sequence,
                "timestamp": row.event_created_at.isoformat(),
            })
        result.sort(key=lambda r: r["timestamp"], reverse=True)
    return result


@router.get("/officer-presence")
def officer_presence(db: Session = Depends(get_db), _: User = Depends(require_roles(*_OFFICER_ROLES))) -> list[dict]:
    """Return the real officer RFID roster and today's attendance state.

    ``state`` is PRESENT (scanned in, not out), CHECKED_OUT (scanned in and out),
    YET_TO_ARRIVE (no scan yet, before the cut-off) or ABSENT (no scan, cut-off
    passed); see ``app/services/attendance_state.py``. ``present`` is kept for
    older clients and is true only for PRESENT. There is no fabricated roster.
    """
    now = datetime.now(timezone.utc)
    today = attendance_day(now)
    rows = db.execute(
        select(User, Attendance)
        .outerjoin(Attendance, and_(Attendance.employee_id == User.employee_id,
                                    Attendance.attendance_date == today))
        .where(User.is_active.is_(True), User.role.in_(("OFFICER", "EMPLOYEE")))
        .order_by(User.full_name)
    )
    result = []
    for user, attendance in rows:
        has_entry = bool(attendance and attendance.entry_at)
        has_exit = bool(attendance and attendance.exit_at)
        state = presence_state(has_entry, has_exit, now)
        result.append({
            "id": str(user.id), "employee_id": user.employee_id, "name": user.full_name,
            "role": user.role, "rfid_uid": user.rfid_uid, "fingerprint_page_id": user.fingerprint_page_id,
            "checkpoints": _checkpoints_of(user),
            "state": state, "present": state == "PRESENT",
            "attendance_date": today.isoformat(),
            "absent_after": absent_after().strftime("%H:%M"), "timezone": str(attendance_timezone()),
            "entry_at": attendance.entry_at.isoformat() if has_entry else None,
            "exit_at": attendance.exit_at.isoformat() if has_exit else None,
        })
    return result
