"""Certificate unlock rules, the scheduler job, download endpoints and public verification."""

from datetime import datetime, timedelta, timezone

import pytest

from app.db.models import Certificate, Enrollment
from app.services import certificate_service
from app.services.certificate_service import (
    COURSE_DURATION_DAYS,
    completion_date,
    is_course_complete,
    process_due_certificates,
    unlock_and_email_certificate,
)
from app.services.enrollments_service import enrollment_to_dict
from tests.conftest import naive_utc_now


def _fresh(db, enrollment) -> Enrollment:
    db.expire_all()
    return db.get(Enrollment, enrollment.id)


def _paid(make_enrollment, user, days_ago, **overrides):
    return make_enrollment(
        user,
        days_ago=days_ago,
        payment_status="paid",
        paid_at=datetime.now(timezone.utc),
        razorpay_order_id="order_x",
        razorpay_payment_id="pay_x",
        **overrides,
    )


# --------------------------------------------------------------------------
# Completion date rules
# --------------------------------------------------------------------------


class TestCompletionRules:
    def test_course_lasts_28_days(self):
        assert COURSE_DURATION_DAYS == 28

    def test_completion_date_is_enrolment_plus_28_days(self, make_user, make_enrollment):
        e = make_enrollment(make_user())
        assert completion_date(e) == e.enrolled_at + timedelta(days=28)

    def test_boundary(self, monkeypatch, make_user, make_enrollment):
        e = make_enrollment(make_user())
        end = completion_date(e)
        monkeypatch.setattr(certificate_service, "_now", lambda: end - timedelta(seconds=1))
        assert is_course_complete(e) is False
        monkeypatch.setattr(certificate_service, "_now", lambda: end)
        assert is_course_complete(e) is True
        monkeypatch.setattr(certificate_service, "_now", lambda: end + timedelta(days=5))
        assert is_course_complete(e) is True


# --------------------------------------------------------------------------
# Scheduler / admin job: process_due_certificates
# --------------------------------------------------------------------------


class TestProcessDueCertificates:
    def test_unlocks_and_emails_paid_enrollment_past_completion(self, db, make_user, make_enrollment, outbox):
        user = make_user()
        e = _paid(make_enrollment, user, days_ago=29)
        assert process_due_certificates(db) == 1
        fresh = _fresh(db, e)
        assert fresh.certificate_unlocked is True
        assert fresh.certificate_id == f"NI-{datetime.now(timezone.utc).year}-{e.id[:8].upper()}"
        assert fresh.certificate_issued_at is not None
        assert len(outbox) == 1
        assert outbox[0].to == user.email
        assert fresh.certificate_id in outbox[0].body
        assert outbox[0].attachments[0][1].startswith(b"%PDF")

    def test_writes_public_certificate_record(self, db, make_user, make_enrollment, outbox):
        e = _paid(make_enrollment, make_user(), days_ago=30)
        process_due_certificates(db)
        record = db.get(Certificate, _fresh(db, e).certificate_id)
        assert record is not None
        assert record.student_name == e.name
        assert record.program == e.program_title

    def test_skips_course_still_running(self, db, make_user, make_enrollment, outbox):
        e = _paid(make_enrollment, make_user(), days_ago=27)
        assert process_due_certificates(db) == 0
        assert _fresh(db, e).certificate_unlocked is False
        assert outbox == []

    @pytest.mark.parametrize("status", ["unpaid", "pending", "failed"])
    def test_never_unlocks_without_payment(self, db, make_user, make_enrollment, outbox, status):
        e = make_enrollment(make_user(), days_ago=60, payment_status=status)
        assert process_due_certificates(db) == 0
        assert _fresh(db, e).certificate_unlocked is False
        assert outbox == []

    def test_second_run_does_nothing(self, db, make_user, make_enrollment, outbox):
        _paid(make_enrollment, make_user(), days_ago=40)
        assert process_due_certificates(db) == 1
        assert process_due_certificates(db) == 0
        assert len(outbox) == 1

    def test_processes_only_the_due_ones_in_a_mixed_batch(self, db, make_user, make_enrollment, outbox):
        due1 = _paid(make_enrollment, make_user(), days_ago=35)
        due2 = _paid(make_enrollment, make_user(), days_ago=29)
        _paid(make_enrollment, make_user(), days_ago=5)
        make_enrollment(make_user(), days_ago=50)  # unpaid
        assert process_due_certificates(db) == 2
        assert {_fresh(db, due1).certificate_unlocked, _fresh(db, due2).certificate_unlocked} == {True}
        assert len(outbox) == 2

    def test_distinct_certificate_ids_per_enrollment(self, db, make_user, make_enrollment, outbox):
        a = _paid(make_enrollment, make_user(), days_ago=40)
        b = _paid(make_enrollment, make_user(), days_ago=40, program_slug="data-science", program_title="Data Science")
        process_due_certificates(db)
        assert _fresh(db, a).certificate_id != _fresh(db, b).certificate_id

    def test_unlock_and_email_certificate_inline_helper(self, db, make_user, make_enrollment, outbox):
        e = _paid(make_enrollment, make_user(), days_ago=40)
        unlock_and_email_certificate(db, e)
        assert e.certificate_unlocked is True
        assert len(outbox) == 1


# --------------------------------------------------------------------------
# POST /admin/certificates/process-due
# --------------------------------------------------------------------------


class TestAdminProcessDue:
    def test_admin_can_trigger_it(self, client, make_user, make_enrollment, auth, outbox):
        admin = make_user(role="admin")
        _paid(make_enrollment, make_user(), days_ago=40)
        r = client.post("/api/admin/certificates/process-due", headers=auth(admin))
        assert r.status_code == 200
        assert r.json()["data"]["processed"] == 1

    def test_students_are_forbidden(self, client, make_user, auth):
        assert client.post("/api/admin/certificates/process-due", headers=auth(make_user())).status_code == 403

    def test_anonymous_is_unauthorized(self, client):
        assert client.post("/api/admin/certificates/process-due").status_code == 401


# --------------------------------------------------------------------------
# GET /enrollments/{id}/certificate and /certificate/pdf
# --------------------------------------------------------------------------


class TestCertificateEndpoints:
    def test_locked_before_payment(self, client, make_user, make_enrollment, auth):
        user = make_user()
        e = make_enrollment(user)
        r = client.get(f"/api/enrollments/{e.id}/certificate", headers=auth(user))
        assert r.status_code == 403
        assert "payment" in r.json()["message"].lower()

    def test_locked_after_payment_states_the_unlock_date(self, client, make_user, make_enrollment, auth):
        user = make_user()
        e = _paid(make_enrollment, user, days_ago=3)
        r = client.get(f"/api/enrollments/{e.id}/certificate", headers=auth(user))
        assert r.status_code == 403
        assert completion_date(e).strftime("%B %d, %Y") in r.json()["message"]

    def test_pdf_is_locked_too(self, client, make_user, make_enrollment, auth):
        user = make_user()
        e = _paid(make_enrollment, user, days_ago=3)
        assert client.get(f"/api/enrollments/{e.id}/certificate/pdf", headers=auth(user)).status_code == 403

    def test_unlocked_certificate_data_and_pdf(self, client, db, make_user, make_enrollment, auth, outbox):
        user = make_user()
        e = _paid(make_enrollment, user, days_ago=40)
        process_due_certificates(db)
        cert_id = _fresh(db, e).certificate_id

        data = client.get(f"/api/enrollments/{e.id}/certificate", headers=auth(user)).json()["data"]
        assert data["certificateId"] == cert_id
        assert data["studentName"] == user.full_name
        assert data["programTitle"] == "React Development"

        pdf = client.get(f"/api/enrollments/{e.id}/certificate/pdf", headers=auth(user))
        assert pdf.status_code == 200
        assert pdf.headers["content-type"] == "application/pdf"
        assert cert_id in pdf.headers["content-disposition"]
        assert pdf.content.startswith(b"%PDF")

    def test_other_student_cannot_read_it(self, client, db, make_user, make_enrollment, auth, outbox):
        owner, stranger = make_user(), make_user()
        e = _paid(make_enrollment, owner, days_ago=40)
        process_due_certificates(db)
        assert client.get(f"/api/enrollments/{e.id}/certificate", headers=auth(stranger)).status_code == 403
        assert client.get(f"/api/enrollments/{e.id}/certificate/pdf", headers=auth(stranger)).status_code == 403

    def test_requires_login(self, client, make_user, make_enrollment):
        e = make_enrollment(make_user())
        assert client.get(f"/api/enrollments/{e.id}/certificate").status_code == 401


# --------------------------------------------------------------------------
# POST /certificate/verify  (public)
# --------------------------------------------------------------------------


class TestPublicVerification:
    def _issue(self, db, make_user, make_enrollment):
        e = _paid(make_enrollment, make_user(), days_ago=40)
        process_due_certificates(db)
        return _fresh(db, e)

    def test_issued_certificate_verifies_without_login(self, client, db, make_user, make_enrollment, outbox):
        e = self._issue(db, make_user, make_enrollment)
        r = client.post("/api/certificate/verify", json={"certificateId": e.certificate_id})
        body = r.json()
        assert body["success"] is True
        assert body["data"]["studentName"] == e.name
        assert body["data"]["program"] == e.program_title

    def test_lookup_is_case_insensitive(self, client, db, make_user, make_enrollment, outbox):
        e = self._issue(db, make_user, make_enrollment)
        r = client.post("/api/certificate/verify", json={"certificateId": e.certificate_id.lower()})
        assert r.json()["success"] is True

    def test_unknown_id_is_reported_not_found(self, client):
        r = client.post("/api/certificate/verify", json={"certificateId": "NI-0000-NOPE"})
        assert r.json()["success"] is False

    def test_empty_id_is_a_validation_error(self, client):
        assert client.post("/api/certificate/verify", json={"certificateId": ""}).status_code == 422

    def test_locked_certificate_is_not_publicly_verifiable(self, client, make_user, make_enrollment):
        """Only issued certificates exist as public records; a paid-but-not-due one must not."""
        e = _paid(make_enrollment, make_user(), days_ago=3)
        r = client.post("/api/certificate/verify", json={"certificateId": f"NI-{datetime.now().year}-{e.id[:8].upper()}"})
        assert r.json()["success"] is False


# --------------------------------------------------------------------------
# Stage shown on the student dashboard
# --------------------------------------------------------------------------


class TestStage:
    def test_progression(self, db, make_user, make_enrollment, outbox):
        e = make_enrollment(make_user(), days_ago=40)
        assert enrollment_to_dict(e)["stage"] == "task"

        e.task_submitted_at = naive_utc_now()
        assert enrollment_to_dict(e)["stage"] == "payment"

        e.payment_status = "paid"
        assert enrollment_to_dict(e)["stage"] == "waiting"

        db.commit()
        process_due_certificates(db)
        assert enrollment_to_dict(_fresh(db, e))["stage"] == "certificate"
