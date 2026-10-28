from app.main import app


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "ok"}


def test_site_config_declares_no_booking_or_payment(client):
    data = client.get("/api/v1/site/config").json()
    assert data["online_booking"] is False
    assert data["online_payment"] is False
    assert data["tagline"] == "Your Journey, Your Rules."


def test_no_booking_or_payment_routes_exist():
    forbidden = ("book", "checkout", "payment", "pay", "reserve", "reservation", "webhook", "order")
    for route in app.routes:
        path = getattr(route, "path", "").lower()
        segments = [s for s in path.split("/") if s]
        assert not any(seg.startswith(f) for seg in segments for f in forbidden), path


def test_security_headers(client):
    r = client.get("/api/v1/site/config")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"


def test_list_cars_only_published(client, cars, db):
    cars[0].is_published = False
    db.commit()
    data = client.get("/api/v1/cars", params={"page_size": 48}).json()
    assert data["total"] == len(cars) - 1
    assert cars[0].slug not in {c["slug"] for c in data["items"]}
    assert client.get(f"/api/v1/cars/{cars[0].slug}").status_code == 404


def test_filters_and_sort(client, cars):
    r = client.get("/api/v1/cars", params={"transmission": "automatic", "sort": "price_asc"}).json()
    prices = [c["daily_price"] for c in r["items"]]
    assert prices == sorted(prices)
    assert all(c["transmission"] == "automatic" for c in r["items"])

    r = client.get("/api/v1/cars", params={"min_seats": 7}).json()
    assert r["total"] >= 1 and all(c["seats"] >= 7 for c in r["items"])

    r = client.get("/api/v1/cars", params=[("category", "sedan"), ("category", "muv")]).json()
    assert {c["category"] for c in r["items"]} <= {"sedan", "muv"}

    r = client.get("/api/v1/cars", params={"q": "creta"}).json()
    assert [c["model"] for c in r["items"]] == ["Creta"]

    r = client.get("/api/v1/cars", params={"q": "%"}).json()
    assert r["total"] == 0  # wildcard is escaped


def test_car_detail_and_similar(client, cars):
    slug = cars[0].slug
    r = client.get(f"/api/v1/cars/{slug}")
    assert r.status_code == 200
    assert r.json()["name"] == cars[0].name
    sim = client.get(f"/api/v1/cars/{slug}/similar").json()
    assert len(sim) == 3 and slug not in {c["slug"] for c in sim}
