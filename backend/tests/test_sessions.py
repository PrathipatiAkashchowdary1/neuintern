"""Server-side sessions: logout really ends a login, a stolen token can be cancelled,
and users can see and remove their own devices."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token, hash_password
from app.db.models import EmailOtp, User, UserSession
from app.main import app
from app.services import session_service

PASSWORD = "CorrectHorse1!"
PW_HASH = hash_password(PASSWORD)
X = {"X-Requested-With": "neuintern"}  # what the website sends; required for cookie-authenticated writes

CHROME_WIN = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
SAFARI_IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture
def student(db, make_user):
    user = make_user(email="stu@example.com")
    user.password_hash = PW_HASH
    db.commit()
    return user


@pytest.fixture
def phone():
    """A second device: its own cookie jar."""
    return TestClient(app)


def login(client, email="stu@example.com", ua=CHROME_WIN):
    r = client.post("/api/auth/login", json={"email": email, "password": PASSWORD}, headers={"User-Agent": ua})
    assert r.status_code == 200, r.text
    return r.json()["data"]["token"]


def sessions(db, user_id=None):
    db.expire_all()
    q = db.query(UserSession)
    if user_id:
        q = q.filter(UserSession.user_id == user_id)
    return q.order_by(UserSession.created_at).all()


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def add_otp(db, email, purpose, code="123456"):
    db.add(
        EmailOtp(
            email=email, otp_hash=hash_password(code), purpose=purpose, expires_at=_now() + timedelta(minutes=10),
            verified=purpose == "register", verified_at=_now() if purpose == "register" else None,
        )
    )
    db.commit()


# --------------------------------------------------------------------------
# Creating sessions
# --------------------------------------------------------------------------


class TestCreation:
    def test_login_creates_a_session_and_the_token_carries_its_id(self, client, db, student):
        token = login(client)
        (row,) = sessions(db)
        assert decode_access_token(token)["jti"] == row.id
        assert row.user_id == student.id and row.revoked_at is None
        assert row.user_agent == CHROME_WIN and row.ip
        assert abs((row.expires_at - _now()) - timedelta(minutes=settings.jwt_expires_minutes)) < timedelta(minutes=1)

    def test_every_login_is_its_own_session(self, client, phone, db, student):
        login(client)
        login(phone, ua=SAFARI_IPHONE)
        assert len(sessions(db)) == 2

    def test_register_creates_a_session_too(self, client, db):
        add_otp(db, "new@example.com", "register")
        r = client.post(
            "/api/auth/register",
            json={"fullName": "New One", "email": "new@example.com", "phone": "9876543210", "degree": "B", "branch": "C", "currentYear": "3", "password": PASSWORD},
        )
        assert r.status_code == 201
        assert len(sessions(db)) == 1 and client.get("/api/auth/me").status_code == 200

    def test_a_user_keeps_at_most_20_active_sessions(self, db, student):
        for _ in range(23):
            session_service.create(db, student, user_agent="x", ip="1.1.1.1")
        active = session_service.list_active(db, student.id)
        assert len(active) == session_service.MAX_ACTIVE_SESSIONS == 20

    def test_the_oldest_sessions_are_the_ones_retired(self, db, student):
        first = session_service.create(db, student, user_agent="oldest", ip="")
        for _ in range(session_service.MAX_ACTIVE_SESSIONS):
            session_service.create(db, student, user_agent="newer", ip="")
        db.expire_all()
        assert db.get(UserSession, first.id).revoked_at is not None

    def test_long_dead_sessions_are_cleaned_up(self, db, student):
        old_id = session_service.create(db, student, user_agent="old", ip="").id
        db.query(UserSession).filter(UserSession.id == old_id).update(
            {"revoked_at": _now() - session_service.KEEP_DEAD_FOR - timedelta(days=1)}
        )
        db.commit()
        session_service.create(db, student, user_agent="new", ip="")
        db.expire_all()
        assert db.get(UserSession, old_id) is None

    def test_other_users_sessions_are_never_touched_by_the_cap(self, db, student, make_user):
        other = make_user(email="other@example.com")
        keep = session_service.create(db, other, user_agent="o", ip="")
        for _ in range(25):
            session_service.create(db, student, user_agent="s", ip="")
        db.expire_all()
        assert db.get(UserSession, keep.id).revoked_at is None


# --------------------------------------------------------------------------
# Logout really ends the login
# --------------------------------------------------------------------------


class TestLogout:
    def test_a_copied_token_is_dead_after_logout(self, client, student):
        """The scenario this feature exists for: the token was stolen, the user logs out."""
        stolen = login(client)
        assert client.get("/api/auth/me", headers=bearer(stolen)).status_code == 200
        assert client.post("/api/auth/logout").status_code == 200  # the real user logs out (cookie)
        assert client.get("/api/auth/me", headers=bearer(stolen)).status_code == 401  # the thief is out too

    def test_logout_marks_the_session_revoked(self, client, db, student):
        login(client)
        client.post("/api/auth/logout")
        (row,) = sessions(db)
        assert row.revoked_at is not None

    def test_logout_with_only_a_bearer_token_revokes_it(self, client, student):
        token = login(client)
        client.cookies.clear()
        assert client.post("/api/auth/logout", headers=bearer(token)).status_code == 200
        assert client.get("/api/auth/me", headers=bearer(token)).status_code == 401

    def test_logout_only_ends_this_device(self, client, phone, student):
        login(client)
        login(phone, ua=SAFARI_IPHONE)
        client.post("/api/auth/logout")
        assert client.get("/api/auth/me").status_code == 401
        assert phone.get("/api/auth/me").status_code == 200

    @pytest.mark.parametrize("auth_header", [None, "Bearer garbage", "Bearer a.b.c", "Basic abc"])
    def test_logout_never_fails_for_bad_or_missing_credentials(self, client, auth_header):
        headers = {"Authorization": auth_header} if auth_header else {}
        assert client.post("/api/auth/logout", headers=headers).status_code == 200

    def test_logging_out_twice_is_fine(self, client, student):
        login(client)
        assert client.post("/api/auth/logout").status_code == 200
        assert client.post("/api/auth/logout").status_code == 200

    def test_old_tokens_without_a_session_still_work_and_logout_does_not_crash(self, client, student, auth):
        legacy = auth(student)  # issued the old way: no jti
        assert client.get("/api/auth/me", headers=legacy).status_code == 200
        assert client.post("/api/auth/logout", headers=legacy).status_code == 200


# --------------------------------------------------------------------------
# Log out of every device
# --------------------------------------------------------------------------


class TestLogoutEverywhere:
    def test_every_device_is_logged_out(self, client, phone, db, student):
        login(client)
        login(phone, ua=SAFARI_IPHONE)
        r = client.post("/api/auth/logout-all", headers=X)
        assert r.status_code == 200 and r.json()["data"]["revoked"] == 2
        assert client.get("/api/auth/me").status_code == 401
        assert phone.get("/api/auth/me").status_code == 401
        assert all(s.revoked_at is not None for s in sessions(db))

    def test_old_style_tokens_are_cut_off_too(self, client, student, auth):
        legacy = auth(student)
        login(client)
        client.post("/api/auth/logout-all", headers=X)
        assert client.get("/api/auth/me", headers=legacy).status_code == 401

    def test_you_can_log_in_again_straight_afterwards(self, client, student):
        login(client)
        client.post("/api/auth/logout-all", headers=X)
        login(client)
        assert client.get("/api/auth/me").status_code == 200

    def test_it_does_not_touch_other_users(self, client, db, student, make_user):
        other = make_user(email="other@example.com")
        other.password_hash = PW_HASH
        db.commit()
        other_client = TestClient(app)
        login(other_client, "other@example.com")
        login(client)
        client.post("/api/auth/logout-all", headers=X)
        assert other_client.get("/api/auth/me").status_code == 200

    def test_requires_a_login(self, client):
        assert client.post("/api/auth/logout-all").status_code == 401

    def test_cookie_requests_need_the_csrf_header(self, client, student):
        login(client)
        assert client.post("/api/auth/logout-all").status_code == 403
        assert client.get("/api/auth/me").status_code == 200  # still logged in


class TestPasswordReset:
    def test_a_reset_logs_out_every_device(self, client, phone, db, student):
        login(client)
        login(phone, ua=SAFARI_IPHONE)
        add_otp(db, "stu@example.com", "reset_password")
        r = client.post("/api/auth/reset-password", json={"email": "stu@example.com", "otp": "123456", "newPassword": "BrandNewPass9!"})
        assert r.status_code == 200
        assert client.get("/api/auth/me").status_code == 401 and phone.get("/api/auth/me").status_code == 401
        assert all(s.revoked_at is not None for s in sessions(db))


# --------------------------------------------------------------------------
# The check on every request
# --------------------------------------------------------------------------


class TestEnforcement:
    def test_an_expired_session_is_rejected_even_with_a_valid_token(self, client, db, student):
        token = login(client)
        db.query(UserSession).update({"expires_at": _now() - timedelta(seconds=1)})
        db.commit()
        assert client.get("/api/auth/me", headers=bearer(token)).status_code == 401

    def test_a_token_pointing_at_a_missing_session_is_rejected(self, client, student):
        forged = create_access_token({"id": student.id, "jti": "f" * 32})
        assert client.get("/api/auth/me", headers=bearer(forged)).status_code == 401

    def test_a_session_belonging_to_someone_else_is_rejected(self, client, db, student, make_user):
        other = make_user(email="other@example.com")
        theirs = session_service.create(db, other, user_agent="o", ip="")
        borrowed = create_access_token({"id": student.id, "jti": theirs.id})  # my id, their session
        assert client.get("/api/auth/me", headers=bearer(borrowed)).status_code == 401

    def test_the_cookie_is_checked_too(self, client, db, student):
        login(client)
        db.query(UserSession).update({"revoked_at": _now()})
        db.commit()
        assert client.get("/api/auth/me").status_code == 401

    def test_last_seen_is_refreshed_only_now_and_then(self, client, db, student):
        token = login(client)
        row = sessions(db)[0]
        before = row.last_seen_at
        client.get("/api/auth/me", headers=bearer(token))
        assert sessions(db)[0].last_seen_at == before  # too soon: no write on every request
        db.query(UserSession).update({"last_seen_at": _now() - session_service.TOUCH_EVERY - timedelta(minutes=1)})
        db.commit()
        client.get("/api/auth/me", headers=bearer(token))
        assert sessions(db)[0].last_seen_at > before - timedelta(minutes=1)
        assert _now() - sessions(db)[0].last_seen_at < timedelta(minutes=1)


# --------------------------------------------------------------------------
# Seeing and removing your own devices
# --------------------------------------------------------------------------


class TestSessionList:
    def test_lists_active_devices_and_marks_this_one(self, client, phone, student):
        login(client, ua=CHROME_WIN)
        login(phone, ua=SAFARI_IPHONE)
        mine = client.get("/api/auth/sessions").json()["data"]
        assert {s["device"] for s in mine} == {"Chrome on Windows", "Safari on iOS"}
        assert [s["device"] for s in mine if s["current"]] == ["Chrome on Windows"]
        theirs = phone.get("/api/auth/sessions").json()["data"]
        assert [s["device"] for s in theirs if s["current"]] == ["Safari on iOS"]

    def test_most_recently_used_comes_first(self, client, phone, db, student):
        login(client, ua=CHROME_WIN)
        login(phone, ua=SAFARI_IPHONE)
        # The phone has been idle for two hours; the laptop is the device asking, so it is the freshest.
        db.query(UserSession).filter(UserSession.user_agent == SAFARI_IPHONE).update({"last_seen_at": _now() - timedelta(hours=2)})
        db.commit()
        assert [s["device"] for s in client.get("/api/auth/sessions").json()["data"]] == ["Chrome on Windows", "Safari on iOS"]

    def test_revoked_and_expired_sessions_are_not_listed(self, client, db, student):
        login(client)
        session_service.create(db, student, user_agent="gone", ip="").id
        old = session_service.create(db, student, user_agent="old", ip="")
        db.query(UserSession).filter(UserSession.id == old.id).update({"expires_at": _now() - timedelta(days=1)})
        db.query(UserSession).filter(UserSession.user_agent == "gone").update({"revoked_at": _now()})
        db.commit()
        assert len(client.get("/api/auth/sessions").json()["data"]) == 1

    def test_only_your_own_sessions_are_listed(self, client, db, student, make_user):
        other = make_user(email="other@example.com")
        session_service.create(db, other, user_agent="their device", ip="")
        login(client)
        assert [s["device"] for s in client.get("/api/auth/sessions").json()["data"]] == ["Chrome on Windows"]

    def test_requires_a_login(self, client):
        assert client.get("/api/auth/sessions").status_code == 401

    def test_old_style_tokens_see_the_list_with_nothing_marked_current(self, client, db, student, auth):
        login(TestClient(app))
        data = client.get("/api/auth/sessions", headers=auth(student)).json()["data"]
        assert len(data) == 1 and not data[0]["current"]


class TestRevokeOne:
    def test_logs_out_just_that_device(self, client, phone, student):
        login(client)
        login(phone, ua=SAFARI_IPHONE)
        phone_id = next(s["id"] for s in client.get("/api/auth/sessions").json()["data"] if not s["current"])
        r = client.delete(f"/api/auth/sessions/{phone_id}", headers=X)
        assert r.status_code == 200
        assert phone.get("/api/auth/me").status_code == 401
        assert client.get("/api/auth/me").status_code == 200

    def test_removing_your_own_current_session_logs_you_out(self, client, student):
        login(client)
        mine = client.get("/api/auth/sessions").json()["data"][0]["id"]
        assert client.delete(f"/api/auth/sessions/{mine}", headers=X).status_code == 200
        assert client.get("/api/auth/me").status_code == 401

    def test_unknown_session_is_404(self, client, student):
        login(client)
        assert client.delete("/api/auth/sessions/" + "0" * 32, headers=X).status_code == 404

    def test_you_cannot_revoke_someone_elses_session(self, client, db, student, make_user):
        other = make_user(email="other@example.com")
        theirs = session_service.create(db, other, user_agent="o", ip="")
        login(client)
        assert client.delete(f"/api/auth/sessions/{theirs.id}", headers=X).status_code == 404
        db.expire_all()
        assert db.get(UserSession, theirs.id).revoked_at is None  # untouched

    def test_revoking_twice_is_a_404_not_an_error(self, client, phone, student):
        login(client)
        login(phone)
        other = next(s["id"] for s in client.get("/api/auth/sessions").json()["data"] if not s["current"])
        assert client.delete(f"/api/auth/sessions/{other}", headers=X).status_code == 200
        assert client.delete(f"/api/auth/sessions/{other}", headers=X).status_code == 404

    def test_cookie_requests_need_the_csrf_header(self, client, student):
        login(client)
        mine = client.get("/api/auth/sessions").json()["data"][0]["id"]
        assert client.delete(f"/api/auth/sessions/{mine}").status_code == 403

    def test_requires_a_login(self, client):
        assert client.delete("/api/auth/sessions/abc").status_code == 401


class TestDeviceLabels:
    @pytest.mark.parametrize(
        "ua,label",
        [
            (CHROME_WIN, "Chrome on Windows"),
            (SAFARI_IPHONE, "Safari on iOS"),
            ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36 Edg/124.0", "Edge on Windows"),
            ("Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0", "Firefox on Linux"),
            ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.4 Safari/605.1.15", "Safari on macOS"),
            ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Chrome/124.0 Mobile Safari/537.36", "Chrome on Android"),
            ("", "Unknown device"),
            (None, "Unknown device"),
            ("curl/8.4.0", "Browser"),
        ],
    )
    def test_label(self, ua, label):
        assert session_service.describe_device(ua) == label
