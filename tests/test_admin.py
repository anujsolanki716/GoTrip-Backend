from datetime import timedelta

from app.core.security import create_access_token
from app.models import AuditLog, Enquiry, EnquiryStatus
from app.schemas.enquiry import today_ist
from tests.conftest import ADMIN_EMAIL, CSRF, STAFF_EMAIL, login, make_png

NEW_CAR = {
    "name": "Kia Seltos",
    "brand": "Kia",
    "model": "Seltos",
    "variant": "HTX",
    "year": 2024,
    "category": "suv",
    "transmission": "automatic",
    "fuel_type": "petrol",
    "seats": 5,
    "daily_price": 3299,
    "features": ["Sunroof", "ADAS"],
}


def test_admin_routes_require_auth(client):
    for method, path in [
        ("get", "/api/v1/admin/cars"),
        ("get", "/api/v1/admin/enquiries"),
        ("get", "/api/v1/admin/stats"),
        ("post", "/api/v1/admin/cars"),
    ]:
        assert getattr(client, method)(path).status_code == 401


def test_login_logout_flow(client, admin_user):
    r = login(client)
    assert r.status_code == 200
    assert r.json()["admin"]["email"] == ADMIN_EMAIL
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert client.get("/api/v1/admin/auth/me").status_code == 200
    assert client.post("/api/v1/admin/auth/logout").status_code == 204
    assert client.get("/api/v1/admin/auth/me").status_code == 401


def test_bad_login_and_lockout(client, admin_user):
    assert login(client, password="wrong").status_code == 401
    assert login(client, email="nobody@x.com").status_code == 401
    for _ in range(4):
        login(client, password="wrong")
    assert login(client).status_code == 429  # locked even with the right password


def test_cookie_requests_need_csrf_header(client, admin_user):
    login(client)
    assert client.post("/api/v1/admin/cars", json=NEW_CAR).status_code == 403
    assert (
        client.post("/api/v1/admin/cars", json=NEW_CAR, headers={**CSRF, "Origin": "https://evil.example"}).status_code
        == 403
    )
    assert client.post("/api/v1/admin/cars", json=NEW_CAR, headers=CSRF).status_code == 201


def test_token_invalidated_by_version(client, admin_user, db):
    token, _ = create_access_token(admin_user.id, admin_user.token_version)
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/admin/auth/me", headers=headers).status_code == 200
    admin_user.token_version += 1
    db.commit()
    assert client.get("/api/v1/admin/auth/me", headers=headers).status_code == 401
    assert client.get("/api/v1/admin/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_car_crud_and_publish(admin_client, client, db):
    r = admin_client.post("/api/v1/admin/cars", json=NEW_CAR)
    assert r.status_code == 201, r.text
    car = r.json()
    assert car["slug"] == "kia-seltos-htx-2024"
    assert car["is_published"] is False
    assert client.get(f"/api/v1/cars/{car['slug']}").status_code == 404

    r = admin_client.patch(f"/api/v1/admin/cars/{car['id']}", json={"is_published": True, "daily_price": 3199})
    assert r.status_code == 200 and r.json()["daily_price"] == 3199
    assert client.get(f"/api/v1/cars/{car['slug']}").status_code == 200

    assert admin_client.patch(f"/api/v1/admin/cars/{car['id']}", json={"name": None}).status_code == 422
    assert admin_client.patch(f"/api/v1/admin/cars/{car['id']}", json={"slug": "Bad Slug"}).status_code == 422

    assert admin_client.delete(f"/api/v1/admin/cars/{car['id']}").status_code == 204
    assert admin_client.get(f"/api/v1/admin/cars/{car['id']}").status_code == 404
    assert db.query(AuditLog).filter(AuditLog.action == "car.deleted").count() == 1


def test_staff_cannot_delete_cars(client, staff_user, cars):
    login(client, email=STAFF_EMAIL)
    client.headers.update(CSRF)
    assert client.patch(f"/api/v1/admin/cars/{cars[0].id}", json={"is_featured": False}).status_code == 200
    assert client.delete(f"/api/v1/admin/cars/{cars[0].id}").status_code == 403


def test_image_upload_and_media_access(admin_client, cars, db):
    car = cars[0]
    r = admin_client.post(
        f"/api/v1/admin/cars/{car.id}/images", files={"file": ("car.png", make_png((3000, 2000)), "image/png")}
    )
    assert r.status_code == 201, r.text
    img = r.json()
    assert img["is_primary"] is True and img["width"] == 1920
    assert img["url"].endswith(".webp")

    media = admin_client.get(img["url"])
    assert media.status_code == 200 and media.headers["content-type"] == "image/webp"

    bad = admin_client.post(
        f"/api/v1/admin/cars/{car.id}/images", files={"file": ("evil.png", b"<?php echo 1; ?>", "image/png")}
    )
    assert bad.status_code == 415

    # unpublished car images are hidden from the public
    car.is_published = False
    db.commit()
    from fastapi.testclient import TestClient

    from app.main import app

    assert TestClient(app).get(img["url"]).status_code == 404
    assert admin_client.get(img["url"]).status_code == 200

    assert admin_client.delete(f"/api/v1/admin/cars/{car.id}/images/{img['id']}").status_code == 204
    assert admin_client.get(img["url"]).status_code == 404


def _make_enquiry(client, slug=None):
    return client.post(
        "/api/v1/enquiries",
        json={
            "full_name": "Priya Verma",
            "phone": "9811122233",
            "customer_type": "corporate",
            "preferred_contact": "phone",
            "consent": True,
            "car_slug": slug,
            "pickup_date": str(today_ist() + timedelta(days=1)),
        },
    ).json()


def test_enquiry_management(admin_client, cars, db):
    ref = _make_enquiry(admin_client, cars[3].slug)["reference"]
    listing = admin_client.get("/api/v1/admin/enquiries").json()
    assert listing["total"] == 1
    item = listing["items"][0]
    assert item["reference"] == ref and item["status"] == "new"

    r = admin_client.patch(
        f"/api/v1/admin/enquiries/{item['id']}",
        json={"status": "contacted", "admin_notes": "Called, will visit office"},
    )
    assert r.status_code == 200 and r.json()["contacted_at"] is not None

    r = admin_client.patch(f"/api/v1/admin/enquiries/{item['id']}", json={"status": "converted_offline"})
    assert r.json()["status"] == "converted_offline" and r.json()["converted_at"]

    assert admin_client.get("/api/v1/admin/enquiries", params={"status": "new"}).json()["total"] == 0
    assert admin_client.get("/api/v1/admin/enquiries", params={"q": "priya"}).json()["total"] == 1

    stats = admin_client.get("/api/v1/admin/stats").json()
    assert stats["converted_offline"] == 1 and stats["enquiries_total"] == 1
    assert stats["top_cars"][0]["name"] == cars[3].name
    assert sum(d["count"] for d in stats["last_14_days"]) == 1
    assert db.query(AuditLog).filter(AuditLog.action == "enquiry.status_changed").count() == 2


def test_csv_export_escapes_formulas(admin_client, db):
    _make_enquiry(admin_client)
    enquiry = db.query(Enquiry).one()
    enquiry.message = '=HYPERLINK("http://evil")'
    enquiry.status = EnquiryStatus.CONTACTED
    db.commit()
    r = admin_client.get("/api/v1/admin/enquiries/export.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "'=HYPERLINK" in r.text


def test_password_change(admin_client):
    r = admin_client.post(
        "/api/v1/admin/auth/password", json={"current_password": "wrong", "new_password": "An0ther-Strong-Pass"}
    )
    assert r.status_code == 400
    r = admin_client.post(
        "/api/v1/admin/auth/password", json={"current_password": "Sup3r-Secret-Pass!", "new_password": "weak"}
    )
    assert r.status_code == 422
    r = admin_client.post(
        "/api/v1/admin/auth/password",
        json={"current_password": "Sup3r-Secret-Pass!", "new_password": "An0ther-Strong-Pass"},
    )
    assert r.status_code == 204
    assert admin_client.get("/api/v1/admin/auth/me").status_code == 200
