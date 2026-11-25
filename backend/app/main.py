from datetime import timedelta, timezone

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
from app.core.startup_checks import validate_admin_account, validate_production_settings
from app.db.base import SessionLocal
from app.db.seed import DEFAULT_ADMIN, seed_admin_user, seed_certificates, seed_programs
from app.routers import (
    admin,
    auth,
    certificate,
    contact,
    enrollments,
    invoice_settings,
    payments,
    programs,
    testimonials,
    unsubscribe,
)
from app.services.certificate_service import process_due_certificates
from app.services.job_lock import run_exclusive
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
    # Keep exc.headers: Retry-After on 429s, WWW-Authenticate on 401s, and so on.
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.detail},
        headers=exc.headers,
    )


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


# Every worker runs a scheduler, so each tick goes through a database lock and only
# one worker actually does the work (see app/services/job_lock.py).
def _scheduled_certificate_check() -> None:
    run_exclusive("certificate_check", _run_certificate_check, min_interval=timedelta(minutes=50), ttl=timedelta(minutes=30))


def _scheduled_reminder_check() -> None:
    run_exclusive("reminder_check", _run_reminder_check, min_interval=timedelta(hours=20), ttl=timedelta(hours=1))


scheduler = BackgroundScheduler()


@app.on_event("startup")
def on_startup():
    validate_production_settings()  # refuses to boot a production server with unsafe settings
    # Schema is managed by Alembic (`alembic upgrade head`), not create_all().
    db = SessionLocal()
    try:
        seed_certificates(db)
        seed_programs(db)
        seed_admin_user(db)
        validate_admin_account(db, DEFAULT_ADMIN["password"], DEFAULT_ADMIN["email"])
    finally:
        db.close()

    if not settings.scheduler_enabled:
        return  # this process serves requests only; another one runs the jobs

    # Checks hourly for enrollments whose course completion date has passed
    # since the last check, and unlocks/emails their certificates. Also runs
    # once immediately on startup so nothing sits stale after a restart (the
    # 1-minute interval just stops N workers starting together from all running it).
    scheduler.add_job(_scheduled_certificate_check, "interval", hours=1, id="certificate_check", replace_existing=True)

    # Once a day at 10:30 UTC (16:00 IST), a sensible hour to receive mail.
    # Deliberately NOT run at startup: restarts must not trigger sends.
    scheduler.add_job(
        _scheduled_reminder_check, "cron", hour=10, minute=30, timezone=timezone.utc,
        id="reminder_check", replace_existing=True,
    )
    scheduler.start()
    run_exclusive("certificate_check", _run_certificate_check, min_interval=timedelta(minutes=1), ttl=timedelta(minutes=30))


@app.on_event("shutdown")
def on_shutdown():
    if scheduler.running:  # not started when SCHEDULER_ENABLED=false
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
app.include_router(invoice_settings.router)
app.include_router(unsubscribe.router)

# Admin-uploaded program images (already validated + re-encoded on upload).
app.mount("/uploads", StaticFiles(directory=upload_root()), name="uploads")