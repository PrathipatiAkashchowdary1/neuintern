"""Admin-editable invoice details, and the guarantee that issued invoices never change."""

import io
from datetime import datetime, timezone

import pytest
from pypdf import PdfReader

from app.db.models import Enrollment
from app.services.invoice_settings import DEFAULTS
from app.services.payment_service import invoice_data
from app.services.pdf_service import generate_invoice_pdf
from tests.conftest import post_webhook, webhook_event

CUSTOM = {
    "company_name": "Acme Learning LLP",
    "address": "12 Park Street\nMumbai, Maharashtra 400001",
    "gstin": "27AAPFU0939F1ZV",
    "email": "billing@acme-learning.com",
    "phone": "+91 99999 11111",
    "gst_rate": 12.0,
    "invoice_prefix": "ACME",
    "document_title": "Tax Invoice",
    "item_description": "Certification fee",
    "team_name": "Acme Billing Desk",
    "brand_line": "An Acme Learning initiative",
    "footer_note": "Computer generated, no signature required.",
}

URL = "/api/admin/invoice-settings"


def pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return " ".join(" ".join(p.extract_text().split()) for p in reader.pages)


def render(details=None, amount=349.0, **over) -> str:
    data = {
        "details": details,
        "invoiceNumber": "INV-2026-TEST0001",
        "invoiceDate": "November 25, 2026",
        "studentName": "Test Student",
        "email": "t@example.com",
        "phone": "9999999999",
        "programTitle": "React Development",
        "amount": amount,
        "currency": "INR",
        "paymentId": "pay_1",
        "orderId": "order_1",
    }
    data.update(over)
    return pdf_text(generate_invoice_pdf(data).read())


@pytest.fixture
def admin(make_user, auth):
    return auth(make_user(role="admin"))


def _pay(client, make_enrollment, make_user, order="order_1", payment="pay_1", **over):
    """Creates a pending enrollment and confirms the payment via the webhook."""
    e = make_enrollment(
        make_user(),
        task_submitted_at=datetime.now(timezone.utc),
        razorpay_order_id=order,
        payment_status="pending",
        **over,
    )
    assert post_webhook(client, webhook_event(order, payment)).status_code == 200
    return e


def _enrollment(db, e) -> Enrollment:
    db.expire_all()
    return db.get(Enrollment, e.id)


# --------------------------------------------------------------------------
# Admin API
# --------------------------------------------------------------------------


class TestAdminApi:
    def test_defaults_are_returned_until_something_is_saved(self, client, admin):
        data = client.get(URL, headers=admin).json()["data"]
        assert data["settings"] == DEFAULTS
        assert data["defaults"] == DEFAULTS

    def test_save_and_read_back(self, client, admin):
        r = client.put(URL, json=CUSTOM, headers=admin)
        assert r.status_code == 200, r.text
        saved = client.get(URL, headers=admin).json()["data"]["settings"]
        assert saved == CUSTOM
        assert client.get(URL, headers=admin).json()["data"]["defaults"] == DEFAULTS  # still resettable

    def test_second_save_updates_the_single_row(self, client, db, admin):
        from app.db.models import InvoiceSettings

        client.put(URL, json=CUSTOM, headers=admin)
        client.put(URL, json={**CUSTOM, "company_name": "Renamed Co"}, headers=admin)
        assert db.query(InvoiceSettings).count() == 1
        assert client.get(URL, headers=admin).json()["data"]["settings"]["company_name"] == "Renamed Co"

    def test_optional_fields_can_be_blank(self, client, admin):
        body = {**CUSTOM, "gstin": "", "email": "", "phone": "", "team_name": "", "brand_line": "", "footer_note": ""}
        assert client.put(URL, json=body, headers=admin).status_code == 200

    def test_gstin_is_normalised_to_uppercase(self, client, admin):
        client.put(URL, json={**CUSTOM, "gstin": "27aapfu0939f1zv"}, headers=admin)
        assert client.get(URL, headers=admin).json()["data"]["settings"]["gstin"] == "27AAPFU0939F1ZV"

    def test_whitespace_is_trimmed(self, client, admin):
        client.put(URL, json={**CUSTOM, "company_name": "  Padded Co  "}, headers=admin)
        assert client.get(URL, headers=admin).json()["data"]["settings"]["company_name"] == "Padded Co"

    @pytest.mark.parametrize(
        "field,value",
        [
            ("gstin", "NOTAGSTIN"),
            ("gstin", "27AAPFU0939F1Z"),  # too short
            ("company_name", ""),
            ("company_name", "   "),
            ("address", ""),
            ("address", "1\n2\n3\n4"),  # too many lines
            ("address", "x" * 91),  # line too long
            ("gst_rate", -1),
            ("gst_rate", 40.5),
            ("invoice_prefix", ""),
            ("invoice_prefix", "has space"),
            ("invoice_prefix", "WAYTOOLONGPREFIX"),
            ("document_title", ""),
            ("item_description", ""),
            ("email", "not-an-email"),
            ("company_name", "Line\nBreak"),
            ("phone", "x" * 31),
            ("footer_note", "y" * 101),
        ],
    )
    def test_invalid_values_are_rejected_and_nothing_is_saved(self, client, admin, field, value):
        assert client.put(URL, json={**CUSTOM, field: value}, headers=admin).status_code == 422
        assert client.get(URL, headers=admin).json()["data"]["settings"] == DEFAULTS

    @pytest.mark.parametrize("text", ["हिन्दी कंपनी", "Company 🚀", "Zażółć Ltd", "日本"])
    def test_characters_the_pdf_font_cannot_draw_are_rejected(self, client, admin, text):
        r = client.put(URL, json={**CUSTOM, "company_name": text}, headers=admin)
        assert r.status_code == 422
        assert "English" in r.json()["message"] or "Western" in r.json()["message"]

    def test_western_accents_and_symbols_are_fine(self, client, admin):
        r = client.put(URL, json={**CUSTOM, "company_name": "Café & Sons (Pvt.) Ltd. — Pune"}, headers=admin)
        assert r.status_code == 200

    def test_students_cannot_read_or_change_it(self, client, make_user, auth):
        h = auth(make_user())
        assert client.get(URL, headers=h).status_code == 403
        assert client.put(URL, json=CUSTOM, headers=h).status_code == 403
        assert client.post(URL + "/preview", json=CUSTOM, headers=h).status_code == 403

    def test_anonymous_is_unauthorized(self, client):
        assert client.get(URL).status_code == 401
        assert client.put(URL, json=CUSTOM).status_code == 401
        assert client.post(URL + "/preview", json=CUSTOM).status_code == 401


# --------------------------------------------------------------------------
# Preview
# --------------------------------------------------------------------------


class TestPreview:
    def test_returns_a_pdf_built_from_the_submitted_values(self, client, admin):
        r = client.post(URL + "/preview", json=CUSTOM, headers=admin)
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        text = pdf_text(r.content)
        assert "Acme Learning LLP" in text and "Tax Invoice" in text and "ACME-2026-SAMPLE01" in text

    def test_preview_does_not_save(self, client, admin):
        client.post(URL + "/preview", json=CUSTOM, headers=admin)
        assert client.get(URL, headers=admin).json()["data"]["settings"] == DEFAULTS

    def test_invalid_input_is_rejected(self, client, admin):
        assert client.post(URL + "/preview", json={**CUSTOM, "gstin": "bad"}, headers=admin).status_code == 422


# --------------------------------------------------------------------------
# What the PDF prints
# --------------------------------------------------------------------------


class TestPdfContent:
    def test_default_details_match_the_original_hardcoded_invoice(self):
        text = render(None, amount=150)
        for expected in [
            "VividOne Pvt. Ltd.",
            "#Flat no 401, Vasista Enclave, A.S.Raju Nagar, KPHB,",
            "Hyderabad, Telangana 500072, India",
            "GSTIN: 36AAHCV0625N1Z1",
            "Email: contact@neuintern.com",
            "Phone: +91 9652522929",
            "Payment Receipt",
            "Certificate processing fee",
            "INR 127.12",
            "CGST @ 9% INR 11.44",
            "SGST @ 9% INR 11.44",
            "Total Paid INR 150.00",
            "NeuIntern Programs Team",
            "A Product of VividOne Pvt. Ltd.",
            "This is a system-generated receipt.",
        ]:
            assert expected in text, expected

    def test_custom_details_are_printed(self):
        text = render(CUSTOM)
        for expected in [
            "Acme Learning LLP",
            "12 Park Street",
            "Mumbai, Maharashtra 400001",
            "GSTIN: 27AAPFU0939F1ZV",
            "Email: billing@acme-learning.com",
            "Phone: +91 99999 11111",
            "Tax Invoice",
            "Certification fee",
            "Acme Billing Desk",
            "An Acme Learning initiative",
            "Computer generated, no signature required.",
        ]:
            assert expected in text, expected
        assert "VividOne" not in text and "36AAHCV0625N1Z1" not in text

    def test_blank_optional_fields_leave_no_empty_labels(self):
        text = render({**CUSTOM, "gstin": "", "email": "", "phone": "", "team_name": "", "brand_line": "", "footer_note": ""})
        for label in ("GSTIN:", "Email:", "Phone:", "Acme Billing Desk", "system-generated"):
            assert label not in text

    def test_gst_rate_drives_the_tax_rows(self):
        text = render({**DEFAULTS, "gst_rate": 5.0}, amount=105)
        assert "INR 100.00" in text  # taxable
        assert "CGST @ 2.5% INR 2.50" in text and "SGST @ 2.5% INR 2.50" in text
        assert "Total Paid INR 105.00" in text

    @pytest.mark.parametrize("amount", [150, 149.99, 349, 1, 999.5, 1234.56])
    def test_rows_always_add_up_to_the_total(self, amount):
        import re

        text = render({**DEFAULTS, "gst_rate": 18.0}, amount=amount)
        taxable = float(re.search(r"React Development internship INR ([\d.]+)", text).group(1))
        cgst = float(re.search(r"CGST @ 9% INR ([\d.]+)", text).group(1))
        sgst = float(re.search(r"SGST @ 9% INR ([\d.]+)", text).group(1))
        assert round(taxable + cgst + sgst, 2) == round(float(amount), 2)

    def test_zero_rate_prints_no_tax_rows(self):
        text = render({**DEFAULTS, "gst_rate": 0}, amount=349)
        assert "CGST" not in text and "SGST" not in text
        assert "React Development internship INR 349.00" in text
        assert "Total Paid INR 349.00" in text

    def test_three_line_address_still_renders(self):
        text = render({**DEFAULTS, "address": "Line one\nLine two\nLine three"})
        assert "Line three" in text and "BILLED TO" in text and "Total Paid" in text

    def test_older_snapshots_missing_new_fields_still_render(self):
        text = render({"company_name": "Only Name Co"})  # everything else falls back to defaults
        assert "Only Name Co" in text and "Payment Receipt" in text


# --------------------------------------------------------------------------
# Issued invoices never change
# --------------------------------------------------------------------------


class TestIssuedInvoicesAreFrozen:
    def test_settings_edited_before_payment_are_used(self, client, db, admin, make_user, make_enrollment, outbox):
        client.put(URL, json=CUSTOM, headers=admin)
        e = _pay(client, make_enrollment, make_user)
        inv = invoice_data(_enrollment(db, e))
        assert inv["invoiceNumber"].startswith("ACME-")
        text = pdf_text(outbox[0].attachments[0][1])
        assert "Acme Learning LLP" in text and "Tax Invoice" in text
        assert outbox[0].attachments[0][0].startswith("NeuIntern-Invoice-ACME-")

    def test_settings_edited_after_payment_do_not_change_that_invoice(
        self, client, db, admin, make_user, make_enrollment, auth, outbox
    ):
        client.put(URL, json=CUSTOM, headers=admin)
        owner = make_user()
        e = make_enrollment(
            owner, task_submitted_at=datetime.now(timezone.utc), razorpay_order_id="order_1", payment_status="pending"
        )
        post_webhook(client, webhook_event("order_1", "pay_1"))

        client.put(URL, json={**CUSTOM, "company_name": "Totally New Name", "gst_rate": 5, "invoice_prefix": "NEW"}, headers=admin)

        r = client.get(f"/api/enrollments/{e.id}/invoice/pdf", headers=auth(owner))
        assert r.status_code == 200
        text = pdf_text(r.content)
        assert "Acme Learning LLP" in text and "Totally New Name" not in text
        assert "CGST @ 6%" in text  # still the 12% it was issued with
        assert invoice_data(_enrollment(db, e))["invoiceNumber"].startswith("ACME-")

    def test_the_emailed_copy_and_the_later_download_are_identical(
        self, client, db, admin, make_user, make_enrollment, auth, outbox
    ):
        client.put(URL, json=CUSTOM, headers=admin)
        owner = make_user()
        e = make_enrollment(
            owner, task_submitted_at=datetime.now(timezone.utc), razorpay_order_id="order_1", payment_status="pending"
        )
        post_webhook(client, webhook_event("order_1", "pay_1"))
        client.put(URL, json={**CUSTOM, "company_name": "Changed Later"}, headers=admin)
        emailed = pdf_text(outbox[0].attachments[0][1])
        downloaded = pdf_text(client.get(f"/api/enrollments/{e.id}/invoice/pdf", headers=auth(owner)).content)
        assert emailed == downloaded

    def test_new_payments_pick_up_the_new_settings(self, client, admin, make_user, make_enrollment, outbox):
        client.put(URL, json=CUSTOM, headers=admin)
        _pay(client, make_enrollment, make_user, order="order_a", payment="pay_a")
        client.put(URL, json={**CUSTOM, "company_name": "Second Era Ltd", "invoice_prefix": "SEC"}, headers=admin)
        _pay(client, make_enrollment, make_user, order="order_b", payment="pay_b")
        first, second = (pdf_text(m.attachments[0][1]) for m in outbox[:2])
        assert "Acme Learning LLP" in first and "Second Era" not in first
        assert "Second Era Ltd" in second and "Acme Learning LLP" not in second
        assert outbox[1].attachments[0][0].startswith("NeuIntern-Invoice-SEC-")

    def test_payments_made_before_snapshots_existed_keep_the_original_details(
        self, client, db, admin, make_user, make_enrollment, auth
    ):
        """A legacy paid enrollment has no snapshot; admin edits must not leak into it."""
        client.put(URL, json=CUSTOM, headers=admin)
        owner = make_user()
        e = make_enrollment(
            owner,
            payment_status="paid",
            paid_at=datetime.now(timezone.utc),
            razorpay_order_id="o",
            razorpay_payment_id="p",
            invoice_details_json=None,
        )
        text = pdf_text(client.get(f"/api/enrollments/{e.id}/invoice/pdf", headers=auth(owner)).content)
        assert "VividOne Pvt. Ltd." in text and "Acme Learning" not in text
        assert invoice_data(_enrollment(db, e))["invoiceNumber"].startswith("INV-")

    def test_corrupt_snapshot_falls_back_to_the_originals(self, client, db, make_user, make_enrollment, auth):
        owner = make_user()
        e = make_enrollment(
            owner, payment_status="paid", paid_at=datetime.now(timezone.utc), invoice_details_json="{not json"
        )
        r = client.get(f"/api/enrollments/{e.id}/invoice/pdf", headers=auth(owner))
        assert r.status_code == 200 and "VividOne" in pdf_text(r.content)

    def test_admin_downloads_the_same_frozen_invoice(self, client, admin, make_user, make_enrollment, outbox):
        client.put(URL, json=CUSTOM, headers=admin)
        e = _pay(client, make_enrollment, make_user)
        client.put(URL, json={**CUSTOM, "company_name": "Changed Later"}, headers=admin)
        text = pdf_text(client.get(f"/api/enrollments/{e.id}/invoice/pdf", headers=admin).content)
        assert "Acme Learning LLP" in text and "Changed Later" not in text

    def test_a_second_confirmation_does_not_refresh_the_snapshot(self, client, db, admin, make_user, make_enrollment, outbox):
        client.put(URL, json=CUSTOM, headers=admin)
        e = _pay(client, make_enrollment, make_user)
        before = _enrollment(db, e).invoice_details_json
        client.put(URL, json={**CUSTOM, "company_name": "Changed Later"}, headers=admin)
        post_webhook(client, webhook_event("order_1", "pay_1"))  # duplicate delivery
        assert _enrollment(db, e).invoice_details_json == before
