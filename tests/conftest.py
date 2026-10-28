import io
import os
from collections.abc import Iterator

os.environ.setdefault(
    "DATABASE_URL", os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://asolanki:gotrip@localhost:5432/gotrip_test")
)
if "TEST_DATABASE_URL" in os.environ:
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
os.environ["ENVIRONMENT"] = "test"
os.environ["EMAIL_PROVIDER"] = "disabled"
os.environ.setdefault("LOCAL_STORAGE_PATH", os.path.join(os.path.dirname(__file__), ".storage"))

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import text

from alembic import command
from app.core.rate_limit import enquiry_limiter, login_limiter
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.models import AdminRole, AdminUser, Car
from app.seed_data import SAMPLE_CARS

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin@123456"
STAFF_EMAIL = "staff@gotrip-demo.in"


@pytest.fixture(scope="session", autouse=True)
def _migrate() -> None:
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
    command.upgrade(cfg, "head")


@pytest.fixture(autouse=True)
def _clean() -> Iterator[None]:
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    enquiry_limiter.reset()
    login_limiter.reset()
    yield


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def cars(db) -> list[Car]:
    rows = [Car(**data) for data in SAMPLE_CARS]
    db.add_all(rows)
    db.commit()
    return rows


@pytest.fixture
def admin_user(db) -> AdminUser:
    user = AdminUser(
        email=ADMIN_EMAIL, full_name="Test Admin", role=AdminRole.ADMIN, password_hash=hash_password(ADMIN_PASSWORD)
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def staff_user(db) -> AdminUser:
    user = AdminUser(
        email=STAFF_EMAIL, full_name="Test Staff", role=AdminRole.STAFF, password_hash=hash_password(ADMIN_PASSWORD)
    )
    db.add(user)
    db.commit()
    return user


CSRF = {"X-Requested-With": "XMLHttpRequest"}


def login(client: TestClient, email: str = ADMIN_EMAIL, password: str = ADMIN_PASSWORD):
    return client.post("/api/v1/admin/auth/login", json={"email": email, "password": password})


@pytest.fixture
def admin_client(client: TestClient, admin_user: AdminUser) -> TestClient:
    assert login(client).status_code == 200
    client.headers.update(CSRF)
    return client


def make_png(size: tuple[int, int] = (64, 40)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (233, 185, 73)).save(buf, format="PNG")
    return buf.getvalue()
