"""Server-side login sessions, so a single login can be cancelled.

A JWT on its own is valid until it expires; there is no way to take back one
that was stolen. Each login therefore also creates a row here, and the token
carries that row's id (`jti`). Every request checks the row: if it was revoked
(logout, "log out of all devices", a password reset) the token stops working at
once, wherever it is.

Tokens issued before this existed have no `jti`; they keep working until their
normal expiry (at most JWT_EXPIRES_MINUTES, 7 days by default) and are still
covered by the password-reset revocation.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import User, UserSession

MAX_ACTIVE_SESSIONS = 20  # a user's oldest sessions are retired beyond this, so the table cannot grow without bound
TOUCH_EVERY = timedelta(minutes=5)  # "last used" is refreshed at most this often, not on every request
KEEP_DEAD_FOR = timedelta(days=30)  # revoked/expired rows are deleted after this


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC, like the DB columns


def new_session_id() -> str:
    return uuid.uuid4().hex


def describe_device(user_agent: str | None) -> str:
    """A short human label such as 'Chrome on Windows' from a User-Agent header."""
    ua = (user_agent or "").lower()
    if not ua:
        return "Unknown device"
    if "edg/" in ua or "edge/" in ua:
        browser = "Edge"
    elif "opr/" in ua or "opera" in ua:
        browser = "Opera"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "chrome" in ua or "crios" in ua:
        browser = "Chrome"
    elif "safari" in ua:
        browser = "Safari"
    else:
        browser = "Browser"
    # iPhone/iPad UAs also contain "like Mac OS X", so check them before macOS.
    if "iphone" in ua or "ipad" in ua:
        system = "iOS"
    elif "android" in ua:
        system = "Android"
    elif "windows" in ua:
        system = "Windows"
    elif "mac os" in ua or "macintosh" in ua:
        system = "macOS"
    elif "linux" in ua:
        system = "Linux"
    else:
        system = None
    return f"{browser} on {system}" if system else browser


def create(db: Session, user: User, *, user_agent: str | None, ip: str | None) -> UserSession:
    now = _now()
    session = UserSession(
        id=new_session_id(),
        user_id=user.id,
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(minutes=settings.jwt_expires_minutes),
        user_agent=(user_agent or "")[:255],
        ip=(ip or "")[:45],
    )
    db.add(session)
    db.flush()

    # Retire the oldest sessions beyond the cap, and clear out long-dead rows.
    active = list_active(db, user.id)  # newest first
    for old in active[MAX_ACTIVE_SESSIONS:]:
        old.revoked_at = now
    db.execute(
        delete(UserSession).where(
            UserSession.user_id == user.id,
            (UserSession.revoked_at < now - KEEP_DEAD_FOR) | (UserSession.expires_at < now - KEEP_DEAD_FOR),
        )
    )
    db.commit()
    return session


def is_active(session: UserSession | None, user_id: str) -> bool:
    now = _now()
    return (
        session is not None
        and session.user_id == user_id
        and session.revoked_at is None
        and session.expires_at > now
    )


def touch(db: Session, session: UserSession) -> None:
    now = _now()
    if now - session.last_seen_at >= TOUCH_EVERY:
        session.last_seen_at = now
        db.commit()


def list_active(db: Session, user_id: str) -> list[UserSession]:
    now = _now()
    return (
        db.query(UserSession)
        .filter(UserSession.user_id == user_id, UserSession.revoked_at.is_(None), UserSession.expires_at > now)
        .order_by(UserSession.last_seen_at.desc(), UserSession.created_at.desc())
        .all()
    )


def revoke(db: Session, session_id: str, user_id: str) -> bool:
    """Revokes one session of this user. False if it is not theirs or already gone."""
    result = db.execute(
        update(UserSession)
        .where(UserSession.id == session_id, UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=_now())
    )
    db.commit()
    return result.rowcount == 1


def revoke_all(db: Session, user_id: str) -> int:
    result = db.execute(
        update(UserSession)
        .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=_now())
    )
    db.commit()
    return result.rowcount
