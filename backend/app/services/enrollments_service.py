from app.db.models import Enrollment


def enrollment_to_dict(e: Enrollment) -> dict:
    task_submitted = bool(e.task_submitted_at)
    return {
        "id": e.id,
        "programSlug": e.program_slug,
        "programTitle": e.program_title,
        "name": e.name,
        "email": e.email,
        "phone": e.phone,
        "enrolledAt": e.enrolled_at.isoformat() if e.enrolled_at else None,
        "githubLink": e.github_link,
        "linkedinLink": e.linkedin_link,
        "taskSubmitted": task_submitted,
        "taskSubmittedAt": e.task_submitted_at.isoformat() if e.task_submitted_at else None,
        "amount": e.amount,
        "currency": e.currency,
        "paymentStatus": e.payment_status,
        "paidAt": e.paid_at.isoformat() if e.paid_at else None,
        "certificateId": e.certificate_id,
        "certificateUnlocked": e.certificate_unlocked,
        # A simple linear stage indicator the frontend stepper can key off of
        "stage": _compute_stage(task_submitted, e.payment_status, e.certificate_unlocked),
    }


def _compute_stage(task_submitted: bool, payment_status: str, certificate_unlocked: bool) -> str:
    if certificate_unlocked:
        return "certificate"
    if payment_status == "paid":
        return "certificate"
    if task_submitted:
        return "payment"
    return "task"


def admin_enrollment_to_dict(e: Enrollment) -> dict:
    base = enrollment_to_dict(e)
    return base
