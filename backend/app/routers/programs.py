import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import Program
from app.services.programs_service import program_to_dict

router = APIRouter(prefix="/api/programs", tags=["programs"])


@router.get("")
async def list_programs(
    category: str = Query("All"),
    search: str = Query(""),
    page: int = Query(1, ge=1),
    limit: int = Query(9, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Program).filter(Program.is_active.is_(True))

    if category and category != "All":
        query = query.filter(Program.category == category)
    if search:
        like = f"%{search.lower()}%"
        query = query.filter(
            Program.title.ilike(like) | Program.tagline.ilike(like)
        )

    all_matching = query.all()
    total = len(all_matching)
    start = (page - 1) * limit
    paginated = all_matching[start : start + limit]

    return {
        "success": True,
        "data": [program_to_dict(p) for p in paginated],
        "meta": {
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": math.ceil(total / limit) if total else 1,
        },
    }


@router.get("/categories")
async def list_categories(db: Session = Depends(get_db)):
    rows = db.query(Program.category).filter(Program.is_active.is_(True)).distinct().all()
    categories = ["All", *[r[0] for r in rows]]
    return {"success": True, "data": categories}


@router.get("/{slug}")
async def get_program(slug: str, db: Session = Depends(get_db)):
    program = db.query(Program).filter(Program.slug == slug, Program.is_active.is_(True)).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    return {"success": True, "data": program_to_dict(program)}
