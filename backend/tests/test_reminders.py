"""Reminder emails for students who stall before paying."""

from datetime import datetime, timedelta, timezone

import pytest

from app.db.models import Enrollment
from app.services import reminder_service
from app.services.reminder_service import (
    MAX_REMINDERS,
    build_reminder,
    is_reminder_due,
    send_due_reminders,
)
from tests.conftest import naive_utc_now


@pytest.fixture
def mailbox(monkeypatch):
    sent = []
    monkeypatch.setattr(reminder_service, "send_email", lambda to, subject, body: sent.append((to, subject, body)))
    return sent


def _fresh(db, e) -> Enrollment:
    db.expire_all()
    return db.get(Enrollment, e.id)


def _submitted(days_ago: float):
    return naive_utc_now() - timedelta(days=days_ago)


# --------------------------------------------------------------------------
# When is a reminder due?
# --------------------------------------------------------------------------


class TestDueRules:
    def test_task_stage_first_reminder_after_two_days(self, make_user, make_enrollment):
        now = naive_utc_now()
        assert not is_reminder_due(make_enrollment(make_user(), days_ago=1.9), now)
        assert is_reminder_due(make_enrollment(make_user(), days_ago=2.1), now)

    def test_payment_stage_first_reminder_one_day_after_task(self, make_user, make_enrollment):
        now = naive_utc_now()
        early = make_enrollment(make_user(), days_ago=10, task_submitted_at=_submitted(0.5))
        later = make_enrollment(make_user(), days_ago=10, task_submitted_at=_submitted(1.1))
        assert not is_reminder_due(early, now)
        assert is_reminder_due(later, now)

    @pytest.mark.parametrize("status", ["unpaid", "pending", "failed"])
    def test_every_unpaid_status_is_eligible(self, make_user, make_enrollment, status):
        e = make_enrollment(make_user(), days_ago=5, payment_status=status)
        assert is_reminder_due(e, naive_utc_now())

    def test_paid_students_are_never_reminded(self, make_user, make_enrollment):
        e = make_enrollment(make_user(), days_ago=5, payment_status="paid", task_submitted_at=_submitted(4))
        assert not is_reminder_due(e, naive_utc_now())

    def test_spacing_between_reminders(self, make_user, make_enrollment):
        now = naive_utc_now()
        recent = make_enrollment(make_user(), days_ago=10, reminder_count=1, last_reminder_at=now - timedelta(days=2.9))
        old = make_enrollment(make_user(), days_ago=10, reminder_count=1, last_reminder_at=now - timedelta(days=3.1))
        assert not is_reminder_due(recent, now)
        assert is_reminder_due(old, now)

    def test_hard_cap_on_reminders(self, make_user, make_enrollment):
        e = make_enrollment(
            make_user(), days_ago=20, reminder_count=MAX_REMINDERS, last_reminder_at=naive_utc_now() - timedelta(days=10)
        )
        assert not is_reminder_due(e, naive_utc_now())

    def test_stale_enrollments_are_left_alone(self, make_user, make_enrollment):
        e = make_enrollment(make_user(), days_ago=61, task_submitted_at=_submitted(60))
        assert not is_reminder_due(e, naive_utc_now())

    def test_no_task_nudges_after_the_course_has_ended(self, make_user, make_enrollment):
        e = make_enrollment(make_user(), days_ago=30)  # task never submitted, program over
        assert not is_reminder_due(e, naive_utc_now())

    def test_payment_nudges_continue_after_the_course_has_ended(self, make_user, make_enrollment):
        e = make_enrollment(make_user(), days_ago=30, task_submitted_at=_submitted(25))
        assert is_reminder_due(e, naive_utc_now())


# --------------------------------------------------------------------------
# Email content
# --------------------------------------------------------------------------


class TestContent:
    def test_task_stage_email(self, make_user, make_enrollment):
        e = make_enrollment(make_user(), days_ago=3)
        subject, body = build_reminder(e)
        assert "waiting" in subject and e.program_title in subject
        assert "GitHub and LinkedIn" in body
        assert "/dashboard" in body
        assert "ignore this email" in body

    def test_payment_stage_email_mentions_fee_and_certificate_timing(self, make_user, make_enrollment):
        e = make_enrollment(make_user(), days_ago=3, task_submitted_at=_submitted(2))
        subject, body = build_reminder(e)
        assert "certificate" in subject.lower()
        assert "₹150" in body
        assert (e.enrolled_at + timedelta(days=28)).strftime("%B %d, %Y") in body

    def test_link_uses_configured_frontend_url(self, monkeypatch, make_user, make_enrollment):
        monkeypatch.setattr("app.core.config.settings.frontend_url", "https://staging.example.com/")
        _, body = build_reminder(make_enrollment(make_user(), days_ago=3))
        assert "https://staging.example.com/dashboard" in body


# --------------------------------------------------------------------------
# send_due_reminders
# --------------------------------------------------------------------------


class TestSending:
    def test_sends_to_due_students_and_records_it(self, db, mailbox, make_user, make_enrollment):
        user = make_user()
        e = make_enrollment(user, days_ago=3)
        sent_ids = send_due_reminders(db)
        assert sent_ids == [e.id]
        assert [m[0] for m in mailbox] == [user.email]
        fresh = _fresh(db, e)
        assert fresh.reminder_count == 1
        assert fresh.last_reminder_at is not None

    def test_not_resent_on_the_next_run(self, db, mailbox, make_user, make_enrollment):
        make_enrollment(make_user(), days_ago=3)
        send_due_reminders(db)
        assert send_due_reminders(db) == []
        assert len(mailbox) == 1

    def test_second_reminder_after_spacing_and_cap_after_third(self, db, mailbox, make_user, make_enrollment):
        e = make_enrollment(make_user(), days_ago=3)
        start = naive_utc_now()
        for day, expected in [(0, 1), (1, 0), (3.5, 1), (7, 1), (11, 0), (30, 0)]:
            sent = send_due_reminders(db, now=start + timedelta(days=day))
            assert len(sent) == expected, f"day {day}"
        assert _fresh(db, e).reminder_count == MAX_REMINDERS
        assert len(mailbox) == 3

    def test_skips_paid_and_not_yet_due(self, db, mailbox, make_user, make_enrollment):
        make_enrollment(make_user(), days_ago=5, payment_status="paid")
        make_enrollment(make_user(), days_ago=1)
        assert send_due_reminders(db) == []
        assert mailbox == []

    def test_mixed_batch_picks_the_right_students(self, db, mailbox, make_user, make_enrollment):
        stalled_task = make_enrollment(make_user(), days_ago=4)
        stalled_pay = make_enrollment(make_user(), days_ago=8, task_submitted_at=_submitted(3), payment_status="pending")
        make_enrollment(make_user(), days_ago=8, payment_status="paid")
        make_enrollment(make_user(), days_ago=1)
        assert set(send_due_reminders(db)) == {stalled_task.id, stalled_pay.id}

    def test_dry_run_reports_without_sending_or_recording(self, db, mailbox, make_user, make_enrollment):
        e = make_enrollment(make_user(), days_ago=3)
        assert send_due_reminders(db, dry_run=True) == [e.id]
        assert mailbox == []
        assert _fresh(db, e).reminder_count == 0

    def test_failed_send_is_released_and_retried(self, db, monkeypatch, mailbox, make_user, make_enrollment):
        e = make_enrollment(make_user(), days_ago=3)

        def smtp_down(**kwargs):
            raise RuntimeError("smtp down")

        monkeypatch.setattr(reminder_service, "send_email", smtp_down)
        assert send_due_reminders(db) == []
        fresh = _fresh(db, e)
        assert fresh.reminder_count == 0 and fresh.last_reminder_at is None

        monkeypatch.setattr(reminder_service, "send_email", lambda to, subject, body: mailbox.append(to))
        assert send_due_reminders(db) == [e.id]

    def test_one_failure_does_not_block_the_rest(self, db, monkeypatch, make_user, make_enrollment):
        bad = make_enrollment(make_user(email="bad@example.com"), days_ago=3)
        good = make_enrollment(make_user(email="good@example.com"), days_ago=3)
        delivered = []

        def flaky(to, subject, body):
            if to == "bad@example.com":
                raise RuntimeError("rejected")
            delivered.append(to)

        monkeypatch.setattr(reminder_service, "send_email", flaky)
        assert send_due_reminders(db) == [good.id]
        assert delivered == ["good@example.com"]
        assert _fresh(db, bad).reminder_count == 0

    def test_cannot_double_send_when_another_worker_claimed_first(self, db, mailbox, make_user, make_enrollment):
        """Simulates the scheduler and an admin trigger racing: the row changed under us."""
        from app.db.base import SessionLocal

        e = make_enrollment(make_user(), days_ago=3)
        assert e.reminder_count == 0  # this session believes nobody has been emailed yet

        other = SessionLocal()
        try:
            row = other.get(Enrollment, e.id)
            row.reminder_count, row.last_reminder_at = 1, naive_utc_now()
            other.commit()
        finally:
            other.close()

        assert reminder_service._claim(db, e, naive_utc_now()) is False
        assert mailbox == []

    def test_student_who_pays_between_selection_and_send_is_not_emailed(self, db, mailbox, make_user, make_enrollment):
        e = make_enrollment(make_user(), days_ago=3)
        stale_view = db.get(Enrollment, e.id)
        from app.db.base import SessionLocal

        other = SessionLocal()
        try:
            other.get(Enrollment, e.id).payment_status = "paid"
            other.commit()
        finally:
            other.close()
        assert reminder_service._claim(db, stale_view, naive_utc_now()) is False


# --------------------------------------------------------------------------
# Admin trigger
# --------------------------------------------------------------------------


class TestAdminEndpoint:
    def test_dry_run_counts_without_sending(self, client, db, mailbox, make_user, make_enrollment, auth):
        make_enrollment(make_user(), days_ago=3)
        r = client.post("/api/admin/reminders/send?dryRun=true", headers=auth(make_user(role="admin")))
        assert r.status_code == 200
        assert r.json()["data"] == {"count": 1, "dryRun": True}
        assert mailbox == []

    def test_real_run_sends(self, client, mailbox, make_user, make_enrollment, auth):
        make_enrollment(make_user(), days_ago=3)
        r = client.post("/api/admin/reminders/send", headers=auth(make_user(role="admin")))
        assert r.json()["data"] == {"count": 1, "dryRun": False}
        assert len(mailbox) == 1

    def test_students_are_forbidden(self, client, make_user, auth):
        assert client.post("/api/admin/reminders/send", headers=auth(make_user())).status_code == 403

    def test_anonymous_is_unauthorized(self, client):
        assert client.post("/api/admin/reminders/send").status_code == 401


# --------------------------------------------------------------------------
# Scheduler job honours the feature flag
# --------------------------------------------------------------------------


class TestSchedulerJob:
    def test_disabled_by_default(self, monkeypatch, mailbox, make_user, make_enrollment):
        from app.core.config import Settings
        from app.main import _run_reminder_check

        assert Settings(_env_file=None).reminders_enabled is False
        make_enrollment(make_user(), days_ago=3)
        monkeypatch.setattr("app.main.settings.reminders_enabled", False)
        _run_reminder_check()
        assert mailbox == []

    def test_runs_when_enabled(self, monkeypatch, mailbox, make_user, make_enrollment):
        from app.main import _run_reminder_check

        make_enrollment(make_user(), days_ago=3)
        monkeypatch.setattr("app.main.settings.reminders_enabled", True)
        _run_reminder_check()
        assert len(mailbox) == 1
