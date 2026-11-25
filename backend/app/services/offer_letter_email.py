"""The offer-letter email (PDF + SMTP). Lives here so the email outbox can call it."""

from app.services.email_service import send_email_with_attachments
from app.services.pdf_service import generate_offer_letter_pdf


def send_offer_letter_email(to: str, name: str, program_title: str, enrollment_id: str, pdf_data: dict) -> None:
    """PDF + SMTP from plain data (no ORM objects), so it can run as a
    background task after the request's DB session is closed."""
    pdf_buffer = generate_offer_letter_pdf(pdf_data)
    filename = f"NeuIntern-Offer-Letter-{enrollment_id[:8]}.pdf"
    send_email_with_attachments(
        to=to,
        subject=f"Your NeuIntern Offer Letter — {program_title}",
        body=(
            f"Hi {name},\n\n"
            f"Congratulations on enrolling in the {program_title} internship program! "
            f"Your official offer letter is attached.\n\n"
            f"Next step: log in to your dashboard and submit your task (GitHub + LinkedIn links) "
            f"to move on to certification.\n\n"
            f"— The NeuIntern Team"
        ),
        attachments=[(filename, pdf_buffer.read())],
    )
