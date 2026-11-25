"""Brute-force protection for logins and one-time codes.

After MAX_FAILURES failed attempts within WINDOW for the same key, that key is
locked for LOCK_FOR and every attempt gets a 429 until it expires, even with the
right password or code. A success clears the counter.

Keys are NOT checked against real accounts: an unknown email locks exactly like
a known one, so the lockout cannot be used to discover which emails are
registered. The trade-off is that someone can lock a victim out for LOCK_FOR by
failing on purpose; the lock is short for that reason.
"""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import LoginThrottle

MAX_FAILURES = 5
WINDOW = timedelta(minutes=15)
LOCK_FOR = timedelta(minutes=15)
FORGET_AFTER = timedelta(days=1)  # rows idle this long are deleted so the table cannot grow forever


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC, like the DB columns


def make_key(kind: str, identifier: str) -> str:
    return f"{kind}:{identifier.strip().lower()}"[:320]


def ensure_not_locked(db: Session, key: str) -> None:
    row = db.get(LoginThrottle, key)
    now = _now()
    if row and row.locked_until and row.locked_until > now:
        seconds = int((row.locked_until - now).total_seconds()) + 1
        minutes = max(1, -(-seconds // 60))
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed attempts. Please try again in {minutes} minute{'s' if minutes != 1 else ''}.",
            headers={"Retry-After": str(seconds)},
        )


def record_failure(db: Session, key: str) -> None:
    now = _now()
    db.execute(delete(LoginThrottle).where(LoginThrottle.window_start < now - FORGET_AFTER))
    row = db.get(LoginThrottle, key)
    if row is None:
        row = LoginThrottle(key=key, failures=0, window_start=now)
        db.add(row)
    elif now - row.window_start > WINDOW or (row.locked_until and row.locked_until <= now):
        row.failures, row.window_start, row.locked_until = 0, now, None  # old window / expired lock: start over
    row.failures += 1
    if row.failures >= MAX_FAILURES:
        row.locked_until = now + LOCK_FOR
    db.commit()


def record_success(db: Session, key: str) -> None:
    db.execute(delete(LoginThrottle).where(LoginThrottle.key == key))
    db.commit()
