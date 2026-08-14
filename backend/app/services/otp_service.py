import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.db.models import EmailOtp
from app.services.email_service import send_otp_email


def _now() -> datetime:
    return datetime.now(timezone.utc)


def generate_and_send_otp(db: Session, email: str, purpose: str) -> str:
    """Creates a fresh 6-digit OTP for (email, purpose), stores it hashed,
    emails it, and returns the plaintext code. The plaintext is only ever
    used by the caller to optionally echo it back in dev mode (see
    send_otp_email / smtp_configured) — it is never stored unhashed."""
    otp = f"{random.randint(0, 999999):06d}"

    record = EmailOtp(
        email=email,
        otp_hash=hash_password(otp),
        purpose=purpose,
        expires_at=_now() + timedelta(minutes=settings.otp_expiry_minutes),
        verified=False,
    )
    db.add(record)
    db.commit()

    send_otp_email(email, otp, purpose)
    return otp


def verify_otp(db: Session, email: str, otp: str, purpose: str) -> bool:
    """Checks the OTP against the most recent unexpired, unverified record
    for this (email, purpose). On success, marks it verified and returns
    True; otherwise returns False without revealing which part failed."""
    record = (
        db.query(EmailOtp)
        .filter(
            EmailOtp.email == email,
            EmailOtp.purpose == purpose,
            EmailOtp.verified.is_(False),
            EmailOtp.expires_at > _now(),
        )
        .order_by(EmailOtp.created_at.desc())
        .first()
    )

    if not record or not verify_password(otp, record.otp_hash):
        return False

    record.verified = True
    record.verified_at = _now()
    db.commit()
    return True


def has_recent_verified_otp(db: Session, email: str, purpose: str) -> bool:
    """Used right before creating an account / resetting a password, to
    confirm the email was actually verified recently — not just that a
    verify-otp call happened at some point in the distant past."""
    cutoff = _now() - timedelta(minutes=settings.otp_verification_valid_minutes)
    record = (
        db.query(EmailOtp)
        .filter(
            EmailOtp.email == email,
            EmailOtp.purpose == purpose,
            EmailOtp.verified.is_(True),
            EmailOtp.verified_at > cutoff,
        )
        .order_by(EmailOtp.verified_at.desc())
        .first()
    )
    return record is not None