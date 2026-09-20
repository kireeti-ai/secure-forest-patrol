from datetime import date, datetime, timezone

import re

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.api.dependencies.database import get_db
from app.core.security import hash_password, require_roles
from app.models.rfid import Attendance, RfidEvent
from app.models.user import User

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


def _employee_out(user: User) -> dict:
    return {"id": str(user.id), "employee_id": user.employee_id, "name": user.full_name,
            "email": user.email, "role": user.role, "rfid_uid": user.rfid_uid, "active": user.is_active}


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


@router.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_employee(employee_id: str, db: Session = Depends(get_db), _: User = Depends(require_roles(*_OFFICER_ROLES))) -> Response:
    employee = _find_employee(employee_id, db)
    db.delete(employee)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/rfid-events")
def list_rfid_events(db: Session = Depends(get_db), _: User = Depends(require_roles(*_OFFICER_ROLES))) -> list[dict]:
    rows = db.scalars(select(RfidEvent).order_by(RfidEvent.timestamp.desc()).limit(200))
    return [{"id": str(row.id), "uid": row.rfid_uid, "employee_id": row.employee_id, "node_id": row.node_id,
             "sequence": row.sequence, "status": row.status, "rssi": row.rssi, "snr": row.snr,
             "timestamp": row.timestamp.isoformat()} for row in rows]


@router.get("/officer-presence")
def officer_presence(db: Session = Depends(get_db), _: User = Depends(require_roles(*_OFFICER_ROLES))) -> list[dict]:
    """Return the real officer RFID roster and today's presence state.

    Presence is green only while an attendance row has an entry and no exit.
    There is deliberately no fabricated fallback roster or random presence.
    """
    today = datetime.now(timezone.utc).date()
    rows = db.execute(
        select(User, Attendance)
        .outerjoin(Attendance, and_(Attendance.employee_id == User.employee_id,
                                    Attendance.attendance_date == today))
        .where(User.is_active.is_(True), User.role.in_(("OFFICER", "EMPLOYEE")))
        .order_by(User.full_name)
    )
    result = []
    for user, attendance in rows:
        result.append({
            "id": str(user.id), "employee_id": user.employee_id, "name": user.full_name,
            "role": user.role, "rfid_uid": user.rfid_uid,
            "present": bool(attendance and attendance.entry_at and not attendance.exit_at),
            "attendance_date": today.isoformat(),
            "entry_at": attendance.entry_at.isoformat() if attendance and attendance.entry_at else None,
            "exit_at": attendance.exit_at.isoformat() if attendance and attendance.exit_at else None,
        })
    return result
