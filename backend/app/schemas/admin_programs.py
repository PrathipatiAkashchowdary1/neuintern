from pydantic import BaseModel, Field


class CurriculumWeek(BaseModel):
    week: str
    title: str
    points: list[str] = []


class ProgramCreate(BaseModel):
    slug: str = Field(min_length=1)
    title: str = Field(min_length=1)
    category: str = Field(min_length=1)
    tagline: str = ""
    image: str = ""
    duration: str = "4 Weeks"
    price: float = 0
    currency: str = "INR"
    mode: str = "Remote"
    certificate: bool = True
    liveProjects: int = 1
    skills: list[str] = []
    tools: list[str] = []
    outcomes: list[str] = []
    eligibility: str = ""
    curriculum: list[CurriculumWeek] = []
    is_active: bool = True


class ProgramUpdate(BaseModel):
    title: str | None = None
    category: str | None = None
    tagline: str | None = None
    image: str | None = None
    duration: str | None = None
    price: float | None = None
    currency: str | None = None
    mode: str | None = None
    certificate: bool | None = None
    liveProjects: int | None = None
    skills: list[str] | None = None
    tools: list[str] | None = None
    outcomes: list[str] | None = None
    eligibility: str | None = None
    curriculum: list[CurriculumWeek] | None = None
    is_active: bool | None = None
