import json

from app.db.models import Program


def program_to_dict(p: Program) -> dict:
    return {
        "slug": p.slug,
        "title": p.title,
        "category": p.category,
        "tagline": p.tagline,
        "image": p.image,
        "duration": p.duration,
        "price": p.price,
        "currency": p.currency,
        "mode": p.mode,
        "certificate": p.certificate,
        "liveProjects": p.live_projects,
        "skills": json.loads(p.skills_json or "[]"),
        "tools": json.loads(p.tools_json or "[]"),
        "outcomes": json.loads(p.outcomes_json or "[]"),
        "eligibility": p.eligibility,
        "curriculum": json.loads(p.curriculum_json or "[]"),
        "isActive": p.is_active,
    }


def apply_program_fields(program: Program, data: dict) -> None:
    """Applies a partial dict (from an admin create/update request) onto a
    Program row, JSON-encoding the list/object fields."""
    simple_fields = [
        "slug", "title", "category", "tagline", "image", "duration",
        "price", "currency", "mode", "certificate", "is_active",
    ]
    for field in simple_fields:
        if field in data and data[field] is not None:
            setattr(program, field, data[field])

    if "liveProjects" in data and data["liveProjects"] is not None:
        program.live_projects = data["liveProjects"]
    if "skills" in data and data["skills"] is not None:
        program.skills_json = json.dumps(data["skills"])
    if "tools" in data and data["tools"] is not None:
        program.tools_json = json.dumps(data["tools"])
    if "outcomes" in data and data["outcomes"] is not None:
        program.outcomes_json = json.dumps(data["outcomes"])
    if "eligibility" in data and data["eligibility"] is not None:
        program.eligibility = data["eligibility"]
    if "curriculum" in data and data["curriculum"] is not None:
        program.curriculum_json = json.dumps(data["curriculum"])
