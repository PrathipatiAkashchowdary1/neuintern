from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.limiter import limiter
from app.db.base import Base, SessionLocal, engine
from app.db.seed import seed_admin_user, seed_certificates, seed_programs
from app.routers import admin, auth, certificate, contact, enrollments, payments, programs, testimonials

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


# Normalize error responses to { success: false, message } so the frontend's
# existing axios error handling (which reads response.data.message) works
# identically whether it's talking to this backend or the Node one.
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"success": False, "message": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    first_error = exc.errors()[0]
    message = first_error.get("msg", "Invalid request")
    return JSONResponse(status_code=422, content={"success": False, "message": message})


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_certificates(db)
        seed_programs(db)
        seed_admin_user(db)
    finally:
        db.close()


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
