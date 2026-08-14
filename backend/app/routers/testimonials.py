from fastapi import APIRouter

from app.data.catalog import TESTIMONIALS

router = APIRouter(prefix="/api/testimonials", tags=["testimonials"])


@router.get("")
async def list_testimonials():
    return {"success": True, "data": TESTIMONIALS}
