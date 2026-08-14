from pydantic import BaseModel, EmailStr, Field


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
    new_password: str = Field(min_length=6, alias="newPassword")

    class Config:
        populate_by_name = True