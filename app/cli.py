import argparse
import getpass
import os
import sys

from sqlalchemy import func, select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import AdminRole, AdminUser, Car
from app.schemas.auth import _validate_password_strength
from app.seed_data import SAMPLE_CARS
from app.db.base import Base
from app.db.session import engine
from app.models.car import CarCategory, Transmission, FuelType, CarStatus


def create_admin(email: str, name: str, role: str, password: str | None) -> None:
    password = (
        password or os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Password: ")
    )
    try:
        _validate_password_strength(None, password)
    except ValueError as exc:
        sys.exit(f"Error: {exc}")
    with SessionLocal() as db:
        existing = db.scalar(
            select(AdminUser).where(func.lower(AdminUser.email) == email.lower())
        )
        if existing:
            existing.password_hash = hash_password(password)
            existing.full_name = name
            existing.role = AdminRole(role)
            existing.is_active = True
            existing.token_version += 1
            print(f"Updated admin {email}")
        else:
            db.add(
                AdminUser(
                    email=email.lower(),
                    full_name=name,
                    role=AdminRole(role),
                    password_hash=hash_password(password),
                )
            )
            print(f"Created admin {email}")
        db.commit()


def seed() -> None:

    Base.metadata.create_all(bind=engine)

    enum_fields = {
        "category": CarCategory,
        "transmission": Transmission,
        "fuel_type": FuelType,
        "status": CarStatus,
    }

    with SessionLocal() as db:
        added = 0
        for data in SAMPLE_CARS:
            if db.scalar(select(Car.id).where(Car.slug == data["slug"])) is None:
                db.add(Car(**data))
                added += 1
        db.commit()
        print(f"Seeded {added} sample cars")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    ca = sub.add_parser("create-admin")
    ca.add_argument("--email", required=True)
    ca.add_argument("--name", required=True)
    ca.add_argument("--role", choices=[r.value for r in AdminRole], default="admin")
    ca.add_argument(
        "--password", help="Prefer the ADMIN_PASSWORD env var or the interactive prompt"
    )
    sub.add_parser("seed")
    args = parser.parse_args()
    if args.cmd == "create-admin":
        create_admin(args.email, args.name, args.role, args.password)
    elif args.cmd == "seed":
        seed()


if __name__ == "__main__":
    main()
