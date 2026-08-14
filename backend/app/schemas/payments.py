from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.validators import normalize_and_validate_indian_phone


class CreateOrderRequest(BaseModel):
    program_slug: str = Field(min_length=1, alias="programSlug")
    name: str = Field(min_length=1)
    email: EmailStr
    phone: str = Field(min_length=8)

    class Config:
        populate_by_name = True

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_and_validate_indian_phone(v)


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str = Field(alias="razorpay_order_id")
    razorpay_payment_id: str = Field(alias="razorpay_payment_id")
    razorpay_signature: str = Field(alias="razorpay_signature")
    enrollment_id: str = Field(alias="enrollmentId")

    class Config:
        populate_by_name = True

