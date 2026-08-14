from pydantic import BaseModel, Field


class CertificateVerifyRequest(BaseModel):
    certificate_id: str = Field(min_length=1, alias="certificateId")

    class Config:
        populate_by_name = True
