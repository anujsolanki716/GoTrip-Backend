import re
from datetime import date, datetime, timedelta
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator, model_validator

from app.models import CustomerType, EnquiryStatus, PreferredContact
from app.schemas.common import ORMModel

Str = Annotated[str, StringConstraints(strip_whitespace=True)]
IST = ZoneInfo("Asia/Kolkata")
NAME_RE = re.compile(r"^[^\W\d_]+(?:[ .'\-]+[^\W\d_]+)*\.?$")


def today_ist() -> date:
    return datetime.now(IST).date()


def normalise_indian_mobile(value: str) -> str:
    """Accept common Indian formats and return +91XXXXXXXXXX."""
    digits = re.sub(r"[\s\-()]", "", value)
    if digits.startswith("+91"):
        digits = digits[3:]
    elif digits.startswith("0091"):
        digits = digits[4:]
    elif len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if not re.fullmatch(r"[6-9]\d{9}", digits):
        raise ValueError("Enter a valid 10-digit Indian mobile number")
    return f"+91{digits}"


class EnquiryCreate(BaseModel):
    car_slug: Annotated[Str, Field(max_length=140)] | None = None
    full_name: Annotated[Str, Field(min_length=2, max_length=100)]
    phone: Annotated[Str, Field(max_length=20)]
    email: EmailStr | None = None
    customer_type: CustomerType
    preferred_contact: PreferredContact = PreferredContact.WHATSAPP
    pickup_date: date | None = None
    return_date: date | None = None
    pickup_area: Annotated[Str, Field(max_length=120)] | None = None
    message: Annotated[Str, Field(max_length=2000)] | None = None
    consent: bool
    source: Annotated[Str, Field(max_length=40)] | None = None
    website: str | None = Field(default=None, max_length=200)

    @field_validator("full_name")
    @classmethod
    def _name(cls, v: str) -> str:
        if not NAME_RE.match(v):
            raise ValueError("Please enter your name using letters only")
        return v

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        return normalise_indian_mobile(v)

    @field_validator("email", mode="before")
    @classmethod
    def _blank_email(cls, v: object) -> object:
        return None if isinstance(v, str) and not v.strip() else v

    @field_validator("consent")
    @classmethod
    def _consent(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Please agree to be contacted about your enquiry")
        return v

    @model_validator(mode="after")
    def _dates(self) -> "EnquiryCreate":
        today = today_ist()
        if self.pickup_date and self.pickup_date < today:
            raise ValueError("Pickup date cannot be in the past")
        if self.pickup_date and self.pickup_date > today + timedelta(days=365):
            raise ValueError("Pickup date must be within the next 12 months")
        if self.return_date and self.pickup_date and self.return_date < self.pickup_date:
            raise ValueError("Return date must be on or after the pickup date")
        if self.return_date and not self.pickup_date:
            raise ValueError("Please choose a pickup date")
        if self.preferred_contact == PreferredContact.EMAIL and not self.email:
            raise ValueError("Please provide an email address if you prefer to be contacted by email")
        return self


class EnquiryReceipt(BaseModel):
    reference: str
    status: Literal["received"] = "received"
    is_booking: Literal[False] = False
    message: str


class EnquiryCarSummary(ORMModel):
    id: int
    slug: str
    name: str


class EnquiryAdmin(ORMModel):
    id: int
    reference: str
    car_id: int | None
    car_name_snapshot: str | None
    car: EnquiryCarSummary | None
    full_name: str
    phone: str
    email: str | None
    customer_type: CustomerType
    preferred_contact: PreferredContact
    pickup_date: date | None
    return_date: date | None
    pickup_area: str | None
    message: str | None
    status: EnquiryStatus
    admin_notes: str | None
    contacted_at: datetime | None
    converted_at: datetime | None
    source: str | None
    created_at: datetime
    updated_at: datetime


class EnquiryUpdate(BaseModel):
    status: EnquiryStatus | None = None
    admin_notes: Annotated[Str, Field(max_length=5000)] | None = None
