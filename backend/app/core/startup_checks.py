"""Refuses to start a PRODUCTION server with settings that would make it unsafe.
In development everything is allowed so local setup stays frictionless."""

from sqlalchemy.orm import Session

from app.core.config import Settings, settings as _settings
from app.core.security import verify_password
from app.db.models import User

KNOWN_DEFAULT_SECRETS = {"dev_secret_change_me", "change_this_to_a_long_random_string", "changeme", "secret"}
MIN_SECRET_LENGTH = 32


class UnsafeConfiguration(RuntimeError):
    pass


def validate_production_settings(s: Settings | None = None) -> None:
    s = s or _settings
    if not s.is_production:
        return

    problems = []
    if s.jwt_secret in KNOWN_DEFAULT_SECRETS or len(s.jwt_secret) < MIN_SECRET_LENGTH:
        problems.append(
            f"JWT_SECRET must be a random value of at least {MIN_SECRET_LENGTH} characters "
            "(generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\")."
        )
    if "*" in s.cors_origins:
        problems.append("CORS_ORIGIN must list your site's exact origin(s), not *, because sessions use cookies.")
    if not s.session_cookie_secure:
        problems.append("COOKIE_SECURE must not be disabled in production (the session cookie would travel over plain HTTP).")
    if s.cookie_samesite.lower() == "none" and not s.session_cookie_secure:
        problems.append("COOKIE_SAMESITE=none requires secure cookies.")
    if problems:
        raise UnsafeConfiguration("Unsafe production configuration:\n  - " + "\n  - ".join(problems))


def validate_admin_account(db: Session, default_password: str, default_email: str, s: Settings | None = None) -> None:
    """Production only: refuse to run while the admin account still has the
    published default password."""
    s = s or _settings
    if not s.is_production:
        return
    admin = db.query(User).filter(User.email == default_email, User.role == "admin").first()
    if admin and verify_password(default_password, admin.password_hash):
        raise UnsafeConfiguration(
            f"The admin account ({default_email}) still has the default password. Change it "
            "(use Forgot password on the login page) and restart."
        )
