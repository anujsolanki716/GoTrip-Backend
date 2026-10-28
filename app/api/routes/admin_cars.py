import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select

from app.api.deps import CurrentAdmin, DbSession, FullAdmin
from app.core.config import get_settings
from app.models import Car, CarImage, Enquiry
from app.schemas.car import CarAdmin, CarCreate, CarImageOut, CarImageUpdate, CarUpdate
from app.services import audit
from app.services.images import InvalidImageError, process_car_image
from app.services.slugs import unique_car_slug
from app.services.storage import get_storage

router = APIRouter(prefix="/admin/cars", tags=["admin-cars"])


def _get_car(db: DbSession, car_id: int) -> Car:
    car = db.get(Car, car_id)
    if car is None:
        raise HTTPException(404, "Car not found")
    return car


def _to_admin(db: DbSession, car: Car, count: int | None = None) -> CarAdmin:
    if count is None:
        count = db.scalar(select(func.count(Enquiry.id)).where(Enquiry.car_id == car.id)) or 0
    out = CarAdmin.model_validate(car)
    out.enquiry_count = count
    return out


@router.get("", response_model=list[CarAdmin])
def list_cars(
    admin: CurrentAdmin,
    db: DbSession,
    q: Annotated[str | None, Query(max_length=80)] = None,
    published: bool | None = None,
) -> list[CarAdmin]:
    counts = select(Enquiry.car_id, func.count(Enquiry.id).label("n")).group_by(Enquiry.car_id).subquery()
    stmt = select(Car, func.coalesce(counts.c.n, 0)).outerjoin(counts, counts.c.car_id == Car.id)
    if q:
        stmt = stmt.where(or_(Car.name.ilike(f"%{q}%"), Car.brand.ilike(f"%{q}%")))
    if published is not None:
        stmt = stmt.where(Car.is_published.is_(published))
    rows = db.execute(stmt.order_by(Car.sort_order, Car.name)).all()
    return [_to_admin(db, car, n) for car, n in rows]


@router.post("", response_model=CarAdmin, status_code=status.HTTP_201_CREATED)
def create_car(payload: CarCreate, admin: CurrentAdmin, db: DbSession) -> CarAdmin:
    data = payload.model_dump()
    slug = data.pop("slug") or f"{payload.brand} {payload.model} {payload.variant or ''} {payload.year}"
    car = Car(**data, slug=unique_car_slug(db, slug))
    db.add(car)
    db.flush()
    audit.record(db, admin, "car.created", "car", car.id, name=car.name)
    db.commit()
    return _to_admin(db, car, 0)


@router.get("/{car_id}", response_model=CarAdmin)
def get_car(car_id: int, admin: CurrentAdmin, db: DbSession) -> CarAdmin:
    return _to_admin(db, _get_car(db, car_id))


@router.patch("/{car_id}", response_model=CarAdmin)
def update_car(car_id: int, payload: CarUpdate, admin: CurrentAdmin, db: DbSession) -> CarAdmin:
    car = _get_car(db, car_id)
    changes = payload.model_dump(exclude_unset=True)
    required = {
        "name",
        "brand",
        "model",
        "year",
        "category",
        "transmission",
        "fuel_type",
        "seats",
        "daily_price",
        "location",
        "status",
        "is_published",
        "is_featured",
        "sort_order",
        "features",
    }
    for field in required & changes.keys():
        if changes[field] is None:
            raise HTTPException(422, f"{field} cannot be empty")
    if "slug" in changes:
        slug = changes.pop("slug")
        if slug and slug != car.slug:
            if db.scalar(select(Car.id).where(Car.slug == slug, Car.id != car.id)):
                raise HTTPException(409, "Another car already uses this slug")
            car.slug = slug
    for field, value in changes.items():
        setattr(car, field, value)
    audit.record(db, admin, "car.updated", "car", car.id, fields=sorted(changes))
    db.commit()
    db.refresh(car)
    return _to_admin(db, car)


@router.delete("/{car_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_car(car_id: int, admin: FullAdmin, db: DbSession) -> None:
    car = _get_car(db, car_id)
    keys = [img.storage_key for img in car.images]
    audit.record(db, admin, "car.deleted", "car", car.id, name=car.name)
    db.delete(car)
    db.commit()
    storage = get_storage()
    for key in keys:
        storage.delete(key)


@router.post("/{car_id}/images", response_model=CarImageOut, status_code=status.HTTP_201_CREATED)
async def upload_image(
    car_id: int,
    admin: CurrentAdmin,
    db: DbSession,
    file: Annotated[UploadFile, File()],
    alt_text: Annotated[str | None, Form(max_length=200)] = None,
) -> CarImage:
    settings = get_settings()
    car = _get_car(db, car_id)
    if len(car.images) >= settings.max_images_per_car:
        raise HTTPException(400, f"A car can have at most {settings.max_images_per_car} images")
    limit = settings.max_upload_mb * 1024 * 1024
    raw = await file.read(limit + 1)
    if len(raw) > limit:
        raise HTTPException(413, f"Image must be smaller than {settings.max_upload_mb} MB")
    try:
        processed = process_car_image(raw)
    except InvalidImageError as exc:
        raise HTTPException(415, str(exc)) from exc

    key = f"cars/{car.id}/{uuid.uuid4().hex}.{processed.extension}"
    get_storage().save(key, processed.data, processed.content_type)
    image = CarImage(
        car_id=car.id,
        storage_key=key,
        alt_text=(alt_text or car.name)[:200],
        width=processed.width,
        height=processed.height,
        sort_order=len(car.images),
        is_primary=not car.images,
    )
    db.add(image)
    audit.record(db, admin, "car.image_uploaded", "car", car.id, key=key)
    db.commit()
    return image


@router.patch("/{car_id}/images/{image_id}", response_model=CarImageOut)
def update_image(car_id: int, image_id: int, payload: CarImageUpdate, admin: CurrentAdmin, db: DbSession) -> CarImage:
    car = _get_car(db, car_id)
    image = next((i for i in car.images if i.id == image_id), None)
    if image is None:
        raise HTTPException(404, "Image not found")
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("is_primary"):
        for other in car.images:
            other.is_primary = other.id == image.id
        changes.pop("is_primary")
    for field, value in changes.items():
        if value is not None:
            setattr(image, field, value)
    db.commit()
    db.refresh(image)
    return image


@router.delete("/{car_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(car_id: int, image_id: int, admin: CurrentAdmin, db: DbSession) -> None:
    car = _get_car(db, car_id)
    image = next((i for i in car.images if i.id == image_id), None)
    if image is None:
        raise HTTPException(404, "Image not found")
    key, was_primary = image.storage_key, image.is_primary
    car.images.remove(image)
    if was_primary and car.images:
        car.images[0].is_primary = True
    audit.record(db, admin, "car.image_deleted", "car", car.id, key=key)
    db.commit()
    get_storage().delete(key)
