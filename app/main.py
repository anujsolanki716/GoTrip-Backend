import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.routes import (
    admin_auth,
    admin_cars,
    admin_enquiries,
    admin_stats,
    cars,
    enquiries,
    media,
    site,
)
from app.core.config import get_settings
from app.db.session import SessionLocal

settings = get_settings()
logging.basicConfig(level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "GoTrip self-drive car rental: car discovery and customer enquiries. "
        "This API intentionally has no booking, reservation or payment endpoints."
    ),
    docs_url=None if settings.is_production else "/api/docs",
    redoc_url=None,
    openapi_url=None if settings.is_production else "/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-Requested-With", "Authorization"],
    max_age=600,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
    if request.url.path.startswith(f"{settings.api_prefix}/admin"):
        response.headers.setdefault("Cache-Control", "no-store")
    if settings.is_production:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception) -> JSONResponse:
    logging.getLogger("gotrip").exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse({"detail": "Something went wrong. Please try again."}, status_code=500)


for module in (site, cars, enquiries, media, admin_auth, admin_cars, admin_enquiries, admin_stats):
    app.include_router(module.router, prefix=settings.api_prefix)


@app.get(f"{settings.api_prefix}/health", tags=["health"])
def health() -> dict[str, str]:
    db_status = "ok"
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unavailable"
    return {"status": "ok" if db_status == "ok" else "degraded", "database": db_status}
