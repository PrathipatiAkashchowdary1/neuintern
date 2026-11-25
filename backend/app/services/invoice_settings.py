"""Admin-editable invoice details (company block, GST rate, wording).

Design rules:
  * DEFAULTS are the values that used to be hard-coded in the PDF, so a fresh
    install, and every invoice issued before this feature existed, render
    exactly as before.
  * Issued invoices are legal documents. When a payment is confirmed the
    CURRENT settings are copied onto the enrollment (invoice_details_json), and
    that snapshot is what the invoice always renders from. Editing the settings
    later only affects invoices issued after the edit.
  * Everything is drawn with the PDF's built-in Helvetica font, which can only
    show Western (cp1252) characters, so the admin API rejects anything else
    rather than producing garbled boxes on a tax document.
"""

import json

from sqlalchemy.orm import Session

from app.db.models import Enrollment, InvoiceSettings

# Field name -> default. This is the single list of editable fields.
DEFAULTS: dict = {
    "company_name": "VividOne Pvt. Ltd.",
    "address": "#Flat no 401, Vasista Enclave, A.S.Raju Nagar, KPHB,\nHyderabad, Telangana 500072, India",
    "gstin": "36AAHCV0625N1Z1",
    "email": "contact@neuintern.com",
    "phone": "+91 9652522929",
    "gst_rate": 18.0,  # percent, treated as INCLUDED in the fee; split equally into CGST + SGST
    "invoice_prefix": "INV",
    "document_title": "Payment Receipt",
    "item_description": "Certificate processing fee",
    "team_name": "NeuIntern Programs Team",
    "brand_line": "A Product of VividOne Pvt. Ltd.",
    "footer_note": "This is a system-generated receipt.",
}

FIELDS = tuple(DEFAULTS)


def with_defaults(values: dict | None) -> dict:
    """Fills any missing field (e.g. a snapshot taken before a field existed)."""
    merged = dict(DEFAULTS)
    if values:
        merged.update({k: v for k, v in values.items() if k in DEFAULTS and v is not None})
    return merged


def get_settings(db: Session) -> dict:
    row = db.get(InvoiceSettings, 1)
    if row is None:
        return dict(DEFAULTS)
    return with_defaults({f: getattr(row, f) for f in FIELDS})


def save_settings(db: Session, values: dict) -> dict:
    row = db.get(InvoiceSettings, 1)
    if row is None:
        row = InvoiceSettings(id=1)
        db.add(row)
    for field in FIELDS:
        if field in values:
            setattr(row, field, values[field])
    db.commit()
    return get_settings(db)


def snapshot_json(db: Session) -> str:
    """The text stored on an enrollment at payment time."""
    return json.dumps(get_settings(db))


def details_for(enrollment: Enrollment) -> dict:
    """The details an issued invoice must show: its snapshot, or, for payments
    made before snapshots existed, the original hard-coded values."""
    if enrollment.invoice_details_json:
        try:
            return with_defaults(json.loads(enrollment.invoice_details_json))
        except ValueError:
            pass
    return dict(DEFAULTS)
