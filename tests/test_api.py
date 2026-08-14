"""Afitsant ilovasi uchun JSON API.

Bu qatlam brauzer sessiyasidan MUSTAQIL: kalit `Authorization` sarlavhasida
keladi va cookie umuman o'qilmaydi. Shu ikki xususiyat eng muhim va shu
yerda qulflanadi:

* bloklangan xodim kaliti O'SHA ZAHOTI ishlamay qoladi (JWT bo'lganda
  muddati tugagunicha ishlayverardi);
* API cookie qabul qilmaydi — aks holda brauzerda ochiq sessiyasi bor
  odamning cookie'si API'ga avtomatik ketardi va CSRF himoyasi yo'q bu
  yerda teshik ochilardi.
"""

import html

import pytest

from app.models import (
    ApiToken,
    AppDevice,
    Category,
    MenuItem,
    Order,
    OrderStatus,
    Role,
    Table,
    User,
)
from app.security import hash_password
from app.services import tokens

from tests.conftest import csrf, login


@pytest.fixture
def cafe(db, tenant_a):
    """Buyurtma yoqilgan restoran, stol, taom va afitsant."""
    restaurant, _ = tenant_a
    restaurant.orders_enabled = True
    category = Category(restaurant_id=restaurant.id, name={"uz": "Taomlar"})
    db.add(category)
    db.flush()
    db.add_all(
        [
            MenuItem(
                restaurant_id=restaurant.id,
                category_id=category.id,
                name={"uz": "Osh"},
                price=38000,
            ),
            Table(restaurant_id=restaurant.id, label="4", code="stolkod4"),
            User(
                username="afitsant",
                password_hash=hash_password("waiterpass123"),
                role=Role.waiter,
                restaurant_id=restaurant.id,
            ),
        ]
    )
    db.commit()
    return restaurant


def sign_in(client, username="afitsant", password="waiterpass123"):
    response = client.post(
        "/api/v1/login", json={"username": username, "password": password, "device": "Redmi"}
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def place_order(client, cafe, db, quantity=2):
    """Mijoz bo'lib buyurtma beradi va sessiyani tozalaydi."""
    import re

    table = db.query(Table).filter(Table.restaurant_id == cafe.id).one()
    client.get(f"/r/{cafe.slug}/t/{table.code}")
    body = client.get(f"/r/{cafe.slug}").text
    token = re.search(r'name="csrf_token" value="([^"]+)"', body).group(1)
    item = db.query(MenuItem).filter(MenuItem.restaurant_id == cafe.id).one()
    client.post(
        f"/r/{cafe.slug}/order",
        data={"csrf_token": token, "item_id": [item.id], "qty": [quantity]},
    )
    client.cookies.clear()


# --- kirish ----------------------------------------------------------------


def test_login_returns_a_token_and_context(client, cafe):
    response = client.post(
        "/api/v1/login", json={"username": "afitsant", "password": "waiterpass123"}
    )
    assert response.status_code == 200

    data = response.json()
    assert data["token"]
    assert data["user"]["role"] == "waiter"
    # Ilova sarlavhada restoran nomini ko'rsatadi — qayta so'rov qilmasin
    assert data["restaurant"]["name"] == cafe.name


def test_a_wrong_password_gives_no_token(client, db, cafe):
    response = client.post(
        "/api/v1/login", json={"username": "afitsant", "password": "yolgon"}
    )
    assert response.status_code == 401
    assert db.query(ApiToken).count() == 0


def test_the_error_is_json_not_html(client, cafe):
    """Ilova HTML xato sahifasini o'qiy olmaydi."""
    response = client.post("/api/v1/login", json={"username": "yoq", "password": "yoq"})
    assert response.headers["content-type"].startswith("application/json")
    assert "detail" in response.json()

    assert client.get("/api/v1/orders").status_code == 401
    assert client.get("/api/v1/orders").headers["content-type"].startswith("application/json")


def test_the_token_is_stored_hashed(client, db, cafe):
    """Baza o'g'irlansa ham undan ishlaydigan kalit chiqmasin."""
    token = sign_in(client)
    row = db.query(ApiToken).one()
    assert row.token_hash != token
    assert len(row.token_hash) == 64          # sha256 hex
    assert token not in row.token_hash


def test_a_restaurant_owner_can_also_sign_in(client, cafe):
    """Kichik kafeda egasi o'zi zalda yuradi."""
    data = client.post(
        "/api/v1/login", json={"username": "osh", "password": "adminpass123"}
    ).json()
    assert data["user"]["role"] == "restaurant_admin"


def test_a_superadmin_cannot_sign_in_to_the_app(client, db, cafe):
    db.add(User(username="root", password_hash=hash_password("rootpass123"), role=Role.superadmin))
    db.commit()
    response = client.post(
        "/api/v1/login", json={"username": "root", "password": "rootpass123"}
    )
    assert response.status_code == 401


def test_repeated_failures_are_throttled(client, cafe):
    """Cheklov brauzer login'i bilan BIR XIL hisoblagichda.

    Alohida bo'lganda ilova orqali cheksiz parol terish yo'li ochiq qolardi.
    """
    from app.security import MAX_ATTEMPTS

    codes = [
        client.post(
            "/api/v1/login", json={"username": "afitsant", "password": "yolgon"}
        ).status_code
        for _ in range(MAX_ATTEMPTS + 2)
    ]
    assert 429 in codes


def test_app_failures_lock_the_browser_login_too(client, cafe):
    from app.security import MAX_ATTEMPTS

    for _ in range(MAX_ATTEMPTS + 1):
        client.post("/api/v1/login", json={"username": "afitsant", "password": "yolgon"})

    token = csrf(client, "/login")
    response = client.post(
        "/login",
        data={"username": "afitsant", "password": "waiterpass123", "csrf_token": token},
    )
    # Shablon apostrofni &#39; qilib qochiradi
    assert "Juda ko'p urinish" in html.unescape(response.text)


# --- kalit bilan ishlash ---------------------------------------------------


def test_orders_need_a_token(client, cafe):
    assert client.get("/api/v1/orders").status_code == 401
    assert client.get("/api/v1/orders", headers=auth("yolgon-kalit")).status_code == 401


def test_the_api_ignores_the_session_cookie(client, cafe):
    """Eng muhim tekshiruv.

    Brauzerda kirgan odamning cookie'si API so'roviga avtomatik qo'shiladi.
    API uni qabul qilsa, boshqa saytdagi forma foydalanuvchi nomidan
    buyurtma holatini o'zgartira olardi — bu yerda CSRF himoyasi yo'q.
    """
    login(client, "afitsant", "waiterpass123")   # sessiya cookie'si o'rnatildi
    assert client.get("/zal").status_code == 200  # brauzer taxtasi ochiladi

    assert client.get("/api/v1/orders").status_code == 401  # API esa yo'q


def test_the_token_survives_across_requests(client, cafe):
    token = sign_in(client)
    client.cookies.clear()
    assert client.get("/api/v1/orders", headers=auth(token)).status_code == 200


def test_blocking_a_waiter_kills_the_token_at_once(client, db, cafe):
    """JWT bo'lganda ishdan bo'shagan odam telefonida buyurtmani ko'rib turardi."""
    token = sign_in(client)
    assert client.get("/api/v1/orders", headers=auth(token)).status_code == 200

    staff = db.query(User).filter(User.username == "afitsant").one()
    staff.is_active = False
    db.commit()

    assert client.get("/api/v1/orders", headers=auth(token)).status_code == 401


def test_deleting_a_waiter_removes_the_token(client, db, cafe):
    token = sign_in(client)
    staff = db.query(User).filter(User.username == "afitsant").one()

    login(client, "osh", "adminpass123")
    client.post(
        f"/admin/staff/{staff.id}/delete",
        data={"csrf_token": csrf(client, "/admin/staff")},
    )
    client.cookies.clear()

    db.expire_all()
    assert db.query(ApiToken).count() == 0
    assert client.get("/api/v1/orders", headers=auth(token)).status_code == 401


def test_logout_kills_only_this_device(client, db, cafe):
    first = sign_in(client)
    second = sign_in(client)

    assert client.post("/api/v1/logout", headers=auth(first)).status_code == 200
    assert client.get("/api/v1/orders", headers=auth(first)).status_code == 401
    # Ikkinchi telefon ishlayveradi
    assert client.get("/api/v1/orders", headers=auth(second)).status_code == 200


def test_old_tokens_are_trimmed(client, db, cafe):
    """Har kirish yozuv qoldiradi — ular yillar davomida yig'ilib qolmasin."""
    for _ in range(tokens.MAX_PER_USER + 3):
        sign_in(client)
    assert db.query(ApiToken).count() == tokens.MAX_PER_USER


# --- buyurtmalar -----------------------------------------------------------


def test_the_order_list_carries_what_the_app_shows(client, db, cafe):
    place_order(client, cafe, db, quantity=2)
    token = sign_in(client)

    data = client.get("/api/v1/orders", headers=auth(token)).json()
    assert len(data["orders"]) == 1

    order = data["orders"][0]
    assert order["table"] == "4"
    assert order["status"] == "new"
    assert order["total"] == 76000
    assert order["lines"] == [{"name": "Osh", "quantity": 2, "price": 38000}]
    # Vaqt UTC belgisi bilan — ilova uni o'z mintaqasida o'qib adashmasin
    assert order["created_at"].endswith("Z")


def test_the_app_moves_an_order_through_its_states(client, db, cafe):
    place_order(client, cafe, db)
    token = sign_in(client)
    order = db.query(Order).one()

    accepted = client.post(
        f"/api/v1/orders/{order.id}/status", json={"status": "accepted"}, headers=auth(token)
    )
    assert accepted.json()["status"] == "accepted"

    client.post(
        f"/api/v1/orders/{order.id}/status", json={"status": "served"}, headers=auth(token)
    )
    db.expire_all()
    assert db.query(Order).one().status is OrderStatus.served
    # Yopilgan buyurtma ro'yxatdan tushadi
    assert client.get("/api/v1/orders", headers=auth(token)).json()["orders"] == []


def test_an_unknown_status_is_refused(client, db, cafe):
    place_order(client, cafe, db)
    token = sign_in(client)
    order = db.query(Order).one()

    response = client.post(
        f"/api/v1/orders/{order.id}/status", json={"status": "bepul"}, headers=auth(token)
    )
    assert response.status_code == 400


def test_another_restaurants_order_is_out_of_reach(client, db, cafe, tenant_b):
    other, _ = tenant_b
    foreign = Order(
        restaurant_id=other.id, table_label="1", code="begonaapi", note=None, total=500
    )
    db.add(foreign)
    db.commit()

    token = sign_in(client)
    response = client.post(
        f"/api/v1/orders/{foreign.id}/status", json={"status": "served"}, headers=auth(token)
    )
    assert response.status_code == 404
    db.expire_all()
    assert db.get(Order, foreign.id).status is OrderStatus.new


def test_the_list_only_shows_your_own_restaurant(client, db, cafe, tenant_b):
    other, _ = tenant_b
    db.add(Order(restaurant_id=other.id, table_label="1", code="begona2api", note=None, total=1))
    db.commit()

    token = sign_in(client)
    assert client.get("/api/v1/orders", headers=auth(token)).json()["orders"] == []


# --- qurilmalar ------------------------------------------------------------


def test_a_device_registers_for_notifications(client, db, cafe):
    token = sign_in(client)
    response = client.post(
        "/api/v1/devices",
        json={"expo_token": "ExponentPushToken[abc123]", "platform": "android"},
        headers=auth(token),
    )
    assert response.status_code == 200

    row = db.query(AppDevice).one()
    assert row.user.username == "afitsant"
    assert row.platform == "android"


def test_registering_twice_does_not_pile_up(client, db, cafe):
    token = sign_in(client)
    for _ in range(3):
        client.post(
            "/api/v1/devices",
            json={"expo_token": "ExponentPushToken[abc123]"},
            headers=auth(token),
        )
    assert db.query(AppDevice).count() == 1


def test_a_device_moves_to_its_new_owner(client, db, cafe):
    """Umumiy planshet boshqa xodimga o'tsa eskisi bildirishnoma olmasin."""
    first = sign_in(client)
    client.post(
        "/api/v1/devices",
        json={"expo_token": "ExponentPushToken[shared]"},
        headers=auth(first),
    )

    second = sign_in(client, "osh", "adminpass123")
    client.post(
        "/api/v1/devices",
        json={"expo_token": "ExponentPushToken[shared]"},
        headers=auth(second),
    )

    db.expire_all()
    row = db.query(AppDevice).one()
    assert row.user.username == "osh"


def test_a_bogus_device_token_is_refused(client, db, cafe):
    token = sign_in(client)
    response = client.post(
        "/api/v1/devices", json={"expo_token": "yolgon"}, headers=auth(token)
    )
    assert response.status_code == 400
    assert db.query(AppDevice).count() == 0


def test_a_device_can_be_forgotten(client, db, cafe):
    token = sign_in(client)
    client.post(
        "/api/v1/devices",
        json={"expo_token": "ExponentPushToken[bye]"},
        headers=auth(token),
    )
    client.request(
        "DELETE",
        "/api/v1/devices?expo_token=ExponentPushToken[bye]",
        headers=auth(token),
    )
    assert db.query(AppDevice).count() == 0


# --- bildirishnoma yuborish ------------------------------------------------


def test_an_order_reaches_app_devices(client, db, cafe, monkeypatch):
    from app.services import push

    token = sign_in(client)
    client.post(
        "/api/v1/devices",
        json={"expo_token": "ExponentPushToken[live]"},
        headers=auth(token),
    )
    client.cookies.clear()

    sent = []
    monkeypatch.setattr(push, "_expo_send", lambda tokens_, seat_='', order_='': sent.extend(tokens_) or [{}])
    place_order(client, cafe, db)

    assert sent == ["ExponentPushToken[live]"]


def test_an_uninstalled_app_is_cleaned_up(db, cafe, monkeypatch):
    """Expo "DeviceNotRegistered" desa qurilma o'chadi."""
    from app.services import push

    staff = db.query(User).filter(User.username == "afitsant").one()
    db.add(AppDevice(user_id=staff.id, expo_token="ExponentPushToken[gone]"))
    db.commit()

    monkeypatch.setattr(
        push,
        "_expo_send",
        lambda tokens_, seat_="", order_="": [{"status": "error", "details": {"error": "DeviceNotRegistered"}}],
    )
    push.notify_restaurant(cafe.id)

    db.expire_all()
    assert db.query(AppDevice).count() == 0


def test_a_working_device_survives(db, cafe, monkeypatch):
    from app.services import push

    staff = db.query(User).filter(User.username == "afitsant").one()
    db.add(AppDevice(user_id=staff.id, expo_token="ExponentPushToken[ok]"))
    db.commit()

    monkeypatch.setattr(push, "_expo_send", lambda tokens_, seat_="", order_="": [{"status": "ok"}])
    push.notify_restaurant(cafe.id)

    db.expire_all()
    assert db.query(AppDevice).count() == 1


def test_expo_failure_never_breaks_the_order(client, db, cafe, monkeypatch):
    from app.services import push

    staff = db.query(User).filter(User.username == "afitsant").one()
    db.add(AppDevice(user_id=staff.id, expo_token="ExponentPushToken[boom]"))
    db.commit()

    def explode(tokens_):
        raise OSError("tarmoq yo'q")

    monkeypatch.setattr(push, "_expo_send", explode)
    place_order(client, cafe, db)

    assert db.query(Order).count() == 1
    assert db.query(AppDevice).count() == 1


def test_the_app_works_without_vapid_keys(client, db, cafe, monkeypatch):
    """Ilova bildirishnomasi VAPID'ga bog'liq emas — Expo o'z yo'li bilan yuboradi."""
    from app.config import settings
    from app.services import push

    monkeypatch.setattr(settings, "vapid_public_key", "")
    monkeypatch.setattr(settings, "vapid_private_key", "")

    staff = db.query(User).filter(User.username == "afitsant").one()
    db.add(AppDevice(user_id=staff.id, expo_token="ExponentPushToken[novapid]"))
    db.commit()

    sent = []
    monkeypatch.setattr(push, "_expo_send", lambda tokens_, seat_='', order_='': sent.extend(tokens_) or [{}])
    push.notify_restaurant(cafe.id)

    assert sent == ["ExponentPushToken[novapid]"]


# --- yangilanish -----------------------------------------------------------


def test_the_app_learns_about_updates(client):
    """APK do'kondan emas, saytdan tarqatiladi — yangilanishni ilovaga
    o'zimiz aytishimiz kerak, buni boshqa hech kim qilmaydi."""
    data = client.get("/api/v1/app/latest").json()
    assert data["version"]
    assert data["apk_url"].startswith("http")


def test_the_released_version_comes_from_the_settings(monkeypatch, client):
    """Yangi APK qo'yilganda faqat `.env` o'zgarishi kerak, kod emas.

    Ilgari versiya kodda qotib turardi va `.env` dagi APP_VERSION hech
    qayerda ishlatilmasdi — server yangi APK'ni berib turib, ilovaga
    "eng oxirgisi sizda" deb aytardi va hech kim yangilanmasdi.
    """
    from app.config import settings

    monkeypatch.setattr(settings, "app_version", "9.9.9")
    assert client.get("/api/v1/app/latest").json()["version"] == "9.9.9"


def test_the_update_link_is_not_the_cached_one(client):
    """Caddy `/static/*` ga 30 kunlik kesh qo'yadi.

    Yangilanish havolasi o'sha yerga qarasa, yangi APK qo'yilgani bilan
    telefon eskisini olib kelaverardi — ya'ni "yangilanish bor" deb turib,
    eskisini bergan bo'lardik. Havola keshlanmaydigan marshrutga qaraydi.
    """
    data = client.get("/api/v1/app/latest").json()
    assert "/static/" not in data["apk_url"]
    assert data["apk_url"].endswith("/ilova/yuklash")

    # ...va o'sha marshrut haqiqatan keshlanmaslikni aytadi
    head = client.get("/ilova/yuklash")
    if head.status_code == 200:
        assert "no-cache" in head.headers.get("cache-control", "")
