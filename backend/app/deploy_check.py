"""Go-live checker: reads the settings this server would run with and reports what is
unsafe, missing or misconfigured, so problems are found before students do.

    python -m app.deploy_check            # run on the server, with the same .env / environment
    python -m app.deploy_check --smtp     # also try logging in to the mail server (network call)
    python -m app.deploy_check --json     # machine-readable output

It judges against PRODUCTION standards no matter what ENVIRONMENT says, so running it on a
development machine reports FAIL for things that are fine in development. Exit code 1 if
anything FAILs, so it can also gate a deployment script.
"""

import argparse
import json
import os
import smtplib
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import Settings, settings as default_settings
from app.core.startup_checks import KNOWN_DEFAULT_SECRETS, MIN_SECRET_LENGTH

PASS, WARN, FAIL, INFO = "PASS", "WARN", "FAIL", "INFO"


@dataclass
class Check:
    level: str
    name: str
    detail: str
    fix: str = ""


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _is_local(host: str) -> bool:
    return host in ("localhost", "127.0.0.1", "::1") or host.endswith(".localhost")


def _site(host: str) -> str:
    """Naive 'registrable domain': the last two labels (good enough to spot an obviously
    different domain; it does not know about suffixes like co.uk)."""
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


# --------------------------------------------------------------------------
# Checks that need only the settings
# --------------------------------------------------------------------------


def check_environment(s: Settings) -> list[Check]:
    if s.is_production:
        return [Check(PASS, "Environment", "ENVIRONMENT=production")]
    return [
        Check(
            FAIL,
            "Environment",
            f"ENVIRONMENT is '{s.environment}', so the production safety checks are not enforced at start-up",
            "Set ENVIRONMENT=production",
        )
    ]


def check_secret(s: Settings) -> list[Check]:
    if s.jwt_secret in KNOWN_DEFAULT_SECRETS:
        return [Check(FAIL, "JWT secret", "still a published default value", "Set JWT_SECRET to a long random value")]
    if len(s.jwt_secret) < MIN_SECRET_LENGTH:
        return [
            Check(
                FAIL,
                "JWT secret",
                f"only {len(s.jwt_secret)} characters (need {MIN_SECRET_LENGTH}+)",
                'python -c "import secrets; print(secrets.token_urlsafe(48))"',
            )
        ]
    return [Check(PASS, "JWT secret", "random and long enough")]


def check_cors(s: Settings) -> list[Check]:
    origins = s.cors_origins
    if "*" in origins:
        return [Check(FAIL, "CORS origins", "'*' allows any website to call the API", "Set CORS_ORIGIN to your site's exact origin, e.g. https://neuintern.in")]
    out, bad, local = [], [], []
    for o in origins:
        host = _host(o)
        if _is_local(host):
            local.append(o)
        elif not o.startswith("https://"):
            bad.append(o)
    if bad:
        out.append(Check(FAIL, "CORS origins", f"not https: {', '.join(bad)}", "Use https:// origins"))
    if local:
        out.append(Check(WARN, "CORS origins", f"development origin(s) still allowed: {', '.join(local)}", "Remove localhost from CORS_ORIGIN"))
    if not out:
        out.append(Check(PASS, "CORS origins", ", ".join(origins) or "(none)"))
    if not origins:
        out = [Check(FAIL, "CORS origins", "no origin allowed: the website could not call the API", "Set CORS_ORIGIN")]
    return out


def check_cookies(s: Settings) -> list[Check]:
    out = []
    if not s.session_cookie_secure:
        out.append(Check(FAIL, "Session cookie", "not marked Secure: it would travel over plain HTTP", "Remove COOKIE_SECURE=false"))
    else:
        out.append(Check(PASS, "Session cookie", "httpOnly + Secure"))
    api, site = _host(s.api_public_url), _host(s.frontend_url)
    if api and site and not _is_local(api) and _site(api) != _site(site) and s.cookie_samesite.lower() != "none":
        out.append(
            Check(
                WARN,
                "Cookie SameSite",
                f"the API ({api}) and the site ({site}) are on different domains; browsers will not send a SameSite=lax cookie",
                "Set COOKIE_SAMESITE=none (or put both on subdomains of one domain)",
            )
        )
    return out


def check_rate_limit(s: Settings) -> list[Check]:
    if not s.rate_limit_enabled:
        return [Check(FAIL, "Rate limits", "disabled", "Remove RATE_LIMIT_ENABLED=false")]
    return [Check(PASS, "Rate limits", "enabled")]


def check_urls(s: Settings) -> list[Check]:
    out = []
    host = _host(s.frontend_url)
    if not s.frontend_url.startswith("https://") or _is_local(host):
        out.append(Check(FAIL, "FRONTEND_URL", f"'{s.frontend_url}': links in emails would point somewhere students cannot use", "Set FRONTEND_URL=https://your-site"))
    else:
        out.append(Check(PASS, "FRONTEND_URL", s.frontend_url))
    if not s.api_public_url:
        out.append(
            Check(
                WARN,
                "API_PUBLIC_URL",
                "not set: uploaded image links use the address the request arrived on (often http:// behind a proxy) and the one-click unsubscribe header is skipped",
                "Set API_PUBLIC_URL=https://api.your-domain",
            )
        )
    elif not s.api_public_url.startswith("https://"):
        out.append(Check(FAIL, "API_PUBLIC_URL", f"'{s.api_public_url}' is not https", "Use an https:// URL"))
    else:
        out.append(Check(PASS, "API_PUBLIC_URL", s.api_public_url))
    return out


def check_razorpay(s: Settings) -> list[Check]:
    out = []
    if not s.razorpay_configured:
        out.append(Check(FAIL, "Razorpay keys", "not configured: students cannot pay", "Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET"))
    elif s.razorpay_key_id.startswith("rzp_test_"):
        out.append(Check(FAIL, "Razorpay keys", "these are TEST keys: no real money will be collected", "Use the live keys (rzp_live_...) from the Razorpay dashboard"))
    elif s.razorpay_key_id.startswith("rzp_live_"):
        out.append(Check(PASS, "Razorpay keys", "live keys"))
    else:
        out.append(Check(WARN, "Razorpay keys", "key id does not look like rzp_live_... or rzp_test_...", "Check RAZORPAY_KEY_ID"))
    if not s.razorpay_webhook_secret:
        out.append(
            Check(
                FAIL,
                "Razorpay webhook",
                "no webhook secret: a student who pays and closes the tab is never confirmed",
                "Add https://<api>/api/payments/webhook in Razorpay > Webhooks (events payment.captured, order.paid) and set RAZORPAY_WEBHOOK_SECRET",
            )
        )
    else:
        out.append(Check(PASS, "Razorpay webhook", "secret set (also confirm the URL is added in the Razorpay dashboard)"))
    return out


def check_smtp(s: Settings, *, connect: bool = False) -> list[Check]:
    if not s.smtp_configured:
        return [Check(FAIL, "Email (SMTP)", "not configured: emails are only printed to the server log, nobody receives them", "Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD (and SMTP_FROM)")]
    if not connect:
        return [Check(PASS, "Email (SMTP)", f"configured for {s.smtp_host}:{s.smtp_port} (run with --smtp to test the login)")]
    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=10) as server:
            server.starttls()
            server.login(s.smtp_user, s.smtp_password)
        return [Check(PASS, "Email (SMTP)", f"logged in to {s.smtp_host}:{s.smtp_port} as {s.smtp_user}")]
    except Exception as err:  # noqa: BLE001
        return [Check(FAIL, "Email (SMTP)", f"could not log in to {s.smtp_host}:{s.smtp_port}: {type(err).__name__}: {err}", "Check the host, port, user and password")]


def check_uploads(s: Settings) -> list[Check]:
    if s.upload_storage == "database":
        out = [Check(PASS, "Image uploads", "stored in the database, so they survive redeploys and are backed up with it")]
        if s.database_url.startswith("mysql"):
            out.append(
                Check(
                    INFO,
                    "Image uploads (MySQL)",
                    f"images up to {s.max_upload_mb} MB are stored as single rows; MySQL's max_allowed_packet must be larger than that (the default is 4 MB or more)",
                )
            )
        return out
    root = Path(s.upload_dir)
    backend_dir = Path(__file__).resolve().parents[1]
    if not root.is_absolute():
        root = backend_dir / root
    try:
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".write-test"
        probe.write_bytes(b"ok")
        probe.unlink()
    except OSError as err:
        return [Check(FAIL, "Image uploads", f"{root} is not writable: {err}", "Fix permissions or set UPLOAD_DIR")]
    inside_app = backend_dir in root.parents or root == backend_dir
    if inside_app:
        return [
            Check(
                WARN,
                "Image uploads",
                f"stored inside the application folder ({root}); many hosts wipe it on every redeploy",
                "Point UPLOAD_DIR at a persistent disk or volume, and back it up",
            )
        ]
    return [Check(PASS, "Image uploads", f"{root} is writable")]


def check_background(s: Settings) -> list[Check]:
    out = []
    if s.scheduler_enabled:
        out.append(Check(PASS, "Background jobs", "enabled (safe with several workers: jobs are database-locked)"))
    else:
        out.append(Check(WARN, "Background jobs", "disabled in this process: certificates, email retries and reminders only run where SCHEDULER_ENABLED=true", "Make sure exactly one running process has it enabled"))
    if s.reminders_enabled:
        out.append(Check(PASS, "Reminder emails", "enabled"))
    else:
        out.append(Check(INFO, "Reminder emails", "off (REMINDERS_ENABLED=false). Do the admin dry run, then turn them on"))
    return out


# --------------------------------------------------------------------------
# Checks that need the database
# --------------------------------------------------------------------------


def check_database_url(s: Settings) -> list[Check]:
    if not s.database_url:
        return [Check(FAIL, "Database", "DATABASE_URL is empty", "Set DATABASE_URL")]
    if s.database_url.startswith("sqlite"):
        return [
            Check(
                WARN,
                "Database",
                "SQLite is a single file: fine for one small server, but not for several servers, and lost if the disk is ephemeral",
                "Use PostgreSQL or MySQL for production",
            )
        ]
    return [Check(PASS, "Database", s.database_url.split("://", 1)[0] + " server")]


def check_connection(engine: Engine) -> list[Check]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return [Check(PASS, "Database connection", "connected")]
    except Exception as err:  # noqa: BLE001
        return [Check(FAIL, "Database connection", f"{type(err).__name__}: {str(err).splitlines()[0][:150]}", "Check DATABASE_URL and that the database is running")]


def check_migrations(engine: Engine) -> list[Check]:
    from alembic.config import Config
    from alembic.runtime.migration import MigrationContext
    from alembic.script import ScriptDirectory

    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    head = ScriptDirectory.from_config(cfg).get_current_head()
    try:
        with engine.connect() as conn:
            current = MigrationContext.configure(conn).get_current_revision()
            has_tables = bool(conn.execute(text("SELECT 1")).scalar()) and _table_exists(conn, "users")
    except Exception as err:  # noqa: BLE001
        return [Check(FAIL, "Database migrations", f"could not read the migration state: {type(err).__name__}", "Fix the database connection first")]
    if current == head:
        return [Check(PASS, "Database migrations", f"up to date ({head})")]
    if current is None and has_tables:
        return [
            Check(
                FAIL,
                "Database migrations",
                "the tables exist but were never registered with Alembic (created before migrations were introduced)",
                "Back up, confirm the schema matches, run `alembic stamp 0001`, then `alembic upgrade head`",
            )
        ]
    if current is None:
        return [Check(FAIL, "Database migrations", "the database is empty", "Run `alembic upgrade head`")]
    return [Check(FAIL, "Database migrations", f"at {current}, latest is {head}", "Run `alembic upgrade head`")]


def _table_exists(conn, name: str) -> bool:
    from sqlalchemy import inspect

    return inspect(conn).has_table(name)


def check_admin(engine: Engine, s: Settings) -> list[Check]:
    from app.core.security import verify_password
    from app.db.models import User
    from app.db.seed import DEFAULT_ADMIN

    try:
        with Session(engine) as db:
            admins = db.query(User).filter(User.role == "admin").all()
            if not admins:
                if s.admin_password:
                    return [Check(INFO, "Admin account", "none yet; one will be created from ADMIN_PASSWORD at first start")]
                return [Check(FAIL, "Admin account", "no admin exists and ADMIN_PASSWORD is not set: nobody can manage the site", "Set ADMIN_PASSWORD before the first start")]
            default = [a.email for a in admins if a.email == DEFAULT_ADMIN["email"] and verify_password(DEFAULT_ADMIN["password"], a.password_hash)]
            if default:
                return [Check(FAIL, "Admin account", f"{default[0]} still has the published default password", "Change it (Forgot password on the login page) before going live")]
            return [Check(PASS, "Admin account", f"{len(admins)} admin account(s); no default password")]
    except Exception as err:  # noqa: BLE001
        return [Check(WARN, "Admin account", f"could not check: {type(err).__name__}")]


def check_email_queue(engine: Engine, now: datetime | None = None) -> list[Check]:
    from app.db.models import EmailOutbox

    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        with Session(engine) as db:
            failed = db.query(EmailOutbox).filter(EmailOutbox.status == "failed").count()
            stuck = (
                db.query(EmailOutbox)
                .filter(EmailOutbox.status == "pending", EmailOutbox.created_at < now - timedelta(minutes=15))
                .count()
            )
    except Exception as err:  # noqa: BLE001
        return [Check(WARN, "Email queue", f"could not check: {type(err).__name__}")]
    out = []
    if failed:
        out.append(Check(WARN, "Email queue", f"{failed} email(s) failed permanently", "Open Admin > Emails, fix the cause, and Retry"))
    if stuck:
        out.append(Check(WARN, "Email queue", f"{stuck} email(s) waiting more than 15 minutes", "Is the scheduler running (SCHEDULER_ENABLED) and SMTP reachable?"))
    if not out:
        out.append(Check(PASS, "Email queue", "nothing stuck or failed"))
    return out


# --------------------------------------------------------------------------


def run_checks(s: Settings | None = None, *, engine: Engine | None = None, smtp_login: bool = False) -> list[Check]:
    s = s or default_settings
    checks: list[Check] = []
    for fn in (check_environment, check_secret, check_cors, check_cookies, check_rate_limit, check_urls, check_razorpay):
        checks += fn(s)
    checks += check_smtp(s, connect=smtp_login)
    checks += check_uploads(s)
    checks += check_background(s)
    checks += check_database_url(s)
    if engine is not None:
        connection = check_connection(engine)
        checks += connection
        if connection[0].level == PASS:
            migrations = check_migrations(engine)
            checks += migrations
            if migrations[0].level == PASS:
                checks += check_admin(engine, s)
                checks += check_email_queue(engine)
            else:
                checks.append(Check(INFO, "Admin account / email queue", "not checked until the migrations are applied"))
    return checks


def summarize(checks: list[Check]) -> dict:
    counts = {PASS: 0, WARN: 0, FAIL: 0, INFO: 0}
    for c in checks:
        counts[c.level] += 1
    return counts


def _render(checks: list[Check]) -> str:
    color = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
    paint = {PASS: "\033[32m", WARN: "\033[33m", FAIL: "\033[31m", INFO: "\033[36m"}
    lines = []
    for c in checks:
        tag = f"[{c.level}]"
        tag = f"{paint[c.level]}{tag}\033[0m" if color else tag
        lines.append(f"{tag} {c.name}: {c.detail}")
        if c.fix and c.level in (FAIL, WARN):
            lines.append(f"       -> {c.fix}")
    counts = summarize(checks)
    lines.append("")
    verdict = "NOT READY: fix the FAIL items above." if counts[FAIL] else ("Ready, with warnings to review." if counts[WARN] else "Ready.")
    lines.append(f"{counts[PASS]} passed, {counts[WARN]} warnings, {counts[FAIL]} failed. {verdict}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check this server's settings before going live.")
    parser.add_argument("--smtp", action="store_true", help="also test logging in to the mail server (makes a network call)")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args(argv)

    from app.db.base import engine

    checks = run_checks(engine=engine, smtp_login=args.smtp)
    counts = summarize(checks)
    if args.json:
        print(json.dumps({"summary": counts, "ready": counts[FAIL] == 0, "checks": [asdict(c) for c in checks]}, indent=2))
    else:
        print(_render(checks))
    return 1 if counts[FAIL] else 0


if __name__ == "__main__":
    raise SystemExit(main())
