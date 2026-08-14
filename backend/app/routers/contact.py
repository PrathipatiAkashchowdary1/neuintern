from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.limiter import limiter
from app.db.base import get_db
from app.db.models import ContactSubmission, NewsletterSubscriber
from app.schemas.contact import ContactCreate, NewsletterCreate
from app.services.email_service import send_email

router = APIRouter(prefix="/api/contact", tags=["contact"])


@router.post("", status_code=201)
@limiter.limit("10/hour")
async def submit_contact(request: Request, payload: ContactCreate, db: Session = Depends(get_db)):
    entry = ContactSubmission(
        name=payload.name, email=payload.email, subject=payload.subject, message=payload.message
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    # Notify the company inbox with the full message, reply-to the sender's
    # own address so replying from the notification works naturally.
    send_email(
        to=settings.contact_notify_email,
        subject=f"New contact form message: {payload.subject}",
        body=(
            f"New message from the NeuIntern contact form.\n\n"
            f"Name: {payload.name}\n"
            f"Email: {payload.email}\n"
            f"Subject: {payload.subject}\n\n"
            f"Message:\n{payload.message}\n\n"
            f"---\nSubmission ID: {entry.id}"
        ),
    )

    # Confirmation email back to whoever submitted the form.
    send_email(
        to=payload.email,
        subject="We've received your message — NeuIntern",
        body=(
            f"Hi {payload.name},\n\n"
            f"Thanks for reaching out to NeuIntern. We've received your message about "
            f"\"{payload.subject}\" and will get back to you within 24 hours.\n\n"
            f"For your records, here's what you sent us:\n\n{payload.message}\n\n"
            f"— The NeuIntern Team"
        ),
    )

    return {
        "success": True,
        "message": "Thanks! We will get back to you within 24 hours.",
        "data": {"id": entry.id},
    }


@router.post("/newsletter", status_code=201)
@limiter.limit("10/hour")
async def subscribe_newsletter(request: Request, payload: NewsletterCreate, db: Session = Depends(get_db)):
    existing = db.query(NewsletterSubscriber).filter(NewsletterSubscriber.email == payload.email).first()
    if not existing:
        db.add(NewsletterSubscriber(email=payload.email))
        db.commit()

    return {"success": True, "message": "Subscribed — welcome aboard."}