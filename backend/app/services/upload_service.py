"""Program image uploads from the admin portal.

Uploaded files are never trusted: the bytes must decode as a real PNG, JPEG or
WebP (checked with Pillow, not the filename or the browser-supplied content
type), and the image is then RE-ENCODED and downscaled before it is stored.
That strips EXIF/GPS metadata and anything smuggled into the file, and keeps
program pages light. The stored filename is random; nothing from the client's
filename is ever used in a path.

Storage is the UPLOAD_STORAGE setting: the database (default) or files on disk.
"""

import io
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import HTTPException
from PIL import Image
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Program, UploadedImage

ALLOWED_FORMATS = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}
CONTENT_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp"}
MAX_PIXELS = 40_000_000  # reject decompression bombs before decoding fully
MAX_SIDE = 1600  # downscale anything larger

# The only names ever served: 32 hex characters and a known extension. This is what keeps
# "/uploads/../../etc/passwd" and friends out, whichever storage is in use.
NAME_PATTERN = re.compile(r"^[0-9a-f]{32}\.(png|jpg|webp)$")

# An image nobody saved onto a program is deleted after this long, so replacing or abandoning
# images in the editor does not make the table grow forever. The wait protects an image that
# was just uploaded in the editor but whose program has not been saved yet.
UNUSED_KEEP_FOR = timedelta(days=7)


def upload_root() -> Path:
    root = Path(settings.upload_dir)
    if not root.is_absolute():
        root = Path(__file__).resolve().parents[2] / root  # relative to backend/
    root.mkdir(parents=True, exist_ok=True)
    return root


def process_image(data: bytes) -> tuple[bytes, str]:
    """Validates and re-encodes an upload. Returns (clean bytes, extension such as '.png')."""
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Image is too large (max {settings.max_upload_mb} MB).")

    try:
        probe = Image.open(io.BytesIO(data))
        fmt = probe.format
        if probe.width * probe.height > MAX_PIXELS:
            raise HTTPException(status_code=400, detail="Image dimensions are too large.")
        probe.verify()  # cheap integrity check; the image must be re-opened to use it
        image = Image.open(io.BytesIO(data))
        image.load()
    except HTTPException:
        raise
    except Exception:  # Pillow raises many types on corrupt/hostile input; all mean "not a usable image"
        raise HTTPException(status_code=400, detail="That file is not a valid image.") from None

    if fmt not in ALLOWED_FORMATS:
        raise HTTPException(status_code=400, detail="Only PNG, JPEG and WebP images are allowed.")

    image.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    if fmt == "JPEG":
        image.convert("RGB").save(out, "JPEG", quality=88, optimize=True)
    elif fmt == "PNG":
        image.save(out, "PNG", optimize=True)
    else:
        image.save(out, "WEBP", quality=88)
    return out.getvalue(), ALLOWED_FORMATS[fmt]


def save_program_image(db: Session, data: bytes) -> str:
    """Validates and stores the image; returns the stored filename."""
    clean, ext = process_image(data)
    filename = f"{uuid.uuid4().hex}{ext}"

    if settings.upload_storage == "disk":
        (upload_root() / filename).write_bytes(clean)
    else:
        db.add(UploadedImage(name=filename, content_type=CONTENT_TYPES[ext], data=clean, size=len(clean)))
        db.commit()

    delete_unused_images(db)  # housekeeping, at most one cheap scan per upload
    return filename


def referenced_names(db: Session) -> set[str]:
    """Filenames that some program currently points at."""
    names = set()
    for (image,) in db.query(Program.image).all():
        match = re.search(r"/uploads/([0-9a-f]{32}\.(?:png|jpg|webp))\s*$", image or "")
        if match:
            names.add(match.group(1))
    return names


def delete_unused_images(db: Session, now: datetime | None = None) -> int:
    """Deletes database images older than UNUSED_KEEP_FOR that no program uses."""
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    keep = referenced_names(db)
    stale = [
        name
        for (name,) in db.query(UploadedImage.name).filter(UploadedImage.created_at < now - UNUSED_KEEP_FOR).all()
        if name not in keep
    ]
    if not stale:
        return 0
    db.execute(delete(UploadedImage).where(UploadedImage.name.in_(stale)))
    db.commit()
    return len(stale)
