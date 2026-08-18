"""Certificate unlock logic, shared by the payment-verification endpoint
(for the edge case where someone pays after the course has already ended)
and the background scheduler (the normal case — payment clears mid-course,
certificate unlocks later once it's actually over).

A certificate is only unlocked — and only emailed — once BOTH are true:
  1. payment_status == "paid"
  2. the course's completion date (enrollment date + COURSE_DURATION_DAYS)
     has passed
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.models import Certificate, Enrollment
from app.services.email_service import send_email_with_attachments
from app.services.pdf_service import generate_certificate_pdf

COURSE_DURATION_DAYS = 28


def _now() -> datetime:
    # Naive UTC — matches what SQLAlchemy hands back for DateTime columns,
    # see the same fix applied in app/routers/admin.py for why this matters.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def completion_date(enrollment: Enrollment) -> datetime:
    return enrollment.enrolled_at + timedelta(days=COURSE_DURATION_DAYS)


def is_course_complete(enrollment: Enrollment) -> bool:
    return _now() >= completion_date(enrollment)


def certificate_pdf_payload(enrollment: Enrollment) -> dict:
    end_date = completion_date(enrollment)
    issued_at = enrollment.certificate_issued_at or _now()
    return {
        "certificateId": enrollment.certificate_id,
        "studentName": enrollment.name,
        "programTitle": enrollment.program_title,
        "issuedOn": issued_at.strftime("%B %d, %Y"),
        "startDate": enrollment.enrolled_at.strftime("%B %d, %Y"),
        "endDate": end_date.strftime("%B %d, %Y"),
    }


def unlock_and_email_certificate(db: Session, enrollment: Enrollment) -> None:
    """Generates the certificate, marks it unlocked, and emails it.
    Caller must have already confirmed payment is complete AND the course
    completion date has passed — this function does not re-check either."""
    cert_id = f"NI-{datetime.now(timezone.utc).year}-{enrollment.id[:8].upper()}"
    enrollment.certificate_id = cert_id
    enrollment.certificate_unlocked = True
    enrollment.certificate_issued_at = _now()
    db.add(
        Certificate(
            certificate_id=cert_id,
            student_name=enrollment.name,
            program=enrollment.program_title,
            issued_on=enrollment.certificate_issued_at.date().isoformat(),
        )
    )
    db.commit()
    db.refresh(enrollment)

    data = certificate_pdf_payload(enrollment)
    pdf_buffer = generate_certificate_pdf(data)
    filename = f"NeuIntern-Certificate-{cert_id}.pdf"
    send_email_with_attachments(
        to=enrollment.email,
        subject=f"Your NeuIntern Certificate — {enrollment.program_title}",
        body=(
            f"Hi {enrollment.name},\n\n"
            f"Congratulations on completing the {enrollment.program_title} internship program! "
            f"Your certificate is attached (ID: {cert_id}).\n\n"
            f"You can also verify this certificate any time on our website.\n\n"
            f"— The NeuIntern Team"
        ),
        attachments=[(filename, pdf_buffer.read())],
    )


def process_due_certificates(db: Session) -> int:
    """Finds every enrollment that's paid but not yet unlocked, unlocks +
    emails the ones whose course completion date has now passed. Returns
    how many were processed. Called by the scheduler on a timer, and by an
    admin endpoint for an on-demand manual run."""
    candidates = (
        db.query(Enrollment)
        .filter(Enrollment.payment_status == "paid", Enrollment.certificate_unlocked.is_(False))
        .all()
    )

    processed = 0
    for enrollment in candidates:
        if is_course_complete(enrollment):
            unlock_and_email_certificate(db, enrollment)
            processed += 1

    return processed