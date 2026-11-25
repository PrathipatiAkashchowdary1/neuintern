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