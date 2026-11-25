"""Certificate-fee payment: order creation, browser verify, Razorpay webhook."""

import hashlib
import hmac
import json
from datetime import datetime, timezone

from app.db.models import Enrollment
from app.services.payment_service import mark_enrollment_paid
from tests.conftest import (
    FEE_PAISE,
    WEBHOOK_SECRET,
    checkout_signature,
    post_webhook,
    verify_body,
    webhook_event,
)


def _fresh(db, enrollment) -> Enrollment:
    db.expire_all()
    return db.get(Enrollment, enrollment.id)


def _pending(make_enrollment, user, order_id="order_1", **overrides):
    return make_enrollment(
        user,
        task_submitted_at=datetime.now(timezone.utc),
        razorpay_order_id=order_id,
        payment_status="pending",
        **overrides,
    )


# --------------------------------------------------------------------------
# POST /enrollments/{id}/payment/create-order
# --------------------------------------------------------------------------


class TestCreateOrder:
    def test_requires_task_submission_first(self, client, make_user, make_enrollment, auth, fake_razorpay):
        user = make_user()
        e = make_enrollment(user)
        r = client.post(f"/api/enrollments/{e.id}/payment/create-order", headers=auth(user))
        assert r.status_code == 400
        assert "task" in r.json()["message"].lower()
        assert fake_razorpay == []

    def test_creates_order_and_marks_pending(self, client, db, make_user, make_enrollment, auth, fake_razorpay):
        user = make_user()
        e = make_enrollment(user, task_submitted_at=datetime.now(timezone.utc))
        r = client.post(f"/api/enrollments/{e.id}/payment/create-order", headers=auth(user))
        assert r.status_code == 201
        data = r.json()["data"]
        assert data["orderId"] == "order_test_1"
        assert data["amount"] == FEE_PAISE
        assert data["keyId"] == "rzp_test_key"
        assert fake_razorpay[0]["amount"] == FEE_PAISE
        fresh = _fresh(db, e)
        assert fresh.razorpay_order_id == "order_test_1"
        assert fresh.payment_status == "pending"

    def test_amount_is_server_side_not_client_controlled(self, client, make_user, make_enrollment, auth, fake_razorpay):
        user = make_user()
        e = make_enrollment(user, task_submitted_at=datetime.now(timezone.utc), amount=1)
        client.post(f"/api/enrollments/{e.id}/payment/create-order", headers=auth(user), json={"amount": 1})
        assert fake_razorpay[0]["amount"] == FEE_PAISE

    def test_rejects_already_paid(self, client, make_user, make_enrollment, auth, fake_razorpay):
        user = make_user()
        e = make_enrollment(user, task_submitted_at=datetime.now(timezone.utc), payment_status="paid")
        r = client.post(f"/api/enrollments/{e.id}/payment/create-order", headers=auth(user))
        assert r.status_code == 400
        assert fake_razorpay == []

    def test_503_when_razorpay_not_configured(self, client, monkeypatch, make_user, make_enrollment, auth, fake_razorpay):
        monkeypatch.setattr("app.core.config.settings.razorpay_key_id", "")
        user = make_user()
        e = make_enrollment(user, task_submitted_at=datetime.now(timezone.utc))
        r = client.post(f"/api/enrollments/{e.id}/payment/create-order", headers=auth(user))
        assert r.status_code == 503

    def test_other_students_enrollment_is_forbidden(self, client, make_user, make_enrollment, auth, fake_razorpay):
        owner, stranger = make_user(), make_user()
        e = make_enrollment(owner, task_submitted_at=datetime.now(timezone.utc))
        r = client.post(f"/api/enrollments/{e.id}/payment/create-order", headers=auth(stranger))
        assert r.status_code == 403

    def test_requires_login(self, client, make_user, make_enrollment):
        e = make_enrollment(make_user())
        assert client.post(f"/api/enrollments/{e.id}/payment/create-order").status_code == 401


# --------------------------------------------------------------------------
# POST /enrollments/{id}/payment/verify  (browser callback after checkout)
# --------------------------------------------------------------------------


class TestVerify:
    def test_valid_signature_marks_paid_and_sends_invoice(self, client, db, make_user, make_enrollment, auth, outbox):
        user = make_user()
        e = _pending(make_enrollment, user)
        r = client.post(
            f"/api/enrollments/{e.id}/payment/verify",
            json=verify_body(e.id, "order_1", "pay_1"),
            headers=auth(user),
        )
        assert r.status_code == 200
        assert r.json()["data"]["paymentStatus"] == "paid"
        fresh = _fresh(db, e)
        assert fresh.payment_status == "paid"
        assert fresh.razorpay_payment_id == "pay_1"
        assert fresh.paid_at is not None
        assert len(outbox) == 1
        assert outbox[0].to == user.email
        assert outbox[0].subject.startswith("Payment Receipt")
        assert outbox[0].attachments[0][1].startswith(b"%PDF")

    def test_mid_course_payment_does_not_unlock_certificate(self, client, db, make_user, make_enrollment, auth, outbox):
        user = make_user()
        e = _pending(make_enrollment, user, days_ago=3)
        r = client.post(
            f"/api/enrollments/{e.id}/payment/verify", json=verify_body(e.id, "order_1", "pay_1"), headers=auth(user)
        )
        assert r.status_code == 200
        assert "once the course is complete" in r.json()["message"]
        assert _fresh(db, e).certificate_unlocked is False
        assert [m.subject.split(" ")[0] for m in outbox] == ["Payment"]

    def test_payment_after_course_end_unlocks_and_emails_certificate(
        self, client, db, make_user, make_enrollment, auth, outbox
    ):
        user = make_user()
        e = _pending(make_enrollment, user, days_ago=40)
        r = client.post(
            f"/api/enrollments/{e.id}/payment/verify", json=verify_body(e.id, "order_1", "pay_1"), headers=auth(user)
        )
        assert r.status_code == 200
        assert "certificate is ready" in r.json()["message"]
        fresh = _fresh(db, e)
        assert fresh.certificate_unlocked is True
        assert fresh.certificate_id.startswith("NI-")
        assert [m.subject.split(" ")[0] for m in outbox] == ["Payment", "Your"]
        assert outbox[1].attachments[0][0].startswith("NeuIntern-Certificate-NI-")

    def test_is_idempotent_retry_sends_nothing_more(self, client, make_user, make_enrollment, auth, outbox):
        user = make_user()
        e = _pending(make_enrollment, user)
        body = verify_body(e.id, "order_1", "pay_1")
        first = client.post(f"/api/enrollments/{e.id}/payment/verify", json=body, headers=auth(user))
        second = client.post(f"/api/enrollments/{e.id}/payment/verify", json=body, headers=auth(user))
        assert first.status_code == second.status_code == 200
        assert second.json()["data"]["paymentStatus"] == "paid"
        assert len(outbox) == 1

    def test_bad_signature_is_rejected_and_nothing_is_marked(self, client, db, make_user, make_enrollment, auth, outbox):
        user = make_user()
        e = _pending(make_enrollment, user)
        r = client.post(
            f"/api/enrollments/{e.id}/payment/verify",
            json=verify_body(e.id, "order_1", "pay_1", signature="0" * 64),
            headers=auth(user),
        )
        assert r.status_code == 400
        fresh = _fresh(db, e)
        assert fresh.payment_status == "pending"  # not "failed": the student may retry
        assert outbox == []

    def test_signature_made_with_wrong_secret_is_rejected(self, client, db, make_user, make_enrollment, auth):
        user = make_user()
        e = _pending(make_enrollment, user)
        forged = checkout_signature("order_1", "pay_1", secret="attacker-guess")
        r = client.post(
            f"/api/enrollments/{e.id}/payment/verify",
            json=verify_body(e.id, "order_1", "pay_1", signature=forged),
            headers=auth(user),
        )
        assert r.status_code == 400
        assert _fresh(db, e).payment_status == "pending"

    def test_bad_signature_cannot_downgrade_a_paid_enrollment(self, client, db, make_user, make_enrollment, auth):
        user = make_user()
        e = make_enrollment(user, payment_status="paid", razorpay_order_id="order_1", razorpay_payment_id="pay_1")
        r = client.post(
            f"/api/enrollments/{e.id}/payment/verify",
            json=verify_body(e.id, "order_1", "pay_1", signature="0" * 64),
            headers=auth(user),
        )
        assert r.status_code == 200  # already paid -> just reports state
        assert _fresh(db, e).payment_status == "paid"

    def test_valid_signature_for_a_different_order_is_rejected(self, client, db, make_user, make_enrollment, auth, outbox):
        """A genuine payment for ANOTHER order must not unlock this enrollment."""
        user = make_user()
        e = _pending(make_enrollment, user, order_id="order_mine")
        r = client.post(
            f"/api/enrollments/{e.id}/payment/verify",
            json=verify_body(e.id, "order_someone_else", "pay_9"),  # correctly signed, wrong order
            headers=auth(user),
        )
        assert r.status_code == 400
        assert _fresh(db, e).payment_status == "pending"
        assert outbox == []

    def test_no_order_created_yet_is_rejected(self, client, make_user, make_enrollment, auth):
        user = make_user()
        e = make_enrollment(user)  # razorpay_order_id is None
        r = client.post(
            f"/api/enrollments/{e.id}/payment/verify", json=verify_body(e.id, "order_1", "pay_1"), headers=auth(user)
        )
        assert r.status_code == 400

    def test_other_students_enrollment_is_forbidden(self, client, make_user, make_enrollment, auth):
        owner, stranger = make_user(), make_user()
        e = _pending(make_enrollment, owner)
        r = client.post(
            f"/api/enrollments/{e.id}/payment/verify", json=verify_body(e.id, "order_1", "pay_1"), headers=auth(stranger)
        )
        assert r.status_code == 403

    def test_email_failure_does_not_fail_the_payment(self, client, db, monkeypatch, make_user, make_enrollment, auth):
        def smtp_down(**kwargs):
            raise RuntimeError("smtp down")

        monkeypatch.setattr("app.services.payment_service.send_email_with_attachments", smtp_down)
        user = make_user()
        e = _pending(make_enrollment, user)
        r = client.post(
            f"/api/enrollments/{e.id}/payment/verify", json=verify_body(e.id, "order_1", "pay_1"), headers=auth(user)
        )
        assert r.status_code == 200
        assert _fresh(db, e).payment_status == "paid"


# --------------------------------------------------------------------------
# POST /payments/webhook  (Razorpay -> us, no JWT)
# --------------------------------------------------------------------------


class TestWebhook:
    def test_captured_payment_marks_paid_and_sends_invoice(self, client, db, make_user, make_enrollment, outbox):
        user = make_user()
        e = _pending(make_enrollment, user)
        r = post_webhook(client, webhook_event("order_1", "pay_1"))
        assert r.status_code == 200
        fresh = _fresh(db, e)
        assert fresh.payment_status == "paid"
        assert fresh.razorpay_payment_id == "pay_1"
        assert len(outbox) == 1

    def test_order_paid_event_is_also_handled(self, client, db, make_user, make_enrollment):
        e = _pending(make_enrollment, make_user())
        event = webhook_event("order_1", "pay_1", event="order.paid")
        assert post_webhook(client, event).status_code == 200
        assert _fresh(db, e).payment_status == "paid"

    def test_rejects_invalid_signature(self, client, db, make_user, make_enrollment, outbox):
        e = _pending(make_enrollment, make_user())
        r = post_webhook(client, webhook_event("order_1", "pay_1"), signature="deadbeef")
        assert r.status_code == 400
        assert _fresh(db, e).payment_status == "pending"
        assert outbox == []

    def test_rejects_body_signed_with_wrong_secret(self, client, db, make_user, make_enrollment):
        e = _pending(make_enrollment, make_user())
        r = post_webhook(client, webhook_event("order_1", "pay_1"), secret="not-the-secret")
        assert r.status_code == 400
        assert _fresh(db, e).payment_status == "pending"

    def test_signature_covers_the_exact_body(self, client, db, make_user, make_enrollment):
        """Sign one amount, send another: must fail even though the secret is right."""
        e = _pending(make_enrollment, make_user())
        signed = json.dumps(webhook_event("order_1", "pay_1", amount=FEE_PAISE)).encode()
        tampered = json.dumps(webhook_event("order_1", "pay_1", amount=FEE_PAISE + 1)).encode()
        sig_for_signed = hmac.new(WEBHOOK_SECRET.encode(), signed, hashlib.sha256).hexdigest()
        r = post_webhook(client, tampered, signature=sig_for_signed)
        assert r.status_code == 400
        assert _fresh(db, e).payment_status == "pending"

    def test_503_when_webhook_secret_not_configured(self, client, monkeypatch, make_user, make_enrollment):
        monkeypatch.setattr("app.core.config.settings.razorpay_webhook_secret", "")
        _pending(make_enrollment, make_user())
        r = post_webhook(client, webhook_event("order_1", "pay_1"), secret="")
        assert r.status_code == 503

    def test_malformed_json_with_valid_signature_is_400(self, client):
        assert post_webhook(client, b"{not json").status_code == 400

    def test_unrelated_events_are_acknowledged_and_ignored(self, client, db, make_user, make_enrollment):
        e = _pending(make_enrollment, make_user())
        r = post_webhook(client, webhook_event("order_1", "pay_1", event="payment.failed"))
        assert r.status_code == 200
        assert _fresh(db, e).payment_status == "pending"

    def test_unknown_order_is_acknowledged_without_error(self, client, outbox):
        r = post_webhook(client, webhook_event("order_does_not_exist", "pay_1"))
        assert r.status_code == 200
        assert outbox == []

    def test_event_without_order_or_payment_is_acknowledged(self, client):
        assert post_webhook(client, {"event": "payment.captured", "payload": {}}).status_code == 200

    def test_underpayment_is_not_applied(self, client, db, make_user, make_enrollment, outbox):
        e = _pending(make_enrollment, make_user())
        r = post_webhook(client, webhook_event("order_1", "pay_1", amount=100))
        assert r.status_code == 200
        assert _fresh(db, e).payment_status == "pending"
        assert outbox == []

    def test_wrong_currency_is_not_applied(self, client, db, make_user, make_enrollment):
        e = _pending(make_enrollment, make_user())
        post_webhook(client, webhook_event("order_1", "pay_1", currency="USD"))
        assert _fresh(db, e).payment_status == "pending"

    def test_duplicate_deliveries_send_one_invoice(self, client, make_user, make_enrollment, outbox):
        _pending(make_enrollment, make_user())
        for _ in range(3):
            assert post_webhook(client, webhook_event("order_1", "pay_1")).status_code == 200
        assert len(outbox) == 1

    def test_webhook_after_browser_verify_is_a_noop(self, client, make_user, make_enrollment, auth, outbox):
        user = make_user()
        e = _pending(make_enrollment, user)
        client.post(
            f"/api/enrollments/{e.id}/payment/verify", json=verify_body(e.id, "order_1", "pay_1"), headers=auth(user)
        )
        post_webhook(client, webhook_event("order_1", "pay_1"))
        assert len(outbox) == 1

    def test_verify_after_webhook_is_a_noop(self, client, make_user, make_enrollment, auth, outbox):
        """The student closed the tab; the webhook paid; they come back and the page calls verify."""
        user = make_user()
        e = _pending(make_enrollment, user)
        post_webhook(client, webhook_event("order_1", "pay_1"))
        r = client.post(
            f"/api/enrollments/{e.id}/payment/verify", json=verify_body(e.id, "order_1", "pay_1"), headers=auth(user)
        )
        assert r.status_code == 200
        assert len(outbox) == 1

    def test_late_payment_via_webhook_unlocks_certificate(self, client, db, make_user, make_enrollment, outbox):
        e = _pending(make_enrollment, make_user(), days_ago=40)
        post_webhook(client, webhook_event("order_1", "pay_1"))
        assert _fresh(db, e).certificate_unlocked is True
        assert len(outbox) == 2


# --------------------------------------------------------------------------
# mark_enrollment_paid: the atomic "exactly one winner" guarantee
# --------------------------------------------------------------------------


class TestMarkEnrollmentPaid:
    def test_only_the_first_caller_wins(self, db, make_user, make_enrollment, outbox):
        e = _pending(make_enrollment, make_user())
        assert mark_enrollment_paid(db, e, "pay_1", "sig") is True
        assert mark_enrollment_paid(db, e, "pay_2", "sig") is False
        db.expire_all()
        assert db.get(Enrollment, e.id).razorpay_payment_id == "pay_1"  # not overwritten
        assert len(outbox) == 1

    def test_stale_object_cannot_win_after_another_session_paid(self, db, make_user, make_enrollment, outbox):
        """Models the verify/webhook race: this session still believes 'pending'."""
        from app.db.base import SessionLocal

        e = _pending(make_enrollment, make_user())
        assert e.payment_status == "pending"  # loaded into this session

        other = SessionLocal()
        try:
            assert mark_enrollment_paid(other, other.get(Enrollment, e.id), "pay_other") is True
        finally:
            other.close()

        assert mark_enrollment_paid(db, e, "pay_late") is False
        assert len(outbox) == 1

    def test_background_queue_is_used_when_provided(self, db, make_user, make_enrollment, outbox):
        from fastapi import BackgroundTasks

        e = _pending(make_enrollment, make_user())
        background = BackgroundTasks()
        assert mark_enrollment_paid(db, e, "pay_1", background=background) is True
        assert outbox == []  # nothing sent yet: queued for after the response
        assert len(background.tasks) == 1


# --------------------------------------------------------------------------
# GET /enrollments/{id}/invoice/pdf
# --------------------------------------------------------------------------


class TestInvoicePdf:
    def test_unavailable_until_paid(self, client, make_user, make_enrollment, auth):
        user = make_user()
        e = make_enrollment(user)
        assert client.get(f"/api/enrollments/{e.id}/invoice/pdf", headers=auth(user)).status_code == 400

    def test_paid_enrollment_gets_a_pdf(self, client, make_user, make_enrollment, auth):
        user = make_user()
        e = make_enrollment(user, payment_status="paid", paid_at=datetime.now(timezone.utc), razorpay_order_id="o", razorpay_payment_id="p")
        r = client.get(f"/api/enrollments/{e.id}/invoice/pdf", headers=auth(user))
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert r.content.startswith(b"%PDF")

    def test_other_student_cannot_download(self, client, make_user, make_enrollment, auth):
        owner, stranger = make_user(), make_user()
        e = make_enrollment(owner, payment_status="paid", paid_at=datetime.now(timezone.utc))
        assert client.get(f"/api/enrollments/{e.id}/invoice/pdf", headers=auth(stranger)).status_code == 403

    def test_admin_can_download_any_invoice(self, client, make_user, make_enrollment, auth):
        student, admin = make_user(), make_user(role="admin")
        e = make_enrollment(student, payment_status="paid", paid_at=datetime.now(timezone.utc))
        assert client.get(f"/api/enrollments/{e.id}/invoice/pdf", headers=auth(admin)).status_code == 200
