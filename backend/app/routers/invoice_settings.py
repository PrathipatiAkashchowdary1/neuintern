from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import User
from app.deps import require_admin
from app.schemas.invoice_settings import InvoiceSettingsIn
from app.services.invoice_settings import DEFAULTS, get_settings, save_settings
from app.services.pdf_service import generate_invoice_pdf

router = APIRouter(prefix="/api/admin/invoice-settings", tags=["admin-invoice"])

_NOTE = (
    "Changes apply to invoices issued from now on. Invoices already issued keep the details "
    "they were issued with."
)


@router.get("")
async def read_invoice_settings(_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return {"success": True, "data": {"settings": get_settings(db), "defaults": DEFAULTS, "note": _NOTE}}


@router.put("")
async def update_invoice_settings(
    payload: InvoiceSettingsIn, _admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    saved = save_settings(db, payload.model_dump())
    return {"success": True, "message": "Invoice details saved.", "data": {"settings": saved, "note": _NOTE}}


@router.post("/preview")
async def preview_invoice(payload: InvoiceSettingsIn, _admin: User = Depends(require_admin)):
    """Renders a sample invoice (fee Rs 349) from the values in the request, WITHOUT saving them."""
    sample = {
        "details": payload.model_dump(),
        "invoiceNumber": f"{payload.invoice_prefix}-2026-SAMPLE01",
        "invoiceDate": "January 15, 2026",
        "studentName": "Sample Student",
        "email": "student@example.com",
        "phone": "9876543210",
        "programTitle": "Sample Program",
        "amount": 349.0,
        "currency": "INR",
        "paymentId": "pay_SAMPLE",
        "orderId": "order_SAMPLE",
    }
    pdf = generate_invoice_pdf(sample).read()
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": 'inline; filename="invoice-preview.pdf"'})
