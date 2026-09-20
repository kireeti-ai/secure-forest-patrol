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
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

# A second card tap this soon after entry is a double tap, not a check-out.
MIN_SECONDS_BEFORE_EXIT = 120


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
