from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import ContactSubmission, Enrollment, Program, User
from app.deps import require_admin
from app.schemas.admin_programs import ProgramCreate, ProgramUpdate
from app.services.enrollments_service import admin_enrollment_to_dict
from app.services.programs_service import apply_program_fields, program_to_dict

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _now():
    # Values loaded back from the database (SQLite and plain DateTime columns
    # on Postgres) come back as timezone-naive, even though we write them
    # with datetime.now(timezone.utc). Comparing an aware "now" against those
    # naive values raises TypeError, so this stays naive too (still UTC —
    # just without the tzinfo attached) to match what the ORM hands back.
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------- Enrollments ----------

@router.get("/enrollments")
async def list_all_enrollments(
    search: str = "",
    program_slug: str = "",
    payment_status: str = "",
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Enrollment)

    if search:
        like = f"%{search.lower()}%"
        query = query.filter(
            Enrollment.name.ilike(like) | Enrollment.email.ilike(like) | Enrollment.phone.ilike(like)
        )
    if program_slug:
        query = query.filter(Enrollment.program_slug == program_slug)
    if payment_status:
        query = query.filter(Enrollment.payment_status == payment_status)

    rows = query.order_by(Enrollment.enrolled_at.desc()).all()

    # Enrich with the student's academic profile fields for the admin table
    user_ids = {r.user_id for r in rows}
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}

    data = []
    for r in rows:
        entry = admin_enrollment_to_dict(r)
        user = users.get(r.user_id)
        entry["degree"] = user.degree if user else None
        entry["branch"] = user.branch if user else None
        entry["currentYear"] = user.current_year if user else None
        data.append(entry)

    return {"success": True, "data": data, "meta": {"total": len(data)}}


# ---------- Analytics ----------

def _pct_change(current: float, previous: float) -> float | None:
    """Returns percentage change from previous -> current, or None when
    there's no previous-period baseline to compare against (so the
    frontend can show "—" instead of a misleading ±∞%)."""
    if previous == 0:
        return None if current == 0 else 100.0
    return round(((current - previous) / previous) * 100, 1)


@router.get("/analytics")
async def analytics(_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    total_students = db.query(User).filter(User.role == "student").count()
    total_enrollments = db.query(Enrollment).count()

    paid_enrollments = db.query(Enrollment).filter(Enrollment.payment_status == "paid").all()
    total_revenue = sum(e.amount for e in paid_enrollments)

    task_submitted_count = db.query(Enrollment).filter(Enrollment.task_submitted_at.isnot(None)).count()
    certificate_count = db.query(Enrollment).filter(Enrollment.certificate_unlocked.is_(True)).count()
    unread_messages = db.query(ContactSubmission).filter(ContactSubmission.is_read.is_(False)).count()

    by_program: dict[str, int] = {}
    for e in db.query(Enrollment).all():
        by_program[e.program_title] = by_program.get(e.program_title, 0) + 1

    # --- Trends: last 7 days vs the 7 days before that ---
    now = _now()
    last7_start = now - timedelta(days=7)
    prev7_start = now - timedelta(days=14)

    students_last7 = db.query(User).filter(User.role == "student", User.created_at >= last7_start).count()
    students_prev7 = (
        db.query(User)
        .filter(User.role == "student", User.created_at >= prev7_start, User.created_at < last7_start)
        .count()
    )

    revenue_last7 = sum(
        e.amount for e in paid_enrollments if e.paid_at and e.paid_at >= last7_start
    )
    revenue_prev7 = sum(
        e.amount for e in paid_enrollments if e.paid_at and prev7_start <= e.paid_at < last7_start
    )

    # --- 30-day daily time series, for the registrations/revenue charts ---
    thirty_days_ago = (now - timedelta(days=29)).date()
    day_buckets = [(thirty_days_ago + timedelta(days=i)).isoformat() for i in range(30)]

    reg_counts = {d: 0 for d in day_buckets}
    for u in db.query(User).filter(User.role == "student", User.created_at >= now - timedelta(days=30)).all():
        d = u.created_at.date().isoformat()
        if d in reg_counts:
            reg_counts[d] += 1

    revenue_by_day = {d: 0.0 for d in day_buckets}
    for e in paid_enrollments:
        if e.paid_at and e.paid_at >= now - timedelta(days=30):
            d = e.paid_at.date().isoformat()
            if d in revenue_by_day:
                revenue_by_day[d] += e.amount

    return {
        "success": True,
        "data": {
            "totalStudents": total_students,
            "totalEnrollments": total_enrollments,
            "totalRevenue": total_revenue,
            "unreadMessages": unread_messages,
            "trends": {
                "studentsPct": _pct_change(students_last7, students_prev7),
                "revenuePct": _pct_change(revenue_last7, revenue_prev7),
            },
            "funnel": {
                "enrolled": total_enrollments,
                "taskSubmitted": task_submitted_count,
                "paid": len(paid_enrollments),
                "certified": certificate_count,
            },
            "enrollmentsByProgram": [
                {"program": title, "count": count} for title, count in sorted(by_program.items(), key=lambda x: -x[1])
            ],
            "registrationsByDay": [{"date": d, "count": reg_counts[d]} for d in day_buckets],
            "revenueByDay": [{"date": d, "amount": revenue_by_day[d]} for d in day_buckets],
        },
    }


# ---------- Program CRUD ----------

@router.get("/programs")
async def admin_list_programs(_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(Program).order_by(Program.title).all()
    return {"success": True, "data": [program_to_dict(p) for p in rows]}


@router.post("/programs", status_code=201)
async def admin_create_program(
    payload: ProgramCreate, _admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    existing = db.query(Program).filter(Program.slug == payload.slug).first()
    if existing:
        raise HTTPException(status_code=409, detail="A program with this slug already exists")

    program = Program(slug=payload.slug, title=payload.title, category=payload.category)
    apply_program_fields(program, payload.model_dump())
    db.add(program)
    db.commit()
    db.refresh(program)

    return {"success": True, "data": program_to_dict(program)}


@router.put("/programs/{slug}")
async def admin_update_program(
    slug: str, payload: ProgramUpdate, _admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    program = db.query(Program).filter(Program.slug == slug).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    apply_program_fields(program, payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(program)

    return {"success": True, "data": program_to_dict(program)}


@router.delete("/programs/{slug}")
async def admin_delete_program(slug: str, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    program = db.query(Program).filter(Program.slug == slug).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    # Soft-delete: keep history for any existing enrollments, just hide it
    # from the public catalog.
    program.is_active = False
    db.commit()

    return {"success": True, "message": "Program deactivated."}


# ---------- Contact Messages ----------

def _message_to_dict(m: ContactSubmission) -> dict:
    return {
        "id": m.id,
        "name": m.name,
        "email": m.email,
        "subject": m.subject,
        "message": m.message,
        "isRead": m.is_read,
        "createdAt": m.created_at.isoformat(),
    }


@router.get("/messages")
async def admin_list_messages(_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(ContactSubmission).order_by(ContactSubmission.created_at.desc()).all()
    return {"success": True, "data": [_message_to_dict(m) for m in rows]}


@router.put("/messages/{message_id}/read")
async def admin_mark_message_read(
    message_id: str, _admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    message = db.query(ContactSubmission).filter(ContactSubmission.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    message.is_read = True
    db.commit()
    return {"success": True, "data": _message_to_dict(message)}


@router.delete("/messages/{message_id}")
async def admin_delete_message(
    message_id: str, _admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    message = db.query(ContactSubmission).filter(ContactSubmission.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    db.delete(message)
    db.commit()
    return {"success": True, "message": "Message deleted."}
