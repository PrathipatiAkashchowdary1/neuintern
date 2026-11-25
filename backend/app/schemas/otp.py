from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.passwords import validate_new_password


class SendOtpRequest(BaseModel):
    email: EmailStr
    purpose: str = Field(default="register", pattern="^(register|reset_password)$")


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=4, max_length=8)
    purpose: str = Field(default="register", pattern="^(register|reset_password)$")


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=4, max_length=8)
    new_password: str = Field(min_length=1, alias="newPassword")

    class Config:
        populate_by_name = True

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_new_password(v)
