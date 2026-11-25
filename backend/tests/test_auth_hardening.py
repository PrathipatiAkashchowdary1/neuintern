"""Auth hardening: production guards, cookie sessions, CSRF guard, login lockout,
OTP brute-force limits, password rules, and session revocation on password reset."""

from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import Settings, settings
from app.core.limiter import limiter
from app.core.security import create_access_token, hash_password, verify_password
from app.core.startup_checks import (
    UnsafeConfiguration,
    validate_admin_account,
    validate_production_settings,
)
from app.db.models import EmailOtp, LoginThrottle, User
from app.db.seed import DEFAULT_ADMIN, seed_admin_user
from app.services import throttle

PASSWORD = "CorrectHorse1!"
PW_HASH = hash_password(PASSWORD)  # bcrypt is slow on purpose; hash once for the whole module
STRONG_SECRET = "x" * 48


def _naive_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture
def student(db, make_user):
    user = make_user(email="stu@example.com")
    user.password_hash = PW_HASH
    db.commit()
    return user


def login(client, email="stu@example.com", password=PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def add_otp(db, email, purpose, code="123456", verified=False):
    now = _naive_now()
    db.add(
        EmailOtp(
            email=email,
            otp_hash=hash_password(code),
            purpose=purpose,
            expires_at=now + timedelta(minutes=10),
            verified=verified,
            verified_at=now if verified else None,
        )
    )
    db.commit()


REGISTER = {
    "fullName": "New Student",
    "email": "new@example.com",
    "phone": "9876543210",
    "degree": "B.Tech",
    "branch": "CSE",
    "currentYear": "3",
    "password": PASSWORD,
}


def fresh_prod(**over) -> Settings:
    base = dict(environment="production", jwt_secret=STRONG_SECRET, cors_origin="https://neuintern.in", _env_file=None)
    base.update(over)
    return Settings(**base)


# --------------------------------------------------------------------------
# Production start-up guards
# --------------------------------------------------------------------------


class TestProductionGuards:
    def test_safe_production_settings_pass(self):
        validate_production_settings(fresh_prod())

    @pytest.mark.parametrize("secret", ["dev_secret_change_me", "change_this_to_a_long_random_string", "changeme", "secret"])
    def test_known_default_secrets_are_refused(self, secret):
        with pytest.raises(UnsafeConfiguration, match="JWT_SECRET"):
            validate_production_settings(fresh_prod(jwt_secret=secret))

    def test_short_secret_is_refused(self):
        with pytest.raises(UnsafeConfiguration, match="JWT_SECRET"):
            validate_production_settings(fresh_prod(jwt_secret="short-but-unique-1"))

    def test_wildcard_cors_is_refused(self):
        with pytest.raises(UnsafeConfiguration, match="CORS_ORIGIN"):
            validate_production_settings(fresh_prod(cors_origin="*"))

    def test_wildcard_among_origins_is_refused(self):
        with pytest.raises(UnsafeConfiguration, match="CORS_ORIGIN"):
            validate_production_settings(fresh_prod(cors_origin="https://neuintern.in, *"))

    def test_disabling_rate_limits_is_refused(self):
        with pytest.raises(UnsafeConfiguration, match="RATE_LIMIT_ENABLED"):
            validate_production_settings(fresh_prod(rate_limit_enabled=False))

    def test_rate_limits_default_to_on(self):
        assert Settings(_env_file=None).rate_limit_enabled is True

    def test_disabling_secure_cookies_is_refused(self):
        with pytest.raises(UnsafeConfiguration, match="COOKIE_SECURE"):
            validate_production_settings(fresh_prod(cookie_secure=False))

    def test_all_problems_are_reported_together(self):
        with pytest.raises(UnsafeConfiguration) as err:
            validate_production_settings(fresh_prod(jwt_secret="secret", cors_origin="*"))
        assert "JWT_SECRET" in str(err.value) and "CORS_ORIGIN" in str(err.value)

    def test_environment_name_is_case_insensitive(self):
        with pytest.raises(UnsafeConfiguration):
            validate_production_settings(fresh_prod(environment=" Production ", jwt_secret="secret"))

    def test_development_is_never_blocked(self):
        validate_production_settings(Settings(environment="development", jwt_secret="secret", cors_origin="*", _env_file=None))

    def test_secure_cookie_defaults_on_only_in_production(self):
        assert fresh_prod().session_cookie_secure is True
        assert Settings(environment="development", _env_file=None).session_cookie_secure is False


class TestAdminAccountSafety:
    def test_production_without_admin_password_creates_no_admin(self, db, monkeypatch):
        monkeypatch.setattr(settings, "environment", "production")
        monkeypatch.setattr(settings, "admin_password", "")
        seed_admin_user(db)
        assert db.query(User).filter(User.role == "admin").count() == 0

    def test_production_with_admin_password_uses_it(self, db, monkeypatch):
        monkeypatch.setattr(settings, "environment", "production")
        monkeypatch.setattr(settings, "admin_password", "Chosen-By-Owner-9")
        seed_admin_user(db)
        admin = db.query(User).filter(User.role == "admin").one()
        assert verify_password("Chosen-By-Owner-9", admin.password_hash)
        assert not verify_password(DEFAULT_ADMIN["password"], admin.password_hash)

    def test_development_keeps_the_convenient_default(self, db, monkeypatch):
        monkeypatch.setattr(settings, "environment", "development")
        monkeypatch.setattr(settings, "admin_password", "")
        seed_admin_user(db)
        admin = db.query(User).filter(User.role == "admin").one()
        assert verify_password(DEFAULT_ADMIN["password"], admin.password_hash)

    def test_production_refuses_to_run_with_the_default_admin_password(self, db, monkeypatch):
        monkeypatch.setattr(settings, "environment", "development")
        seed_admin_user(db)  # created with the published default
        monkeypatch.setattr(settings, "environment", "production")
        with pytest.raises(UnsafeConfiguration, match="default password"):
            validate_admin_account(db, DEFAULT_ADMIN["password"], DEFAULT_ADMIN["email"])

    def test_production_accepts_a_changed_admin_password(self, db, monkeypatch):
        monkeypatch.setattr(settings, "environment", "development")
        seed_admin_user(db)
        admin = db.query(User).filter(User.role == "admin").one()
        admin.password_hash = hash_password("Changed-Already-7")
        db.commit()
        monkeypatch.setattr(settings, "environment", "production")
        validate_admin_account(db, DEFAULT_ADMIN["password"], DEFAULT_ADMIN["email"])

    def test_development_does_not_check_the_admin_password(self, db, monkeypatch):
        monkeypatch.setattr(settings, "environment", "development")
        seed_admin_user(db)
        validate_admin_account(db, DEFAULT_ADMIN["password"], DEFAULT_ADMIN["email"])


# --------------------------------------------------------------------------
# httpOnly session cookie
# --------------------------------------------------------------------------


class TestSessionCookie:
    def _cookie_header(self, r) -> str:
        return r.headers["set-cookie"]

    def test_login_sets_an_httponly_cookie(self, client, student):
        r = login(client)
        assert r.status_code == 200
        header = self._cookie_header(r).lower()
        assert f"{settings.session_cookie_name}=" in header
        assert "httponly" in header and "samesite=lax" in header and "path=/" in header
        assert "max-age=" in header

    def test_cookie_is_not_secure_in_development_but_is_when_enabled(self, client, student, monkeypatch):
        assert "secure" not in self._cookie_header(login(client)).lower().replace("samesite", "")
        monkeypatch.setattr(settings, "cookie_secure", True)
        assert "secure" in self._cookie_header(login(client)).lower()

    def test_samesite_and_domain_are_configurable(self, client, student, monkeypatch):
        monkeypatch.setattr(settings, "cookie_samesite", "none")
        monkeypatch.setattr(settings, "cookie_secure", True)
        monkeypatch.setattr(settings, "cookie_domain", ".neuintern.in")
        header = self._cookie_header(login(client)).lower()
        assert "samesite=none" in header and "domain=.neuintern.in" in header

    def test_json_body_still_carries_the_token_for_api_clients(self, client, student):
        assert login(client).json()["data"]["token"]

    def test_the_cookie_alone_authenticates_the_website(self, client, student):
        login(client)
        r = client.get("/api/auth/me")  # no Authorization header
        assert r.status_code == 200 and r.json()["data"]["email"] == "stu@example.com"

    def test_bearer_header_still_works_without_the_cookie(self, client, student, auth):
        assert client.get("/api/auth/me", headers=auth(student)).status_code == 200

    def test_register_also_logs_the_user_in(self, client, db):
        add_otp(db, "new@example.com", "register", verified=True)
        r = client.post("/api/auth/register", json=REGISTER)
        assert r.status_code == 201
        assert "httponly" in self._cookie_header(r).lower()
        assert client.get("/api/auth/me").status_code == 200

    def test_logout_clears_the_cookie(self, client, student):
        login(client)
        r = client.post("/api/auth/logout")
        assert r.status_code == 200
        assert client.get("/api/auth/me").status_code == 401

    def test_logout_without_a_session_is_fine(self, client):
        assert client.post("/api/auth/logout").status_code == 200

    def test_garbage_cookie_is_rejected(self, client):
        client.cookies.set(settings.session_cookie_name, "not.a.jwt")
        assert client.get("/api/auth/me").status_code == 401

    def test_no_credentials_is_rejected(self, client):
        assert client.get("/api/auth/me").status_code == 401

    def test_header_wins_when_both_are_present(self, client, student, make_user, auth):
        other = make_user(email="other@example.com")
        login(client)  # cookie belongs to `student`
        r = client.get("/api/auth/me", headers=auth(other))
        assert r.json()["data"]["email"] == "other@example.com"


# --------------------------------------------------------------------------
# CSRF guard for cookie-authenticated writes
# --------------------------------------------------------------------------


class TestCsrfGuard:
    """POST /api/enrollments with an unknown program answers 404 once authentication
    passes, so 403 vs 404 shows whether the CSRF guard let the request through."""

    BODY = {"programSlug": "does-not-exist"}

    def test_cookie_write_without_the_header_is_blocked(self, client, student):
        login(client)
        r = client.post("/api/enrollments", json=self.BODY)
        assert r.status_code == 403 and "X-Requested-With" in r.json()["message"]

    def test_cookie_write_with_the_header_is_allowed(self, client, student):
        login(client)
        r = client.post("/api/enrollments", json=self.BODY, headers={"X-Requested-With": "neuintern"})
        assert r.status_code == 404

    def test_cookie_reads_do_not_need_the_header(self, client, student):
        login(client)
        assert client.get("/api/enrollments/me").status_code == 200

    def test_bearer_writes_do_not_need_the_header(self, client, student, auth):
        r = client.post("/api/enrollments", json=self.BODY, headers=auth(student))
        assert r.status_code == 404

    def test_admin_writes_are_guarded_too(self, client, db, make_user):
        admin = make_user(role="admin", email="adm@example.com")
        admin.password_hash = PW_HASH
        db.commit()
        login(client, "adm@example.com")
        r = client.put("/api/admin/programs/x", json={"title": "t"})
        assert r.status_code == 403
        r = client.put("/api/admin/programs/x", json={"title": "t"}, headers={"X-Requested-With": "neuintern"})
        assert r.status_code == 404

    def test_public_endpoints_are_unaffected(self, client, student):
        login(client)
        assert client.post("/api/certificate/verify", json={"certificateId": "NI-0000"}).status_code == 200
        assert client.post("/api/auth/logout").status_code == 200


# --------------------------------------------------------------------------
# Login lockout
# --------------------------------------------------------------------------


class TestLoginLockout:
    def _fail(self, client, n, email="stu@example.com"):
        return [login(client, email, "wrong-password").status_code for _ in range(n)]

    def test_fifth_failure_locks_the_account(self, client, student):
        assert self._fail(client, 5) == [401] * 5
        r = login(client, password="wrong-password")
        assert r.status_code == 429
        assert int(r.headers["retry-after"]) > 0
        assert "try again in" in r.json()["message"].lower()

    def test_the_correct_password_is_refused_while_locked(self, client, student):
        self._fail(client, 5)
        assert login(client).status_code == 429

    def test_success_before_the_limit_resets_the_counter(self, client, student):
        self._fail(client, 4)
        assert login(client).status_code == 200
        assert self._fail(client, 4) == [401] * 4  # a fresh count, not 8 failures in a row

    def test_unknown_emails_lock_exactly_like_real_ones(self, client, student):
        """No account discovery: same responses whether or not the email is registered."""
        ghost = self._fail(client, 6, "ghost@example.com")
        real = self._fail(client, 6, "stu@example.com")
        assert ghost == real == [401] * 5 + [429]

    def test_the_key_ignores_letter_case(self, client, student):
        self._fail(client, 3, "STU@example.com")
        self._fail(client, 2, "stu@example.com")
        assert login(client, "stu@example.com", "wrong-password").status_code == 429

    def test_other_emails_are_not_affected(self, client, db, student, make_user):
        other = make_user(email="other@example.com")
        other.password_hash = PW_HASH
        db.commit()
        self._fail(client, 5)
        assert login(client, "other@example.com").status_code == 200

    def test_the_lock_expires(self, client, student, monkeypatch):
        self._fail(client, 5)
        later = _naive_now() + throttle.LOCK_FOR + timedelta(seconds=5)
        monkeypatch.setattr(throttle, "_now", lambda: later)
        assert login(client).status_code == 200

    def test_old_failures_age_out_of_the_window(self, client, student, monkeypatch):
        self._fail(client, 4)
        later = _naive_now() + throttle.WINDOW + timedelta(minutes=1)
        monkeypatch.setattr(throttle, "_now", lambda: later)
        assert self._fail(client, 4) == [401] * 4  # not locked: the earlier four expired

    def test_a_password_reset_clears_the_lock(self, client, db, student):
        self._fail(client, 5)
        add_otp(db, "stu@example.com", "reset_password")
        r = client.post("/api/auth/reset-password", json={"email": "stu@example.com", "otp": "123456", "newPassword": "BrandNewPass9!"})
        assert r.status_code == 200
        assert login(client, password="BrandNewPass9!").status_code == 200

    def test_idle_rows_are_pruned(self, client, db, student):
        db.add(LoginThrottle(key="login:old@example.com", failures=2, window_start=_naive_now() - timedelta(days=3)))
        db.commit()
        self._fail(client, 1)
        assert db.get(LoginThrottle, "login:old@example.com") is None

    def test_success_removes_the_row(self, client, db, student):
        self._fail(client, 2)
        login(client)
        db.expire_all()
        assert db.get(LoginThrottle, "login:stu@example.com") is None


class TestTimingEqualisation:
    @pytest.mark.parametrize("email", ["stu@example.com", "nobody@example.com"])
    def test_a_password_hash_is_always_checked(self, client, student, monkeypatch, email):
        calls = []
        real = verify_password

        def counting(plain, hashed):
            calls.append(1)
            return real(plain, hashed)

        monkeypatch.setattr("app.routers.auth.verify_password", counting)
        login(client, email, "wrong-password")
        assert calls == [1]


# --------------------------------------------------------------------------
# One-time code brute force
# --------------------------------------------------------------------------


class TestOtpBruteForce:
    def _guess(self, client, n, path="/api/auth/reset-password", **extra):
        return [
            client.post(path, json={"email": "stu@example.com", "otp": f"00000{i}", **extra}).status_code
            for i in range(n)
        ]

    def test_reset_password_locks_after_five_wrong_codes(self, client, db, student):
        add_otp(db, "stu@example.com", "reset_password")
        codes = self._guess(client, 6, newPassword="BrandNewPass9!")
        assert codes == [400] * 5 + [429]

    def test_the_right_code_is_refused_while_locked(self, client, db, student):
        add_otp(db, "stu@example.com", "reset_password")
        self._guess(client, 5, newPassword="BrandNewPass9!")
        r = client.post("/api/auth/reset-password", json={"email": "stu@example.com", "otp": "123456", "newPassword": "BrandNewPass9!"})
        assert r.status_code == 429

    def test_verify_otp_is_limited_too(self, client, db):
        add_otp(db, "stu@example.com", "register")
        codes = self._guess(client, 6, path="/api/auth/verify-otp", purpose="register")
        assert codes == [400] * 5 + [429]

    def test_a_correct_code_clears_the_counter(self, client, db, student):
        add_otp(db, "stu@example.com", "reset_password")
        self._guess(client, 3, newPassword="BrandNewPass9!")
        ok = client.post("/api/auth/reset-password", json={"email": "stu@example.com", "otp": "123456", "newPassword": "BrandNewPass9!"})
        assert ok.status_code == 200
        db.expire_all()
        assert db.get(LoginThrottle, "otp:stu@example.com") is None

    def test_code_guessing_and_login_failures_are_counted_separately(self, client, db, student):
        add_otp(db, "stu@example.com", "reset_password")
        self._guess(client, 5, newPassword="BrandNewPass9!")  # locks the OTP key only
        assert login(client).status_code == 200


# --------------------------------------------------------------------------
# Password rules
# --------------------------------------------------------------------------


class TestPasswordRules:
    @pytest.mark.parametrize("pw", ["short1!", "1234567", "", "        "])
    def test_too_short_or_blank_is_rejected_on_register(self, client, db, pw):
        add_otp(db, "new@example.com", "register", verified=True)
        assert client.post("/api/auth/register", json={**REGISTER, "password": pw}).status_code == 422

    def test_eight_characters_is_enough(self, client, db):
        add_otp(db, "new@example.com", "register", verified=True)
        assert client.post("/api/auth/register", json={**REGISTER, "password": "Abcdef1!"}).status_code == 201

    @pytest.mark.parametrize("pw", ["a" * 73, "🔒" * 19])  # 73 bytes, and 76 bytes in 19 characters
    def test_over_72_bytes_is_a_clean_422_not_a_crash(self, client, db, pw):
        add_otp(db, "new@example.com", "register", verified=True)
        r = client.post("/api/auth/register", json={**REGISTER, "password": pw})
        assert r.status_code == 422 and "72" in r.json()["message"]

    def test_exactly_72_bytes_is_accepted(self, client, db):
        add_otp(db, "new@example.com", "register", verified=True)
        assert client.post("/api/auth/register", json={**REGISTER, "password": "a" * 72}).status_code == 201

    def test_the_same_rules_apply_to_password_reset(self, client, db, student):
        add_otp(db, "stu@example.com", "reset_password")
        for bad in ("short", "a" * 80):
            r = client.post("/api/auth/reset-password", json={"email": "stu@example.com", "otp": "123456", "newPassword": bad})
            assert r.status_code == 422

    def test_login_with_an_enormous_password_is_rejected_cheaply(self, client, student):
        assert login(client, password="a" * 5000).status_code == 422

    def test_existing_short_passwords_can_still_log_in(self, client, db, make_user):
        """Raising the minimum must not lock out people who registered under the old rule."""
        legacy = make_user(email="legacy@example.com")
        legacy.password_hash = hash_password("abc123")
        db.commit()
        assert login(client, "legacy@example.com", "abc123").status_code == 200


# --------------------------------------------------------------------------
# Password reset revokes existing sessions
# --------------------------------------------------------------------------


class TestSessionRevocation:
    def test_tokens_carry_an_issued_at_time(self):
        from app.core.security import decode_access_token

        payload = decode_access_token(create_access_token({"id": "x"}))
        assert "iat" in payload and "iatf" in payload

    def test_reset_logs_out_every_existing_session(self, client, db, student, auth):
        old_header = auth(student)
        login(client)  # also holds an old cookie session
        assert client.get("/api/auth/me").status_code == 200

        add_otp(db, "stu@example.com", "reset_password")
        r = client.post("/api/auth/reset-password", json={"email": "stu@example.com", "otp": "123456", "newPassword": "BrandNewPass9!"})
        assert r.status_code == 200

        assert client.get("/api/auth/me").status_code == 401  # old cookie
        assert client.get("/api/auth/me", headers=old_header).status_code == 401  # old bearer token

    def test_logging_in_again_in_the_same_second_as_a_reset_works(self, client, db, student):
        """Regression: whole-second token timestamps made this fail."""
        add_otp(db, "stu@example.com", "reset_password")
        client.post("/api/auth/reset-password", json={"email": "stu@example.com", "otp": "123456", "newPassword": "BrandNewPass9!"})
        client.cookies.clear()
        assert login(client, password="BrandNewPass9!").status_code == 200
        assert client.get("/api/auth/me").status_code == 200

    def test_old_password_stops_working(self, client, db, student):
        add_otp(db, "stu@example.com", "reset_password")
        client.post("/api/auth/reset-password", json={"email": "stu@example.com", "otp": "123456", "newPassword": "BrandNewPass9!"})
        assert login(client, password=PASSWORD).status_code == 401

    def test_tokens_without_iat_are_fine_until_a_reset_has_happened(self, client, student):
        from jose import jwt

        legacy = jwt.encode(
            {"id": student.id, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )
        assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {legacy}"}).status_code == 200

    def test_tokens_without_iat_are_rejected_after_a_reset(self, client, db, student):
        from jose import jwt

        student.token_valid_after = _naive_now() - timedelta(minutes=1)
        db.commit()
        legacy = jwt.encode(
            {"id": student.id, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )
        assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {legacy}"}).status_code == 401

    def test_a_token_issued_after_the_reset_is_valid(self, client, db, student, auth):
        student.token_valid_after = _naive_now() - timedelta(minutes=5)
        db.commit()
        assert client.get("/api/auth/me", headers=auth(student)).status_code == 200


# --------------------------------------------------------------------------
# Per-IP rate limits on the remaining auth endpoints
# --------------------------------------------------------------------------


class TestIpRateLimit:
    def test_register_is_limited_per_ip(self, client, monkeypatch):
        monkeypatch.setattr(limiter, "enabled", True)
        limiter.reset()
        try:
            codes = [client.post("/api/auth/register", json=REGISTER).status_code for _ in range(21)]
        finally:
            limiter.reset()
        assert codes[:20] == [400] * 20  # "verify your email first": counted, but allowed
        assert codes[20] == 429
