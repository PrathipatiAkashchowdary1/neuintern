"""The certificate fee is the program's price, editable by an admin, and the
Razorpay order, the invoice and the webhook check must all agree with it."""

from datetime import datetime, timezone

import pytest

from app.db.models import Enrollment, Program
from app.services.payment_service import invoice_data
from app.services.reminder_service import build_reminder
from tests.conftest import post_webhook, verify_body, webhook_event

SLUG = "react-development"


def _program(db, price: float, slug: str = SLUG) -> Program:
    program = Program(slug=slug, title="React Development", category="Web", tagline="t", image="i", price=price)
    db.add(program)
    db.commit()
    return program


def _set_price(client, auth, admin, price, slug=SLUG):
    return client.put(f"/api/admin/programs/{slug}", json={"price": price}, headers=auth(admin))


def _fresh(db, e) -> Enrollment:
    db.expire_all()
    return db.get(Enrollment, e.id)


def _enroll(client, auth, user, slug=SLUG) -> dict:
    r = client.post("/api/enrollments", json={"programSlug": slug}, headers=auth(user))
    assert r.status_code == 201, r.text
    return r.json()["data"]


def _order(client, auth, user, enrollment_id):
    return client.post(f"/api/enrollments/{enrollment_id}/payment/create-order", headers=auth(user))


@pytest.fixture(autouse=True)
def _no_outgoing_mail(outbox):
    return outbox


# --------------------------------------------------------------------------
# Admin edits the fee
# --------------------------------------------------------------------------


class TestAdminEditsFee:
    def test_admin_can_change_the_price(self, client, db, make_user, auth):
        _program(db, 150)
        admin = make_user(role="admin")
        r = _set_price(client, auth, admin, 499)
        assert r.status_code == 200
        assert r.json()["data"]["price"] == 499

    @pytest.mark.parametrize("bad", [0, -5, 0.5])
    def test_price_below_one_rupee_is_rejected(self, client, db, make_user, auth, bad):
        _program(db, 150)
        r = _set_price(client, auth, make_user(role="admin"), bad)
        assert r.status_code == 422
        db.expire_all()
        assert db.get(Program, SLUG).price == 150

    def test_new_programs_must_have_a_valid_fee(self, client, make_user, auth):
        admin = make_user(role="admin")
        body = {"slug": "new-prog", "title": "New", "category": "Web", "price": 0}
        assert client.post("/api/admin/programs", json=body, headers=auth(admin)).status_code == 422
        body["price"] = 250
        r = client.post("/api/admin/programs", json=body, headers=auth(admin))
        assert r.status_code == 201 and r.json()["data"]["price"] == 250

    def test_new_programs_default_to_the_standard_fee(self, client, make_user, auth):
        admin = make_user(role="admin")
        r = client.post("/api/admin/programs", json={"slug": "p", "title": "P", "category": "Web"}, headers=auth(admin))
        assert r.json()["data"]["price"] == 150

    def test_students_cannot_edit_prices(self, client, db, make_user, auth):
        _program(db, 150)
        assert _set_price(client, auth, make_user(), 1).status_code == 403

    def test_public_catalog_shows_the_new_fee(self, client, db, make_user, auth):
        _program(db, 150)
        _set_price(client, auth, make_user(role="admin"), 275)
        assert client.get(f"/api/programs/{SLUG}").json()["data"]["price"] == 275


# --------------------------------------------------------------------------
# Gateway, invoice and webhook all follow the admin's number
# --------------------------------------------------------------------------


class TestChargesFollowAdminPrice:
    def test_enrollment_starts_at_the_program_price(self, client, db, make_user, auth):
        _program(db, 300)
        assert _enroll(client, auth, make_user())["amount"] == 300

    def test_razorpay_order_uses_the_program_price(self, client, db, make_user, auth, fake_razorpay):
        _program(db, 300)
        user = make_user()
        e = _enroll(client, auth, user)
        _submit_task(db, e["id"])
        r = _order(client, auth, user, e["id"])
        assert r.status_code == 201
        assert fake_razorpay[0]["amount"] == 30000  # paise
        assert fake_razorpay[0]["currency"] == "INR"
        assert r.json()["data"]["amount"] == 30000

    def test_price_change_before_paying_is_picked_up(self, client, db, make_user, auth, fake_razorpay):
        _program(db, 150)
        admin, user = make_user(role="admin"), make_user()
        e = _enroll(client, auth, user)
        _submit_task(db, e["id"])
        _set_price(client, auth, admin, 999)

        shown = client.get(f"/api/enrollments/{e['id']}", headers=auth(user)).json()["data"]
        assert shown["amount"] == 999  # dashboard shows the new fee before an order exists

        _order(client, auth, user, e["id"])
        assert fake_razorpay[0]["amount"] == 99900
        assert _fresh(db, _row(e)).amount == 999

    def test_my_enrollments_list_shows_the_current_fee(self, client, db, make_user, auth):
        _program(db, 150)
        user = make_user()
        _enroll(client, auth, user)
        _set_price(client, auth, make_user(role="admin"), 180)
        rows = client.get("/api/enrollments/me", headers=auth(user)).json()["data"]
        assert [r["amount"] for r in rows] == [180]

    def test_invoice_shows_the_amount_actually_paid(self, client, db, make_user, auth, fake_razorpay):
        _program(db, 150)
        user = make_user()
        e = _enroll(client, auth, user)
        _submit_task(db, e["id"])
        _set_price(client, auth, make_user(role="admin"), 420)
        _order(client, auth, user, e["id"])
        row = _fresh(db, _row(e))
        r = client.post(
            f"/api/enrollments/{e['id']}/payment/verify",
            json=verify_body(e["id"], row.razorpay_order_id, "pay_1"),
            headers=auth(user),
        )
        assert r.status_code == 200
        inv = invoice_data(_fresh(db, _row(e)))
        assert inv["amount"] == 420 and inv["currency"] == "INR"

    def test_paid_invoice_is_frozen_when_the_price_changes_later(self, client, db, make_user, auth, fake_razorpay):
        _program(db, 150)
        admin, user = make_user(role="admin"), make_user()
        e = _enroll(client, auth, user)
        _submit_task(db, e["id"])
        _order(client, auth, user, e["id"])
        order_id = _fresh(db, _row(e)).razorpay_order_id
        client.post(
            f"/api/enrollments/{e['id']}/payment/verify",
            json=verify_body(e["id"], order_id, "pay_1"),
            headers=auth(user),
        )

        _set_price(client, auth, admin, 9999)

        shown = client.get(f"/api/enrollments/{e['id']}", headers=auth(user)).json()["data"]
        assert shown["amount"] == 150
        assert shown["feeToPay"] == 150  # paid: frozen, not the new 9999
        assert invoice_data(_fresh(db, _row(e)))["amount"] == 150
        assert client.get(f"/api/enrollments/{e['id']}/invoice/pdf", headers=auth(user)).status_code == 200

    def test_webhook_accepts_the_new_amount_and_rejects_the_old(self, client, db, make_user, auth, fake_razorpay):
        _program(db, 150)
        user = make_user()
        e = _enroll(client, auth, user)
        _submit_task(db, e["id"])
        _set_price(client, auth, make_user(role="admin"), 400)
        _order(client, auth, user, e["id"])
        order_id = _fresh(db, _row(e)).razorpay_order_id

        post_webhook(client, webhook_event(order_id, "pay_old", amount=15000))  # stale price
        assert _fresh(db, _row(e)).payment_status == "pending"

        post_webhook(client, webhook_event(order_id, "pay_ok", amount=40000))
        assert _fresh(db, _row(e)).payment_status == "paid"

    def test_fractional_prices_round_to_whole_paise(self, client, db, make_user, auth, fake_razorpay):
        _program(db, 149.5)
        user = make_user()
        e = _enroll(client, auth, user)
        _submit_task(db, e["id"])
        _order(client, auth, user, e["id"])
        assert fake_razorpay[0]["amount"] == 14950
        assert _fresh(db, _row(e)).amount == 149.5

    def test_dashboard_shows_new_price_for_a_student_who_already_opened_checkout(
        self, client, db, make_user, auth, fake_razorpay
    ):
        """The displayed fee must equal what the next checkout charges."""
        _program(db, 150)
        user = make_user()
        e = _enroll(client, auth, user)
        _submit_task(db, e["id"])
        _order(client, auth, user, e["id"])  # abandoned checkout -> status pending at 150
        _set_price(client, auth, make_user(role="admin"), 750)
        rows = client.get("/api/enrollments/me", headers=auth(user)).json()["data"]
        assert rows[0]["paymentStatus"] == "pending"
        assert rows[0]["feeToPay"] == 750
        _order(client, auth, user, e["id"])
        assert fake_razorpay[-1]["amount"] == int(rows[0]["feeToPay"] * 100)

    def test_pending_order_keeps_its_amount_until_a_new_order_is_made(self, client, db, make_user, auth, fake_razorpay):
        """Razorpay's order amount is fixed, so the enrollment must keep matching it."""
        _program(db, 150)
        user = make_user()
        e = _enroll(client, auth, user)
        _submit_task(db, e["id"])
        _order(client, auth, user, e["id"])
        _set_price(client, auth, make_user(role="admin"), 600)
        shown = client.get(f"/api/enrollments/{e['id']}", headers=auth(user)).json()["data"]
        assert shown["amount"] == 150  # still the open order's amount
        assert shown["feeToPay"] == 600  # but the dashboard must show what paying now costs
        _order(client, auth, user, e["id"])  # student retries -> new order at the new price
        assert fake_razorpay[-1]["amount"] == 60000
        assert _fresh(db, _row(e)).amount == 600


# --------------------------------------------------------------------------
# Safety nets
# --------------------------------------------------------------------------


class TestSafetyNets:
    def test_legacy_zero_price_falls_back_to_the_standard_fee(self, client, db, make_user, auth, fake_razorpay):
        _program(db, 0)
        user = make_user()
        e = _enroll(client, auth, user)
        assert e["amount"] == 150
        _submit_task(db, e["id"])
        _order(client, auth, user, e["id"])
        assert fake_razorpay[0]["amount"] == 15000
        assert client.get(f"/api/programs/{SLUG}").json()["data"]["price"] == 150

    def test_deactivated_program_can_still_be_paid_for(self, client, db, make_user, auth, fake_razorpay):
        _program(db, 200)
        user = make_user()
        e = _enroll(client, auth, user)
        _submit_task(db, e["id"])
        client.delete(f"/api/admin/programs/{SLUG}", headers=auth(make_user(role="admin")))
        assert _order(client, auth, user, e["id"]).status_code == 201
        assert fake_razorpay[0]["amount"] == 20000

    def test_missing_program_row_falls_back_instead_of_failing(self, client, db, make_user, auth, make_enrollment, fake_razorpay):
        user = make_user()
        e = make_enrollment(user, task_submitted_at=datetime.now(timezone.utc), program_slug="vanished")
        assert _order(client, auth, user, e.id).status_code == 201
        assert fake_razorpay[0]["amount"] == 15000


# --------------------------------------------------------------------------
# Reminder emails quote the current fee
# --------------------------------------------------------------------------


class TestReminderQuotesCurrentFee:
    def test_payment_reminder_shows_the_programs_current_fee(self, db, monkeypatch, make_user, make_enrollment):
        from app.services import reminder_service
        from tests.test_reminders import _submitted

        _program(db, 150)
        db.get(Program, SLUG).price = 333
        db.commit()
        make_enrollment(make_user(), days_ago=5, task_submitted_at=_submitted(3))
        sent = []
        monkeypatch.setattr(reminder_service, "send_email", lambda to, subject, body, headers=None: sent.append(body))
        reminder_service.send_due_reminders(db)
        assert "₹333" in sent[0]

    def test_build_reminder_defaults_to_the_enrollment_amount(self, make_user, make_enrollment):
        from tests.test_reminders import _submitted

        e = make_enrollment(make_user(), days_ago=5, amount=275, task_submitted_at=_submitted(3))
        assert "₹275" in build_reminder(e)[1]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


class _row:
    """Lets tests pass an enrollment dict where an object with .id is expected."""

    def __init__(self, data):
        self.id = data["id"]


def _submit_task(db, enrollment_id: str) -> None:
    db.expire_all()
    db.get(Enrollment, enrollment_id).task_submitted_at = datetime.now(timezone.utc)
    db.commit()
