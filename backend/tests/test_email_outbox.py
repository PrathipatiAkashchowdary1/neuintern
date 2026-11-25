"""Durable email: saved with the triggering change, sent now, retried if that fails."""

import threading
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

import app.main as main_module
from app.db.base import SessionLocal
from app.db.models import EmailOutbox, Enrollment
from app.services import outbox_service
from app.services.certificate_service import process_due_certificates
from app.services.outbox_service import BACKOFF, CLAIM_TTL, FIRST_DELAY, KEEP_SENT_FOR, MAX_ATTEMPTS
from tests.conftest import post_webhook, webhook_event

START = datetime(2026, 6, 1, 12, 0, 0)


@pytest.fixture
def smtp(monkeypatch):
    """A mail server we can switch off. Records every message that goes out."""
    state = SimpleNamespace(down=False, sent=[], delay=0.0)

    def attach(to, subject, body, attachments):
        if state.delay:
            time.sleep(state.delay)
        if state.down:
            raise ConnectionError("smtp down")
        state.sent.append(SimpleNamespace(to=to, subject=subject, attachments=attachments))

    def plain(to, subject, body, headers=None):
        if state.delay:
            time.sleep(state.delay)
        if state.down:
            raise ConnectionError("smtp down")
        state.sent.append(SimpleNamespace(to=to, subject=subject, attachments=[]))

    for target in (
        "app.services.payment_service.send_email_with_attachments",
        "app.services.certificate_service.send_email_with_attachments",
        "app.services.offer_letter_email.send_email_with_attachments",
    ):
        monkeypatch.setattr(target, attach)
    monkeypatch.setattr("app.services.email_service.send_email", plain)
    return state


@pytest.fixture
def clock(monkeypatch):
    """Controls the outbox's notion of 'now'."""
    c = SimpleNamespace(now=START)
    monkeypatch.setattr(outbox_service, "_now", lambda: c.now)
    return c


def rows(db, **filters):
    db.expire_all()
    q = db.query(EmailOutbox)
    for k, v in filters.items():
        q = q.filter(getattr(EmailOutbox, k) == v)
    return q.order_by(EmailOutbox.created_at, EmailOutbox.id).all()


def queue(db, kind="contact", to="a@example.com", **over):
    payload = over.pop("payload", {"to": to, "subject": "Hi", "body": "Body"})
    row = outbox_service.add(db, kind, to=to, subject="Hi", payload=payload, **over)
    db.commit()
    return row.id


def pay_pending(make_user, make_enrollment, order="order_1", **over):
    return make_enrollment(
        make_user(),
        task_submitted_at=datetime.now(timezone.utc),
        razorpay_order_id=order,
        payment_status="pending",
        **over,
    )


# --------------------------------------------------------------------------
# Saved with the thing that triggers it, then sent
# --------------------------------------------------------------------------


class TestEnrollOfferLetter:
    def test_a_failed_enrollment_queues_nothing(self, client, db, smtp, make_user, auth):
        r = client.post("/api/enrollments", json={"programSlug": "no-such-program"}, headers=auth(make_user()))
        assert r.status_code == 404
        assert rows(db) == [] and smtp.sent == []

    def test_enrolling_sends_one_offer_letter_and_records_it(self, client, db, smtp, make_user, auth):
        from app.db.models import Program

        db.add(Program(slug="p1", title="Prog One", category="c", tagline="t", image="i", price=150))
        db.commit()
        user = make_user()
        r = client.post("/api/enrollments", json={"programSlug": "p1"}, headers=auth(user))
        assert r.status_code == 201
        assert [m.to for m in smtp.sent] == [user.email]
        (row,) = rows(db)
        assert row.kind == "offer_letter" and row.status == "sent" and row.payload is None  # nothing left lying around
        assert row.sent_at is not None

    def test_an_smtp_outage_does_not_fail_enrolling_and_the_email_waits(self, client, db, smtp, make_user, auth, clock):
        from app.db.models import Program

        db.add(Program(slug="p1", title="Prog One", category="c", tagline="t", image="i", price=150))
        db.commit()
        smtp.down = True
        r = client.post("/api/enrollments", json={"programSlug": "p1"}, headers=auth(make_user()))
        assert r.status_code == 201
        (row,) = rows(db)
        assert row.status == "pending" and row.attempts == 1
        assert "smtp down" in row.last_error
        assert row.payload is not None  # kept so it can be retried
        assert row.next_attempt_at == START + BACKOFF[0]

    def test_re_enrolling_does_not_queue_a_second_letter(self, client, db, smtp, make_user, auth):
        from app.db.models import Program

        db.add(Program(slug="p1", title="Prog One", category="c", tagline="t", image="i", price=150))
        db.commit()
        h = auth(make_user())
        client.post("/api/enrollments", json={"programSlug": "p1"}, headers=h)
        client.post("/api/enrollments", json={"programSlug": "p1"}, headers=h)
        assert len(rows(db)) == 1 and len(smtp.sent) == 1


class TestAtomicity:
    def test_the_email_row_is_saved_or_discarded_with_the_caller_transaction(self, db):
        outbox_service.add(db, "contact", to="a@example.com", subject="s", payload={"to": "a", "subject": "s", "body": "b"})
        db.rollback()  # e.g. the payment failed to commit
        assert rows(db) == []

    def test_the_same_dedupe_key_returns_the_existing_row(self, db):
        first = queue(db, dedupe_key="invoice:123")
        again = queue(db, dedupe_key="invoice:123")
        assert first == again and len(rows(db)) == 1

    def test_emails_without_a_dedupe_key_are_independent(self, db):
        queue(db)
        queue(db)
        assert len(rows(db)) == 2


class TestPayments:
    def test_invoice_is_sent_once_when_all_is_well(self, client, db, smtp, make_user, make_enrollment):
        pay_pending(make_user, make_enrollment)
        post_webhook(client, webhook_event("order_1", "pay_1"))
        assert len(smtp.sent) == 1
        (row,) = rows(db, kind="invoice")
        assert row.status == "sent"

    def test_payment_survives_an_smtp_outage_and_the_invoice_still_arrives_later(
        self, client, db, smtp, make_user, make_enrollment, clock
    ):
        e = pay_pending(make_user, make_enrollment)
        smtp.down = True
        post_webhook(client, webhook_event("order_1", "pay_1"))
        db.expire_all()
        assert db.get(Enrollment, e.id).payment_status == "paid"  # the money side is unaffected
        (row,) = rows(db, kind="invoice")
        assert row.status == "pending" and smtp.sent == []

        # The outage ends; "a restart" has nothing in memory, only the database.
        smtp.down = False
        clock.now = START + timedelta(minutes=2)
        assert outbox_service.process_due() == 1
        assert len(smtp.sent) == 1 and smtp.sent[0].to == e.email
        assert rows(db, kind="invoice")[0].status == "sent"

    def test_a_duplicate_payment_notification_queues_no_second_invoice(self, client, db, smtp, make_user, make_enrollment):
        pay_pending(make_user, make_enrollment)
        for _ in range(3):
            post_webhook(client, webhook_event("order_1", "pay_1"))
        assert len(rows(db, kind="invoice")) == 1 and len(smtp.sent) == 1

    def test_paying_after_the_course_ends_queues_invoice_and_certificate(self, client, db, smtp, make_user, make_enrollment):
        pay_pending(make_user, make_enrollment, days_ago=40)
        post_webhook(client, webhook_event("order_1", "pay_1"))
        assert sorted(r.kind for r in rows(db)) == ["certificate", "invoice"]
        assert len(smtp.sent) == 2 and all(r.status == "sent" for r in rows(db))


class TestCertificates:
    def test_a_certificate_is_never_unlocked_without_its_email_being_queued(self, db, smtp, make_user, make_enrollment):
        smtp.down = True  # the worst moment: SMTP is down when the scheduler unlocks it
        e = make_enrollment(
            make_user(), days_ago=40, payment_status="paid", paid_at=datetime.now(timezone.utc),
            razorpay_order_id="o", razorpay_payment_id="p",
        )
        assert process_due_certificates(db) == 1
        db.expire_all()
        assert db.get(Enrollment, e.id).certificate_unlocked is True
        (row,) = rows(db, kind="certificate")
        assert row.status == "pending" and smtp.sent == []  # unlocked AND queued: not lost

    def test_the_queued_certificate_is_delivered_once_smtp_returns(self, db, smtp, make_user, make_enrollment, clock):
        smtp.down = True
        make_enrollment(
            make_user(), days_ago=40, payment_status="paid", paid_at=datetime.now(timezone.utc),
            razorpay_order_id="o", razorpay_payment_id="p",
        )
        process_due_certificates(db)
        smtp.down = False
        clock.now = START + timedelta(minutes=2)
        outbox_service.process_due()
        assert len(smtp.sent) == 1 and smtp.sent[0].attachments[0][0].startswith("NeuIntern-Certificate-")

    def test_the_scheduler_does_not_email_a_certificate_twice(self, db, smtp, make_user, make_enrollment):
        make_enrollment(
            make_user(), days_ago=40, payment_status="paid", paid_at=datetime.now(timezone.utc),
            razorpay_order_id="o", razorpay_payment_id="p",
        )
        process_due_certificates(db)
        process_due_certificates(db)
        outbox_service.process_due()
        assert len(smtp.sent) == 1


class TestContactForm:
    BODY = {"name": "Zed Visitor", "email": "z@example.com", "subject": "Hello there", "message": "A message long enough"}

    def test_both_emails_are_queued_and_sent(self, client, db, smtp):
        r = client.post("/api/contact", json=self.BODY)
        assert r.status_code == 201
        assert len(rows(db, kind="contact")) == 2 and all(x.status == "sent" for x in rows(db))
        assert sorted(m.to for m in smtp.sent) == sorted([outbox_service_notify_address(), "z@example.com"])

    def test_the_message_is_kept_and_the_emails_retried_after_an_outage(self, client, db, smtp, clock):
        smtp.down = True
        assert client.post("/api/contact", json=self.BODY).status_code == 201
        assert [r.status for r in rows(db)] == ["pending", "pending"]
        smtp.down = False
        clock.now = START + timedelta(minutes=2)
        assert outbox_service.process_due() == 2
        assert len(smtp.sent) == 2


def outbox_service_notify_address() -> str:
    from app.core.config import settings

    return settings.contact_notify_email


# --------------------------------------------------------------------------
# Retries and backoff
# --------------------------------------------------------------------------


class TestRetries:
    def test_failures_back_off_then_give_up(self, db, smtp, clock):
        smtp.down = True
        email_id = queue(db)
        waits = []
        for attempt in range(1, MAX_ATTEMPTS + 1):
            clock.now += timedelta(days=1)  # always due
            outbox_service.deliver(email_id)
            row = rows(db)[0]
            assert row.attempts == attempt
            if attempt < MAX_ATTEMPTS:
                assert row.status == "pending"
                waits.append(row.next_attempt_at - clock.now)
        assert waits == BACKOFF[: MAX_ATTEMPTS - 1] and len(waits) == 5
        assert row.status == "failed" and "smtp down" in row.last_error

    def test_a_failed_email_is_not_retried_automatically(self, db, smtp, clock):
        smtp.down = True
        email_id = queue(db)
        for _ in range(MAX_ATTEMPTS):
            clock.now += timedelta(days=1)
            outbox_service.deliver(email_id)
        smtp.down = False
        clock.now += timedelta(days=30)
        assert outbox_service.process_due() == 0
        assert smtp.sent == []

    def test_success_marks_it_sent_and_clears_the_payload(self, db, smtp):
        email_id = queue(db)
        assert outbox_service.deliver(email_id) is True
        (row,) = rows(db)
        assert (row.status, row.payload, row.last_error, row.locked_until) == ("sent", None, None, None)
        assert row.sent_at is not None

    def test_a_recovered_email_clears_its_old_error(self, db, smtp, clock):
        email_id = queue(db)
        smtp.down = True
        outbox_service.deliver(email_id)
        smtp.down = False
        clock.now += timedelta(minutes=2)
        outbox_service.deliver(email_id)
        (row,) = rows(db)
        assert row.status == "sent" and row.last_error is None and row.attempts == 2

    def test_a_sent_email_is_never_sent_again(self, db, smtp):
        email_id = queue(db)
        outbox_service.deliver(email_id)
        assert outbox_service.deliver(email_id) is False
        assert len(smtp.sent) == 1

    def test_retry_refuses_an_already_sent_email(self, db, smtp):
        """Guarded in the service itself, not only by the admin API in front of it."""
        email_id = queue(db)
        outbox_service.deliver(email_id)
        assert outbox_service.retry(db, email_id) is None
        assert rows(db)[0].status == "sent"

    def test_unknown_kinds_and_broken_payloads_fail_cleanly(self, db, smtp, clock):
        bad_kind = queue(db, kind="mystery", payload={})
        outbox_service.deliver(bad_kind)
        row = rows(db)[0]
        assert row.status == "pending" and "Unknown email kind" in row.last_error

    def test_one_failing_email_does_not_block_the_others(self, db, smtp, clock):
        bad = queue(db, kind="mystery", payload={})
        good = queue(db)
        clock.now = START + timedelta(minutes=5)
        outbox_service.process_due()
        by_id = {r.id: r for r in rows(db)}
        assert by_id[bad].status == "pending" and by_id[good].status == "sent"


class TestScheduling:
    def test_a_new_email_can_go_immediately_but_the_retry_job_waits(self, db, smtp, clock):
        email_id = queue(db)
        assert rows(db)[0].next_attempt_at == START + FIRST_DELAY
        assert outbox_service.process_due() == 0  # the retry job leaves fresh mail to the immediate send
        assert outbox_service.deliver(email_id) is True  # ...which is allowed to go straight away

    def test_the_retry_job_picks_up_mail_the_immediate_send_never_got_to(self, db, smtp, clock):
        """The process died after saving the row and before sending it."""
        queue(db)
        clock.now = START + FIRST_DELAY + timedelta(seconds=1)
        assert outbox_service.process_due() == 1
        assert len(smtp.sent) == 1

    def test_not_yet_due_retries_are_skipped(self, db, smtp, clock):
        email_id = queue(db)
        smtp.down = True
        outbox_service.deliver(email_id)
        smtp.down = False
        clock.now = START + BACKOFF[0] - timedelta(seconds=1)
        assert outbox_service.process_due() == 0

    def test_a_crashed_sender_is_retried_after_its_claim_expires(self, db, smtp, clock):
        email_id = queue(db)
        # A worker claims it and dies mid-send: attempts=1, locked, never marked sent.
        db.query(EmailOutbox).filter(EmailOutbox.id == email_id).update(
            {"attempts": 1, "locked_until": START + CLAIM_TTL, "next_attempt_at": START}
        )
        db.commit()
        clock.now = START + CLAIM_TTL - timedelta(seconds=5)
        assert outbox_service.process_due() == 0
        clock.now = START + CLAIM_TTL + timedelta(seconds=5)
        assert outbox_service.process_due() == 1
        assert len(smtp.sent) == 1

    def test_only_one_sender_wins_when_two_try_at_once(self, db, smtp):
        smtp.delay = 0.3  # keeps the first sender busy long enough for the race to matter
        email_id = queue(db)
        barrier = threading.Barrier(4)

        def worker():
            barrier.wait()
            outbox_service.deliver(email_id)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        assert len(smtp.sent) == 1

    def test_old_sent_rows_are_deleted_but_waiting_and_failed_ones_never_are(self, db, smtp, clock):
        old = queue(db)
        keep_recent = queue(db)
        waiting = queue(db)
        failed = queue(db)
        outbox_service.deliver(old)
        outbox_service.deliver(keep_recent)
        db.query(EmailOutbox).filter(EmailOutbox.id == old).update({"sent_at": START - KEEP_SENT_FOR - timedelta(days=1)})
        db.query(EmailOutbox).filter(EmailOutbox.id == failed).update({"status": "failed", "created_at": START - timedelta(days=400)})
        db.commit()
        outbox_service.process_due()
        ids = {r.id for r in rows(db)}
        assert old not in ids and {keep_recent, waiting, failed} <= ids

    def test_the_scheduled_job_runs_once_however_many_workers_tick(self, monkeypatch):
        calls = []
        monkeypatch.setattr(main_module, "process_outbox", lambda: calls.append(1))
        for _ in range(3):
            main_module._scheduled_outbox_check()
        assert calls == [1]


# --------------------------------------------------------------------------
# Admin view and retry
# --------------------------------------------------------------------------


class TestAdminApi:
    @pytest.fixture
    def admin(self, make_user, auth):
        return auth(make_user(role="admin"))

    def _failed(self, db, smtp, clock):
        email_id = queue(db, to="stuck@example.com")
        smtp.down = True
        for _ in range(MAX_ATTEMPTS):
            clock.now += timedelta(days=1)
            outbox_service.deliver(email_id)
        smtp.down = False
        return email_id

    def test_lists_counts_and_messages_without_their_content(self, client, db, smtp, clock, admin):
        sent = queue(db)
        outbox_service.deliver(sent)
        self._failed(db, smtp, clock)
        queue(db, to="waiting@example.com")
        data = client.get("/api/admin/emails", headers=admin).json()["data"]
        assert data["counts"] == {"pending": 1, "sent": 1, "failed": 1}
        assert {i["status"] for i in data["items"]} == {"pending", "sent", "failed"}
        assert all("payload" not in i and "body" not in i for i in data["items"])
        failed = next(i for i in data["items"] if i["status"] == "failed")
        assert failed["to"] == "stuck@example.com" and failed["attempts"] == MAX_ATTEMPTS and "smtp down" in failed["lastError"]

    def test_can_filter_by_status(self, client, db, smtp, clock, admin):
        self._failed(db, smtp, clock)
        queue(db)
        items = client.get("/api/admin/emails?status=failed", headers=admin).json()["data"]["items"]
        assert [i["status"] for i in items] == ["failed"]

    def test_invalid_status_is_rejected(self, client, admin):
        assert client.get("/api/admin/emails?status=bogus", headers=admin).status_code == 422

    def test_retrying_a_failed_email_sends_it(self, client, db, smtp, clock, admin):
        email_id = self._failed(db, smtp, clock)
        r = client.post(f"/api/admin/emails/{email_id}/retry", headers=admin)
        assert r.status_code == 200
        assert len(smtp.sent) == 1 and smtp.sent[0].to == "stuck@example.com"
        assert rows(db)[0].status == "sent"

    def test_a_retry_that_fails_again_starts_a_fresh_cycle(self, client, db, smtp, clock, admin):
        email_id = self._failed(db, smtp, clock)
        smtp.down = True
        client.post(f"/api/admin/emails/{email_id}/retry", headers=admin)
        row = rows(db)[0]
        assert row.status == "pending" and row.attempts == 1  # a full set of attempts again, not instantly dead

    def test_a_sent_email_cannot_be_retried(self, client, db, smtp, admin):
        email_id = queue(db)
        outbox_service.deliver(email_id)
        assert client.post(f"/api/admin/emails/{email_id}/retry", headers=admin).status_code == 400
        assert len(smtp.sent) == 1

    def test_unknown_email_is_404(self, client, admin):
        assert client.post("/api/admin/emails/nope/retry", headers=admin).status_code == 404

    def test_students_cannot_see_or_retry(self, client, db, make_user, auth):
        h = auth(make_user())
        email_id = queue(db)
        assert client.get("/api/admin/emails", headers=h).status_code == 403
        assert client.post(f"/api/admin/emails/{email_id}/retry", headers=h).status_code == 403

    def test_anonymous_is_unauthorized(self, client):
        assert client.get("/api/admin/emails").status_code == 401
