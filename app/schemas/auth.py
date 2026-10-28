from datetime import datetime
from typing import Annotated

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
    ConfigDict,
)

from app.models import AdminRole
from app.schemas.common import ORMModel


class LoginRequest(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=1, max_length=256)]


class AdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: str
    is_active: bool


class LoginResponse(BaseModel):
    admin: AdminOut
    expires_at: datetime


def _validate_password_strength(cls: object, pw: str) -> str:
    if len(pw) < 12:
        raise ValueError("Password must be at least 12 characters")
    classes = sum(
        [
            any(c.islower() for c in pw),
            any(c.isupper() for c in pw),
            any(c.isdigit() for c in pw),
            any(not c.isalnum() for c in pw),
        ]
    )
    if classes < 3:
        raise ValueError("Use at least three of: lowercase, uppercase, digits, symbols")
    return pw


StrongPassword = Annotated[str, StringConstraints(max_length=256), Field(min_length=12)]


class PasswordChange(BaseModel):
    current_password: Annotated[str, Field(min_length=1, max_length=256)]
    new_password: StrongPassword

    _strength = field_validator("new_password")(_validate_password_strength)
