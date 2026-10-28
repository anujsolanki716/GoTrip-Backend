import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column


from app.db.base import Base, TimestampMixin
class StrEnum(str, enum.Enum):
    """String enum compatible with Python 3.10."""


class AdminRole(StrEnum):
    ADMIN = "admin"
    STAFF = "staff"


class AdminUser(TimestampMixin, Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[AdminRole] = mapped_column(
        Enum(AdminRole, native_enum=False, length=20, values_callable=lambda e: [m.value for m in e]),
        default=AdminRole.STAFF,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
