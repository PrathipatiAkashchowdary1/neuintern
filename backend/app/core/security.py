import base64
import time
import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expires_minutes)
    # iat lets a password reset invalidate every token issued before it.
    # iatf is a high-resolution issued-at (the standard iat is whole seconds, so a
    # login in the same second as a password reset would look older than the reset).
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "iatf": time.time()})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


# --- Unsubscribe links -------------------------------------------------------
# Stateless and non-expiring (an unsubscribe link in an old email must keep
# working). Token = "<user_id>.<HMAC of user_id under the JWT secret>", with a
# purpose prefix in the MAC so it can never be confused with another token.


def _unsubscribe_mac(user_id: str) -> str:
    digest = hmac.new(settings.jwt_secret.encode(), f"unsubscribe:{user_id}".encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def make_unsubscribe_token(user_id: str) -> str:
    return f"{user_id}.{_unsubscribe_mac(user_id)}"


def verify_unsubscribe_token(token: str) -> str | None:
    """Returns the user id the token was issued for, or None if it is forged."""
    user_id, _, mac = token.partition(".")
    if not user_id or not mac or not hmac.compare_digest(mac, _unsubscribe_mac(user_id)):
        return None
    return user_id
