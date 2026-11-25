from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import EmailOutbox, User
from app.deps import require_admin
from app.services import outbox_service

router = APIRouter(prefix="/api/admin/emails", tags=["admin-emails"])


def _item(e: EmailOutbox) -> dict:
    return {
        "id": e.id,
        "kind": e.kind,
        "to": e.to_email,
        "subject": e.subject,
        "status": e.status,
        "attempts": e.attempts,
        "lastError": e.last_error,
        "createdAt": e.created_at.isoformat() if e.created_at else None,
        "nextAttemptAt": e.next_attempt_at.isoformat() if e.next_attempt_at and e.status == "pending" else None,
        "sentAt": e.sent_at.isoformat() if e.sent_at else None,
    }


@router.get("")
async def list_emails(
    status: str = Query("all", pattern="^(all|pending|sent|failed)$"),
    limit: int = Query(100, ge=1, le=200),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """The email outbox: counts per status plus the newest messages (the body and
    attachments are never returned, only who it is for and what happened)."""
    query = db.query(EmailOutbox)
    if status != "all":
        query = query.filter(EmailOutbox.status == status)
    rows = query.order_by(EmailOutbox.created_at.desc()).limit(limit).all()
    return {"success": True, "data": {"counts": outbox_service.counts(db), "items": [_item(e) for e in rows]}}


@router.post("/{email_id}/retry")
async def retry_email(
    email_id: str,
    background_tasks: BackgroundTasks,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Puts a failed email back in the queue with a fresh set of attempts and tries it now."""
    row = db.get(EmailOutbox, email_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Email not found")
    if row.status == "sent":
        raise HTTPException(status_code=400, detail="That email was already sent.")
    queued = outbox_service.retry(db, email_id)
    if queued is None:
        raise HTTPException(status_code=409, detail="That email could not be retried right now.")
    outbox_service.send_soon(background_tasks, queued)
    return {"success": True, "message": "Retrying now."}
