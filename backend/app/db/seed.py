import json

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.data.catalog import PROGRAMS, TESTIMONIALS  # noqa: F401 (testimonials stay JSON-served)
from app.db.models import Certificate, Program, User

SAMPLE_CERTIFICATES = [
    {"certificate_id": "NI-2026-1001", "student_name": "Ananya Sharma", "program": "React Development", "issued_on": "2026-03-14"},
    {"certificate_id": "NI-2026-1002", "student_name": "Rohan Mehta", "program": "Data Science", "issued_on": "2026-04-02"},
]

DEFAULT_ADMIN = {
    "full_name": "NeuIntern Admin",
    "email": "info@neuintern.in",
    "phone": "9999999999",
    "degree": "N/A",
    "branch": "N/A",
    "current_year": "N/A",
    "password": "Admin@123",  # change immediately after first login in production
}


def _commit_seed(db: Session) -> None:
    """Commits a seed batch. With several workers starting at once, two can pass the
    "already seeded?" check together; the loser hits a duplicate key. That means the
    other worker has just inserted the same rows, so discard ours and carry on
    instead of crashing the whole worker at start-up."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()


def seed_certificates(db: Session) -> None:
    if db.query(Certificate).count() > 0:
        return
    for cert in SAMPLE_CERTIFICATES:
        db.add(Certificate(**cert))
    _commit_seed(db)


def seed_programs(db: Session) -> None:
    if db.query(Program).count() > 0:
        return
    for p in PROGRAMS:
        db.add(
            Program(
                slug=p["slug"],
                title=p["title"],
                category=p["category"],
                tagline=p["tagline"],
                image=p["image"],
                duration=p["duration"],
                price=p.get("price", 0),
                currency=p.get("currency", "INR"),
                mode=p.get("mode", "Remote"),
                certificate=p.get("certificate", True),
                live_projects=p.get("liveProjects", 1),
                skills_json=json.dumps(p.get("skills", [])),
                tools_json=json.dumps(p.get("tools", [])),
                outcomes_json=json.dumps(p.get("outcomes", [])),
                eligibility=p.get("eligibility", ""),
                curriculum_json=json.dumps(p.get("curriculum", [])),
                is_active=True,
            )
        )
    _commit_seed(db)


def seed_admin_user(db: Session) -> None:
    existing = db.query(User).filter(User.email == DEFAULT_ADMIN["email"]).first()
    if existing:
        return
    # The default password is public (README, source). In production an admin is only
    # created when ADMIN_PASSWORD is provided; otherwise none is, and nobody can log in
    # with a known password.
    password = settings.admin_password or (None if settings.is_production else DEFAULT_ADMIN["password"])
    if password is None:
        print("[seed] ENVIRONMENT=production and ADMIN_PASSWORD is not set: no admin account was created.")
        return
    db.add(
        User(
            full_name=DEFAULT_ADMIN["full_name"],
            email=DEFAULT_ADMIN["email"],
            phone=DEFAULT_ADMIN["phone"],
            degree=DEFAULT_ADMIN["degree"],
            branch=DEFAULT_ADMIN["branch"],
            current_year=DEFAULT_ADMIN["current_year"],
            password_hash=hash_password(password),
            role="admin",
        )
    )
    _commit_seed(db)
