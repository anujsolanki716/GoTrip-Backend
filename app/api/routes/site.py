from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings
from app.models import CarCategory, CustomerType, FuelType, Transmission

router = APIRouter(tags=["site"])


class SiteConfig(BaseModel):
    business_name: str
    tagline: str
    phone: str
    whatsapp: str
    email: str
    address: str
    hours: str
    service_areas: list[str]
    categories: list[str]
    transmissions: list[str]
    fuel_types: list[str]
    customer_types: list[str]
    online_booking: bool = False
    online_payment: bool = False


@router.get("/site/config", response_model=SiteConfig)
def site_config() -> SiteConfig:
    s = get_settings()
    return SiteConfig(
        business_name=s.business_name,
        tagline=s.business_tagline,
        phone=s.business_phone,
        whatsapp=s.business_whatsapp,
        email=s.business_email,
        address=s.business_address,
        hours=s.business_hours,
        service_areas=s.service_areas,
        categories=[c.value for c in CarCategory],
        transmissions=[t.value for t in Transmission],
        fuel_types=[f.value for f in FuelType],
        customer_types=[c.value for c in CustomerType],
    )
