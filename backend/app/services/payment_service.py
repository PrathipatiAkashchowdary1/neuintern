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

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.db.models import Enrollment
from app.services.certificate_service import is_course_complete, unlock_and_email_certificate
from app.services.email_service import send_email_with_attachments
from app.services.pdf_service import generate_invoice_pdf

logger = logging.getLogger(__name__)


def invoice_data(enrollment: Enrollment) -> dict:
    paid_at = enrollment.paid_at or datetime.now(timezone.utc)
    return {
        "invoiceNumber": f"INV-{paid_at.year}-{enrollment.id[:8].upper()}",
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


def email_invoice(enrollment: Enrollment) -> None:
    data = invoice_data(enrollment)
    pdf_buffer = generate_invoice_pdf(data)
    filename = f"NeuIntern-Invoice-{data['invoiceNumber']}.pdf"
    send_email_with_attachments(
        to=enrollment.email,
        subject=f"Payment Receipt — {data['invoiceNumber']}",
        body=(
            f"Hi {enrollment.name},\n\n"
            f"Thanks for your payment of {enrollment.currency} {enrollment.amount:.2f} for the "
            f"{enrollment.program_title} certificate fee. Your receipt is attached.\n\n"
            f"— The NeuIntern Team"
        ),
        attachments=[(filename, pdf_buffer.read())],
    )


def mark_enrollment_paid(
    db: Session,
    enrollment: Enrollment,
    payment_id: str,
    signature: str | None = None,
) -> bool:
    """Marks the enrollment paid. Returns True only for the caller that
    actually performed the transition (False if it was already paid)."""
    result = db.execute(
        update(Enrollment)
        .where(Enrollment.id == enrollment.id, Enrollment.payment_status != "paid")
        .values(
            payment_status="paid",
            razorpay_payment_id=payment_id,
            razorpay_signature=signature,
            paid_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    db.refresh(enrollment)
    if result.rowcount != 1:
        return False

    # Payment is already committed; a mail/PDF hiccup must not undo or fail it.
    try:
        email_invoice(enrollment)
    except Exception:
        logger.exception("Invoice email failed for enrollment %s", enrollment.id)

    # Normally the hourly scheduler unlocks the certificate once the course
    # ends. Someone paying after that point shouldn't wait for the next tick.
    if is_course_complete(enrollment) and not enrollment.certificate_unlocked:
        try:
            unlock_and_email_certificate(db, enrollment)
            db.refresh(enrollment)
        except Exception:
            logger.exception("Certificate unlock failed for enrollment %s", enrollment.id)

    return True
