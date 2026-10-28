import enum

from sqlalchemy import JSON, Boolean, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


def _enum(cls: type[enum.Enum], length: int = 24) -> Enum:
    return Enum(cls, native_enum=False, length=length, values_callable=lambda e: [m.value for m in e])


class StrEnum(str, enum.Enum):
    """String enum compatible with Python 3.10."""


class CarCategory(StrEnum):
    HATCHBACK = "hatchback"
    SEDAN = "sedan"
    COMPACT_SUV = "compact_suv"
    SUV = "suv"
    MUV = "muv"
    PREMIUM = "premium"


class Transmission(StrEnum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"


class FuelType(StrEnum):
    PETROL = "petrol"
    DIESEL = "diesel"
    CNG = "cng"
    ELECTRIC = "electric"
    HYBRID = "hybrid"


class CarStatus(StrEnum):
    """Indicative availability shown to customers. Never a reservation."""

    AVAILABLE = "available"
    ON_REQUEST = "on_request"
    UNDER_MAINTENANCE = "under_maintenance"
    UNAVAILABLE = "unavailable"


class Car(TimestampMixin, Base):
    __tablename__ = "cars"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    brand: Mapped[str] = mapped_column(String(60))
    model: Mapped[str] = mapped_column(String(60))
    variant: Mapped[str | None] = mapped_column(String(60))
    year: Mapped[int] = mapped_column(Integer)
    category: Mapped[CarCategory] = mapped_column(_enum(CarCategory), index=True)
    transmission: Mapped[Transmission] = mapped_column(_enum(Transmission), index=True)
    fuel_type: Mapped[FuelType] = mapped_column(_enum(FuelType), index=True)
    seats: Mapped[int] = mapped_column(Integer)
    luggage_bags: Mapped[int | None] = mapped_column(Integer)
    mileage_kmpl: Mapped[float | None] = mapped_column(Numeric(5, 1))
    color: Mapped[str | None] = mapped_column(String(40))

    daily_price: Mapped[int] = mapped_column(Integer)
    weekly_price: Mapped[int | None] = mapped_column(Integer)
    security_deposit: Mapped[int | None] = mapped_column(Integer)
    km_limit_per_day: Mapped[int | None] = mapped_column(Integer)
    extra_km_charge: Mapped[int | None] = mapped_column(Integer)
    fuel_policy: Mapped[str | None] = mapped_column(String(200))

    short_description: Mapped[str | None] = mapped_column(String(240))
    description: Mapped[str | None] = mapped_column(Text)
    features: Mapped[list[str]] = mapped_column(JSON, default=list)
    additional_terms: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str] = mapped_column(String(120), default="Greater Noida")

    status: Mapped[CarStatus] = mapped_column(_enum(CarStatus), default=CarStatus.AVAILABLE)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    images: Mapped[list["CarImage"]] = relationship(
        back_populates="car",
        cascade="all, delete-orphan",
        order_by="(CarImage.is_primary.desc(), CarImage.sort_order, CarImage.id)",
        lazy="selectin",
    )


class CarImage(TimestampMixin, Base):
    __tablename__ = "car_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    car_id: Mapped[int] = mapped_column(ForeignKey("cars.id", ondelete="CASCADE"), index=True)
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    alt_text: Mapped[str | None] = mapped_column(String(200))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

    car: Mapped[Car] = relationship(back_populates="images")
