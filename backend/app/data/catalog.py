import json
from pathlib import Path

_DATA_DIR = Path(__file__).parent

with open(_DATA_DIR / "programs.json", encoding="utf-8") as f:
    PROGRAMS: list[dict] = json.load(f)

with open(_DATA_DIR / "testimonials.json", encoding="utf-8") as f:
    TESTIMONIALS: list[dict] = json.load(f)


def get_program_by_slug(slug: str) -> dict | None:
    return next((p for p in PROGRAMS if p["slug"] == slug), None)


def get_categories() -> list[str]:
    seen = []
    for p in PROGRAMS:
        if p["category"] not in seen:
            seen.append(p["category"])
    return ["All", *seen]
