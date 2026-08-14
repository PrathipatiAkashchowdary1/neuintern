from pydantic import BaseModel, Field


class EnrollRequest(BaseModel):
    program_slug: str = Field(min_length=1, alias="programSlug")

    class Config:
        populate_by_name = True


class TaskSubmitRequest(BaseModel):
    github_link: str = Field(min_length=1, alias="githubLink")
    linkedin_link: str = Field(min_length=1, alias="linkedinLink")

    class Config:
        populate_by_name = True
