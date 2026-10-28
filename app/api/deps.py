from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import AdminRole, AdminUser

DbSession = Annotated[Session, Depends(get_db)]

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_HEADER = "x-requested-with"


def client_ip(request: Request) -> str | None:
    hops = get_settings().trusted_proxy_count
    if hops > 0:
        forwarded = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
        if len(forwarded) >= hops:
            return forwarded[-hops]
    return request.client.host if request.client else None


def _unauthorized() -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})


def get_current_admin(request: Request, db: DbSession) -> AdminUser:
    settings = get_settings()
    token = request.cookies.get(settings.auth_cookie_name)
    via_cookie = token is not None
    if not token:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
    if not token:
        raise _unauthorized()

    if via_cookie and request.method not in SAFE_METHODS:
        if request.headers.get(CSRF_HEADER, "").lower() != "xmlhttprequest":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Missing CSRF header")
        origin = request.headers.get("origin")
        if origin and origin not in settings.cors_origins and origin != str(request.base_url).rstrip("/"):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Origin not allowed")

    payload = decode_access_token(token)
    if payload is None:
        raise _unauthorized()
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise _unauthorized() from None
    admin = db.get(AdminUser, user_id)
    if admin is None or not admin.is_active or admin.token_version != payload.get("ver"):
        raise _unauthorized()
    return admin


CurrentAdmin = Annotated[AdminUser, Depends(get_current_admin)]


def require_full_admin(admin: CurrentAdmin) -> AdminUser:
    if admin.role != AdminRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This action requires the admin role")
    return admin


FullAdmin = Annotated[AdminUser, Depends(require_full_admin)]
