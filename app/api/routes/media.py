from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, Response
from sqlalchemy import select

from app.api.deps import DbSession, get_current_admin
from app.models import Car, CarImage
from app.services.storage import get_storage

router = APIRouter(tags=["media"])


@router.get("/media/{key:path}", include_in_schema=False)
def get_media(key: str, request: Request, db: DbSession) -> Response:
    image = db.scalar(select(CarImage).where(CarImage.storage_key == key))
    if image is None:
        raise HTTPException(404, "Not found")
    car = db.get(Car, image.car_id)
    public = car is not None and car.is_published
    if not public:
        try:
            get_current_admin(request, db)
        except HTTPException:
            raise HTTPException(404, "Not found") from None

    storage = get_storage()
    cache = "public, max-age=86400" if public else "private, no-store"
    path = storage.local_path(key)
    if path is not None:
        return FileResponse(path, media_type="image/webp", headers={"Cache-Control": cache})
    url = storage.presigned_url(key)
    if url is None:
        raise HTTPException(404, "Not found")
    return RedirectResponse(url, status_code=302, headers={"Cache-Control": "private, max-age=300"})
