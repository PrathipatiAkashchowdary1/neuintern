"""Run a scheduled job on only ONE server worker at a time.

Every worker process starts its own scheduler, so with N workers a job would
fire N times per tick (duplicate certificate emails, duplicate reminders). Each
job instead takes a lock row in the database before it runs:

  * only one worker can hold it at a time (an atomic compare-and-set UPDATE);
  * `min_interval` stops a second worker whose clock fires a few seconds later
    from running the same tick again;
  * `ttl` frees the lock automatically if the holder dies mid-run.

Because it lives in the database it works across processes, hosts and restarts,
with no extra infrastructure. Jobs must still be safe to run twice in a rare
failure case (the certificate unlock and reminder claims are atomic for that).
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import or_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import SessionLocal
from app.db.models import JobLock

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC, like the DB columns


def try_acquire(db: Session, name: str, *, min_interval: timedelta, ttl: timedelta) -> bool:
    """True if THIS caller now holds the lock and should run the job."""
    now = _now()
    if db.get(JobLock, name) is None:
        try:
            db.add(JobLock(name=name))
            db.commit()
        except IntegrityError:  # another worker created the row first: fine
            db.rollback()

    result = db.execute(
        update(JobLock)
        .where(
            JobLock.name == name,
            or_(JobLock.locked_until.is_(None), JobLock.locked_until < now),  # free, or the holder's ttl lapsed
            or_(JobLock.last_run_at.is_(None), JobLock.last_run_at <= now - min_interval),  # not run too recently
        )
        .values(locked_until=now + ttl, last_run_at=now)
    )
    db.commit()
    return result.rowcount == 1


def release(db: Session, name: str) -> None:
    db.execute(update(JobLock).where(JobLock.name == name).values(locked_until=None))
    db.commit()


def run_exclusive(
    name: str,
    job: Callable[[], None],
    *,
    min_interval: timedelta,
    ttl: timedelta = timedelta(minutes=30),
) -> bool:
    """Runs `job()` if this worker wins the lock. Returns whether it ran. A
    failing job is logged and the lock is still released, so the next tick can
    try again instead of waiting out the ttl."""
    db = SessionLocal()
    try:
        if not try_acquire(db, name, min_interval=min_interval, ttl=ttl):
            return False
    finally:
        db.close()

    try:
        job()
    except Exception:
        logger.exception("Scheduled job %s failed", name)
    finally:
        db = SessionLocal()
        try:
            release(db, name)
        finally:
            db.close()
    return True
