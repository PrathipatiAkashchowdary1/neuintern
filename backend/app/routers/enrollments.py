import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.limiter import limiter
from app.db.base import get_db
from app.db.models import Enrollment, Program, User
from app.deps import get_current_user
from app.schemas.enrollments import EnrollRequest, TaskSubmitRequest
from app.schemas.payments import VerifyPaymentRequest
from app.services.certificate_service import (
    completion_date,
    certificate_pdf_payload,
)
from app.services.enrollments_service import enrollment_to_dict
from app.services.fee_service import CERTIFICATE_CURRENCY, effective_fee, fee_to_pay, sync_unpaid_fee
from app.services.email_service import run_email_task, send_email_with_attachments
from app.services.payment_service import invoice_data as _invoice_data, mark_enrollment_paid
from app.services.pdf_service import generate_certificate_pdf, generate_invoice_pdf, generate_offer_letter_pdf
from app.services.razorpay_client import get_client

router = APIRouter(prefix="/api/enrollments", tags=["enrollments"])


def _out(db: Session, enrollment: Enrollment) -> dict:
    return enrollment_to_dict(enrollment, fee_to_pay(db, enrollment))


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
    background_tasks: BackgroundTasks,
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
        sync_unpaid_fee(db, existing)
        return {"success": True, "data": _out(db, existing)}

    enrollment = Enrollment(
        user_id=current_user.id,
        program_slug=program.slug,
        program_title=program.title,
        name=current_user.full_name,
        email=current_user.email,
        phone=current_user.phone,
        amount=effective_fee(program),  # admin-editable program price
        currency=CERTIFICATE_CURRENCY,
        payment_status="unpaid",
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)

    background_tasks.add_task(
        run_email_task,
        send_offer_letter_email,
        enrollment.email,
        enrollment.name,
        enrollment.program_title,
        enrollment.id,
        _offer_letter_pdf_payload(enrollment),
    )

    return {"success": True, "data": _out(db, enrollment)}


@router.get("/me")
async def my_enrollments(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == current_user.id)
        .order_by(Enrollment.enrolled_at.desc())
        .all()
    )
    for e in rows:
        sync_unpaid_fee(db, e)
    return {"success": True, "data": [_out(db, e) for e in rows]}


@router.get("/{enrollment_id}")
async def get_enrollment(
    enrollment_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    enrollment = _get_owned_enrollment(enrollment_id, current_user, db)
    sync_unpaid_fee(db, enrollment)
    return {"success": True, "data": _out(db, enrollment)}


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


def send_offer_letter_email(to: str, name: str, program_title: str, enrollment_id: str, pdf_data: dict) -> None:
    """PDF + SMTP from plain data (no ORM objects), so it can run as a
    background task after the request's DB session is closed."""
    pdf_buffer = generate_offer_letter_pdf(pdf_data)
    filename = f"NeuIntern-Offer-Letter-{enrollment_id[:8]}.pdf"
    send_email_with_attachments(
        to=to,
        subject=f"Your NeuIntern Offer Letter — {program_title}",
        body=(
            f"Hi {name},\n\n"
            f"Congratulations on enrolling in the {program_title} internship program! "
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

    return {"success": True, "message": "Task submitted successfully.", "data": _out(db, enrollment)}


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
    # Charge what the admin has set right now, and pin it on the enrollment so
    # the invoice and the webhook amount check match this exact order.
    fee = effective_fee(db.get(Program, enrollment.program_slug))
    amount_in_paise = round(fee * 100)

    try:
        order = client.order.create(
            {
                "amount": amount_in_paise,
                "currency": CERTIFICATE_CURRENCY,
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

    enrollment.amount = amount_in_paise / 100
    enrollment.currency = CERTIFICATE_CURRENCY
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
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enrollment = _get_owned_enrollment(enrollment_id, current_user, db)

    # Idempotent: a retry, double-click, or webhook that got here first just
    # reports the current state: no second invoice, no downgrade.
    if enrollment.payment_status == "paid":
        return {"success": True, "message": _paid_message(enrollment), "data": _out(db, enrollment)}

    # The signature must be for THIS enrollment's order, not just any order.
    if not enrollment.razorpay_order_id or payload.razorpay_order_id != enrollment.razorpay_order_id:
        raise HTTPException(status_code=400, detail="Payment does not match this enrollment.")

    expected_signature = hmac.new(
        (settings.razorpay_key_secret or "").encode(),
        f"{payload.razorpay_order_id}|{payload.razorpay_payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, payload.razorpay_signature):
        # Not marked "failed": the student can retry on the same order, and
        # the webhook can still confirm a genuine payment.
        raise HTTPException(
            status_code=400, detail="Payment verification failed. Please contact support if you were charged."
        )

    # Sends the invoice (and unlocks the certificate if the course is already
    # over) only for the caller that actually flips unpaid -> paid.
    mark_enrollment_paid(
        db, enrollment, payload.razorpay_payment_id, payload.razorpay_signature, background_tasks
    )

    return {"success": True, "message": _paid_message(enrollment), "data": _out(db, enrollment)}


def _paid_message(enrollment: Enrollment) -> str:
    if enrollment.certificate_unlocked:
        return "Payment verified. Your certificate is ready!"
    return "Payment verified. Your certificate will be emailed once the course is complete."


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
