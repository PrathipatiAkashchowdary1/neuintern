from pydantic import BaseModel, Field


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str = Field(alias="razorpay_order_id")
    razorpay_payment_id: str = Field(alias="razorpay_payment_id")
    razorpay_signature: str = Field(alias="razorpay_signature")
    enrollment_id: str = Field(alias="enrollmentId")

    class Config:
        populate_by_name = True

