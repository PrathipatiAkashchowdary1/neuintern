from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import Certificate
from app.schemas.certificate import CertificateVerifyRequest

router = APIRouter(prefix="/api/certificate", tags=["certificate"])


@router.post("/verify")
async def verify_certificate(payload: CertificateVerifyRequest, db: Session = Depends(get_db)):
    found = (
        db.query(Certificate)
        .filter(Certificate.certificate_id.ilike(payload.certificate_id))
        .first()
    )

    if not found:
        return {
            "success": False,
            "message": "No certificate found with that ID. Double-check and try again.",
        }

    return {
        "success": True,
        "message": "Certificate verified.",
        "data": {
            "certificateId": found.certificate_id,
            "studentName": found.student_name,
            "program": found.program,
            "issuedOn": found.issued_on,
        },
    }
