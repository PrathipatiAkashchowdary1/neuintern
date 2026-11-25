"""Scheduled jobs run once across workers; certificate unlock is atomic."""

import threading
import time
from datetime import datetime, timedelta, timezone

import pytest

import app.main as main_module
from app.core.config import settings
from app.db.base import SessionLocal
from app.db.models import Certificate, Enrollment, JobLock
from app.services import job_lock, payment_service
from app.services.certificate_service import (
    process_due_certificates,
    unlock_and_email_certificate,
    unlock_certificate,
)
from app.services.job_lock import release, run_exclusive, try_acquire

HOUR = timedelta(hours=1)
TTL = timedelta(minutes=30)


def _paid(make_enrollment, make_user, days_ago=40, **over):
    return make_enrollment(
        make_user(),
        days_ago=days_ago,
        payment_status="paid",
        paid_at=datetime.now(timezone.utc),
        razorpay_order_id="o",
        razorpay_payment_id="p",
        **over,
    )


def _fresh(db, e) -> Enrollment:
    db.expire_all()
    return db.get(Enrollment, e.id)


def _clock(monkeypatch, when: datetime):
    monkeypatch.setattr(job_lock, "_now", lambda: when)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# --------------------------------------------------------------------------
# The lock itself
# --------------------------------------------------------------------------


class TestTryAcquire:
    def test_first_caller_wins_and_a_second_is_refused(self, db):
        assert try_acquire(db, "job", min_interval=timedelta(0), ttl=TTL) is True
        assert try_acquire(db, "job", min_interval=timedelta(0), ttl=TTL) is False  # still held

    def test_a_different_session_is_refused_too(self, db):
        other = SessionLocal()
        try:
            assert try_acquire(db, "job", min_interval=timedelta(0), ttl=TTL) is True
            assert try_acquire(other, "job", min_interval=timedelta(0), ttl=TTL) is False
        finally:
            other.close()

    def test_released_lock_can_be_taken_again(self, db):
        try_acquire(db, "job", min_interval=timedelta(0), ttl=TTL)
        release(db, "job")
        assert try_acquire(db, "job", min_interval=timedelta(0), ttl=TTL) is True

    def test_min_interval_blocks_a_second_worker_firing_the_same_tick(self, db, monkeypatch):
        start = _now()
        _clock(monkeypatch, start)
        assert try_acquire(db, "job", min_interval=HOUR, ttl=TTL) is True
        release(db, "job")
        _clock(monkeypatch, start + timedelta(minutes=5))  # a slower worker's tick for the same hour
        assert try_acquire(db, "job", min_interval=HOUR, ttl=TTL) is False
        _clock(monkeypatch, start + HOUR + timedelta(seconds=1))  # the next real tick
        assert try_acquire(db, "job", min_interval=HOUR, ttl=TTL) is True

    def test_a_crashed_holder_does_not_block_forever(self, db, monkeypatch):
        start = _now()
        _clock(monkeypatch, start)
        assert try_acquire(db, "job", min_interval=timedelta(0), ttl=TTL) is True  # holder dies: never releases
        _clock(monkeypatch, start + TTL - timedelta(seconds=5))
        assert try_acquire(db, "job", min_interval=timedelta(0), ttl=TTL) is False
        _clock(monkeypatch, start + TTL + timedelta(seconds=5))
        assert try_acquire(db, "job", min_interval=timedelta(0), ttl=TTL) is True

    def test_jobs_have_independent_locks(self, db):
        assert try_acquire(db, "a", min_interval=timedelta(0), ttl=TTL) is True
        assert try_acquire(db, "b", min_interval=timedelta(0), ttl=TTL) is True

    def test_losing_the_row_creation_race_is_harmless(self, db, monkeypatch):
        """Two workers start together and both see no row; the second insert collides."""
        other = SessionLocal()
        try:
            other.add(JobLock(name="job"))
            other.commit()
        finally:
            other.close()
        monkeypatch.setattr(db, "get", lambda *a, **k: None)  # this worker saw "no row" a moment ago
        assert try_acquire(db, "job", min_interval=timedelta(0), ttl=TTL) is True


class TestRunExclusive:
    def test_runs_the_job_and_releases_the_lock(self, db):
        calls = []
        assert run_exclusive("job", lambda: calls.append(1), min_interval=timedelta(0)) is True
        assert calls == [1]
        db.expire_all()
        assert db.get(JobLock, "job").locked_until is None

    def test_does_not_run_while_another_worker_holds_it(self, db):
        try_acquire(db, "job", min_interval=timedelta(0), ttl=TTL)
        calls = []
        assert run_exclusive("job", lambda: calls.append(1), min_interval=timedelta(0)) is False
        assert calls == []

    def test_a_failing_job_is_swallowed_and_the_lock_is_released(self, db, caplog):
        def boom():
            raise RuntimeError("job exploded")

        assert run_exclusive("job", boom, min_interval=timedelta(0)) is True
        assert "job exploded" in caplog.text
        db.expire_all()
        assert db.get(JobLock, "job").locked_until is None
        assert run_exclusive("job", lambda: None, min_interval=timedelta(0)) is True  # not stuck

    def test_four_workers_firing_the_same_tick_run_the_job_once(self):
        calls = []
        results = [run_exclusive("job", lambda: calls.append(1), min_interval=HOUR) for _ in range(4)]
        assert results == [True, False, False, False]
        assert calls == [1]

    def test_truly_concurrent_workers_run_the_job_once(self):
        calls, errors = [], []
        barrier = threading.Barrier(6)

        def worker():
            barrier.wait()
            try:
                run_exclusive("job", lambda: (calls.append(1), time.sleep(0.2)), min_interval=HOUR)
            except Exception as err:  # noqa: BLE001
                errors.append(err)

        threads = [threading.Thread(target=worker) for _ in range(6)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        assert errors == []
        assert calls == [1]


# --------------------------------------------------------------------------
# The scheduler's entry points
# --------------------------------------------------------------------------


class TestSchedulerEntryPoints:
    def test_certificates_are_processed_once_however_many_workers_tick(self, db, make_user, make_enrollment, outbox):
        e = _paid(make_enrollment, make_user)
        for _ in range(3):
            main_module._scheduled_certificate_check()
        assert _fresh(db, e).certificate_unlocked is True
        assert len(outbox) == 1

    def test_nothing_runs_while_another_worker_holds_the_lock(self, db, make_user, make_enrollment, outbox):
        e = _paid(make_enrollment, make_user)
        try_acquire(db, "certificate_check", min_interval=timedelta(0), ttl=TTL)  # another worker is mid-run
        main_module._scheduled_certificate_check()
        assert _fresh(db, e).certificate_unlocked is False
        assert outbox == []

    def test_reminders_run_once_per_day_across_workers(self, monkeypatch):
        calls = []
        monkeypatch.setattr(main_module, "_run_reminder_check", lambda: calls.append(1))
        for _ in range(3):
            main_module._scheduled_reminder_check()
        assert calls == [1]

    def test_the_certificate_job_does_not_block_the_reminder_job(self, db, monkeypatch):
        try_acquire(db, "certificate_check", min_interval=timedelta(0), ttl=TTL)
        calls = []
        monkeypatch.setattr(main_module, "_run_reminder_check", lambda: calls.append(1))
        main_module._scheduled_reminder_check()
        assert calls == [1]

    def test_the_scheduler_is_skipped_when_disabled(self, monkeypatch):
        events = []

        class FakeScheduler:
            running = False

            def add_job(self, *a, **k):
                events.append("add_job")

            def start(self):
                events.append("start")

        monkeypatch.setattr(main_module, "scheduler", FakeScheduler())
        monkeypatch.setattr(main_module, "run_exclusive", lambda *a, **k: events.append("run"))
        monkeypatch.setattr(settings, "scheduler_enabled", False)
        main_module.on_startup()
        assert events == []

    def test_the_scheduler_starts_when_enabled(self, monkeypatch):
        events = []

        class FakeScheduler:
            running = False

            def add_job(self, func, *a, id=None, **k):
                events.append(f"add_job:{id}")

            def start(self):
                events.append("start")

        monkeypatch.setattr(main_module, "scheduler", FakeScheduler())
        monkeypatch.setattr(main_module, "run_exclusive", lambda *a, **k: events.append("run"))
        monkeypatch.setattr(settings, "scheduler_enabled", True)
        main_module.on_startup()
        assert events == [
            "add_job:certificate_check",
            "add_job:reminder_check",
            "add_job:outbox_retry",
            "start",
            "run",  # certificate check
            "run",  # flush the email outbox left over from before the restart
        ]

    def test_shutdown_is_safe_when_the_scheduler_never_started(self):
        main_module.on_shutdown()  # must not raise SchedulerNotRunningError


# --------------------------------------------------------------------------
# Certificate unlock is atomic
# --------------------------------------------------------------------------


class TestAtomicUnlock:
    def test_only_the_first_unlock_gets_the_payload(self, db, make_user, make_enrollment):
        e = _paid(make_enrollment, make_user)
        first = unlock_certificate(db, e)
        second = unlock_certificate(db, e)
        assert first is not None and first["certificateId"].startswith("NI-")
        assert second is None
        assert db.query(Certificate).count() == 1

    def test_a_stale_copy_cannot_unlock_again(self, db, make_user, make_enrollment, outbox):
        """Models two workers: this session still believes the certificate is locked."""
        e = _paid(make_enrollment, make_user)
        assert e.certificate_unlocked is False

        other = SessionLocal()
        try:
            assert unlock_and_email_certificate(other, other.get(Enrollment, e.id)) is True
        finally:
            other.close()

        assert unlock_and_email_certificate(db, e) is False
        assert len(outbox) == 1  # one email, not two
        assert db.query(Certificate).count() == 1

    def test_two_scheduler_runs_in_a_row_email_once(self, db, make_user, make_enrollment, outbox):
        _paid(make_enrollment, make_user)
        assert process_due_certificates(db) == 1
        other = SessionLocal()
        try:
            assert process_due_certificates(other) == 0
        finally:
            other.close()
        assert len(outbox) == 1

    def test_only_paid_enrollments_can_be_unlocked(self, db, make_user, make_enrollment):
        e = make_enrollment(make_user(), days_ago=40, payment_status="pending")
        assert unlock_certificate(db, e) is None
        assert _fresh(db, e).certificate_unlocked is False
        assert db.query(Certificate).count() == 0

    def test_the_claim_and_the_public_record_succeed_or_fail_together(self, db, make_user, make_enrollment, monkeypatch):
        e = _paid(make_enrollment, make_user)

        def broken(*args, **kwargs):
            raise RuntimeError("disk full")

        monkeypatch.setattr(db, "add", broken)  # the public Certificate record cannot be written
        with pytest.raises(RuntimeError):
            unlock_certificate(db, e)
        db.rollback()
        assert _fresh(db, e).certificate_unlocked is False  # nothing half-done

    def test_payment_after_course_end_skips_the_email_if_someone_else_unlocked(
        self, db, monkeypatch, make_user, make_enrollment, outbox
    ):
        monkeypatch.setattr(payment_service, "unlock_certificate", lambda db_, e_: None)
        e = make_enrollment(
            make_user(), days_ago=40, payment_status="pending", razorpay_order_id="o1",
            task_submitted_at=datetime.now(timezone.utc),
        )
        assert payment_service.mark_enrollment_paid(db, e, "pay_1") is True
        assert [m.subject.split(" ")[0] for m in outbox] == ["Payment"]  # invoice only, no certificate

    def test_unlock_and_email_certificate_returns_true_when_it_did_the_work(self, db, make_user, make_enrollment, outbox):
        e = _paid(make_enrollment, make_user)
        assert unlock_and_email_certificate(db, e) is True
        assert len(outbox) == 1


# --------------------------------------------------------------------------
# Several workers starting at once must not crash on duplicate seed rows
# --------------------------------------------------------------------------


class _SeesNothing:
    """Stands in for a query that ran just before another worker inserted the rows."""

    def filter(self, *a, **k):
        return self

    def count(self):
        return 0

    def first(self):
        return None


class TestStartupSeedRace:
    def _race(self, db, monkeypatch, seed_fn):
        other = SessionLocal()
        try:
            seed_fn(other)  # the "other worker" wins the race and seeds first
        finally:
            other.close()
        monkeypatch.setattr(db, "query", lambda *a, **k: _SeesNothing())  # this worker saw an empty table
        seed_fn(db)  # must not raise
        monkeypatch.undo()

    def test_certificates_seed_tolerates_a_concurrent_worker(self, db, monkeypatch):
        from app.db.seed import seed_certificates

        self._race(db, monkeypatch, seed_certificates)
        assert db.query(Certificate).count() == 2  # no duplicates, no crash

    def test_programs_seed_tolerates_a_concurrent_worker(self, db, monkeypatch):
        from app.db.models import Program
        from app.db.seed import seed_programs

        self._race(db, monkeypatch, seed_programs)
        assert db.query(Program).count() == 16

    def test_admin_seed_tolerates_a_concurrent_worker(self, db, monkeypatch):
        from app.db.models import User
        from app.db.seed import seed_admin_user

        self._race(db, monkeypatch, seed_admin_user)
        assert db.query(User).filter(User.role == "admin").count() == 1

    def test_the_session_is_usable_after_losing_the_race(self, db, monkeypatch):
        from app.db.seed import seed_certificates

        self._race(db, monkeypatch, seed_certificates)
        assert db.query(Certificate).count() >= 1  # rolled back cleanly, not left in a failed transaction
