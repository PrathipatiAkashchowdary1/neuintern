"""Reminder emails for students who stall before paying the certificate fee.

Two stalls are covered, each with its own email:
  * "task":    enrolled, but never submitted the GitHub/LinkedIn task
  * "payment": submitted the task, but the certificate fee is not paid
              (status unpaid / pending / failed)

Pacing (all constants below): the first reminder goes out a short while after
the student stalled, later ones are spaced out, and there is a hard cap on the
number of reminders and on how old an enrollment can be. Paid enrollments are
never emailed.

Each send first "claims" the reminder with a compare-and-set UPDATE, so two
workers running the job at once (or an admin trigger overlapping the
scheduler) cannot email the same student twice. If the send then fails, the
claim is released so the next run retries.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import CERTIFICATE_FEE_INR, Enrollment
from app.services.certificate_service import completion_date
from app.services.email_service import send_email

logger = logging.getLogger(__name__)

MAX_REMINDERS = 3
FIRST_DELAY_TASK = timedelta(days=2)  # after enrolling
FIRST_DELAY_PAYMENT = timedelta(days=1)  # after submitting the task
REMINDER_SPACING = timedelta(days=3)
MAX_ENROLLMENT_AGE = timedelta(days=60)  # stop nagging stale enrollments entirely


def _now() -> datetime:
    # Naive UTC, matching what SQLAlchemy returns for DateTime columns.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def reminder_stage(enrollment: Enrollment) -> str:
    return "payment" if enrollment.task_submitted_at else "task"


def is_reminder_due(enrollment: Enrollment, now: datetime) -> bool:
    if enrollment.payment_status == "paid":
        return False
    if enrollment.reminder_count >= MAX_REMINDERS:
        return False
    if now - enrollment.enrolled_at > MAX_ENROLLMENT_AGE:
        return False

    stage = reminder_stage(enrollment)
    # Nudging someone to start a 4-week program that has already ended is noise.
    # (Payment reminders still make sense: paying after the end unlocks the
    # certificate immediately.)
    if stage == "task" and now >= completion_date(enrollment):
        return False

    if enrollment.reminder_count == 0:
        if stage == "task":
            return now - enrollment.enrolled_at >= FIRST_DELAY_TASK
        return now - enrollment.task_submitted_at >= FIRST_DELAY_PAYMENT

    return enrollment.last_reminder_at is not None and now - enrollment.last_reminder_at >= REMINDER_SPACING


def build_reminder(enrollment: Enrollment) -> tuple[str, str]:
    """(subject, body) for this student's current stall."""
    dashboard = f"{settings.frontend_url.rstrip('/')}/dashboard"
    ends = completion_date(enrollment).strftime("%B %d, %Y")
    footer = (
        "\n\nIf you've already done this, please ignore this email.\n"
        "You're receiving it because you enrolled in a NeuIntern program.\n\n"
        "— The NeuIntern Team"
    )

    if reminder_stage(enrollment) == "task":
        subject = f"Your NeuIntern internship is waiting — {enrollment.program_title}"
        body = (
            f"Hi {enrollment.name},\n\n"
            f"You enrolled in the {enrollment.program_title} internship but haven't submitted your task yet. "
            f"Your program runs until {ends}.\n\n"
            f"Next step: log in and submit your GitHub and LinkedIn links to move on to certification:\n"
            f"{dashboard}"
        )
    else:
        subject = f"Complete your certificate — {enrollment.program_title}"
        body = (
            f"Hi {enrollment.name},\n\n"
            f"Thanks for submitting your task for the {enrollment.program_title} internship. "
            f"One step left: pay the ₹{CERTIFICATE_FEE_INR:g} certificate fee from your dashboard:\n"
            f"{dashboard}\n\n"
            f"Your certificate is emailed to you once your program completes on {ends} "
            f"(or right away if that date has passed)."
        )
    return subject, body + footer


def _claim(db: Session, enrollment: Enrollment, now: datetime) -> bool:
    result = db.execute(
        update(Enrollment)
        .where(
            Enrollment.id == enrollment.id,
            Enrollment.reminder_count == enrollment.reminder_count,
            Enrollment.payment_status != "paid",
        )
        .values(reminder_count=enrollment.reminder_count + 1, last_reminder_at=now)
    )
    db.commit()
    return result.rowcount == 1


def _release(db: Session, enrollment_id: str, claimed_count: int, previous_last: datetime | None) -> None:
    db.execute(
        update(Enrollment)
        .where(Enrollment.id == enrollment_id, Enrollment.reminder_count == claimed_count)
        .values(reminder_count=claimed_count - 1, last_reminder_at=previous_last)
    )
    db.commit()


def send_due_reminders(db: Session, *, now: datetime | None = None, dry_run: bool = False) -> list[str]:
    """Emails every student whose reminder is due. Returns the enrollment IDs
    emailed (or, with dry_run, the ones that WOULD be emailed; nothing is sent
    or recorded). Runs inline: called from the scheduler thread or an admin
    request, never from a student-facing request path."""
    now = now or _now()
    candidates = (
        db.query(Enrollment)
        .filter(Enrollment.payment_status != "paid", Enrollment.reminder_count < MAX_REMINDERS)
        .all()
    )
    due = [e for e in candidates if is_reminder_due(e, now)]
    if dry_run:
        return [e.id for e in due]

    sent: list[str] = []
    for enrollment in due:
        previous_count, previous_last = enrollment.reminder_count, enrollment.last_reminder_at
        subject, body = build_reminder(enrollment)  # built before the claim: ORM state is fresh here
        to, enrollment_id = enrollment.email, enrollment.id
        if not _claim(db, enrollment, now):
            continue  # another worker got there first
        try:
            send_email(to=to, subject=subject, body=body)
        except Exception:
            logger.exception("Reminder email failed for enrollment %s; will retry next run", enrollment_id)
            _release(db, enrollment_id, previous_count + 1, previous_last)
            continue
        sent.append(enrollment_id)
    return sent
