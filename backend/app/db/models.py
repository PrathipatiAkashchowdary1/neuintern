import uuid
from datetime import datetime, timezone

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

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    full_name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    phone: Mapped[str] = mapped_column(String)
    degree: Mapped[str] = mapped_column(String)
    branch: Mapped[str] = mapped_column(String)
    current_year: Mapped[str] = mapped_column(String)
    password_hash: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="student")  # student | admin
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ContactSubmission(Base):
    __tablename__ = "contact_submissions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    subject: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class NewsletterSubscriber(Base):
    __tablename__ = "newsletter_subscribers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    subscribed_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Certificate(Base):
    __tablename__ = "certificates"

    certificate_id: Mapped[str] = mapped_column(String, primary_key=True)
    student_name: Mapped[str] = mapped_column(String)
    program: Mapped[str] = mapped_column(String)
    issued_on: Mapped[str] = mapped_column(String)


class Program(Base):
    """DB-backed program catalog so admins can edit it. Seeded once from
    app/data/programs.json on first run (see db/seed.py)."""

    __tablename__ = "programs"

    slug: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)
    tagline: Mapped[str] = mapped_column(Text)
    image: Mapped[str] = mapped_column(String)
    duration: Mapped[str] = mapped_column(String, default="4 Weeks")
    price: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String, default="INR")
    mode: Mapped[str] = mapped_column(String, default="Remote")
    certificate: Mapped[bool] = mapped_column(Boolean, default=True)
    live_projects: Mapped[int] = mapped_column(Integer, default=1)
    skills_json: Mapped[str] = mapped_column(Text, default="[]")
    tools_json: Mapped[str] = mapped_column(Text, default="[]")
    outcomes_json: Mapped[str] = mapped_column(Text, default="[]")
    eligibility: Mapped[str] = mapped_column(Text, default="")
    curriculum_json: Mapped[str] = mapped_column(Text, default="[]")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class EmailOtp(Base):
    """Tracks one-time codes for both email verification (before account
    creation) and password reset. `purpose` keeps the two flows from being
    mixed up; `verified`/`verified_at` let registration check "was this
    email actually verified recently" without needing a column on User
    for accounts that don't exist yet."""

    __tablename__ = "email_otps"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    email: Mapped[str] = mapped_column(String, index=True)
    otp_hash: Mapped[str] = mapped_column(String)
    purpose: Mapped[str] = mapped_column(String)  # "register" | "reset_password"
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Enrollment(Base):
    """One record per student-program enrollment, tracking the full journey:
    enroll -> offer letter (implicit, always available) -> task submission ->
    ₹150 certificate payment -> certificate unlock.
    """

    __tablename__ = "enrollments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    user_id: Mapped[str] = mapped_column(String, index=True)

    program_slug: Mapped[str] = mapped_column(String)
    program_title: Mapped[str] = mapped_column(String)

    # Snapshot of student info at enrollment time (also available via User)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    phone: Mapped[str] = mapped_column(String)

    enrolled_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    # Task submission
    github_link: Mapped[str] = mapped_column(String, nullable=True)
    linkedin_link: Mapped[str] = mapped_column(String, nullable=True)
    task_submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Certificate payment (flat fee, independent of program price)
    amount: Mapped[float] = mapped_column(Float, default=CERTIFICATE_FEE_INR)
    currency: Mapped[str] = mapped_column(String, default="INR")
    razorpay_order_id: Mapped[str] = mapped_column(String, nullable=True)
    razorpay_payment_id: Mapped[str] = mapped_column(String, nullable=True)
    razorpay_signature: Mapped[str] = mapped_column(String, nullable=True)
    payment_status: Mapped[str] = mapped_column(String, default="unpaid")  # unpaid | pending | paid | failed
    paid_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Certificate
    certificate_id: Mapped[str] = mapped_column(String, nullable=True)
    certificate_unlocked: Mapped[bool] = mapped_column(Boolean, default=False)
    certificate_issued_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)