"""Program image uploads from the admin portal.

Uploaded files are never trusted: the bytes must decode as a real PNG, JPEG or
WebP (checked with Pillow, not the filename or the browser-supplied content
type), and the image is then RE-ENCODED and downscaled before it is stored.
That strips EXIF/GPS metadata and anything smuggled into the file, and keeps
program pages light. The stored filename is random; nothing from the client's
filename is ever used in a path.
"""

import io
import uuid
from pathlib import Path

from fastapi import HTTPException
from PIL import Image

from app.core.config import settings

ALLOWED_FORMATS = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}
MAX_PIXELS = 40_000_000  # reject decompression bombs before decoding fully
MAX_SIDE = 1600  # downscale anything larger


def upload_root() -> Path:
    root = Path(settings.upload_dir)
    if not root.is_absolute():
        root = Path(__file__).resolve().parents[2] / root  # relative to backend/
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_program_image(data: bytes) -> str:
    """Validates and stores the image; returns the stored filename."""
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

    filename = f"{uuid.uuid4().hex}{ALLOWED_FORMATS[fmt]}"
    (upload_root() / filename).write_bytes(out.getvalue())
    return filename
