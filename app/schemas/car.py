import re
from datetime import datetime
from typing import Annotated

from pydantic import Field, StringConstraints, computed_field, field_validator

from app.core.config import get_settings
from app.models import CarCategory, CarStatus, FuelType, Transmission
from app.schemas.common import ORMModel

Str = Annotated[str, StringConstraints(strip_whitespace=True)]
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _validate_slug(cls: object, v: str | None) -> str | None:
    if v and not SLUG_RE.match(v):
        raise ValueError("Slug may only contain lowercase letters, numbers and single hyphens")
    return v or None


class CarImageOut(ORMModel):
    id: int
    alt_text: str | None
    width: int | None
    height: int | None
    sort_order: int
    is_primary: bool
    storage_key: str = Field(exclude=True)

    @computed_field
    @property
    def url(self) -> str:
        return f"{get_settings().api_prefix}/media/{self.storage_key}"


class CarBase(ORMModel):
    name: Annotated[Str, Field(min_length=2, max_length=120)]
    brand: Annotated[Str, Field(min_length=1, max_length=60)]
    model: Annotated[Str, Field(min_length=1, max_length=60)]
    variant: Annotated[Str, Field(max_length=60)] | None = None
    year: int = Field(ge=2000, le=2100)
    category: CarCategory
    transmission: Transmission
    fuel_type: FuelType
    seats: int = Field(ge=2, le=12)
    luggage_bags: int | None = Field(default=None, ge=0, le=10)
    mileage_kmpl: float | None = Field(default=None, ge=0, le=100)
    color: Annotated[Str, Field(max_length=40)] | None = None
    daily_price: int = Field(ge=0, le=1_000_000)
    weekly_price: int | None = Field(default=None, ge=0, le=10_000_000)
    security_deposit: int | None = Field(default=None, ge=0, le=10_000_000)
    km_limit_per_day: int | None = Field(default=None, ge=0, le=5000)
    extra_km_charge: int | None = Field(default=None, ge=0, le=1000)
    fuel_policy: Annotated[Str, Field(max_length=200)] | None = None
    short_description: Annotated[Str, Field(max_length=240)] | None = None
    description: Annotated[Str, Field(max_length=5000)] | None = None
    features: list[Annotated[Str, Field(min_length=1, max_length=60)]] = Field(default_factory=list, max_length=30)
    additional_terms: Annotated[Str, Field(max_length=5000)] | None = None
    location: Annotated[Str, Field(min_length=2, max_length=120)] = "Greater Noida"
    status: CarStatus = CarStatus.AVAILABLE


class CarPublic(CarBase):
    id: int
    slug: str
    is_featured: bool
    images: list[CarImageOut]


class CarCreate(CarBase):
    slug: Annotated[Str, Field(max_length=140)] | None = None
    is_published: bool = False
    is_featured: bool = False
    sort_order: int = 0

    _slug = field_validator("slug")(_validate_slug)


class CarUpdate(ORMModel):
    slug: Annotated[Str, Field(max_length=140)] | None = None
    name: Annotated[Str, Field(min_length=2, max_length=120)] | None = None
    brand: Annotated[Str, Field(min_length=1, max_length=60)] | None = None
    model: Annotated[Str, Field(min_length=1, max_length=60)] | None = None
    variant: Annotated[Str, Field(max_length=60)] | None = None
    year: int | None = Field(default=None, ge=2000, le=2100)
    category: CarCategory | None = None
    transmission: Transmission | None = None
    fuel_type: FuelType | None = None
    seats: int | None = Field(default=None, ge=2, le=12)
    luggage_bags: int | None = Field(default=None, ge=0, le=10)
    mileage_kmpl: float | None = Field(default=None, ge=0, le=100)
    color: Annotated[Str, Field(max_length=40)] | None = None
    daily_price: int | None = Field(default=None, ge=0, le=1_000_000)
    weekly_price: int | None = Field(default=None, ge=0, le=10_000_000)
    security_deposit: int | None = Field(default=None, ge=0, le=10_000_000)
    km_limit_per_day: int | None = Field(default=None, ge=0, le=5000)
    extra_km_charge: int | None = Field(default=None, ge=0, le=1000)
    fuel_policy: Annotated[Str, Field(max_length=200)] | None = None
    short_description: Annotated[Str, Field(max_length=240)] | None = None
    description: Annotated[Str, Field(max_length=5000)] | None = None
    features: list[Annotated[Str, Field(min_length=1, max_length=60)]] | None = Field(default=None, max_length=30)
    additional_terms: Annotated[Str, Field(max_length=5000)] | None = None
    location: Annotated[Str, Field(min_length=2, max_length=120)] | None = None
    status: CarStatus | None = None
    is_published: bool | None = None
    is_featured: bool | None = None
    sort_order: int | None = None

    _slug = field_validator("slug")(_validate_slug)


class CarAdmin(CarPublic):
    is_published: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime
    enquiry_count: int = 0


class CarImageUpdate(ORMModel):
    alt_text: Annotated[Str, Field(max_length=200)] | None = None
    sort_order: int | None = None
    is_primary: bool | None = None
