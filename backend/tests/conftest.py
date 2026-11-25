"""Shared test setup.

The DATABASE_URL (and every other setting that could reach a real service) is
pinned BEFORE the app is imported, because app.db.base builds its engine at
import time. Environment variables beat the developer's .env file, so these
tests can never touch a real database or SMTP server.
"""

import hashlib
import hmac
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

_TMP_DIR = tempfile.mkdtemp(prefix="neuintern-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_TMP_DIR, "test.db")
os.environ["JWT_SECRET"] = "test-jwt-secret"
os.environ["UPLOAD_DIR"] = os.path.join(_TMP_DIR, "uploads")  # admin image uploads go to a throwaway dir
os.environ["API_PUBLIC_URL"] = ""
for _name in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "RAZORPAY_WEBHOOK_SECRET"):
    os.environ[_name] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.limiter import limiter  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.db.base import Base, SessionLocal, engine  # noqa: E402
from app.db.models import Enrollment, User  # noqa: E402
from app.main import app  # noqa: E402

KEY_SECRET = "test-key-secret"
WEBHOOK_SECRET = "test-webhook-secret"
FEE_PAISE = 15000  # CERTIFICATE_FEE_INR (150) in paise


def naive_utc_now() -> datetime:
    # The DB layer stores naive UTC datetimes.
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture(autouse=True)
def _fresh_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture(autouse=True)
def _razorpay_settings(monkeypatch):
    monkeypatch.setattr(settings, "razorpay_key_id", "rzp_test_key")
    monkeypatch.setattr(settings, "razorpay_key_secret", KEY_SECRET)
    monkeypatch.setattr(settings, "razorpay_webhook_secret", WEBHOOK_SECRET)
    # Rate limits are per-IP and in-memory; they would make tests order-dependent.
    monkeypatch.setattr(limiter, "enabled", False)


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client():
    # Not used as a context manager on purpose: that would run the app's
    # startup hook (seeding + the hourly scheduler).
    return TestClient(app)


@pytest.fixture
def outbox(monkeypatch):
    """Captures every email-with-attachments instead of sending it. PDF
    generation still runs for real, so a broken template fails the test."""
    sent: list[SimpleNamespace] = []

    def fake_send(to, subject, body, attachments):
        sent.append(SimpleNamespace(to=to, subject=subject, body=body, attachments=attachments))

    for target in (
        "app.services.payment_service.send_email_with_attachments",
        "app.services.certificate_service.send_email_with_attachments",
        "app.routers.enrollments.send_email_with_attachments",
    ):
        monkeypatch.setattr(target, fake_send)
    return sent


@pytest.fixture
def fake_razorpay(monkeypatch):
    """Replaces the Razorpay SDK client so order creation never goes online."""
    created: list[dict] = []

    class _Orders:
        def create(self, data):
            created.append(data)
            return {"id": f"order_test_{len(created)}", "amount": data["amount"], "currency": data["currency"]}

    monkeypatch.setattr("app.routers.enrollments.get_client", lambda: SimpleNamespace(order=_Orders()))
    return created


@pytest.fixture
def make_user(db):
    counter = {"n": 0}

    def _make(role: str = "student", email: str | None = None) -> User:
        counter["n"] += 1
        user = User(
            full_name=f"Test User {counter['n']}",
            email=email or f"user{counter['n']}@example.com",
            phone="9999999999",
            degree="B.Tech",
            branch="CSE",
            current_year="3",
            password_hash="not-a-real-hash",
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return _make


@pytest.fixture
def auth():
    def _auth(user: User) -> dict:
        return {"Authorization": "Bearer " + create_access_token({"id": user.id})}

    return _auth


@pytest.fixture
def make_enrollment(db):
    def _make(user: User, *, days_ago: float = 1, **overrides) -> Enrollment:
        fields = dict(
            user_id=user.id,
            program_slug="react-development",
            program_title="React Development",
            name=user.full_name,
            email=user.email,
            phone=user.phone,
            amount=150,
            currency="INR",
            enrolled_at=naive_utc_now() - timedelta(days=days_ago),
            payment_status="unpaid",
        )
        fields.update(overrides)
        enrollment = Enrollment(**fields)
        db.add(enrollment)
        db.commit()
        db.refresh(enrollment)
        return enrollment

    return _make


def checkout_signature(order_id: str, payment_id: str, secret: str = KEY_SECRET) -> str:
    """What Razorpay's checkout hands the browser after a successful payment."""
    return hmac.new(secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()


def verify_body(enrollment_id: str, order_id: str, payment_id: str, signature: str | None = None) -> dict:
    return {
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": signature or checkout_signature(order_id, payment_id),
        "enrollmentId": enrollment_id,
    }


def webhook_event(order_id: str, payment_id: str, *, amount: int = FEE_PAISE, currency: str = "INR", event: str = "payment.captured") -> dict:
    return {
        "event": event,
        "payload": {"payment": {"entity": {"id": payment_id, "order_id": order_id, "amount": amount, "currency": currency}}},
    }


def post_webhook(client: TestClient, event: dict | bytes, secret: str | None = WEBHOOK_SECRET, signature: str | None = None):
    raw = event if isinstance(event, bytes) else json.dumps(event).encode()
    if signature is None:
        signature = hmac.new((secret or "").encode(), raw, hashlib.sha256).hexdigest()
    return client.post("/api/payments/webhook", content=raw, headers={"X-Razorpay-Signature": signature})
