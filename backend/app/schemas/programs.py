from pydantic import BaseModel


class ProgramsQuery(BaseModel):
    category: str | None = "All"
    search: str | None = ""
    page: int = 1
    limit: int = 9
