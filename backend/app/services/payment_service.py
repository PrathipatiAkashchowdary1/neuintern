"""Shared payment-confirmation logic.

Two independent paths can confirm a Razorpay payment: the browser calling
`/enrollments/{id}/payment/verify` after checkout, and Razorpay's server-to-
server webhook (which still fires if the student closes the tab mid-payment).
Both funnel through `mark_enrollment_paid`, which flips the status with a
single atomic UPDATE so that exactly one caller "wins" — only the winner sends
the invoice and unlocks the certificate. Retries and races are harmless.
"""

import logging
from datetime import datetime, timezone

from fastapi import BackgroundTasks
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.db.models import Enrollment
from app.services.certificate_service import is_course_complete, send_certificate_email, unlock_certificate
from app.services.email_service import run_email_task, send_email_with_attachments
from app.services.invoice_settings import details_for, snapshot_json
from app.services.pdf_service import generate_invoice_pdf

logger = logging.getLogger(__name__)


def invoice_data(enrollment: Enrollment) -> dict:
    paid_at = enrollment.paid_at or datetime.now(timezone.utc)
    details = details_for(enrollment)  # snapshot taken when the payment was confirmed
    return {
        "details": details,
        "invoiceNumber": f"{details['invoice_prefix']}-{paid_at.year}-{enrollment.id[:8].upper()}",
        "invoiceDate": paid_at.strftime("%B %d, %Y"),
        "studentName": enrollment.name,
        "email": enrollment.email,
        "phone": enrollment.phone,
        "programTitle": enrollment.program_title,
        "amount": enrollment.amount,
        "currency": enrollment.currency,
        "paymentId": enrollment.razorpay_payment_id or "—",
        "orderId": enrollment.razorpay_order_id or "—",
    }


def send_invoice_email(data: dict) -> None:
    """Takes the dict from invoice_data() (plain data, no ORM objects)."""
    pdf_buffer = generate_invoice_pdf(data)
    filename = f"NeuIntern-Invoice-{data['invoiceNumber']}.pdf"
    send_email_with_attachments(
        to=data["email"],
        subject=f"Payment Receipt — {data['invoiceNumber']}",
        body=(
            f"Hi {data['studentName']},\n\n"
            f"Thanks for your payment of {data['currency']} {data['amount']:.2f} for the "
            f"{data['programTitle']} certificate fee. Your receipt is attached.\n\n"
            f"— The NeuIntern Team"
        ),
        attachments=[(filename, pdf_buffer.read())],
    )


def _dispatch(background: BackgroundTasks | None, fn, *args) -> None:
    """Queue on the request's background tasks, or run inline when there is no
    request (e.g. called from a script). Failures are logged either way."""
    if background is not None:
        background.add_task(run_email_task, fn, *args)
    else:
        run_email_task(fn, *args)


def mark_enrollment_paid(
    db: Session,
    enrollment: Enrollment,
    payment_id: str,
    signature: str | None = None,
    background: BackgroundTasks | None = None,
) -> bool:
    """Marks the enrollment paid. Returns True only for the caller that
    actually performed the transition (False if it was already paid).
    Invoice / certificate emails are queued on `background` when given, so the
    HTTP response is not held up by PDF generation or SMTP."""
    result = db.execute(
        update(Enrollment)
        .where(Enrollment.id == enrollment.id, Enrollment.payment_status != "paid")
        .values(
            payment_status="paid",
            razorpay_payment_id=payment_id,
            razorpay_signature=signature,
            paid_at=datetime.now(timezone.utc),
            # Freeze the invoice details as they are right now (see invoice_settings.py).
            invoice_details_json=snapshot_json(db),
        )
    )
    db.commit()
    db.refresh(enrollment)
    if result.rowcount != 1:
        return False

    # Payment is already committed; a mail/PDF hiccup must not undo or fail it.
    _dispatch(background, send_invoice_email, invoice_data(enrollment))

    # Normally the hourly scheduler unlocks the certificate once the course
    # ends. Someone paying after that point shouldn't wait for the next tick.
    if is_course_complete(enrollment) and not enrollment.certificate_unlocked:
        try:
            cert_data = unlock_certificate(db, enrollment)
        except Exception:
            logger.exception("Certificate unlock failed for enrollment %s", enrollment.id)
        else:
            if cert_data is not None:  # None: another worker already unlocked and emailed it
                _dispatch(
                    background,
                    send_certificate_email,
                    enrollment.email,
                    enrollment.name,
                    enrollment.program_title,
                    cert_data,
                )

    return True
