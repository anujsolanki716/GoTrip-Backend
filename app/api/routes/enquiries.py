import secrets
import string

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DbSession, client_ip
from app.core.config import get_settings
from app.core.rate_limit import enquiry_limiter
from app.core.security import hash_ip
from app.models import Car, Enquiry, EnquiryStatus
from app.schemas.enquiry import EnquiryCreate, EnquiryReceipt, today_ist
from app.services.email import notify_new_enquiry

router = APIRouter(tags=["enquiries"])

ALPHABET = "".join(c for c in string.ascii_uppercase + string.digits if c not in "O0I1")
RECEIPT_MESSAGE = (
    "Thank you! Your enquiry has been received. This is not a booking and no car has been reserved. "
    "The GoTrip team will contact you to discuss availability, eligibility, pricing and rental terms."
)


def _reference() -> str:
    return f"GT-{today_ist():%y%m}-" + "".join(secrets.choice(ALPHABET) for _ in range(5))


@router.post("/enquiries", response_model=EnquiryReceipt, status_code=status.HTTP_201_CREATED)
def create_enquiry(
    payload: EnquiryCreate, request: Request, background: BackgroundTasks, db: DbSession
) -> EnquiryReceipt:
    settings = get_settings()
    ip = client_ip(request)
    if not enquiry_limiter.hit(
        f"enq:{ip}", settings.enquiry_rate_limit_count, settings.enquiry_rate_limit_window_seconds
    ):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many enquiries from this connection. Please call or WhatsApp us instead.",
        )

    car: Car | None = None
    if payload.car_slug:
        car = db.scalar(select(Car).where(Car.slug == payload.car_slug, Car.is_published.is_(True)))
        if car is None:
            raise HTTPException(422, "The selected car is not available for enquiry")

    is_spam = bool(payload.website)
    data = payload.model_dump(exclude={"car_slug", "website"})
    for _ in range(5):
        enquiry = Enquiry(
            **data,
            reference=_reference(),
            car_id=car.id if car else None,
            car_name_snapshot=car.name if car else None,
            status=EnquiryStatus.SPAM if is_spam else EnquiryStatus.NEW,
            ip_hash=hash_ip(ip),
            user_agent=(request.headers.get("user-agent") or "")[:255] or None,
        )
        db.add(enquiry)
        try:
            db.commit()
            break
        except IntegrityError:
            db.rollback()
    else:
        raise HTTPException(500, "Could not save enquiry, please try again")

    if not is_spam:
        background.add_task(notify_new_enquiry, enquiry)
    return EnquiryReceipt(reference=enquiry.reference, message=RECEIPT_MESSAGE)
