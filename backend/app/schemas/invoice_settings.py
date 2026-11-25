import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, Field, TypeAdapter

_email = TypeAdapter(EmailStr)


def _printable(value: str) -> str:
    """The PDF uses the built-in Helvetica font, which only covers Western
    (cp1252) characters. Anything else would print as empty boxes on a tax
    document, so refuse it up front."""
    value = value.strip()
    try:
        value.encode("cp1252")
    except UnicodeEncodeError:
        raise ValueError("Only English/Western characters can be printed on the invoice.") from None
    return value


def _one_line(value: str) -> str:
    value = _printable(value)
    if "\n" in value or "\r" in value:
        raise ValueError("This must be a single line.")
    return value


def _address(value: str) -> str:
    lines = [l.strip() for l in _printable(value).replace("\r", "").split("\n") if l.strip()]
    if not lines:
        raise ValueError("Enter at least one address line.")
    if len(lines) > 3:
        raise ValueError("Use at most 3 address lines.")
    if any(len(l) > 90 for l in lines):
        raise ValueError("Each address line must be 90 characters or fewer.")
    return "\n".join(lines)


def _gstin(value: str) -> str:
    value = _one_line(value).upper()
    if value and not re.fullmatch(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]", value):
        raise ValueError("That is not a valid 15-character GSTIN (for example 36AAHCV0625N1Z1).")
    return value


def _optional_email(value: str) -> str:
    value = _one_line(value)
    if value:
        _email.validate_python(value)
    return value


def _required_line(value: str) -> str:
    value = _one_line(value)
    if not value:
        raise ValueError("This field is required.")
    return value




class InvoiceSettingsIn(BaseModel):
    company_name: Annotated[str, Field(min_length=1, max_length=120), AfterValidator(_required_line)]
    address: Annotated[str, Field(max_length=300), AfterValidator(_address)]
    gstin: Annotated[str, Field(max_length=15), AfterValidator(_gstin)] = ""
    email: Annotated[str, Field(max_length=255), AfterValidator(_optional_email)] = ""
    phone: Annotated[str, Field(max_length=30), AfterValidator(_one_line)] = ""
    gst_rate: float = Field(ge=0, le=40)
    invoice_prefix: str = Field(pattern=r"^[A-Za-z0-9-]{1,10}$")
    document_title: Annotated[str, Field(min_length=1, max_length=40), AfterValidator(_required_line)]
    item_description: Annotated[str, Field(min_length=1, max_length=80), AfterValidator(_required_line)]
    team_name: Annotated[str, Field(max_length=80), AfterValidator(_one_line)] = ""
    brand_line: Annotated[str, Field(max_length=100), AfterValidator(_one_line)] = ""
    footer_note: Annotated[str, Field(max_length=100), AfterValidator(_one_line)] = ""
