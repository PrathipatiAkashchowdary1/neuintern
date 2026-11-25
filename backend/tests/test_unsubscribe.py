"""Unsubscribe links in reminder emails."""

import pytest

from app.core.security import make_unsubscribe_token, verify_unsubscribe_token
from app.db.models import Enrollment, User
from app.services import reminder_service
from app.services.reminder_service import (
    build_reminder,
    send_due_reminders,
    unsubscribe_headers,
    unsubscribe_url,
)


@pytest.fixture
def mailbox(monkeypatch):
    sent = []

    def fake(to, subject, body, headers=None):
        sent.append({"to": to, "subject": subject, "body": body, "headers": headers or {}})

    monkeypatch.setattr(reminder_service, "send_email", fake)
    return sent


def _opted_out(db, user) -> bool:
    db.expire_all()
    return db.get(User, user.id).reminders_opt_out


# --------------------------------------------------------------------------
# Tokens
# --------------------------------------------------------------------------


class TestTokens:
    def test_round_trip(self):
        assert verify_unsubscribe_token(make_unsubscribe_token("abc123")) == "abc123"

    def test_tampered_user_id_is_rejected(self):
        token = make_unsubscribe_token("victim")
        _, _, mac = token.partition(".")
        assert verify_unsubscribe_token(f"attacker.{mac}") is None

    def test_tampered_mac_is_rejected(self):
        assert verify_unsubscribe_token("victim." + "A" * 43) is None

    @pytest.mark.parametrize("junk", ["", ".", "nodot", "a.", ".b"])
    def test_malformed_tokens_are_rejected(self, junk):
        assert verify_unsubscribe_token(junk) is None

    def test_token_from_another_secret_is_rejected(self, monkeypatch):
        token = make_unsubscribe_token("u1")
        monkeypatch.setattr("app.core.config.settings.jwt_secret", "a-different-secret")
        assert verify_unsubscribe_token(token) is None

    def test_does_not_expire_or_change(self):
        assert make_unsubscribe_token("u1") == make_unsubscribe_token("u1")


# --------------------------------------------------------------------------
# Endpoint
# --------------------------------------------------------------------------


class TestEndpoint:
    def test_post_opts_the_user_out_without_login(self, client, db, make_user):
        user = make_user()
        r = client.post(f"/api/unsubscribe/{make_unsubscribe_token(user.id)}")
        assert r.status_code == 200
        assert _opted_out(db, user) is True

    def test_is_idempotent(self, client, db, make_user):
        user = make_user()
        url = f"/api/unsubscribe/{make_unsubscribe_token(user.id)}"
        assert client.post(url).status_code == 200
        assert client.post(url).status_code == 200
        assert _opted_out(db, user) is True

    def test_one_click_post_from_mail_clients_works(self, client, db, make_user):
        """RFC 8058: the mail client POSTs a form body to the List-Unsubscribe URL."""
        user = make_user()
        r = client.post(
            f"/api/unsubscribe/{make_unsubscribe_token(user.id)}",
            data={"List-Unsubscribe": "One-Click"},
        )
        assert r.status_code == 200
        assert _opted_out(db, user) is True

    def test_get_does_not_unsubscribe(self, client, db, make_user):
        """Mail scanners prefetch links; a GET must never change anything."""
        user = make_user()
        r = client.get(f"/api/unsubscribe/{make_unsubscribe_token(user.id)}")
        assert r.status_code == 405
        assert _opted_out(db, user) is False

    def test_forged_token_is_rejected_and_changes_nothing(self, client, db, make_user):
        user = make_user()
        r = client.post(f"/api/unsubscribe/{user.id}.{'A' * 43}")
        assert r.status_code == 400
        assert _opted_out(db, user) is False

    def test_only_affects_the_token_owner(self, client, db, make_user):
        me, other = make_user(), make_user()
        client.post(f"/api/unsubscribe/{make_unsubscribe_token(me.id)}")
        assert _opted_out(db, me) is True
        assert _opted_out(db, other) is False

    def test_valid_token_for_a_deleted_user_is_a_harmless_success(self, client):
        assert client.post(f"/api/unsubscribe/{make_unsubscribe_token('no-such-user')}").status_code == 200

    def test_delete_undoes_it(self, client, db, make_user):
        user = make_user()
        url = f"/api/unsubscribe/{make_unsubscribe_token(user.id)}"
        client.post(url)
        assert client.delete(url).status_code == 200
        assert _opted_out(db, user) is False

    def test_delete_with_forged_token_is_rejected(self, client, db, make_user):
        user = make_user()
        client.post(f"/api/unsubscribe/{make_unsubscribe_token(user.id)}")
        assert client.delete(f"/api/unsubscribe/{user.id}.{'A' * 43}").status_code == 400
        assert _opted_out(db, user) is True


# --------------------------------------------------------------------------
# Reminders honour the opt-out
# --------------------------------------------------------------------------


class TestReminderBehaviour:
    def test_opted_out_student_is_not_emailed(self, db, mailbox, make_user, make_enrollment):
        user = make_user()
        make_enrollment(user, days_ago=5)
        user.reminders_opt_out = True
        db.commit()
        assert send_due_reminders(db) == []
        assert mailbox == []

    def test_opt_out_covers_all_of_the_students_enrollments(self, db, mailbox, make_user, make_enrollment):
        user = make_user()
        make_enrollment(user, days_ago=5)
        make_enrollment(user, days_ago=6, program_slug="data-science", program_title="Data Science")
        user.reminders_opt_out = True
        db.commit()
        assert send_due_reminders(db) == []

    def test_other_students_are_still_emailed(self, db, mailbox, make_user, make_enrollment):
        gone, stays = make_user(), make_user()
        make_enrollment(gone, days_ago=5)
        keep = make_enrollment(stays, days_ago=5)
        gone.reminders_opt_out = True
        db.commit()
        assert send_due_reminders(db) == [keep.id]

    def test_dry_run_excludes_opted_out(self, db, mailbox, make_user, make_enrollment):
        user = make_user()
        make_enrollment(user, days_ago=5)
        user.reminders_opt_out = True
        db.commit()
        assert send_due_reminders(db, dry_run=True) == []

    def test_unsubscribing_after_selection_but_before_send_still_wins(self, db, make_user, make_enrollment):
        """The claim re-checks opt-out, so a click that lands mid-run is honoured."""
        from app.db.base import SessionLocal
        from tests.conftest import naive_utc_now

        user = make_user()
        e = make_enrollment(user, days_ago=5)
        stale = db.get(Enrollment, e.id)

        other = SessionLocal()
        try:
            other.get(User, user.id).reminders_opt_out = True
            other.commit()
        finally:
            other.close()
        assert reminder_service._claim(db, stale, naive_utc_now()) is False

    def test_resubscribed_student_gets_reminders_again(self, client, db, mailbox, make_user, make_enrollment):
        user = make_user()
        e = make_enrollment(user, days_ago=5)
        url = f"/api/unsubscribe/{make_unsubscribe_token(user.id)}"
        client.post(url)
        assert send_due_reminders(db) == []
        client.delete(url)
        assert send_due_reminders(db) == [e.id]


# --------------------------------------------------------------------------
# What the email contains
# --------------------------------------------------------------------------


class TestEmailContent:
    def test_body_contains_a_working_unsubscribe_link(self, make_user, make_enrollment):
        user = make_user()
        e = make_enrollment(user, days_ago=5)
        _, body = build_reminder(e)
        url = unsubscribe_url(e)
        assert url in body
        token = url.split("token=")[1]
        assert verify_unsubscribe_token(token) == user.id

    def test_each_student_gets_their_own_link(self, make_user, make_enrollment):
        a = make_enrollment(make_user(), days_ago=5)
        b = make_enrollment(make_user(), days_ago=5)
        assert unsubscribe_url(a) != unsubscribe_url(b)

    def test_sent_email_carries_the_link(self, db, mailbox, make_user, make_enrollment):
        make_enrollment(make_user(), days_ago=5)
        send_due_reminders(db)
        assert "/unsubscribe?token=" in mailbox[0]["body"]

    def test_one_click_headers_present_when_api_url_configured(self, monkeypatch, db, mailbox, make_user, make_enrollment):
        monkeypatch.setattr("app.core.config.settings.api_public_url", "https://api.example.com/")
        e = make_enrollment(make_user(), days_ago=5)
        send_due_reminders(db)
        headers = mailbox[0]["headers"]
        token = unsubscribe_url(e).split("token=")[1]
        assert headers["List-Unsubscribe"] == f"<https://api.example.com/api/unsubscribe/{token}>"
        assert headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"

    def test_headers_omitted_without_api_url(self, monkeypatch, make_user, make_enrollment):
        monkeypatch.setattr("app.core.config.settings.api_public_url", "")
        assert unsubscribe_headers(make_enrollment(make_user(), days_ago=5)) == {}
