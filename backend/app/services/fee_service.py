"""The certificate fee a student pays is the program's price, which an admin
can edit (Admin > Programs). This module is the single place that turns a
Program into "what do we charge".

Rules:
  * The fee is read from the program when the enrollment is created and again
    when the Razorpay order is created, so the order, the invoice and the
    webhook amount check always agree with each other.
  * Once an enrollment is paid its amount is frozen: later price changes never
    alter an invoice that was already issued.
  * A program with no usable price (legacy rows defaulted to 0) falls back to
    the original flat fee, so nothing becomes free by accident.
  * The gateway currency is always INR (the admin UI is in rupees).
"""

from sqlalchemy.orm import Session

from app.db.models import CERTIFICATE_FEE_INR, Enrollment, Program

CERTIFICATE_CURRENCY = "INR"
MIN_FEE = 1  # Razorpay's minimum order is Rs 1


def effective_fee(program: Program | None) -> float:
    if program is not None and program.price is not None and program.price >= MIN_FEE:
        return round(float(program.price), 2)
    return float(CERTIFICATE_FEE_INR)


def sync_unpaid_fee(db: Session, enrollment: Enrollment) -> None:
    """Brings a not-yet-paid enrollment's displayed amount in line with the
    program's current price. A "pending" enrollment already has a Razorpay
    order at a fixed amount, so it is left alone until the next order."""
    if enrollment.payment_status != "unpaid":
        return
    fee = effective_fee(db.get(Program, enrollment.program_slug))
    if enrollment.amount != fee or enrollment.currency != CERTIFICATE_CURRENCY:
        enrollment.amount = fee
        enrollment.currency = CERTIFICATE_CURRENCY
        db.commit()
        db.refresh(enrollment)


def fee_to_pay(db: Session, enrollment: Enrollment) -> float:
    """What the student would be charged if they paid now, for display.

    Paid: the frozen amount on the invoice. Anything else: the program's current
    fee. This can differ from `enrollment.amount` for a "pending" enrollment,
    whose open Razorpay order is fixed at the old amount; the next order the
    student starts (they always start a fresh one from the dashboard) uses the
    current fee, so that is the number the dashboard must show.
    """
    if enrollment.payment_status == "paid":
        return enrollment.amount
    return effective_fee(db.get(Program, enrollment.program_slug))
