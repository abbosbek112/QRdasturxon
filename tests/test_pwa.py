"""Afitsant ilovasi (PWA).

Eng muhim ikki qoida shu yerda qulflanadi:

* ilova FAQAT afitsant taxtasiga o'rnatiladi — mijoz menyusida "ilova
  o'rnatasizmi?" degan taklif chiqishi QR skanerlagan odamga xalaqit berardi;
* service worker keshlanmaydi — aks holda yangilangan nusxa afitsantga
  bir oygacha yetib bormasdi (Caddy `/static/*` ga 30 kunlik kesh qo'yadi).
"""

import html
import json
import re

import pytest

from app.models import Category, MenuItem, PushSubscription, Role, Table, User
from app.security import hash_password

from tests.conftest import csrf, login


@pytest.fixture
def cafe(db, tenant_a):
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
            Table(restaurant_id=restaurant.id, label="1", code="stolkod1"),
        ]
    )
    db.add(
        User(
            username="afitsant",
            password_hash=hash_password("waiterpass123"),
            role=Role.waiter,
            restaurant_id=restaurant.id,
        )
    )
    db.commit()
    return restaurant


# --- manifest --------------------------------------------------------------


def test_the_manifest_is_served(client):
    response = client.get("/static/manifest.webmanifest")
    assert response.status_code == 200

    data = json.loads(response.text)
    assert data["start_url"] == "/zal"
    assert data["display"] == "standalone"
    # Sessiya tugab /login ga o'tganda ilova o'z oynasida qolsin
    assert data["scope"] == "/"


def test_the_manifest_ships_a_maskable_icon(client):
    """Android ikonkani o'z shakliga qirqadi — maskali variantsiz belgi kesiladi."""
    data = json.loads(client.get("/static/manifest.webmanifest").text)
    purposes = {icon["purpose"] for icon in data["icons"]}
    assert "maskable" in purposes and "any" in purposes

    for icon in data["icons"]:
        assert client.get(icon["src"]).status_code == 200


def test_only_the_hall_is_installable(client, cafe):
    """Mijoz menyusi va egasining paneli o'rnatilmaydigan bo'lib qolsin."""
    login(client, "afitsant", "waiterpass123")
    assert 'rel="manifest"' in client.get("/zal").text

    client.cookies.clear()
    login(client, "osh", "adminpass123")
    assert 'rel="manifest"' not in client.get("/admin").text

    client.cookies.clear()
    assert 'rel="manifest"' not in client.get(f"/r/{cafe.slug}").text
    assert 'rel="manifest"' not in client.get("/").text


# --- service worker --------------------------------------------------------


def test_the_service_worker_is_served_from_the_root(client):
    """Ildizdan bo'lishi shart: worker faqat o'z papkasidan pastini boshqaradi."""
    response = client.get("/sw.js")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/javascript")
    assert "addEventListener" in response.text


def test_the_service_worker_is_not_cached(client):
    """Eski nusxa qolib ketsa yangilanish umuman yetib bormaydi."""
    response = client.get("/sw.js")
    assert response.headers.get("cache-control") == "no-cache"
    assert response.headers.get("service-worker-allowed") == "/"


def test_the_service_worker_never_caches_orders(client):
    """Eskirgan buyurtmani ko'rsatish ko'rsatmaslikdan yomonroq.

    Afitsant allaqachon berilgan taomni yana olib kelardi. Himoya —
    `fetch` ishlovchisidagi qorovul: `/static/` dan boshqasiga umuman
    aralashmaydi, ya'ni sahifalar ham, `/zal/list` ham keshga tushmaydi.
    """
    body = client.get("/sw.js").text
    assert 'url.pathname.indexOf("/static/") !== 0' in body


def test_the_service_worker_needs_no_login(client):
    """Brauzer worker'ni sessiyasiz ham so'raydi — u yopiq bo'lmasligi kerak."""
    assert client.get("/sw.js").status_code == 200


# --- taxtadagi tasmalar ----------------------------------------------------


def test_the_board_offers_to_install(client, cafe):
    login(client, "afitsant", "waiterpass123")
    body = html.unescape(client.get("/zal?lang=uz").text)
    assert 'id="installBar"' in body
    assert "Ilovani o'rnatish" in body
    # iPhone yo'riqnomasi ham sahifada tayyor turadi
    assert "Bosh ekranga qo'shish" in body


def test_the_board_offers_notifications(client, cafe):
    login(client, "afitsant", "waiterpass123")
    body = client.get("/zal?lang=ru").text
    assert 'id="notifyBar"' in body
    assert "Включить уведомления" in body


def test_the_app_texts_follow_the_language(client, cafe):
    login(client, "afitsant", "waiterpass123")
    assert "Install the app" in client.get("/zal?lang=en").text
    assert "Установить приложение" in client.get("/zal?lang=ru").text


# --- bildirishnoma (Web Push) ----------------------------------------------


@pytest.fixture
def keys(monkeypatch):
    """Haqiqiy VAPID juftligi — imzo aslida tekshirilsin."""
    from app.config import settings
    from scripts.vapid_keys import generate

    public, private = generate()
    monkeypatch.setattr(settings, "vapid_public_key", public)
    monkeypatch.setattr(settings, "vapid_private_key", private)
    return public, private


def subscribe(client, endpoint="https://fcm.googleapis.com/fcm/send/abc"):
    return client.post(
        "/zal/push/subscribe",
        data={
            "csrf_token": csrf(client, "/zal"),
            "endpoint": endpoint,
            "p256dh": "BKxQ",
            "auth": "c2Vj",
        },
    )


def test_a_waiter_subscribes_a_device(client, db, cafe):
    login(client, "afitsant", "waiterpass123")
    assert subscribe(client).status_code == 204

    row = db.query(PushSubscription).one()
    assert row.user.username == "afitsant"
    assert row.endpoint.startswith("https://")


def test_subscribing_twice_does_not_pile_up(client, db, cafe):
    """Bir qurilma qayta obuna bo'lsa yozuv ko'paymasin."""
    login(client, "afitsant", "waiterpass123")
    subscribe(client)
    subscribe(client)
    assert db.query(PushSubscription).count() == 1


def test_a_stranger_cannot_subscribe(client, db, cafe):
    """Marshrut zal ruxsati ortida — begona odam obuna yozdira olmaydi.

    Kirmagan odam login sahifasiga yuboriladi, ya'ni oxirgi holat 200 bo'ladi.
    Tekshiriladigan narsa holat emas: bazaga hech narsa tushmasligi.
    """
    response = subscribe(client)
    assert response.url.path == "/login"
    assert db.query(PushSubscription).count() == 0


def test_subscribing_needs_a_csrf_token(client, db, cafe):
    login(client, "afitsant", "waiterpass123")
    response = client.post(
        "/zal/push/subscribe",
        data={"endpoint": "https://x.example/1", "p256dh": "a", "auth": "b"},
    )
    assert response.status_code == 403
    assert db.query(PushSubscription).count() == 0


def test_a_plain_http_endpoint_is_refused(client, db, cafe):
    login(client, "afitsant", "waiterpass123")
    response = client.post(
        "/zal/push/subscribe",
        data={
            "csrf_token": csrf(client, "/zal"),
            "endpoint": "http://yolgon.example/1",
            "p256dh": "a",
            "auth": "b",
        },
    )
    assert response.status_code == 400
    assert db.query(PushSubscription).count() == 0


def test_unsubscribing_removes_the_device(client, db, cafe):
    login(client, "afitsant", "waiterpass123")
    subscribe(client)
    response = client.post(
        "/zal/push/unsubscribe",
        data={
            "csrf_token": csrf(client, "/zal"),
            "endpoint": "https://fcm.googleapis.com/fcm/send/abc",
        },
    )
    assert response.status_code == 204
    assert db.query(PushSubscription).count() == 0


def test_deleting_a_waiter_takes_their_devices(client, db, cafe):
    """Xodim ketgach uning telefoniga bildirishnoma bormasin."""
    login(client, "afitsant", "waiterpass123")
    subscribe(client)

    client.cookies.clear()
    login(client, "osh", "adminpass123")
    staff = db.query(User).filter(User.username == "afitsant").one()
    client.post(
        f"/admin/staff/{staff.id}/delete",
        data={"csrf_token": csrf(client, "/admin/staff")},
    )

    db.expire_all()
    assert db.query(PushSubscription).count() == 0


# --- /zal/ping -------------------------------------------------------------


def test_the_ping_describes_the_newest_order(client, db, cafe):
    """Push mazmunsiz keladi — matn shu yerda, o'z serverimizda yasaladi."""
    table = db.query(Table).one()
    client.get(f"/r/{cafe.slug}/t/{table.code}")
    body = html.unescape(client.get(f"/r/{cafe.slug}").text)
    token = re.search(r'name="csrf_token" value="([^"]+)"', body).group(1)
    item = db.query(MenuItem).one()
    client.post(
        f"/r/{cafe.slug}/order",
        data={"csrf_token": token, "item_id": [item.id], "qty": [2]},
    )

    client.cookies.clear()
    login(client, "afitsant", "waiterpass123")
    data = client.get("/zal/ping?lang=uz").json()

    assert data["new"] == 1
    assert "1-stol" in data["text"]
    assert "2× Osh" in data["text"]
    assert data["title"] == "Yangi buyurtma"


def test_the_ping_is_closed_to_strangers(client, cafe):
    """Kirmagan odam buyurtma matnini ololmasin — login'ga yuboriladi."""
    response = client.get("/zal/ping")
    assert response.url.path == "/login"
    assert "new" not in response.text


def test_the_ping_only_counts_your_own_restaurant(client, db, cafe, tenant_b):
    from app.models import Order

    other, _ = tenant_b
    db.add(
        Order(
            restaurant_id=other.id, table_label="9", code="begonapush", note=None, total=1
        )
    )
    db.commit()

    login(client, "afitsant", "waiterpass123")
    assert client.get("/zal/ping").json()["new"] == 0


# --- yuborish --------------------------------------------------------------


def test_the_vapid_header_is_a_signed_jwt(keys):
    """Imzo xom r||s bo'lishi shart — DER bilan push serveri rad etadi."""
    import base64 as b64
    import json as js

    from app.services import push

    header = push._authorization("https://fcm.googleapis.com/fcm/send/abc")
    assert header.startswith("vapid t=")

    token = header[len("vapid t=") :].split(",")[0]
    parts = token.split(".")
    assert len(parts) == 3

    def unpad(text):
        return b64.urlsafe_b64decode(text + "=" * (-len(text) % 4))

    assert js.loads(unpad(parts[0]))["alg"] == "ES256"
    claims = js.loads(unpad(parts[1]))
    # `aud` push serverining ILDIZI — to'liq manzil qo'yilsa imzo rad etiladi
    assert claims["aud"] == "https://fcm.googleapis.com"
    assert claims["sub"].startswith("mailto:")
    assert len(unpad(parts[2])) == 64


def test_a_dead_subscription_is_cleaned_up(db, cafe, keys, monkeypatch):
    """410 — afitsant ilovani o'chirgan. Jadval axlat bilan to'lmasin."""
    from app.services import push

    staff = db.query(User).filter(User.username == "afitsant").one()
    push.save(db, staff, "https://fcm.googleapis.com/fcm/send/dead", "a", "b")

    monkeypatch.setattr(push, "_deliver", lambda endpoint: 410)
    push.notify_restaurant(cafe.id)

    db.expire_all()
    assert db.query(PushSubscription).count() == 0


def test_a_live_subscription_survives(db, cafe, keys, monkeypatch):
    from app.services import push

    staff = db.query(User).filter(User.username == "afitsant").one()
    push.save(db, staff, "https://fcm.googleapis.com/fcm/send/live", "a", "b")

    monkeypatch.setattr(push, "_deliver", lambda endpoint: 201)
    push.notify_restaurant(cafe.id)

    db.expire_all()
    assert db.query(PushSubscription).count() == 1


def test_sending_never_raises(db, cafe, keys, monkeypatch):
    """Bildirishnoma xatosi allaqachon qabul qilingan buyurtmani buzmasin."""
    from app.services import push

    staff = db.query(User).filter(User.username == "afitsant").one()
    push.save(db, staff, "https://fcm.googleapis.com/fcm/send/boom", "a", "b")

    def explode(endpoint):
        raise OSError("tarmoq yo'q")

    monkeypatch.setattr(push, "_deliver", explode)
    push.notify_restaurant(cafe.id)  # xato tashlamasligi kerak

    db.expire_all()
    assert db.query(PushSubscription).count() == 1


def test_push_stays_quiet_without_keys(db, cafe, monkeypatch):
    """Kalit unutilgani sababli buyurtma qabul qilinmay qolishi mumkin emas."""
    from app.config import settings
    from app.services import push

    monkeypatch.setattr(settings, "vapid_public_key", "")
    monkeypatch.setattr(settings, "vapid_private_key", "")

    called = []
    monkeypatch.setattr(push, "_deliver", lambda endpoint: called.append(endpoint) or 201)
    push.notify_restaurant(cafe.id)
    assert called == []


def test_the_board_hides_the_key_when_push_is_off(client, cafe, monkeypatch):
    """Kalit sozlanmagan bo'lsa sahifa bo'sh qiymat beradi va hall.js
    obunani umuman qilmaydi.

    Kalit ATAYLAB monkeypatch bilan tozalanadi: aks holda test ishlab
    chiquvchining `.env` fayliga bog'lanib qolardi va boshqa mashinada
    boshqacha natija berardi.
    """
    from app.config import settings

    monkeypatch.setattr(settings, "vapid_public_key", "")
    monkeypatch.setattr(settings, "vapid_private_key", "")

    login(client, "afitsant", "waiterpass123")
    assert 'data-vapid=""' in client.get("/zal").text


def test_the_board_publishes_the_public_key_only(client, cafe, keys):
    public, private = keys
    login(client, "afitsant", "waiterpass123")
    body = client.get("/zal").text
    assert public in body
    assert private not in body        # maxfiy kalit hech qachon sahifada bo'lmasin


def test_ordering_still_works_when_push_explodes(client, db, cafe, keys, monkeypatch):
    """Bildirishnoma bosqichi yiqilsa ham buyurtma qabul qilinaveradi.

    `notify_restaurant` ning o'zi qorovul — shuning uchun uni emas, uning
    ICHIDAGI qismni buzamiz. Aks holda test qorovulni chetlab o'tib,
    haqiqiy kod yo'lini umuman tekshirmagan bo'lardi.
    """
    from app.models import Order
    from app.services import push

    def explode(db_session, restaurant_id):
        raise RuntimeError("push yiqildi")

    monkeypatch.setattr(push, "_waiter_ids", explode)

    table = db.query(Table).one()
    client.get(f"/r/{cafe.slug}/t/{table.code}")
    body = client.get(f"/r/{cafe.slug}").text
    token = re.search(r'name="csrf_token" value="([^"]+)"', body).group(1)
    item = db.query(MenuItem).one()

    response = client.post(
        f"/r/{cafe.slug}/order",
        data={"csrf_token": token, "item_id": [item.id], "qty": [1]},
    )
    assert response.status_code == 200
    assert db.query(Order).count() == 1


# --- ilovani yuklab olish sahifasi -----------------------------------------


def test_the_download_page_opens_without_login(client):
    """Afitsant ilovani o'rnatishdan OLDIN kirmagan bo'ladi."""
    response = client.get("/ilova")
    assert response.status_code == 200
    assert "TestFlight" in response.text or "iPhone" in response.text


def test_the_page_offers_both_platforms(client):
    body = html.unescape(client.get("/ilova?lang=uz").text)
    assert 'data-for="android"' in body
    assert 'data-for="ios"' in body
    # Kompyuterda telefonga o'tish uchun QR
    assert 'data-for="desktop"' in body and "<svg" in body


def test_the_apk_link_is_absent_until_the_file_exists(client):
    """Ilova hali yig'ilmagan bo'lsa ishlamaydigan tugma ko'rsatilmasin."""
    from app.routers import public

    ready = public._apk_path().exists()
    body = client.get("/ilova?lang=uz").text
    if ready:
        assert "/ilova/yuklash" in body
    else:
        assert "/ilova/yuklash" not in body
        assert "Tez orada" in html.unescape(body)


def test_downloading_before_the_build_gives_a_clear_answer(client):
    from app.routers import public

    if public._apk_path().exists():
        pytest.skip("APK mavjud — bu holat tekshirilmaydi")
    response = client.get("/ilova/yuklash")
    assert response.status_code == 404
    assert "hali yuklanmagan" in html.unescape(response.text)


def test_the_apk_is_served_uncached(client, tmp_path, monkeypatch):
    """Caddy /static/* ga 30 kunlik kesh qo'yadi.

    APK o'sha yerdan berilsa yangi versiya bir xil nom bilan chiqqanda eskisi
    berilib turardi — shuning uchun u alohida marshrutdan keladi.
    """
    from app.routers import public

    fake = tmp_path / "qrdasturxon-zal.apk"
    fake.write_bytes(b"PK\x03\x04 soxta apk")
    monkeypatch.setattr(public, "_apk_path", lambda: fake)

    response = client.get("/ilova/yuklash")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["content-type"] == "application/vnd.android.package-archive"
    assert "qrdasturxon-zal.apk" in response.headers["content-disposition"]


def test_the_page_shows_the_testflight_link_when_set(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "testflight_url", "https://testflight.apple.com/join/abc123")
    body = client.get("/ilova").text
    assert "https://testflight.apple.com/join/abc123" in body


def test_without_testflight_iphone_users_get_the_pwa_route(client, monkeypatch):
    """Sahifa hech qachon bo'sh qolmasin — PWA yo'li ko'rsatiladi."""
    from app.config import settings

    monkeypatch.setattr(settings, "testflight_url", "")
    body = html.unescape(client.get("/ilova?lang=uz").text)
    assert "Bosh ekranga qo'shish" in body
