"""Durable outgoing email (a "transactional outbox").

Problem it solves: emails used to be queued in memory after the response, so a
restart or crash lost them, and an SMTP outage at the wrong moment meant a
student never got their invoice or certificate.

How it works:
  1. `add()` stores the email as a row in the SAME database transaction as the
     thing that triggers it (the payment, the certificate unlock, the
     enrollment, the contact message). Either both are saved or neither is, so
     an email can never be "forgotten" between the two commits.
  2. `deliver()` sends it right away from a background task, so students still
     get it within seconds in the normal case.
  3. If that fails (SMTP down, crash, restart), `process_due()` (run every
     minute by the scheduler) retries with growing delays, up to MAX_ATTEMPTS,
     then parks the email as "failed" where an admin can see it and retry.

Rows store a small JSON description, not the PDF: attachments are regenerated at
send time, so the table stays small. Delivery is at-least-once: a crash after the
SMTP server accepted the message but before the row is marked sent can cause one
duplicate on the retry. Idempotent keys (`dedupe_key`) stop the same invoice or
certificate from being queued twice. One-time login codes deliberately do NOT use
this: they expire in minutes and must not sit in the database in plain text.
"""

import json
import logging
from datetime import datetime, timedelta, timezone

from fastapi import BackgroundTasks
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from app.db.base import SessionLocal
from app.db.models import EmailOutbox

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 6
BACKOFF = [timedelta(minutes=1), timedelta(minutes=5), timedelta(minutes=15), timedelta(hours=1), timedelta(hours=6)]
FIRST_DELAY = timedelta(minutes=2)  # gives the immediate send first go before the retry job looks at a new row
CLAIM_TTL = timedelta(minutes=5)  # a sender that dies mid-send frees its claim after this
KEEP_SENT_FOR = timedelta(days=30)
BATCH = 50


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC, like the DB columns


# --------------------------------------------------------------------------
# What each kind of email does when it is finally sent
# --------------------------------------------------------------------------


def _send(kind: str, payload: dict) -> None:
    # Imported here: these services import this module to enqueue, so a top-level
    # import would be circular.
    if kind == "invoice":
        from app.services.payment_service import send_invoice_email

        send_invoice_email(payload["data"])
    elif kind == "certificate":
        from app.services.certificate_service import send_certificate_email

        send_certificate_email(payload["to"], payload["name"], payload["program_title"], payload["data"])
    elif kind == "offer_letter":
        from app.services.offer_letter_email import send_offer_letter_email

        send_offer_letter_email(
            payload["to"], payload["name"], payload["program_title"], payload["enrollment_id"], payload["pdf_data"]
        )
    elif kind == "contact":
        from app.services.email_service import send_email

        send_email(to=payload["to"], subject=payload["subject"], body=payload["body"])
    else:
        raise ValueError(f"Unknown email kind: {kind}")


# --------------------------------------------------------------------------
# Enqueue (inside the caller's transaction)
# --------------------------------------------------------------------------


def add(
    db: Session, kind: str, *, to: str, subject: str, payload: dict, dedupe_key: str | None = None
) -> EmailOutbox:
    """Stores an email to send. Does NOT commit: the caller's commit saves it
    together with whatever triggered it. With a dedupe_key, queuing the same
    thing again returns the existing row instead of a second email."""
    if dedupe_key:
        existing = db.query(EmailOutbox).filter(EmailOutbox.dedupe_key == dedupe_key).first()
        if existing:
            return existing
    row = EmailOutbox(
        kind=kind,
        to_email=to,
        subject=subject[:255],
        payload=json.dumps(payload),
        dedupe_key=dedupe_key,
        status="pending",
        attempts=0,
        next_attempt_at=_now() + FIRST_DELAY,
    )
    db.add(row)
    db.flush()  # assigns the id
    return row


def send_soon(background: BackgroundTasks | None, *email_ids: str) -> None:
    """After the caller has committed: try each email right now, off the request's
    critical path. With no request (scheduler, scripts) it sends inline."""
    for email_id in email_ids:
        if background is not None:
            background.add_task(deliver, email_id)
        else:
            deliver(email_id)


# --------------------------------------------------------------------------
# Deliver one email
# --------------------------------------------------------------------------


def _claim(db: Session, email_id: str) -> bool:
    """Atomically takes the right to send this email, so the immediate send, the
    retry job and an admin's retry can never send it twice at once."""
    now = _now()
    result = db.execute(
        update(EmailOutbox)
        .where(
            EmailOutbox.id == email_id,
            EmailOutbox.status == "pending",
            or_(EmailOutbox.locked_until.is_(None), EmailOutbox.locked_until < now),
            or_(EmailOutbox.attempts == 0, EmailOutbox.next_attempt_at <= now),  # a fresh email may go immediately
        )
        .values(locked_until=now + CLAIM_TTL, attempts=EmailOutbox.attempts + 1)
    )
    db.commit()
    return result.rowcount == 1


def deliver(email_id: str) -> bool:
    """Sends one outbox email. Never raises. Returns True if it was sent now."""
    db = SessionLocal()
    try:
        if not _claim(db, email_id):
            return False
        row = db.get(EmailOutbox, email_id)
        kind, attempts = row.kind, row.attempts
        try:
            _send(kind, json.loads(row.payload or "{}"))
        except Exception as err:  # noqa: BLE001  (SMTP, PDF generation, bad payload: all handled the same way)
            logger.exception("Email %s (%s) attempt %s failed", email_id, kind, attempts)
            _record_failure(db, email_id, attempts, err)
            return False
        db.execute(
            update(EmailOutbox)
            .where(EmailOutbox.id == email_id)
            .values(status="sent", sent_at=_now(), payload=None, locked_until=None, last_error=None)
        )
        db.commit()
        return True
    except Exception:  # noqa: BLE001  (database trouble: the claim expires and the retry job tries again)
        logger.exception("Could not process outbox email %s", email_id)
        return False
    finally:
        db.close()


def _record_failure(db: Session, email_id: str, attempts: int, err: Exception) -> None:
    dead = attempts >= MAX_ATTEMPTS
    values = {"locked_until": None, "last_error": f"{type(err).__name__}: {err}"[:500]}
    if dead:
        values["status"] = "failed"
    else:
        values["next_attempt_at"] = _now() + BACKOFF[min(attempts, len(BACKOFF)) - 1]
    db.execute(update(EmailOutbox).where(EmailOutbox.id == email_id).values(**values))
    db.commit()


# --------------------------------------------------------------------------
# Retry job, admin tools
# --------------------------------------------------------------------------


def process_due() -> int:
    """Scheduler job: retries every pending email that is due, then deletes old
    sent rows. Returns how many sends were attempted."""
    db = SessionLocal()
    try:
        now = _now()
        due = (
            db.execute(
                select(EmailOutbox.id)
                .where(
                    EmailOutbox.status == "pending",
                    EmailOutbox.next_attempt_at <= now,
                    or_(EmailOutbox.locked_until.is_(None), EmailOutbox.locked_until < now),
                )
                .order_by(EmailOutbox.next_attempt_at)
                .limit(BATCH)
            )
            .scalars()
            .all()
        )
        db.execute(delete(EmailOutbox).where(EmailOutbox.status == "sent", EmailOutbox.sent_at < now - KEEP_SENT_FOR))
        db.commit()
    finally:
        db.close()

    attempted = 0
    for email_id in due:
        deliver(email_id)
        attempted += 1
    return attempted


def retry(db: Session, email_id: str) -> str | None:
    """Admin: puts a failed (or waiting) email back in the queue with a fresh set
    of attempts. Returns the id to send now, or None if it can't be retried."""
    result = db.execute(
        update(EmailOutbox)
        .where(EmailOutbox.id == email_id, EmailOutbox.status.in_(("failed", "pending")))
        .values(status="pending", attempts=0, next_attempt_at=_now(), locked_until=None)
    )
    db.commit()
    return email_id if result.rowcount == 1 else None


def counts(db: Session) -> dict:
    rows = db.execute(select(EmailOutbox.status, func.count()).group_by(EmailOutbox.status)).all()
    result = {"pending": 0, "sent": 0, "failed": 0}
    result.update({status: n for status, n in rows})
    return result
