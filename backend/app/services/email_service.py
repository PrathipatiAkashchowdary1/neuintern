"""Sends real email via SMTP when configured. In development (or whenever
SMTP isn't configured yet), OTP emails are logged to the console instead of
sent, and the OTP is echoed back in the API response so the flow stays
testable without a mail server — the same "gracefully degrade, don't crash"
pattern used for Razorpay elsewhere in this backend.
"""

import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings


def send_email(to: str, subject: str, body: str) -> None:
    if not settings.smtp_configured:
        print(f"[DEV EMAIL — SMTP not configured] To: {to}\nSubject: {subject}\n\n{body}\n")
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.smtp_from, [to], msg.as_string())


def send_email_with_attachments(to: str, subject: str, body: str, attachments: list[tuple[str, bytes]]) -> None:
    """Like send_email, but with one or more PDF attachments.
    `attachments` is a list of (filename, pdf_bytes) tuples.

    In dev mode (no SMTP configured), logs the email body and attachment
    filenames to the console instead of sending — same fallback pattern as
    every other email in this backend, so nothing crashes without SMTP set up."""
    if not settings.smtp_configured:
        names = ", ".join(name for name, _ in attachments)
        print(f"[DEV EMAIL — SMTP not configured] To: {to}\nSubject: {subject}\nAttachments: {names}\n\n{body}\n")
        return

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg.attach(MIMEText(body))

    for filename, pdf_bytes in attachments:
        part = MIMEApplication(pdf_bytes, _subtype="pdf")
        part.add_header("Content-Disposition", "attachment", filename=filename)
        msg.attach(part)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.smtp_from, [to], msg.as_string())


def send_otp_email(to: str, otp: str, purpose: str) -> None:
    if purpose == "reset_password":
        subject = "Your NeuIntern password reset code"
        body = (
            f"Your password reset code is: {otp}\n\n"
            f"This code expires in {settings.otp_expiry_minutes} minutes. "
            f"If you didn't request this, you can safely ignore this email."
        )
    else:
        subject = "Verify your email for NeuIntern"
        body = (
            f"Your NeuIntern verification code is: {otp}\n\n"
            f"This code expires in {settings.otp_expiry_minutes} minutes. "
            f"Enter it to finish creating your account."
        )
    send_email(to, subject, body)