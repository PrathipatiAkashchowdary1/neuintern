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
from app.services.certificate_service import certificate_outbox_id, is_course_complete, unlock_certificate
from app.services.email_service import send_email_with_attachments
from app.services.outbox_service import add as queue_email, send_soon
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


def mark_enrollment_paid(
    db: Session,
    enrollment: Enrollment,
    payment_id: str,
    signature: str | None = None,
    background: BackgroundTasks | None = None,
) -> bool:
    """Marks the enrollment paid. Returns True only for the caller that
    actually performed the transition (False if it was already paid).
    The invoice / certificate emails are saved to the email outbox with the payment
    and sent from `background` when given (so the HTTP response is not held up by
    PDF generation or SMTP), or inline when there is no request."""
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
    if result.rowcount != 1:
        db.commit()
        db.refresh(enrollment)
        return False

    # The invoice email is saved in the SAME transaction as the payment, so a paid
    # enrollment can never lose its receipt (it is retried until it sends).
    db.refresh(enrollment)  # the row as just updated, inside this transaction
    invoice = queue_email(
        db,
        "invoice",
        to=enrollment.email,
        subject=f"Payment Receipt — {enrollment.program_title}",
        payload={"data": invoice_data(enrollment)},
        dedupe_key=f"invoice:{enrollment.id}",
    )
    invoice_id = invoice.id
    db.commit()
    db.refresh(enrollment)

    to_send = [invoice_id]

    # Normally the hourly scheduler unlocks the certificate once the course
    # ends. Someone paying after that point shouldn't wait for the next tick.
    if is_course_complete(enrollment) and not enrollment.certificate_unlocked:
        try:
            cert_data = unlock_certificate(db, enrollment)  # queues the certificate email itself
        except Exception:
            logger.exception("Certificate unlock failed for enrollment %s", enrollment.id)
        else:
            if cert_data is not None:  # None: another worker already unlocked it
                certificate_id = certificate_outbox_id(db, cert_data["certificateId"])
                if certificate_id:
                    to_send.append(certificate_id)

    send_soon(background, *to_send)
    return True
