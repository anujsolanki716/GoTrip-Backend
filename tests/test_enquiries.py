from datetime import timedelta

from app.models import Enquiry, EnquiryStatus
from app.schemas.enquiry import today_ist


def payload(**kw):
    data = {
        "full_name": "Aarav Sharma",
        "phone": "98765 43210",
        "email": "aarav@example.com",
        "customer_type": "student",
        "preferred_contact": "whatsapp",
        "pickup_date": str(today_ist() + timedelta(days=2)),
        "return_date": str(today_ist() + timedelta(days=4)),
        "pickup_area": "Knowledge Park II",
        "message": "Need the car for a weekend trip.",
        "consent": True,
    }
    data.update(kw)
    return data


def test_create_enquiry_for_car_is_not_a_booking(client, cars, db):
    r = client.post("/api/v1/enquiries", json=payload(car_slug=cars[0].slug))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["is_booking"] is False
    assert body["reference"].startswith("GT-")
    assert "not a booking" in body["message"]

    enquiry = db.query(Enquiry).one()
    assert enquiry.phone == "+919876543210"
    assert enquiry.car_id == cars[0].id
    assert enquiry.car_name_snapshot == cars[0].name
    assert enquiry.status == EnquiryStatus.NEW
    assert enquiry.ip_hash and "." not in enquiry.ip_hash  # raw IP is not stored


def test_general_enquiry_without_car_or_email(client):
    r = client.post("/api/v1/enquiries", json=payload(email="", pickup_date=None, return_date=None))
    assert r.status_code == 201, r.text


def test_phone_formats(client):
    for phone in ["+91 98765-43210", "09876543210", "919876543210"]:
        assert client.post("/api/v1/enquiries", json=payload(phone=phone)).status_code == 201
    for phone in ["12345", "5876543210", "abcdefghij"]:
        assert client.post("/api/v1/enquiries", json=payload(phone=phone)).status_code == 422


def test_validation_errors(client):
    today = today_ist()
    cases = [
        payload(consent=False),
        payload(pickup_date=str(today - timedelta(days=1))),
        payload(return_date=str(today)),  # before pickup
        payload(full_name="1234"),
        payload(customer_type="vip"),
        payload(preferred_contact="email", email=""),
        payload(message="x" * 2001),
    ]
    for case in cases:
        assert client.post("/api/v1/enquiries", json=case).status_code == 422, case


def test_unknown_or_unpublished_car_rejected(client, cars, db):
    assert client.post("/api/v1/enquiries", json=payload(car_slug="nope")).status_code == 422
    cars[1].is_published = False
    db.commit()
    assert client.post("/api/v1/enquiries", json=payload(car_slug=cars[1].slug)).status_code == 422


def test_honeypot_marks_spam(client, db):
    assert client.post("/api/v1/enquiries", json=payload(website="http://spam")).status_code == 201
    assert db.query(Enquiry).one().status == EnquiryStatus.SPAM


def test_rate_limit(client):
    codes = [client.post("/api/v1/enquiries", json=payload()).status_code for _ in range(6)]
    assert codes[:5] == [201] * 5
    assert codes[5] == 429
