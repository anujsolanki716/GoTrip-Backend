import csv
import io
import math
from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import Select, func, or_, select

from app.api.deps import CurrentAdmin, DbSession
from app.models import Enquiry, EnquiryStatus
from app.schemas.common import Page
from app.schemas.enquiry import IST, EnquiryAdmin, EnquiryUpdate
from app.services import audit

router = APIRouter(prefix="/admin/enquiries", tags=["admin-enquiries"])


def _filtered(
    status: list[EnquiryStatus], q: str | None, car_id: int | None, date_from: date | None, date_to: date | None
) -> Select[tuple[Enquiry]]:
    stmt = select(Enquiry)
    stmt = stmt.where(Enquiry.status.in_(status) if status else Enquiry.status != EnquiryStatus.SPAM)
    if q and q.strip():
        term = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Enquiry.full_name.ilike(term),
                Enquiry.phone.ilike(term),
                Enquiry.email.ilike(term),
                Enquiry.reference.ilike(term),
                Enquiry.car_name_snapshot.ilike(term),
            )
        )
    if car_id:
        stmt = stmt.where(Enquiry.car_id == car_id)
    if date_from:
        stmt = stmt.where(Enquiry.created_at >= datetime.combine(date_from, time.min, IST))
    if date_to:
        stmt = stmt.where(Enquiry.created_at < datetime.combine(date_to + timedelta(days=1), time.min, IST))
    return stmt


@router.get("", response_model=Page[EnquiryAdmin])
def list_enquiries(
    admin: CurrentAdmin,
    db: DbSession,
    status: list[EnquiryStatus] = Query(default_factory=list),
    q: Annotated[str | None, Query(max_length=80)] = None,
    car_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
) -> Page[EnquiryAdmin]:
    stmt = _filtered(status, q, car_id, date_from, date_to)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Enquiry.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return Page(
        items=[EnquiryAdmin.model_validate(r) for r in rows],
        total=total,
        page=page,
        size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


def _csv_safe(value: object) -> str:
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


@router.get("/export.csv")
def export_enquiries(
    admin: CurrentAdmin,
    db: DbSession,
    status: list[EnquiryStatus] = Query(default_factory=list),
    q: Annotated[str | None, Query(max_length=80)] = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> StreamingResponse:
    rows = db.scalars(_filtered(status, q, None, date_from, date_to).order_by(Enquiry.created_at.desc())).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    cols = [
        "reference",
        "created_at",
        "status",
        "car_name_snapshot",
        "full_name",
        "phone",
        "email",
        "customer_type",
        "preferred_contact",
        "pickup_date",
        "return_date",
        "pickup_area",
        "message",
        "admin_notes",
    ]
    writer.writerow(cols)
    for r in rows:
        writer.writerow(
            [_csv_safe(getattr(r, c).value if hasattr(getattr(r, c), "value") else getattr(r, c)) for c in cols]
        )
    filename = f"gotrip-enquiries-{datetime.now(IST):%Y%m%d-%H%M}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"},
    )


@router.get("/{enquiry_id}", response_model=EnquiryAdmin)
def get_enquiry(enquiry_id: int, admin: CurrentAdmin, db: DbSession) -> Enquiry:
    enquiry = db.get(Enquiry, enquiry_id)
    if enquiry is None:
        raise HTTPException(404, "Enquiry not found")
    return enquiry


@router.patch("/{enquiry_id}", response_model=EnquiryAdmin)
def update_enquiry(enquiry_id: int, payload: EnquiryUpdate, admin: CurrentAdmin, db: DbSession) -> Enquiry:
    enquiry = db.get(Enquiry, enquiry_id)
    if enquiry is None:
        raise HTTPException(404, "Enquiry not found")
    changes = payload.model_dump(exclude_unset=True)
    now = datetime.now(timezone.utc)
    if (new_status := changes.get("status")) and new_status != enquiry.status:
        audit.record(
            db, admin, "enquiry.status_changed", "enquiry", enquiry.id, old=enquiry.status.value, new=new_status.value
        )
        enquiry.status = new_status
        if new_status != EnquiryStatus.NEW and enquiry.contacted_at is None and new_status != EnquiryStatus.SPAM:
            enquiry.contacted_at = now
        enquiry.converted_at = now if new_status == EnquiryStatus.CONVERTED_OFFLINE else None
    if "admin_notes" in changes:
        enquiry.admin_notes = changes["admin_notes"] or None
        audit.record(db, admin, "enquiry.notes_updated", "enquiry", enquiry.id)
    db.commit()
    db.refresh(enquiry)
    return enquiry
