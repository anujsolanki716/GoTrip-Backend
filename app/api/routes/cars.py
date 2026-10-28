import math
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, or_, select

from app.api.deps import DbSession
from app.models import Car, CarCategory, CarStatus, FuelType, Transmission
from app.schemas.car import CarPublic
from app.schemas.common import Page

router = APIRouter(tags=["cars"])

SORTS = {
    "recommended": (Car.is_featured.desc(), Car.sort_order, Car.daily_price),
    "price_asc": (Car.daily_price, Car.id),
    "price_desc": (Car.daily_price.desc(), Car.id),
    "newest": (Car.year.desc(), Car.id.desc()),
    "seats_desc": (Car.seats.desc(), Car.daily_price),
}


def _like(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


@router.get("/cars", response_model=Page[CarPublic])
def list_cars(
    db: DbSession,
    q: Annotated[str | None, Query(max_length=80)] = None,
    category: list[CarCategory] = Query(default_factory=list),
    transmission: Transmission | None = None,
    fuel_type: list[FuelType] = Query(default_factory=list),
    min_seats: Annotated[int | None, Query(ge=2, le=12)] = None,
    max_price: Annotated[int | None, Query(ge=0)] = None,
    featured: bool | None = None,
    available_only: bool = False,
    sort: Literal[
        "recommended", "price_asc", "price_desc", "newest", "seats_desc"
    ] = "recommended",
    page: Annotated[int, Query(ge=1, le=1000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=48)] = 12,
) -> Page[CarPublic]:
    conditions = [Car.is_published.is_(True)]
    if q and q.strip():
        pattern = _like(q.strip())
        conditions.append(
            or_(
                Car.name.ilike(pattern, escape="\\"),
                Car.brand.ilike(pattern, escape="\\"),
                Car.model.ilike(pattern, escape="\\"),
            )
        )
    if category:
        conditions.append(Car.category.in_(category))
    if transmission:
        conditions.append(Car.transmission == transmission)
    if fuel_type:
        conditions.append(Car.fuel_type.in_(fuel_type))
    if min_seats:
        conditions.append(Car.seats >= min_seats)
    if max_price is not None:
        conditions.append(Car.daily_price <= max_price)
    if featured is not None:
        conditions.append(Car.is_featured.is_(featured))
    if available_only:
        conditions.append(Car.status.in_([CarStatus.AVAILABLE, CarStatus.ON_REQUEST]))

    total = db.scalar(select(func.count()).select_from(Car).where(*conditions)) or 0
    cars = db.scalars(
        select(Car)
        .where(*conditions)
        .order_by(*SORTS[sort])
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(
        items=[CarPublic.model_validate(c) for c in cars],
        total=total,
        page=page,
        size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


@router.get("/cars/{slug}", response_model=CarPublic)
def get_car(slug: str, db: DbSession) -> Car:
    car = db.scalar(select(Car).where(Car.slug == slug, Car.is_published.is_(True)))
    if car is None:
        raise HTTPException(404, "Car not found")
    return car


@router.get("/cars/{slug}/similar", response_model=list[CarPublic])
def similar_cars(
    slug: str, db: DbSession, limit: Annotated[int, Query(ge=1, le=8)] = 3
) -> list[Car]:
    car = db.scalar(select(Car).where(Car.slug == slug, Car.is_published.is_(True)))
    if car is None:
        raise HTTPException(404, "Car not found")
    rows = db.scalars(
        select(Car)
        .where(Car.is_published.is_(True), Car.id != car.id)
        .order_by(
            (Car.category == car.category).desc(),
            func.abs(Car.daily_price - car.daily_price),
        )
        .limit(limit)
    ).all()
    return list(rows)
