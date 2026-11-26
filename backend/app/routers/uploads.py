from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import UploadedImage
from app.services.upload_service import CONTENT_TYPES, NAME_PATTERN, upload_root

router = APIRouter(tags=["uploads"])

# The name is random and never reused, so the bytes behind it never change: browsers and CDNs
# may keep them for a year. nosniff stops a browser second-guessing the content type.
_HEADERS = {"Cache-Control": "public, max-age=31536000, immutable", "X-Content-Type-Options": "nosniff"}


@router.api_route("/uploads/{filename}", methods=["GET", "HEAD"], include_in_schema=False)
async def serve_upload(filename: str, db: Session = Depends(get_db)):
    """Program images: from the database, or (images stored before the database option
    existed, or UPLOAD_STORAGE=disk) from files under UPLOAD_DIR."""
    if not NAME_PATTERN.fullmatch(filename):
        raise HTTPException(status_code=404, detail="Not found")  # also blocks path tricks like ../

    row = db.get(UploadedImage, filename)
    if row is not None:
        return Response(content=row.data, media_type=row.content_type, headers=_HEADERS)

    path = upload_root() / filename
    if path.is_file():
        return FileResponse(path, media_type=CONTENT_TYPES["." + filename.rsplit(".", 1)[1]], headers=_HEADERS)
    raise HTTPException(status_code=404, detail="Not found")
