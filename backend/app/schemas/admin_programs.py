import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


def _clean_list(items: list[str]) -> list[str]:
    """Trim whitespace and drop blank entries (the admin form sends one per line)."""
    return [i.strip() for i in items if i and i.strip()]


def _check_image(url: str) -> str:
    url = url.strip()
    if url and not re.match(r"^https?://", url):
        raise ValueError("Image must be an http(s) URL (upload one, or paste a link).")
    return url


CleanList = Annotated[list[str], Field(max_length=40), AfterValidator(_clean_list)]
ImageUrl = Annotated[str, Field(max_length=500), AfterValidator(_check_image)]


class CurriculumWeek(BaseModel):
    week: str = Field(max_length=50)
    title: str = Field(max_length=255)
    points: CleanList = []


class ProgramCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=150, pattern=SLUG_PATTERN)  # lowercase-with-dashes, URL-safe
    title: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=100)
    tagline: str = ""
    image: ImageUrl = ""
    duration: str = Field(default="4 Weeks", min_length=1, max_length=50)
    price: float = Field(default=150, ge=1)  # the certificate fee students pay (Rs)
    currency: str = "INR"
    mode: str = Field(default="Remote", min_length=1, max_length=50)
    certificate: bool = True
    liveProjects: int = Field(default=1, ge=0, le=50)
    skills: CleanList = []
    tools: CleanList = []
    outcomes: CleanList = []
    eligibility: str = ""
    curriculum: list[CurriculumWeek] = Field(default=[], max_length=12)
    is_active: bool = True


class ProgramUpdate(BaseModel):
    """Every field except the slug can be edited. The slug is the program's
    permanent ID: enrollments, certificates and public URLs refer to it."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    tagline: str | None = None
    image: ImageUrl | None = None
    duration: str | None = Field(default=None, min_length=1, max_length=50)
    price: float | None = Field(default=None, ge=1)
    currency: str | None = None
    mode: str | None = Field(default=None, min_length=1, max_length=50)
    certificate: bool | None = None
    liveProjects: int | None = Field(default=None, ge=0, le=50)
    skills: CleanList | None = None
    tools: CleanList | None = None
    outcomes: CleanList | None = None
    eligibility: str | None = None
    curriculum: list[CurriculumWeek] | None = Field(default=None, max_length=12)
    is_active: bool | None = None
