from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.validators import normalize_and_validate_indian_phone


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=1, alias="fullName")
    email: EmailStr
    phone: str = Field(min_length=8)
    degree: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    current_year: str = Field(min_length=1, alias="currentYear")
    password: str = Field(min_length=6)

    class Config:
        populate_by_name = True

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_and_validate_indian_phone(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class UserOut(BaseModel):
    id: str
    fullName: str
    email: str
    phone: str
    degree: str
    branch: str
    currentYear: str
    role: str


class TokenResponse(BaseModel):
    token: str
    user: UserOut