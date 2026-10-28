from datetime import datetime, time, timedelta, timezone

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import CurrentAdmin, DbSession
from app.models import Car, Enquiry, EnquiryStatus
from app.schemas.enquiry import IST

router = APIRouter(prefix="/admin", tags=["admin-stats"])


class TopCar(BaseModel):
    car_id: int | None
    name: str
    enquiries: int


class DayCount(BaseModel):
    day: str
    count: int


class Stats(BaseModel):
    cars_total: int
    cars_published: int
    enquiries_total: int
    enquiries_new: int
    enquiries_last_7_days: int
    converted_offline: int
    by_status: dict[str, int]
    top_cars: list[TopCar]
    last_14_days: list[DayCount]


@router.get("/stats", response_model=Stats)
def stats(admin: CurrentAdmin, db: DbSession) -> Stats:
    not_spam = Enquiry.status != EnquiryStatus.SPAM
    by_status = {s.value: 0 for s in EnquiryStatus}
    for status, n in db.execute(select(Enquiry.status, func.count()).group_by(Enquiry.status)).all():
        by_status[status.value] = n
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    top = db.execute(
        select(Enquiry.car_id, func.max(Enquiry.car_name_snapshot), func.count(Enquiry.id))
        .where(not_spam, Enquiry.car_id.is_not(None))
        .group_by(Enquiry.car_id)
        .order_by(func.count(Enquiry.id).desc())
        .limit(5)
    ).all()

    start = (now.astimezone(IST) - timedelta(days=13)).date()
    recent = db.scalars(
        select(Enquiry.created_at).where(not_spam, Enquiry.created_at >= datetime.combine(start, time.min, IST))
    ).all()
    buckets = {(start + timedelta(days=i)).isoformat(): 0 for i in range(14)}
    for created in recent:
        key = created.astimezone(IST).date().isoformat()
        if key in buckets:
            buckets[key] += 1

    return Stats(
        cars_total=db.scalar(select(func.count(Car.id))) or 0,
        cars_published=db.scalar(select(func.count(Car.id)).where(Car.is_published.is_(True))) or 0,
        enquiries_total=sum(v for k, v in by_status.items() if k != EnquiryStatus.SPAM.value),
        enquiries_new=by_status[EnquiryStatus.NEW.value],
        enquiries_last_7_days=db.scalar(select(func.count(Enquiry.id)).where(not_spam, Enquiry.created_at >= week_ago))
        or 0,
        converted_offline=by_status[EnquiryStatus.CONVERTED_OFFLINE.value],
        by_status=by_status,
        top_cars=[TopCar(car_id=cid, name=name or "Unknown", enquiries=n) for cid, name, n in top],
        last_14_days=[DayCount(day=k, count=v) for k, v in buckets.items()],
    )
