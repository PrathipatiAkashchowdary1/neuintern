from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import verify_unsubscribe_token
from app.db.base import get_db
from app.db.models import User

router = APIRouter(prefix="/api/unsubscribe", tags=["unsubscribe"])

# These are POST/DELETE on purpose. Mail scanners and link previewers follow
# GET links automatically, which would silently unsubscribe people. The link
# in the email opens a frontend page that asks for a click and then POSTs here;
# mail clients that support RFC 8058 one-click unsubscribe POST here directly.


def _user_for_token(token: str, db: Session) -> User | None:
    user_id = verify_unsubscribe_token(token)
    if not user_id:
        raise HTTPException(status_code=400, detail="This unsubscribe link is invalid.")
    return db.get(User, user_id)  # None for a deleted account: nothing left to change


@router.post("/{token}")
async def unsubscribe(token: str, db: Session = Depends(get_db)):
    user = _user_for_token(token, db)
    if user and not user.reminders_opt_out:
        user.reminders_opt_out = True
        db.commit()
    return {"success": True, "message": "You've been unsubscribed from reminder emails."}


@router.delete("/{token}")
async def resubscribe(token: str, db: Session = Depends(get_db)):
    """Undo for an accidental click."""
    user = _user_for_token(token, db)
    if user and user.reminders_opt_out:
        user.reminders_opt_out = False
        db.commit()
    return {"success": True, "message": "Reminder emails are back on."}
