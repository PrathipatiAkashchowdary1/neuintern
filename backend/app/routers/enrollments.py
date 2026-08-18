import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.limiter import limiter
from app.db.base import get_db
from app.db.models import CERTIFICATE_FEE_INR, Enrollment, Program, User
from app.deps import get_current_user
from app.schemas.enrollments import EnrollRequest, TaskSubmitRequest
from app.schemas.payments import VerifyPaymentRequest
from app.services.certificate_service import (
    completion_date,
    certificate_pdf_payload,
    is_course_complete,
    unlock_and_email_certificate,
)
from app.services.enrollments_service import enrollment_to_dict
from app.services.email_service import send_email_with_attachments
from app.services.pdf_service import generate_certificate_pdf, generate_invoice_pdf, generate_offer_letter_pdf
from app.services.razorpay_client import get_client

router = APIRouter(prefix="/api/enrollments", tags=["enrollments"])


def _get_owned_enrollment(enrollment_id: str, user: User, db: Session) -> Enrollment:
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    if enrollment.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="You do not have access to this enrollment")
    return enrollment


@router.post("", status_code=201)
async def enroll(
    payload: EnrollRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    program = db.query(Program).filter(Program.slug == payload.program_slug, Program.is_active.is_(True)).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    existing = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == current_user.id, Enrollment.program_slug == program.slug)
        .first()
    )
    if existing:
        return {"success": True, "data": enrollment_to_dict(existing)}

    enrollment = Enrollment(
        user_id=current_user.id,
        program_slug=program.slug,
        program_title=program.title,
        name=current_user.full_name,
        email=current_user.email,
        phone=current_user.phone,
        amount=CERTIFICATE_FEE_INR,
        currency="INR",
        payment_status="unpaid",
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)

    _email_offer_letter(enrollment)

    return {"success": True, "data": enrollment_to_dict(enrollment)}


@router.get("/me")
async def my_enrollments(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == current_user.id)
        .order_by(Enrollment.enrolled_at.desc())
        .all()
    )
    return {"success": True, "data": [enrollment_to_dict(e) for e in rows]}


@router.get("/{enrollment_id}")
async def get_enrollment(
    enrollment_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    enrollment = _get_owned_enrollment(enrollment_id, current_user, db)
    return {"success": True, "data": enrollment_to_dict(enrollment)}


def _offer_letter_data(enrollment: Enrollment) -> dict:
    end_date = enrollment.enrolled_at + timedelta(days=28)  # "1 month" per the approved offer letter wording
    return {
        "studentName": enrollment.name,
        "programTitle": enrollment.program_title,
        "startDate": enrollment.enrolled_at.isoformat(),
        "endDate": end_date.isoformat(),
        "duration": "4 Weeks",
        "mode": "Remote",
        "referenceId": f"NI-OL-{enrollment.id[:8].upper()}",
        "issuedBy": "NeuIntern Programs Team",
    }


def _offer_letter_pdf_payload(enrollment: Enrollment) -> dict:
    """Same data as _offer_letter_data, but with human-readable dates —
    used both by the manual PDF download endpoint and the automatic
    email sent right after enrolling."""
    data = _offer_letter_data(enrollment)
    data["startDate"] = enrollment.enrolled_at.strftime("%B %d, %Y")
    data["endDate"] = (enrollment.enrolled_at + timedelta(days=28)).strftime("%B %d, %Y")
    return data


def _email_offer_letter(enrollment: Enrollment) -> None:
    pdf_buffer = generate_offer_letter_pdf(_offer_letter_pdf_payload(enrollment))
    filename = f"NeuIntern-Offer-Letter-{enrollment.id[:8]}.pdf"
    send_email_with_attachments(
        to=enrollment.email,
        subject=f"Your NeuIntern Offer Letter — {enrollment.program_title}",
        body=(
            f"Hi {enrollment.name},\n\n"
            f"Congratulations on enrolling in the {enrollment.program_title} internship program! "
            f"Your official offer letter is attached.\n\n"
            f"Next step: log in to your dashboard and submit your task (GitHub + LinkedIn links) "
            f"to move on to certification.\n\n"
            f"— The NeuIntern Team"
        ),
        attachments=[(filename, pdf_buffer.read())],
    )


@router.get("/{enrollment_id}/offer-letter")
async def get_offer_letter(
    enrollment_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    enrollment = _get_owned_enrollment(enrollment_id, current_user, db)
    return {"success": True, "data": _offer_letter_data(enrollment)}


@router.get("/{enrollment_id}/offer-letter/pdf")
async def get_offer_letter_pdf(
    enrollment_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    enrollment = _get_owned_enrollment(enrollment_id, current_user, db)
    data = _offer_letter_pdf_payload(enrollment)

    pdf_buffer = generate_offer_letter_pdf(data)
    filename = f"NeuIntern-Offer-Letter-{enrollment.id[:8]}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{enrollment_id}/task")
async def submit_task(
    enrollment_id: str,
    payload: TaskSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enrollment = _get_owned_enrollment(enrollment_id, current_user, db)

    enrollment.github_link = payload.github_link
    enrollment.linkedin_link = payload.linkedin_link
    enrollment.task_submitted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(enrollment)

    return {"success": True, "message": "Task submitted successfully.", "data": enrollment_to_dict(enrollment)}


@router.post("/{enrollment_id}/payment/create-order", status_code=201)
@limiter.limit("20/hour")
async def create_certificate_order(
    request: Request,
    enrollment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enrollment = _get_owned_enrollment(enrollment_id, current_user, db)

    if not enrollment.task_submitted_at:
        raise HTTPException(status_code=400, detail="Submit your task (GitHub + LinkedIn links) before paying.")
    if enrollment.payment_status == "paid":
        raise HTTPException(status_code=400, detail="This enrollment is already paid.")
    if not settings.razorpay_configured:
        raise HTTPException(
            status_code=503,
            detail="Payments are not configured yet. Add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET to the backend .env file.",
        )

    client = get_client()
    amount_in_paise = round(CERTIFICATE_FEE_INR * 100)

    try:
        order = client.order.create(
            {
                "amount": amount_in_paise,
                "currency": "INR",
                "receipt": f"ni_cert_{enrollment.id[:12]}",
                "notes": {
                    "enrollmentId": enrollment.id,
                    "programTitle": enrollment.program_title,
                    "email": enrollment.email,
                },
            }
        )
    except Exception as err:  # razorpay SDK raises its own exception types
        raise HTTPException(status_code=502, detail=f"Could not create payment order: {err}") from err

    enrollment.razorpay_order_id = order["id"]
    enrollment.payment_status = "pending"
    db.commit()

    return {
        "success": True,
        "data": {
            "orderId": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "keyId": settings.razorpay_key_id,
            "enrollmentId": enrollment.id,
        },
    }


@router.post("/{enrollment_id}/payment/verify")
async def verify_certificate_payment(
    enrollment_id: str,
    payload: VerifyPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enrollment = _get_owned_enrollment(enrollment_id, current_user, db)

    expected_signature = hmac.new(
        (settings.razorpay_key_secret or "").encode(),
        f"{payload.razorpay_order_id}|{payload.razorpay_payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, payload.razorpay_signature):
        enrollment.payment_status = "failed"
        db.commit()
        raise HTTPException(
            status_code=400, detail="Payment verification failed. Please contact support if you were charged."
        )

    enrollment.payment_status = "paid"
    enrollment.razorpay_payment_id = payload.razorpay_payment_id
    enrollment.razorpay_signature = payload.razorpay_signature
    enrollment.paid_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(enrollment)

    # Payment confirmation goes out immediately regardless of course timing.
    _email_invoice(enrollment)

    # The certificate itself is a different story: it only unlocks (and only
    # gets emailed) once the course's completion date has actually passed.
    # Most students pay mid-course, so normally the background scheduler
    # (see app/services/certificate_service.py + app/main.py) picks this up
    # later. The one exception handled here: someone who pays *after* the
    # course has already ended shouldn't have to wait for the next scheduler
    # tick — unlock immediately in that case.
    message = "Payment verified. Your certificate will be emailed once the course is complete."
    if is_course_complete(enrollment):
        unlock_and_email_certificate(db, enrollment)
        db.refresh(enrollment)
        message = "Payment verified. Your certificate is ready!"

    return {
        "success": True,
        "message": message,
        "data": enrollment_to_dict(enrollment),
    }


def _invoice_data(enrollment: Enrollment) -> dict:
    invoice_number = f"INV-{(enrollment.paid_at or datetime.now(timezone.utc)).year}-{enrollment.id[:8].upper()}"
    return {
        "invoiceNumber": invoice_number,
        "invoiceDate": (enrollment.paid_at or datetime.now(timezone.utc)).strftime("%B %d, %Y"),
        "studentName": enrollment.name,
        "email": enrollment.email,
        "phone": enrollment.phone,
        "programTitle": enrollment.program_title,
        "amount": enrollment.amount,
        "currency": enrollment.currency,
        "paymentId": enrollment.razorpay_payment_id or "—",
        "orderId": enrollment.razorpay_order_id or "—",
    }


def _email_invoice(enrollment: Enrollment) -> None:
    data = _invoice_data(enrollment)
    pdf_buffer = generate_invoice_pdf(data)
    filename = f"NeuIntern-Invoice-{data['invoiceNumber']}.pdf"
    send_email_with_attachments(
        to=enrollment.email,
        subject=f"Payment Receipt — {data['invoiceNumber']}",
        body=(
            f"Hi {enrollment.name},\n\n"
            f"Thanks for your payment of {enrollment.currency} {enrollment.amount:.2f} for the "
            f"{enrollment.program_title} certificate fee. Your receipt is attached.\n\n"
            f"— The NeuIntern Team"
        ),
        attachments=[(filename, pdf_buffer.read())],
    )


@router.get("/{enrollment_id}/invoice/pdf")
async def get_invoice_pdf(
    enrollment_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Available to the enrolled student themselves, or any admin — same
    ownership check used by the offer letter and certificate downloads."""
    enrollment = _get_owned_enrollment(enrollment_id, current_user, db)
    if enrollment.payment_status != "paid":
        raise HTTPException(status_code=400, detail="No invoice is available until payment is completed.")

    data = _invoice_data(enrollment)
    pdf_buffer = generate_invoice_pdf(data)
    filename = f"NeuIntern-Invoice-{data['invoiceNumber']}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _certificate_lock_message(enrollment: Enrollment) -> str:
    if enrollment.payment_status != "paid":
        return "Complete your task and payment to unlock the certificate."
    return (
        f"Payment received — your certificate unlocks on "
        f"{completion_date(enrollment).strftime('%B %d, %Y')}, once the course is complete."
    )


@router.get("/{enrollment_id}/certificate")
async def get_certificate(
    enrollment_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    enrollment = _get_owned_enrollment(enrollment_id, current_user, db)
    if not enrollment.certificate_unlocked:
        raise HTTPException(status_code=403, detail=_certificate_lock_message(enrollment))
    return {"success": True, "data": certificate_pdf_payload(enrollment)}


@router.get("/{enrollment_id}/certificate/pdf")
async def get_certificate_pdf(
    enrollment_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    enrollment = _get_owned_enrollment(enrollment_id, current_user, db)
    if not enrollment.certificate_unlocked:
        raise HTTPException(status_code=403, detail=_certificate_lock_message(enrollment))

    data = certificate_pdf_payload(enrollment)
    pdf_buffer = generate_certificate_pdf(data)
    filename = f"NeuIntern-Certificate-{enrollment.certificate_id}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
