import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings

_hasher = PasswordHasher()
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        return (
            _hasher.verify(password_hash or _DUMMY_HASH, password)
            and password_hash is not None
        )
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def create_access_token(user_id: int, token_version: int) -> tuple[str, datetime]:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "ver": token_version,
        "typ": "admin",
        "iat": now,
        "exp": expires,
        "jti": secrets.token_urlsafe(12),
    }
    token = jwt.encode(
        payload, settings.secret_key.get_secret_value(), algorithm=ALGORITHM
    )
    return token, expires


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(
            token,
            get_settings().secret_key.get_secret_value(),
            algorithms=[ALGORITHM],
            options={"require": ["sub", "exp", "iat", "ver"]},
        )
    except jwt.PyJWTError:
        return None
    if payload.get("typ") != "admin":
        return None
    return payload


def hash_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    key = get_settings().secret_key.get_secret_value().encode()
    return hashlib.blake2b(ip.encode(), key=key[:64], digest_size=16).hexdigest()
