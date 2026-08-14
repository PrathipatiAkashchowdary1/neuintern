import hashlib
import hmac
from datetime import datetime, timezone

import razorpay
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.limiter import limiter
from app.data.catalog import get_program_by_slug
from app.db.base import get_db
from app.db.models import Enrollment
from app.schemas.payments import CreateOrderRequest, VerifyPaymentRequest

router = APIRouter(prefix="/api/payments", tags=["payments"])


def _get_client() -> razorpay.Client:
    return razorpay.Client(
        auth=(settings.razorpay_key_id or "rzp_test_placeholder", settings.razorpay_key_secret or "placeholder")
    )


@router.post("/create-order", status_code=201)
@limiter.limit("20/hour")
async def create_order(request: Request, payload: CreateOrderRequest, db: Session = Depends(get_db)):
    if not settings.razorpay_configured:
        raise HTTPException(
            status_code=503,
            detail="Payments are not configured yet. Add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET to the backend .env file.",
        )

    program = get_program_by_slug(payload.program_slug)
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    if not program.get("price"):
        raise HTTPException(status_code=400, detail="This program does not require payment")

    amount_in_paise = round(program["price"] * 100)
    client = _get_client()

    try:
        order = client.order.create(
            {
                "amount": amount_in_paise,
                "currency": program.get("currency", "INR"),
                "receipt": f"ni_{payload.program_slug[:20]}_{int(datetime.now(timezone.utc).timestamp())}",
                "notes": {
                    "programSlug": program["slug"],
                    "programTitle": program["title"],
                    "name": payload.name,
                    "email": payload.email,
                },
            }
        )
    except Exception as err:  # razorpay SDK raises generic/its own exceptions
        raise HTTPException(status_code=502, detail=f"Could not create payment order: {err}") from err

    enrollment = Enrollment(
        program_slug=program["slug"],
        program_title=program["title"],
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        amount=program["price"],
        currency=program.get("currency", "INR"),
        razorpay_order_id=order["id"],
        status="pending",
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)

    return {
        "success": True,
        "data": {
            "orderId": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "keyId": settings.razorpay_key_id,
            "programTitle": program["title"],
            "enrollmentId": enrollment.id,
        },
    }


@router.post("/verify")
async def verify_payment(payload: VerifyPaymentRequest, db: Session = Depends(get_db)):
    enrollment = db.query(Enrollment).filter(Enrollment.id == payload.enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    expected_signature = hmac.new(
        (settings.razorpay_key_secret or "").encode(),
        f"{payload.razorpay_order_id}|{payload.razorpay_payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()

    is_valid = hmac.compare_digest(expected_signature, payload.razorpay_signature)

    if not is_valid:
        enrollment.status = "failed"
        db.commit()
        raise HTTPException(
            status_code=400,
            detail="Payment verification failed. Please contact support if you were charged.",
        )

    enrollment.status = "paid"
    enrollment.razorpay_payment_id = payload.razorpay_payment_id
    enrollment.razorpay_signature = payload.razorpay_signature
    enrollment.paid_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "success": True,
        "message": "Payment verified. You are enrolled!",
        "data": {"enrollmentId": enrollment.id, "programTitle": enrollment.program_title},
    }


@router.get("/enrollment/{enrollment_id}")
async def get_enrollment(enrollment_id: str, db: Session = Depends(get_db)):
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    return {
        "success": True,
        "data": {
            "id": enrollment.id,
            "programSlug": enrollment.program_slug,
            "programTitle": enrollment.program_title,
            "status": enrollment.status,
            "amount": enrollment.amount,
            "currency": enrollment.currency,
        },
    }
