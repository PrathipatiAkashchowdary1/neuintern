from datetime import timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.background import BackgroundScheduler
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.limiter import limiter
from app.db.base import SessionLocal
from app.db.seed import seed_admin_user, seed_certificates, seed_programs
from app.routers import admin, auth, certificate, contact, enrollments, payments, programs, testimonials, unsubscribe
from app.services.certificate_service import process_due_certificates
from app.services.reminder_service import send_due_reminders
from app.services.upload_service import upload_root

app = FastAPI(title=settings.app_name)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"success": False, "message": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    first_error = exc.errors()[0]
    message = first_error.get("msg", "Invalid request")
    return JSONResponse(status_code=422, content={"success": False, "message": message})


def _run_certificate_check() -> None:
    """Scheduler job: unlocks + emails any certificate whose course
    completion date has now passed. Runs on its own DB session since it's
    not triggered by a request (no FastAPI dependency injection here)."""
    db = SessionLocal()
    try:
        processed = process_due_certificates(db)
        if processed:
            print(f"[certificate-scheduler] Unlocked and emailed {processed} certificate(s).")
    finally:
        db.close()


def _run_reminder_check() -> None:
    """Scheduler job: emails students who have stalled before paying. A no-op
    unless REMINDERS_ENABLED is set."""
    if not settings.reminders_enabled:
        return
    db = SessionLocal()
    try:
        sent = send_due_reminders(db)
        if sent:
            print(f"[reminder-scheduler] Sent {len(sent)} reminder email(s).")
    finally:
        db.close()


scheduler = BackgroundScheduler()


@app.on_event("startup")
def on_startup():
    # Schema is managed by Alembic (`alembic upgrade head`), not create_all().
    db = SessionLocal()
    try:
        seed_certificates(db)
        seed_programs(db)
        seed_admin_user(db)
    finally:
        db.close()

    # Checks hourly for enrollments whose course completion date has passed
    # since the last check, and unlocks/emails their certificates. Also runs
    # once immediately on startup so nothing sits stale after a restart.
    scheduler.add_job(_run_certificate_check, "interval", hours=1, id="certificate_check", replace_existing=True)
    scheduler.start()
    _run_certificate_check()

    # Once a day at 10:30 UTC (16:00 IST), a sensible hour to receive mail.
    # Deliberately NOT run at startup: restarts must not trigger sends.
    scheduler.add_job(
        _run_reminder_check, "cron", hour=10, minute=30, timezone=timezone.utc,
        id="reminder_check", replace_existing=True,
    )


@app.on_event("shutdown")
def on_shutdown():
    scheduler.shutdown(wait=False)


@app.get("/api/health")
async def health():
    from datetime import datetime, timezone

    return {"success": True, "message": "NeuIntern API is running", "time": datetime.now(timezone.utc).isoformat()}


app.include_router(programs.router)
app.include_router(testimonials.router)
app.include_router(contact.router)
app.include_router(certificate.router)
app.include_router(auth.router)
app.include_router(payments.router)
app.include_router(enrollments.router)
app.include_router(admin.router)
app.include_router(unsubscribe.router)

# Admin-uploaded program images (already validated + re-encoded on upload).
app.mount("/uploads", StaticFiles(directory=upload_root()), name="uploads")