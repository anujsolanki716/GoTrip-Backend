import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Car


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value[:120] or "car"


def unique_car_slug(db: Session, base: str, exclude_id: int | None = None) -> str:
    base = slugify(base)
    candidate, n = base, 2
    while True:
        existing = db.scalar(select(Car.id).where(Car.slug == candidate))
        if existing is None or existing == exclude_id:
            return candidate
        candidate = f"{base}-{n}"
        n += 1
