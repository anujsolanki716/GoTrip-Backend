from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import func, select

from app.api.deps import CurrentAdmin, DbSession, client_ip
from app.core.config import get_settings
from app.core.rate_limit import login_limiter
from app.core.security import (
    create_access_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.models import AdminUser
from app.schemas.auth import AdminOut, LoginRequest, LoginResponse, PasswordChange
from app.services import audit

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])


def _set_cookie(response: Response, token: str, expires: datetime) -> None:
    s = get_settings()
    response.set_cookie(
        s.auth_cookie_name,
        token,
        httponly=True,
        secure=s.cookie_secure,
        samesite=s.cookie_samesite,
        domain=s.cookie_domain,
        expires=expires,
        path="/",
    )


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest, request: Request, response: Response, db: DbSession
) -> LoginResponse:
    s = get_settings()
    email = payload.email.lower()
    keys = (f"login-ip:{client_ip(request)}", f"login-email:{email}")
    if any(
        login_limiter.is_blocked(k, s.login_max_attempts, s.login_window_seconds)
        for k in keys
    ):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many failed attempts. Try again later.",
        )

    admin = db.scalar(select(AdminUser).where(func.lower(AdminUser.email) == email))
    ok = verify_password(payload.password, admin.password_hash if admin else None)
    if not ok or admin is None or not admin.is_active:
        for k in keys:
            login_limiter.hit(k, s.login_max_attempts, s.login_window_seconds)
        audit.record(
            db,
            None,
            "auth.login_failed",
            "admin_user",
            admin.id if admin else None,
            email=email,
        )
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    for k in keys:
        login_limiter.reset(k)
    if needs_rehash(admin.password_hash):
        admin.password_hash = hash_password(payload.password)
    admin.last_login_at = datetime.now(timezone.utc)
    audit.record(db, admin, "auth.login", "admin_user", admin.id)
    db.commit()

    token, expires = create_access_token(admin.id, admin.token_version)
    _set_cookie(response, token, expires)
    return LoginResponse(admin=AdminOut.model_validate(admin), expires_at=expires)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> Response:
    s = get_settings()
    response.delete_cookie(s.auth_cookie_name, path="/", domain=s.cookie_domain)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=AdminOut)
def me(admin: CurrentAdmin) -> AdminUser:
    return admin


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: PasswordChange, admin: CurrentAdmin, db: DbSession, response: Response
) -> Response:
    if not verify_password(payload.current_password, admin.password_hash):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Current password is incorrect"
        )
    admin.password_hash = hash_password(payload.new_password)
    admin.token_version += 1
    audit.record(db, admin, "auth.password_changed", "admin_user", admin.id)
    db.commit()
    token, expires = create_access_token(admin.id, admin.token_version)
    _set_cookie(response, token, expires)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
