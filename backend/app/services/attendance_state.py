"""Attendance day and presence state for officers.

Basis, per officer, for the current day in the configured timezone:

* PRESENT        - scanned in today and has not scanned out
* CHECKED_OUT    - scanned in and out today (worked, has left)
* YET_TO_ARRIVE  - no scan today and it is still before the cut-off time
* ABSENT         - no scan today and the cut-off time has passed

Configuration (environment):

    FOREST_TIMEZONE         IANA timezone that defines "today"       default Asia/Kolkata
    ATTENDANCE_ABSENT_AFTER local HH:MM after which no scan = absent default 10:00
"""

import os
import re
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rfid import Attendance

# A second card tap this soon after entry is a double tap, not a check-out.
MIN_SECONDS_BEFORE_EXIT = 10


def attendance_timezone() -> ZoneInfo:
    return ZoneInfo(os.getenv("FOREST_TIMEZONE") or "Asia/Kolkata")


def absent_after() -> time:
    raw = os.getenv("ATTENDANCE_ABSENT_AFTER") or "10:00"
    try:
        hour, minute = raw.split(":")
        return time(int(hour), int(minute))
    except (ValueError, TypeError):
        return time(10, 0)


def attendance_day(now: datetime | None = None) -> date:
    """The local calendar day that attendance rows are keyed by."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(attendance_timezone()).date()


def presence_state(has_entry: bool, has_exit: bool, now: datetime | None = None) -> str:
    if has_entry:
        return "CHECKED_OUT" if has_exit else "PRESENT"
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    local_now = now.astimezone(attendance_timezone()).time()
    return "ABSENT" if local_now >= absent_after() else "YET_TO_ARRIVE"


def hex_uid_key(uid: str | None) -> str:
    """Normalize an RFID UID for comparison regardless of colon/case formatting --
    e.g. "30:BD:57:58" and "30bd5758" (the raw hex a signed patrol event's officer_id
    carries, see node-firmware's officerUidHex) both normalize to "30bd5758"."""
    return re.sub(r"[^0-9a-f]", "", (uid or "").lower())


def record_attendance_match(db: Session, employee_id: str, now: datetime) -> str | None:
    """Record a verified (fingerprint-MATCH) checkpoint visit as today's entry or exit.

    Shared by both the legacy unsigned verification path (app/services/verification.py)
    and the signed patrol path (app/services/forest_patrol.py) -- either one completing a
    real two-factor match marks attendance the same way; see MIN_SECONDS_BEFORE_EXIT for
    why a second match too soon after entry is not treated as a checkout.
    """
    today = attendance_day(now)
    row = db.scalar(select(Attendance).where(Attendance.employee_id == employee_id,
                                             Attendance.attendance_date == today))
    if row is None:
        db.add(Attendance(employee_id=employee_id, attendance_date=today, entry_at=now))
        return "ENTRY"
    if row.exit_at is None:
        entry_at = row.entry_at if row.entry_at.tzinfo else row.entry_at.replace(tzinfo=timezone.utc)
        if (now - entry_at).total_seconds() >= MIN_SECONDS_BEFORE_EXIT:
            row.exit_at = now
            return "EXIT"
    return None
