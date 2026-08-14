from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.limiter import limiter
from app.core.security import create_access_token, hash_password, verify_password
from app.db.base import get_db
from app.db.models import User
from app.deps import get_current_user
from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.otp import ForgotPasswordRequest, ResetPasswordRequest, SendOtpRequest, VerifyOtpRequest
from app.services.otp_service import generate_and_send_otp, has_recent_verified_otp, verify_otp

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


def _token_response(user: User) -> dict:
    token = create_access_token({"id": user.id, "email": user.email, "role": user.role})
    return {"success": True, "data": {"token": token, "user": _user_out(user)}}


# ---------------------------------------------------------------------------
# Email OTP verification (used before registration) and password reset
# ---------------------------------------------------------------------------

@router.post("/send-otp")
@limiter.limit("5/hour")
async def send_otp(request: Request, payload: SendOtpRequest, db: Session = Depends(get_db)):
    if payload.purpose == "register":
        existing = db.query(User).filter(User.email == payload.email).first()
        if existing:
            raise HTTPException(status_code=409, detail="An account with this email already exists")

    otp = generate_and_send_otp(db, payload.email, payload.purpose)

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
    if not verify_otp(db, payload.email, payload.otp, payload.purpose):
        raise HTTPException(status_code=400, detail="Invalid or expired code. Please request a new one.")
    return {"success": True, "message": "Email verified."}


@router.post("/forgot-password")
@limiter.limit("5/hour")
async def forgot_password(request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    generic_message = "If an account exists for that email, a reset code has been sent."

    if not user:
        # Don't reveal whether the email is registered.
        return {"success": True, "message": generic_message}

    otp = generate_and_send_otp(db, payload.email, "reset_password")

    response = {"success": True, "message": generic_message}
    if not settings.smtp_configured:
        response["devOtp"] = otp
    return response


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    if not verify_otp(db, payload.email, payload.otp, "reset_password"):
        raise HTTPException(status_code=400, detail="Invalid or expired code. Please request a new one.")

    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="No account found for that email")

    user.password_hash = hash_password(payload.new_password)
    db.commit()

    return {"success": True, "message": "Password updated. You can now log in."}


# ---------------------------------------------------------------------------
# Register / login
# ---------------------------------------------------------------------------

@router.post("/register", status_code=201)
async def register(payload: RegisterRequest, db: Session = Depends(get_db)):
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

    return _token_response(user)


@router.post("/login")
async def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return _token_response(user)


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {"success": True, "data": _user_out(current_user)}


# Reserved for Phase 2
@router.post("/google", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def google_login_placeholder():
    return {"success": False, "message": "Google login is not available yet."}