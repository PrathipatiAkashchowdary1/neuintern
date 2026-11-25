from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.base import get_db
from app.db.models import User

bearer_scheme = HTTPBearer(auto_error=False)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    # Two ways in: an Authorization header (API clients) or the httpOnly session
    # cookie (the website). The header wins if both are present.
    if credentials is not None:
        token, from_cookie = credentials.credentials, False
    else:
        token, from_cookie = request.cookies.get(settings.session_cookie_name), True

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    # CSRF guard. Browsers attach cookies automatically, so a cookie-authenticated
    # request that changes data must prove it came from our own frontend: a custom
    # header cannot be sent by a cross-site form, and a cross-origin fetch that sets
    # one needs a CORS preflight, which only the allow-listed origins pass.
    # (Header-authenticated requests are not exposed to CSRF, so they are exempt.)
    if from_cookie and request.method not in SAFE_METHODS and not request.headers.get("x-requested-with"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing X-Requested-With header")

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == payload.get("id")).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # A password reset revokes every token issued before it.
    if user.token_valid_after is not None:
        issued_at = payload.get("iatf")
        revoked_before = user.token_valid_after.replace(tzinfo=timezone.utc).timestamp()
        if issued_at is None or issued_at < revoked_before:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired. Please log in again.")

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user
