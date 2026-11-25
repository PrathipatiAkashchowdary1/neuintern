from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.limiter import limiter
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.db.base import get_db
from app.db.models import User
from app.deps import get_current_user
from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.otp import ForgotPasswordRequest, ResetPasswordRequest, SendOtpRequest, VerifyOtpRequest
from app.services import session_service
from app.services.otp_service import generate_and_send_otp, has_recent_verified_otp, verify_otp
from app.services.throttle import ensure_not_locked, make_key, record_failure, record_success

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_out(user: User) -> dict:
    return {
        "id": user.id,
        "fullName": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "degree": user.degree,
        "branch": user.branch,
        "currentYear": user.current_year,
        "role": user.role,
    }


# Verified when the email is unknown so a login for a real account and one for a
# non-existent account take the same time (no account discovery by timing).
_DUMMY_HASH = hash_password("timing-equalisation-placeholder")


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.jwt_expires_minutes * 60,
        httponly=True,  # not readable by page scripts, so XSS cannot steal the session
        secure=settings.session_cookie_secure,
        samesite=settings.cookie_samesite.lower(),
        domain=settings.cookie_domain or None,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        domain=settings.cookie_domain or None,
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite.lower(),
    )


def _token_response(user: User, response: Response, request: Request, db: Session) -> dict:
    # Every login is a server-side session (see app/services/session_service.py) so it can be
    # cancelled individually; the token carries its id as `jti`.
    session = session_service.create(
        db, user, user_agent=request.headers.get("user-agent"), ip=request.client.host if request.client else None
    )
    token = create_access_token({"id": user.id, "email": user.email, "role": user.role, "jti": session.id})
    _set_session_cookie(response, token)
    # The token is still returned for non-browser API clients; the website ignores it.
    return {"success": True, "data": {"token": token, "user": _user_out(user)}}


# ---------------------------------------------------------------------------
# Email OTP verification (used before registration) and password reset
# ---------------------------------------------------------------------------

@router.post("/send-otp")
@limiter.limit("5/hour")
async def send_otp(
    request: Request, payload: SendOtpRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    if payload.purpose == "register":
        existing = db.query(User).filter(User.email == payload.email).first()
        if existing:
            raise HTTPException(status_code=409, detail="An account with this email already exists")

    otp = generate_and_send_otp(db, payload.email, payload.purpose, background_tasks)

    response = {"success": True, "message": f"A verification code has been sent to {payload.email}."}
    # Dev convenience only: with no SMTP configured, echo the code back so
    # the flow is testable without a real mail server. Never happens once
    # SMTP is configured (see app/services/email_service.py).
    if not settings.smtp_configured:
        response["devOtp"] = otp
    return response


@router.post("/verify-otp")
@limiter.limit("10/hour")
async def verify_otp_route(request: Request, payload: VerifyOtpRequest, db: Session = Depends(get_db)):
    key = make_key("otp", payload.email)
    ensure_not_locked(db, key)
    if not verify_otp(db, payload.email, payload.otp, payload.purpose):
        record_failure(db, key)
        raise HTTPException(status_code=400, detail="Invalid or expired code. Please request a new one.")
    record_success(db, key)
    return {"success": True, "message": "Email verified."}


@router.post("/forgot-password")
@limiter.limit("5/hour")
async def forgot_password(
    request: Request, payload: ForgotPasswordRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == payload.email).first()
    generic_message = "If an account exists for that email, a reset code has been sent."

    if not user:
        # Don't reveal whether the email is registered.
        return {"success": True, "message": generic_message}

    otp = generate_and_send_otp(db, payload.email, "reset_password", background_tasks)

    response = {"success": True, "message": generic_message}
    if not settings.smtp_configured:
        response["devOtp"] = otp
    return response


@router.post("/reset-password")
@limiter.limit("20/hour")
async def reset_password(request: Request, payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    key = make_key("otp", payload.email)
    ensure_not_locked(db, key)
    if not verify_otp(db, payload.email, payload.otp, "reset_password"):
        record_failure(db, key)
        raise HTTPException(status_code=400, detail="Invalid or expired code. Please request a new one.")
    record_success(db, key)

    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="No account found for that email")

    user.password_hash = hash_password(payload.new_password)
    # Log out everywhere: any token issued before this moment stops working.
    user.token_valid_after = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    session_service.revoke_all(db, user.id)  # every device is logged out
    record_success(db, make_key("login", payload.email))  # a reset also clears a login lockout

    return {"success": True, "message": "Password updated. You can now log in."}


# ---------------------------------------------------------------------------
# Register / login
# ---------------------------------------------------------------------------

@router.post("/register", status_code=201)
@limiter.limit("20/hour")
async def register(request: Request, response: Response, payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    if not has_recent_verified_otp(db, payload.email, "register"):
        raise HTTPException(
            status_code=400,
            detail="Please verify your email with the code we sent before creating your account.",
        )

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        degree=payload.degree,
        branch=payload.branch,
        current_year=payload.current_year,
        password_hash=hash_password(payload.password),
        role="student",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return _token_response(user, response, request, db)


@router.post("/login")
@limiter.limit("60/minute")
async def login(request: Request, response: Response, payload: LoginRequest, db: Session = Depends(get_db)):
    key = make_key("login", payload.email)
    ensure_not_locked(db, key)

    user = db.query(User).filter(User.email == payload.email).first()
    if user:
        password_ok = verify_password(payload.password, user.password_hash)
    else:
        verify_password(payload.password, _DUMMY_HASH)
        password_ok = False

    if not password_ok:
        record_failure(db, key)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    record_success(db, key)
    return _token_response(user, response, request, db)


@router.post("/logout")
async def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    """Ends THIS login: the session is revoked on the server (so a copy of the token stops
    working too) and the cookie is cleared. Safe to call when not logged in."""
    authorization = request.headers.get("authorization", "")
    token = authorization[7:] if authorization.lower().startswith("bearer ") else request.cookies.get(settings.session_cookie_name)
    payload = decode_access_token(token) if token else None
    if payload and payload.get("jti") and payload.get("id"):
        session_service.revoke(db, payload["jti"], payload["id"])
    _clear_session_cookie(response)
    return {"success": True, "message": "Logged out."}


@router.post("/logout-all")
async def logout_all(response: Response, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Logs this account out on EVERY device, including this one."""
    revoked = session_service.revoke_all(db, current_user.id)
    # Also cuts off tokens issued before sessions existed (they have no session row to revoke).
    current_user.token_valid_after = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    _clear_session_cookie(response)
    return {"success": True, "message": "Logged out of all devices.", "data": {"revoked": revoked}}


@router.get("/sessions")
async def list_sessions(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The devices currently logged in to this account."""
    current_id = getattr(request.state, "session_id", None)
    items = [
        {
            "id": s.id,
            "device": session_service.describe_device(s.user_agent),
            "ip": s.ip,
            "createdAt": s.created_at.isoformat(),
            "lastSeenAt": s.last_seen_at.isoformat(),
            "current": s.id == current_id,
        }
        for s in session_service.list_active(db, current_user.id)
    ]
    return {"success": True, "data": items}


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Logs out one device. Only your own sessions can be revoked."""
    if not session_service.revoke(db, session_id, current_user.id):
        raise HTTPException(status_code=404, detail="Session not found")
    if session_id == getattr(request.state, "session_id", None):
        _clear_session_cookie(response)  # you logged yourself out
    return {"success": True, "message": "Device logged out."}


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {"success": True, "data": _user_out(current_user)}


# Reserved for Phase 2
@router.post("/google", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def google_login_placeholder():
    return {"success": False, "message": "Google login is not available yet."}