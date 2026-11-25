"""The go-live checker (python -m app.deploy_check)."""

import json
import smtplib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from app import deploy_check as dc
from app.core.config import Settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.models import EmailOutbox, User
from app.deploy_check import FAIL, INFO, PASS, WARN, run_checks

STRONG = "k" * 48


def good(tmp_path, **over) -> Settings:
    """A production configuration with nothing wrong with it."""
    base = dict(
        environment="production",
        jwt_secret=STRONG,
        cors_origin="https://neuintern.in",
        frontend_url="https://neuintern.in",
        api_public_url="https://api.neuintern.in",
        razorpay_key_id="rzp_live_abc123",
        razorpay_key_secret="secret",
        razorpay_webhook_secret="whsec",
        smtp_host="smtp.example.com",
        smtp_user="mailer",
        smtp_password="pw",
        database_url="postgresql://u:p@db.example.com/neuintern",
        upload_dir=str(tmp_path / "uploads"),
        _env_file=None,
    )
    base.update(over)
    return Settings(**base)


def levels(checks) -> dict:
    """name -> worst level among checks with that name."""
    order = {PASS: 0, INFO: 1, WARN: 2, FAIL: 3}
    out = {}
    for c in checks:
        if c.name not in out or order[c.level] > order[out[c.name]]:
            out[c.name] = c.level
    return out


def settings_only(s) -> dict:
    return levels(run_checks(s))


# --------------------------------------------------------------------------
# Settings checks
# --------------------------------------------------------------------------


class TestSettingsChecks:
    def test_a_correct_production_config_has_no_failures(self, tmp_path):
        result = run_checks(good(tmp_path))
        assert [c for c in result if c.level == FAIL] == []
        assert [c for c in result if c.level == WARN] == []

    def test_development_environment_fails(self, tmp_path):
        assert settings_only(good(tmp_path, environment="development"))["Environment"] == FAIL

    @pytest.mark.parametrize("secret", ["dev_secret_change_me", "changeme"])
    def test_published_default_secrets_are_called_out_as_such(self, tmp_path, secret):
        c = next(c for c in run_checks(good(tmp_path, jwt_secret=secret)) if c.name == "JWT secret")
        assert c.level == FAIL and "published default" in c.detail

    def test_short_secrets_fail_with_their_length(self, tmp_path):
        c = next(c for c in run_checks(good(tmp_path, jwt_secret="short")) if c.name == "JWT secret")
        assert c.level == FAIL and "5 characters" in c.detail

    def test_wildcard_cors_fails_with_the_right_explanation(self, tmp_path):
        c = next(c for c in run_checks(good(tmp_path, cors_origin="*")) if c.name == "CORS origins")
        assert c.level == FAIL and "any website" in c.detail

    def test_plain_http_origin_fails(self, tmp_path):
        assert settings_only(good(tmp_path, cors_origin="http://neuintern.in"))["CORS origins"] == FAIL

    def test_leftover_localhost_origin_warns(self, tmp_path):
        assert settings_only(good(tmp_path, cors_origin="https://neuintern.in,http://localhost:5173"))["CORS origins"] == WARN

    def test_insecure_cookie_fails(self, tmp_path):
        assert settings_only(good(tmp_path, cookie_secure=False))["Session cookie"] == FAIL

    def test_cookie_samesite_warning_when_site_and_api_are_on_different_domains(self, tmp_path):
        s = good(tmp_path, api_public_url="https://neuintern-api.azurewebsites.net")
        assert settings_only(s)["Cookie SameSite"] == WARN
        assert "Cookie SameSite" not in settings_only(good(tmp_path, api_public_url="https://neuintern-api.azurewebsites.net", cookie_samesite="none"))

    def test_subdomains_of_one_site_need_no_samesite_change(self, tmp_path):
        assert "Cookie SameSite" not in settings_only(good(tmp_path))

    def test_disabled_rate_limits_fail(self, tmp_path):
        assert settings_only(good(tmp_path, rate_limit_enabled=False))["Rate limits"] == FAIL

    def test_localhost_or_http_frontend_url_fails(self, tmp_path):
        assert settings_only(good(tmp_path, frontend_url="http://localhost:5173"))["FRONTEND_URL"] == FAIL
        assert settings_only(good(tmp_path, frontend_url="http://neuintern.in"))["FRONTEND_URL"] == FAIL

    def test_missing_api_public_url_warns_and_non_https_fails(self, tmp_path):
        assert settings_only(good(tmp_path, api_public_url=""))["API_PUBLIC_URL"] == WARN
        assert settings_only(good(tmp_path, api_public_url="http://api.neuintern.in"))["API_PUBLIC_URL"] == FAIL

    def test_razorpay_unconfigured_fails(self, tmp_path):
        assert settings_only(good(tmp_path, razorpay_key_id="", razorpay_key_secret=""))["Razorpay keys"] == FAIL

    def test_razorpay_test_keys_fail_in_production(self, tmp_path):
        assert settings_only(good(tmp_path, razorpay_key_id="rzp_test_abc"))["Razorpay keys"] == FAIL

    def test_razorpay_live_keys_pass(self, tmp_path):
        assert settings_only(good(tmp_path))["Razorpay keys"] == PASS

    def test_missing_webhook_secret_fails(self, tmp_path):
        assert settings_only(good(tmp_path, razorpay_webhook_secret=""))["Razorpay webhook"] == FAIL

    def test_unconfigured_smtp_fails(self, tmp_path):
        assert settings_only(good(tmp_path, smtp_host="", smtp_user="", smtp_password=""))["Email (SMTP)"] == FAIL

    def test_smtp_login_is_only_tried_when_asked(self, tmp_path, monkeypatch):
        def boom(*a, **k):
            raise AssertionError("must not connect without --smtp")

        monkeypatch.setattr(smtplib, "SMTP", boom)
        assert settings_only(good(tmp_path))["Email (SMTP)"] == PASS

    def test_smtp_login_success(self, tmp_path, monkeypatch):
        calls = []

        class FakeSMTP:
            def __init__(self, host, port, timeout=None):
                calls.append(("connect", host, port))

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def starttls(self):
                calls.append("starttls")

            def login(self, user, password):
                calls.append(("login", user))

        monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
        result = run_checks(good(tmp_path), smtp_login=True)
        assert levels(result)["Email (SMTP)"] == PASS
        assert calls == [("connect", "smtp.example.com", 587), "starttls", ("login", "mailer")]

    def test_smtp_login_failure(self, tmp_path, monkeypatch):
        class BadSMTP:
            def __init__(self, *a, **k):
                raise ConnectionRefusedError("nope")

        monkeypatch.setattr(smtplib, "SMTP", BadSMTP)
        result = run_checks(good(tmp_path), smtp_login=True)
        assert levels(result)["Email (SMTP)"] == FAIL
        assert "ConnectionRefusedError" in next(c.detail for c in result if c.name == "Email (SMTP)")

    def test_unwritable_upload_dir_fails(self, tmp_path):
        blocker = tmp_path / "a-file"
        blocker.write_text("x")
        assert settings_only(good(tmp_path, upload_dir=str(blocker / "uploads")))["Image uploads"] == FAIL

    def test_upload_dir_inside_the_app_folder_warns(self, tmp_path):
        inside = Path(dc.__file__).resolve().parents[1] / "uploads-check-test"
        try:
            assert settings_only(good(tmp_path, upload_dir=str(inside)))["Image uploads"] == WARN
        finally:
            inside.rmdir() if inside.exists() else None

    def test_disabled_scheduler_warns(self, tmp_path):
        assert settings_only(good(tmp_path, scheduler_enabled=False))["Background jobs"] == WARN

    def test_reminders_state_is_reported(self, tmp_path):
        assert settings_only(good(tmp_path))["Reminder emails"] == INFO
        assert settings_only(good(tmp_path, reminders_enabled=True))["Reminder emails"] == PASS

    def test_sqlite_database_warns_and_empty_url_fails(self, tmp_path):
        assert settings_only(good(tmp_path, database_url="sqlite:///./x.db"))["Database"] == WARN
        assert settings_only(good(tmp_path, database_url=""))["Database"] == FAIL

    def test_every_failure_carries_a_fix(self, tmp_path):
        s = good(tmp_path, environment="development", jwt_secret="x", cors_origin="*", rate_limit_enabled=False, razorpay_key_id="")
        failed = [c for c in run_checks(s) if c.level == FAIL]
        assert failed and all(c.fix for c in failed)


# --------------------------------------------------------------------------
# Database checks
# --------------------------------------------------------------------------


@pytest.fixture
def engine(tmp_path):
    eng = create_engine(f"sqlite:///{(tmp_path / 'check.db').as_posix()}")
    yield eng
    eng.dispose()


def head_revision() -> str:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    root = Path(dc.__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "alembic"))
    return ScriptDirectory.from_config(cfg).get_current_head()


def stamp(engine, revision):
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"))
        conn.execute(text("DELETE FROM alembic_version"))
        if revision:
            conn.execute(text("INSERT INTO alembic_version VALUES (:v)"), {"v": revision})


class TestConnection:
    def test_a_reachable_database_passes(self, engine):
        assert dc.check_connection(engine)[0].level == PASS

    def test_an_unreachable_database_fails(self, tmp_path):
        bad = create_engine(f"sqlite:///{(tmp_path / 'missing-dir' / 'x.db').as_posix()}")
        result = dc.check_connection(bad)[0]
        assert result.level == FAIL and result.fix


class TestMigrations:
    def test_an_empty_database_fails_with_upgrade_advice(self, engine):
        result = dc.check_migrations(engine)[0]
        assert result.level == FAIL and "alembic upgrade head" in result.fix

    def test_existing_tables_never_registered_with_alembic_get_the_stamp_advice(self, engine):
        Base.metadata.create_all(engine)
        result = dc.check_migrations(engine)[0]
        assert result.level == FAIL and "alembic stamp 0001" in result.fix

    def test_an_old_revision_fails(self, engine):
        Base.metadata.create_all(engine)
        stamp(engine, "0001")
        result = dc.check_migrations(engine)[0]
        assert result.level == FAIL and "0001" in result.detail and head_revision() in result.detail

    def test_the_latest_revision_passes(self, engine):
        Base.metadata.create_all(engine)
        stamp(engine, head_revision())
        assert dc.check_migrations(engine)[0].level == PASS


class TestAdminAccount:
    @pytest.fixture(autouse=True)
    def _tables(self, engine):
        Base.metadata.create_all(engine)

    def _add_admin(self, engine, password, email="info@neuintern.in"):
        from sqlalchemy.orm import Session

        with Session(engine) as db:
            db.add(
                User(full_name="A", email=email, phone="9", degree="d", branch="b", current_year="1",
                     password_hash=hash_password(password), role="admin")
            )
            db.commit()

    def test_no_admin_and_no_password_fails(self, engine, tmp_path):
        assert dc.check_admin(engine, good(tmp_path))[0].level == FAIL

    def test_no_admin_yet_but_a_password_is_set_is_fine(self, engine, tmp_path):
        assert dc.check_admin(engine, good(tmp_path, admin_password="Chosen-Pw-9!"))[0].level == INFO

    def test_the_published_default_password_fails(self, engine, tmp_path):
        self._add_admin(engine, "Admin@123")
        result = dc.check_admin(engine, good(tmp_path))[0]
        assert result.level == FAIL and "default password" in result.detail

    def test_a_changed_password_passes(self, engine, tmp_path):
        self._add_admin(engine, "Something-Else-77")
        assert dc.check_admin(engine, good(tmp_path))[0].level == PASS


class TestEmailQueue:
    @pytest.fixture(autouse=True)
    def _tables(self, engine):
        Base.metadata.create_all(engine)

    def _row(self, engine, **over):
        from sqlalchemy.orm import Session

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        fields = dict(kind="contact", to_email="a@example.com", subject="s", status="pending", attempts=1,
                      next_attempt_at=now, created_at=now)
        fields.update(over)
        with Session(engine) as db:
            db.add(EmailOutbox(**fields))
            db.commit()

    def test_a_clean_queue_passes(self, engine):
        assert dc.check_email_queue(engine)[0].level == PASS

    def test_failed_emails_warn(self, engine):
        self._row(engine, status="failed")
        result = dc.check_email_queue(engine)
        assert result[0].level == WARN and "failed permanently" in result[0].detail

    def test_old_waiting_emails_warn(self, engine):
        self._row(engine, created_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1))
        assert any(c.level == WARN and "waiting" in c.detail for c in dc.check_email_queue(engine))

    def test_fresh_waiting_emails_are_normal(self, engine):
        self._row(engine)
        assert dc.check_email_queue(engine)[0].level == PASS


class TestRunChecks:
    def test_database_dependent_checks_are_skipped_until_migrated(self, engine, tmp_path):
        names = [c.name for c in run_checks(good(tmp_path), engine=engine)]
        assert "Database migrations" in names and "Admin account" not in names and "Email queue" not in names
        assert "Admin account / email queue" in names

    def test_everything_is_checked_once_migrated(self, engine, tmp_path):
        Base.metadata.create_all(engine)
        stamp(engine, head_revision())
        names = [c.name for c in run_checks(good(tmp_path, admin_password="Chosen-Pw-9!"), engine=engine)]
        assert {"Database connection", "Database migrations", "Admin account", "Email queue"} <= set(names)

    def test_a_fully_ready_server_has_no_failures(self, engine, tmp_path):
        Base.metadata.create_all(engine)
        stamp(engine, head_revision())
        result = run_checks(good(tmp_path, admin_password="Chosen-Pw-9!"), engine=engine)
        assert [c for c in result if c.level == FAIL] == []


# --------------------------------------------------------------------------
# The command line
# --------------------------------------------------------------------------


class TestCommandLine:
    def _prepare(self, monkeypatch, engine, tmp_path, **over):
        import app.db.base as base

        monkeypatch.setattr(base, "engine", engine)
        monkeypatch.setattr(dc, "default_settings", good(tmp_path, admin_password="Chosen-Pw-9!", **over))

    def test_exit_code_is_zero_when_ready(self, monkeypatch, engine, tmp_path, capsys):
        Base.metadata.create_all(engine)
        stamp(engine, head_revision())
        self._prepare(monkeypatch, engine, tmp_path)
        assert dc.main([]) == 0
        assert "Ready" in capsys.readouterr().out

    def test_exit_code_is_one_when_something_fails(self, monkeypatch, engine, tmp_path, capsys):
        self._prepare(monkeypatch, engine, tmp_path, jwt_secret="short")
        assert dc.main([]) == 1
        out = capsys.readouterr().out
        assert "[FAIL] JWT secret" in out and "NOT READY" in out

    def test_json_output_is_valid_and_complete(self, monkeypatch, engine, tmp_path, capsys):
        self._prepare(monkeypatch, engine, tmp_path, cors_origin="*")
        assert dc.main(["--json"]) == 1
        data = json.loads(capsys.readouterr().out)
        assert data["ready"] is False and data["summary"]["FAIL"] >= 1
        assert any(c["name"] == "CORS origins" and c["level"] == "FAIL" and c["fix"] for c in data["checks"])
