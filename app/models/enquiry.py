import enum
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.car import Car


def _enum(cls: type[enum.Enum]) -> Enum:
    return Enum(
        cls,
        native_enum=False,
        length=32,
        values_callable=lambda e: [m.value for m in e],
    )


class StrEnum(str, enum.Enum):
    """String enum compatible with Python 3.10."""


class CustomerType(StrEnum):
    STUDENT = "student"
    CORPORATE = "corporate"
    RESIDENT = "resident"
    TRAVELLER = "traveller"
    OTHER = "other"


class PreferredContact(StrEnum):
    WHATSAPP = "whatsapp"
    PHONE = "phone"
    EMAIL = "email"


class EnquiryStatus(StrEnum):
    NEW = "new"
    CONTACTED = "contacted"
    IN_DISCUSSION = "in_discussion"
    CONVERTED_OFFLINE = "converted_offline"
    NOT_CONVERTED = "not_converted"
    SPAM = "spam"


class Enquiry(TimestampMixin, Base):
    """A customer enquiry. An enquiry is NOT a booking or reservation."""

    __tablename__ = "enquiries"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    car_id: Mapped[int | None] = mapped_column(
        ForeignKey("cars.id", ondelete="SET NULL"), index=True
    )
    car_name_snapshot: Mapped[str | None] = mapped_column(String(120))

    full_name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(20), index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    customer_type: Mapped[CustomerType] = mapped_column(_enum(CustomerType))
    preferred_contact: Mapped[PreferredContact] = mapped_column(_enum(PreferredContact))
    pickup_date: Mapped[date | None] = mapped_column(Date)
    return_date: Mapped[date | None] = mapped_column(Date)
    pickup_area: Mapped[str | None] = mapped_column(String(120))
    message: Mapped[str | None] = mapped_column(Text)
    consent: Mapped[bool] = mapped_column(Boolean, default=False)

    status: Mapped[EnquiryStatus] = mapped_column(
        _enum(EnquiryStatus), default=EnquiryStatus.NEW, index=True
    )
    admin_notes: Mapped[str | None] = mapped_column(Text)
    contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    converted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    source: Mapped[str | None] = mapped_column(String(40))
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(255))

    car: Mapped[Car | None] = relationship(lazy="joined")
