import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import get_db
from app.db.models import Enrollment
from app.services.payment_service import mark_enrollment_paid

router = APIRouter(prefix="/api/payments", tags=["payments"])
logger = logging.getLogger(__name__)


@router.post("/webhook")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    """Razorpay server-to-server confirmation. Covers the case where the
    student pays but never returns to our site (tab closed, network drop), so
    /enrollments/{id}/payment/verify is never called.

    Authenticated by an HMAC of the raw body with the webhook secret; no JWT.
    Always answers 200 for events we deliberately ignore so Razorpay does not
    keep retrying them; only a bad signature or missing config is an error."""
    if not settings.razorpay_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook secret is not configured.")

    raw_body = await request.body()
    expected = hmac.new(settings.razorpay_webhook_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, request.headers.get("X-Razorpay-Signature", "")):
        raise HTTPException(status_code=400, detail="Invalid webhook signature.")

    try:
        event = json.loads(raw_body)
    except ValueError:
        raise HTTPException(status_code=400, detail="Malformed webhook body.")

    if event.get("event") not in ("payment.captured", "order.paid"):
        return {"success": True, "message": "Event ignored."}

    payload = event.get("payload") or {}
    payment = (payload.get("payment") or {}).get("entity") or {}
    order_id = payment.get("order_id") or ((payload.get("order") or {}).get("entity") or {}).get("id")
    payment_id = payment.get("id")
    if not order_id or not payment_id:
        return {"success": True, "message": "No order/payment in event."}

    enrollment = db.query(Enrollment).filter(Enrollment.razorpay_order_id == order_id).first()
    if not enrollment:
        logger.warning("Webhook for unknown order %s", order_id)
        return {"success": True, "message": "Unknown order."}

    expected_paise = round(enrollment.amount * 100)
    if payment.get("amount") != expected_paise or payment.get("currency", enrollment.currency) != enrollment.currency:
        logger.error(
            "Webhook amount mismatch for enrollment %s: got %s %s, expected %s",
            enrollment.id, payment.get("amount"), payment.get("currency"), expected_paise,
        )
        return {"success": True, "message": "Amount mismatch; not applied."}

    # No-op (returns False) if /verify already confirmed this payment.
    mark_enrollment_paid(db, enrollment, payment_id)
    return {"success": True}
