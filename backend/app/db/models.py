import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def gen_id() -> str:
    return uuid.uuid4().hex[:16]


def now() -> datetime:
    return datetime.now(timezone.utc)


CERTIFICATE_FEE_INR = 150


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=gen_id
    )
    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20))
    degree: Mapped[str] = mapped_column(String(100))
    branch: Mapped[str] = mapped_column(String(150))
    current_year: Mapped[str] = mapped_column(String(50))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="student")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    # Tokens issued before this moment are rejected (set on password reset).
    token_valid_after: Mapped[datetime] = mapped_column(
        DateTime, nullable=True
    )
    # Set by the unsubscribe link in reminder emails; stops all reminders.
    reminders_opt_out: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=sa.false()
    )


class ContactSubmission(Base):
    __tablename__ = "contact_submissions"

    id: Mapped[str] = mapped_column(
        String(16), primary_key=True, default=gen_id
    )
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class NewsletterSubscriber(Base):
    __tablename__ = "newsletter_subscribers"

    id: Mapped[str] = mapped_column(
        String(16), primary_key=True, default=gen_id
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True
    )
    subscribed_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Certificate(Base):
    __tablename__ = "certificates"

    certificate_id: Mapped[str] = mapped_column(
        String(50), primary_key=True
    )
    student_name: Mapped[str] = mapped_column(String(255))
    program: Mapped[str] = mapped_column(String(255))
    issued_on: Mapped[str] = mapped_column(String(50))


class Program(Base):
    """DB-backed program catalog."""

    __tablename__ = "programs"

    slug: Mapped[str] = mapped_column(
        String(150), primary_key=True
    )
    title: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(100))
    tagline: Mapped[str] = mapped_column(Text)
    image: Mapped[str] = mapped_column(String(500))
    duration: Mapped[str] = mapped_column(
        String(50), default="4 Weeks"
    )
    price: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(
        String(10), default="INR"
    )
    mode: Mapped[str] = mapped_column(
        String(50), default="Remote"
    )
    certificate: Mapped[bool] = mapped_column(
        Boolean, default=True
    )
    live_projects: Mapped[int] = mapped_column(
        Integer, default=1
    )
    skills_json: Mapped[str] = mapped_column(
        Text, default="[]"
    )
    tools_json: Mapped[str] = mapped_column(
        Text, default="[]"
    )
    outcomes_json: Mapped[str] = mapped_column(
        Text, default="[]"
    )
    eligibility: Mapped[str] = mapped_column(
        Text, default=""
    )
    curriculum_json: Mapped[str] = mapped_column(
        Text, default="[]"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True
    )


class EmailOtp(Base):
    __tablename__ = "email_otps"

    id: Mapped[str] = mapped_column(
        String(16), primary_key=True, default=gen_id
    )
    email: Mapped[str] = mapped_column(
        String(255), index=True
    )
    otp_hash: Mapped[str] = mapped_column(
        String(255)
    )
    purpose: Mapped[str] = mapped_column(
        String(30)
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime
    )
    verified: Mapped[bool] = mapped_column(
        Boolean, default=False
    )
    verified_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=now
    )


class Enrollment(Base):
    __tablename__ = "enrollments"

    id: Mapped[str] = mapped_column(
        String(16), primary_key=True, default=gen_id
    )
    user_id: Mapped[str] = mapped_column(
        String(16), index=True
    )

    program_slug: Mapped[str] = mapped_column(
        String(150)
    )
    program_title: Mapped[str] = mapped_column(
        String(255)
    )

    name: Mapped[str] = mapped_column(
        String(255)
    )
    email: Mapped[str] = mapped_column(
        String(255)
    )
    phone: Mapped[str] = mapped_column(
        String(20)
    )

    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime, default=now
    )

    github_link: Mapped[str] = mapped_column(
        String(500), nullable=True
    )
    linkedin_link: Mapped[str] = mapped_column(
        String(500), nullable=True
    )
    task_submitted_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True
    )

    amount: Mapped[float] = mapped_column(
        Float, default=CERTIFICATE_FEE_INR
    )
    currency: Mapped[str] = mapped_column(
        String(10), default="INR"
    )
    razorpay_order_id: Mapped[str] = mapped_column(
        String(100), nullable=True
    )
    razorpay_payment_id: Mapped[str] = mapped_column(
        String(100), nullable=True
    )
    razorpay_signature: Mapped[str] = mapped_column(
        String(255), nullable=True
    )
    payment_status: Mapped[str] = mapped_column(
        String(20), default="unpaid"
    )
    paid_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True
    )

    certificate_id: Mapped[str] = mapped_column(
        String(50), nullable=True
    )
    certificate_unlocked: Mapped[bool] = mapped_column(
        Boolean, default=False
    )
    certificate_issued_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True
    )

    # Reminder emails for students who stall before paying (see
    # app/services/reminder_service.py).
    reminder_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    last_reminder_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True
    )

    # Invoice details (company block, GST rate, wording) copied at payment time
    # so an issued invoice never changes when an admin edits the settings.
    # NULL for payments made before this existed (they use the original defaults).
    invoice_details_json: Mapped[str] = mapped_column(
        Text, nullable=True
    )


class InvoiceSettings(Base):
    """Single-row table (id = 1): the invoice details admins can edit.
    Defaults live in app/services/invoice_settings.py, not in the database."""

    __tablename__ = "invoice_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    company_name: Mapped[str] = mapped_column(String(120))
    address: Mapped[str] = mapped_column(Text)
    gstin: Mapped[str] = mapped_column(String(15), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(30), default="")
    gst_rate: Mapped[float] = mapped_column(Float, default=18.0)
    invoice_prefix: Mapped[str] = mapped_column(String(10), default="INV")
    document_title: Mapped[str] = mapped_column(String(40))
    item_description: Mapped[str] = mapped_column(String(80))
    team_name: Mapped[str] = mapped_column(String(80), default="")
    brand_line: Mapped[str] = mapped_column(String(100), default="")
    footer_note: Mapped[str] = mapped_column(String(100), default="")


class LoginThrottle(Base):
    """Failed-attempt counter per key (for example "login:<email>"), kept in the
    database so the limit holds across server workers and restarts."""

    __tablename__ = "login_throttle"

    key: Mapped[str] = mapped_column(String(320), primary_key=True)
    failures: Mapped[int] = mapped_column(Integer, default=0)
    window_start: Mapped[datetime] = mapped_column(DateTime, default=now)
    locked_until: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class JobLock(Base):
    """One row per scheduled job; see app/services/job_lock.py."""

    __tablename__ = "job_locks"

    name: Mapped[str] = mapped_column(String(100), primary_key=True)
    locked_until: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_run_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class EmailOutbox(Base):
    """An email waiting to be (re)sent; see app/services/outbox_service.py."""

    __tablename__ = "email_outbox"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=gen_id)
    kind: Mapped[str] = mapped_column(String(30))
    to_email: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(255))
    payload: Mapped[str] = mapped_column(Text, nullable=True)  # JSON; cleared once sent
    dedupe_key: Mapped[str] = mapped_column(String(120), unique=True, nullable=True)
    status: Mapped[str] = mapped_column(String(10), default="pending", index=True)  # pending | sent | failed
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    locked_until: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
