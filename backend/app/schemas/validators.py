import re

# Standard Indian mobile number: 10 digits, first digit 6-9 (TRAI numbering
# plan). Accepts an optional +91 / 91 / 0 prefix and common separators
# (spaces, dashes, parentheses) which are stripped before validation.
_INDIAN_MOBILE_RE = re.compile(r"^[6-9]\d{9}$")


def normalize_and_validate_indian_phone(value: str) -> str:
    """Strips separators/country-code prefixes and validates the remaining
    10 digits look like a real Indian mobile number. Returns the cleaned
    10-digit string (no prefix), or raises ValueError with a clear message."""
    if not value:
        raise ValueError("Phone number is required")

    cleaned = re.sub(r"[\s\-()]", "", value)

    if cleaned.startswith("+91"):
        cleaned = cleaned[3:]
    elif cleaned.startswith("91") and len(cleaned) == 12:
        cleaned = cleaned[2:]
    elif cleaned.startswith("0") and len(cleaned) == 11:
        cleaned = cleaned[1:]

    if not _INDIAN_MOBILE_RE.match(cleaned):
        raise ValueError("Enter a valid 10-digit Indian mobile number")

    return cleaned