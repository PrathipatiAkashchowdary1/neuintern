from pydantic import BaseModel, EmailStr, Field


class ContactCreate(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    subject: str = Field(min_length=1)
    message: str = Field(min_length=5)


class NewsletterCreate(BaseModel):
    email: EmailStr
