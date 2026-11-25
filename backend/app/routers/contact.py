from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.limiter import limiter
from app.db.base import get_db
from app.db.models import ContactSubmission, NewsletterSubscriber
from app.schemas.contact import ContactCreate, NewsletterCreate
from app.services.outbox_service import add as queue_email, send_soon

router = APIRouter(prefix="/api/contact", tags=["contact"])


@router.post("", status_code=201)
@limiter.limit("10/hour")
async def submit_contact(
    request: Request, payload: ContactCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    entry = ContactSubmission(
        name=payload.name, email=payload.email, subject=payload.subject, message=payload.message
    )
    db.add(entry)
    db.flush()  # assigns the id

    # Both emails are saved with the message in one transaction, then sent right after
    # the response; if SMTP is down they are retried instead of lost.
    notify_subject = f"New contact form message: {payload.subject}"
    notify_body = (
        f"New message from the NeuIntern contact form.\n\n"
        f"Name: {payload.name}\n"
        f"Email: {payload.email}\n"
        f"Subject: {payload.subject}\n\n"
        f"Message:\n{payload.message}\n\n"
        f"---\nSubmission ID: {entry.id}"
    )
    confirm_subject = "We've received your message — NeuIntern"
    confirm_body = (
        f"Hi {payload.name},\n\n"
        f"Thanks for reaching out to NeuIntern. We've received your message about "
        f"\"{payload.subject}\" and will get back to you within 24 hours.\n\n"
        f"For your records, here's what you sent us:\n\n{payload.message}\n\n"
        f"— The NeuIntern Team"
    )
    notify = queue_email(
        db, "contact", to=settings.contact_notify_email, subject=notify_subject,
        payload={"to": settings.contact_notify_email, "subject": notify_subject, "body": notify_body},
        dedupe_key=f"contact-notify:{entry.id}",
    )
    confirm = queue_email(
        db, "contact", to=payload.email, subject=confirm_subject,
        payload={"to": payload.email, "subject": confirm_subject, "body": confirm_body},
        dedupe_key=f"contact-confirm:{entry.id}",
    )
    entry_id, notify_id, confirm_id = entry.id, notify.id, confirm.id
    db.commit()

    send_soon(background_tasks, notify_id, confirm_id)

    return {
        "success": True,
        "message": "Thanks! We will get back to you within 24 hours.",
        "data": {"id": entry_id},
    }


@router.post("/newsletter", status_code=201)
@limiter.limit("10/hour")
async def subscribe_newsletter(request: Request, payload: NewsletterCreate, db: Session = Depends(get_db)):
    existing = db.query(NewsletterSubscriber).filter(NewsletterSubscriber.email == payload.email).first()
    if not existing:
        db.add(NewsletterSubscriber(email=payload.email))
        db.commit()

    return {"success": True, "message": "Subscribed — welcome aboard."}