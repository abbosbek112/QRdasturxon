"""Stoldan buyurtma berish.

Bu yerdagi eng muhim tekshiruvlar mijoz brauzeriga ISHONMASLIK haqida:
narx bazadan olinadi, taomning restoranga tegishliligi tekshiriladi, afitsant
esa menyuga umuman yaqinlasha olmaydi.
"""

import html
import re
from datetime import timedelta

import pytest

from app.models import (
    Category,
    MenuItem,
    Order,
    OrderStatus,
    Role,
    Table,
    User,
    utcnow_naive,
)
from app.security import hash_password
from app.services import orders, tables

from tests.conftest import csrf, login, make_restaurant


@pytest.fixture
def cafe(db, tenant_a):
    """Buyurtma yoqilgan restoran, bitta stol va bitta taom."""
    restaurant, _ = tenant_a
    restaurant.orders_enabled = True
    restaurant.order_window_minutes = 30

    category = Category(restaurant_id=restaurant.id, name={"uz": "Taomlar"})
    db.add(category)
    db.flush()
    item = MenuItem(
        restaurant_id=restaurant.id,
        category_id=category.id,
        name={"uz": "Osh"},
        price=38000,
    )
    table = Table(restaurant_id=restaurant.id, label="7", code="stolkod7")
    db.add_all([item, table])
    db.commit()
    return restaurant, table, item


def scan(client, restaurant, table):
    """Stoldagi QR ni skanerlash."""
    response = client.get(f"/r/{restaurant.slug}/t/{table.code}", follow_redirects=False)
    assert response.status_code == 303
    return response


def shift_clock(monkeypatch, minutes: int):
    """Soatni oldinga suradi.

    Ikkala modulda ham: `public.py` QR skanerlangan vaqtni yozadi, `orders.py`
    esa uni tekshiradi — ikkalasi `utcnow_naive` ni o'z nomlar fazosiga
    import qilgan, shuning uchun bittasini almashtirish yetmaydi.
    """
    from app.routers import public

    later = utcnow_naive() + timedelta(minutes=minutes)
    monkeypatch.setattr(orders, "utcnow_naive", lambda: later)
    monkeypatch.setattr(public, "utcnow_naive", lambda: later)
    return later


def order_form(client, restaurant):
    """CSRF tokeni.

    Odatda savat formasidan olinadi. Savat ko'rinmaydigan holatlarni ham
    tekshiramiz (stol yo'q, buyurtma o'chirilgan) — o'shanda token boshqa
    sahifadan olinadi, chunki sessiya bitta.
    """
    html = client.get(f"/r/{restaurant.slug}").text
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    return match.group(1) if match else csrf(client, "/login")


# --- stol havolasi --------------------------------------------------------


def test_scanning_a_table_qr_opens_the_cart(client, cafe):
    restaurant, table, _ = cafe
    scan(client, restaurant, table)

    body = client.get(f"/r/{restaurant.slug}").text
    assert 'id="cart"' in body
    assert "7-stol" in body


def test_the_menu_has_no_cart_without_a_table(client, cafe):
    """Havolani to'g'ridan-to'g'ri ochgan odam buyurtma bera olmasin."""
    restaurant, _, _ = cafe
    assert 'id="cart"' not in client.get(f"/r/{restaurant.slug}").text


def test_the_table_code_never_reaches_the_address_bar(client, cafe):
    """Kod sessiyada qoladi.

    Aks holda mijoz manzilni nusxalab do'stiga tashlasa, u uydan turib
    buyurtma bera olardi.
    """
    restaurant, table, _ = cafe
    response = scan(client, restaurant, table)
    assert response.headers["location"] == f"/r/{restaurant.slug}"
    assert table.code not in client.get(f"/r/{restaurant.slug}").text


def test_an_unknown_table_code_just_shows_the_menu(client, cafe):
    """Xato kod xato sahifasi emas — stolda o'tirgan mijoz bunga ta'sir qila olmaydi."""
    restaurant, _, _ = cafe
    response = client.get(f"/r/{restaurant.slug}/t/yolgonkod", follow_redirects=True)
    assert response.status_code == 200
    assert 'id="cart"' not in response.text


def test_a_table_from_another_restaurant_does_not_work(client, db, cafe, tenant_b):
    """Kod global unikal, lekin u faqat O'Z restoranida ochiladi."""
    restaurant, _, _ = cafe
    other, _ = tenant_b
    other.orders_enabled = True
    stranger = Table(restaurant_id=other.id, label="1", code="begonakod")
    db.add(stranger)
    db.commit()

    client.get(f"/r/{restaurant.slug}/t/begonakod", follow_redirects=False)
    assert 'id="cart"' not in client.get(f"/r/{restaurant.slug}").text


# --- buyurtma berish ------------------------------------------------------


def test_placing_an_order_lands_on_the_status_page(client, db, cafe):
    restaurant, table, item = cafe
    scan(client, restaurant, table)

    response = client.post(
        f"/r/{restaurant.slug}/order",
        data={
            "csrf_token": order_form(client, restaurant),
            "item_id": [item.id],
            "qty": [2],
            "note": "piyozsiz",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Osh" in response.text

    order = db.query(Order).one()
    assert order.table_label == "7"
    assert order.status is OrderStatus.new
    assert order.note == "piyozsiz"
    assert order.total == 76000


def test_the_price_comes_from_the_database_not_the_form(client, db, cafe):
    """Eng muhim tekshiruv.

    Sahifadagi narxni brauzer konsolidan o'zgartirib bo'ladi. Server esa
    narxni bazadan qayta o'qiydi, ya'ni arzonga buyurtma berib bo'lmaydi.
    """
    restaurant, table, item = cafe
    scan(client, restaurant, table)

    client.post(
        f"/r/{restaurant.slug}/order",
        data={
            "csrf_token": order_form(client, restaurant),
            "item_id": [item.id],
            "qty": [1],
            # Soxta narx — server bunga umuman qaramaydi
            "price": [1],
            "unit_price": [1],
            "total": [1],
        },
    )

    order = db.query(Order).one()
    assert order.total == 38000
    assert order.lines[0].unit_price == 38000


def test_a_dish_from_another_restaurant_is_dropped(client, db, cafe, tenant_b):
    restaurant, table, item = cafe
    other, _ = tenant_b
    category = Category(restaurant_id=other.id, name={"uz": "Boshqa"})
    db.add(category)
    db.flush()
    stranger = MenuItem(
        restaurant_id=other.id, category_id=category.id, name={"uz": "Somsa"}, price=9000
    )
    db.add(stranger)
    db.commit()

    scan(client, restaurant, table)
    client.post(
        f"/r/{restaurant.slug}/order",
        data={
            "csrf_token": order_form(client, restaurant),
            "item_id": [item.id, stranger.id],
            "qty": [1, 1],
        },
    )

    order = db.query(Order).one()
    assert [line.name for line in order.lines] == ["Osh"]
    assert order.total == 38000


def test_an_unavailable_dish_is_dropped(client, db, cafe):
    restaurant, table, item = cafe
    item.is_available = False
    db.commit()
    scan(client, restaurant, table)

    response = client.post(
        f"/r/{restaurant.slug}/order",
        data={"csrf_token": order_form(client, restaurant), "item_id": [item.id], "qty": [1]},
    )
    assert response.status_code == 400
    assert db.query(Order).count() == 0


def test_quantity_is_capped(client, db, cafe):
    restaurant, table, item = cafe
    scan(client, restaurant, table)

    client.post(
        f"/r/{restaurant.slug}/order",
        data={"csrf_token": order_form(client, restaurant), "item_id": [item.id], "qty": [9999]},
    )
    assert db.query(Order).one().lines[0].quantity == orders.MAX_QTY


def test_ordering_without_a_table_is_refused(client, cafe):
    restaurant, _, item = cafe
    response = client.post(
        f"/r/{restaurant.slug}/order",
        data={"csrf_token": order_form(client, restaurant), "item_id": [item.id], "qty": [1]},
    )
    assert response.status_code == 403


def test_an_expired_window_refuses_the_order(client, db, cafe, monkeypatch):
    """Oyna tugagach buyurtma ketmaydi — QR ni qayta skanerlash kerak."""
    restaurant, table, item = cafe
    scan(client, restaurant, table)
    token = order_form(client, restaurant)

    # QR skanerlangandan beri 61 daqiqa o'tdi, restoran oynasi esa 30 daqiqa
    shift_clock(monkeypatch, 61)

    response = client.post(
        f"/r/{restaurant.slug}/order",
        data={"csrf_token": token, "item_id": [item.id], "qty": [1]},
    )
    assert response.status_code == 403
    assert db.query(Order).count() == 0


def test_rescanning_the_qr_opens_a_new_window(client, db, cafe, monkeypatch):
    """Muddat tugagach mijoz QR ni qayta skanerlaydi va yana buyurtma beradi."""
    restaurant, table, item = cafe
    scan(client, restaurant, table)

    shift_clock(monkeypatch, 61)
    scan(client, restaurant, table)  # yangi oyna

    response = client.post(
        f"/r/{restaurant.slug}/order",
        data={
            "csrf_token": order_form(client, restaurant),
            "item_id": [item.id],
            "qty": [1],
        },
    )
    assert response.status_code == 200
    assert db.query(Order).count() == 1


def test_a_zero_window_never_expires(cafe):
    """0 = cheksiz: restoran xohlasa muddatni butunlay o'chira oladi."""
    restaurant, _, _ = cafe
    restaurant.order_window_minutes = 0
    assert orders.window_open(restaurant, utcnow_naive() - timedelta(days=3))


def test_orders_are_refused_when_the_switch_is_off(client, db, cafe):
    restaurant, table, item = cafe
    scan(client, restaurant, table)
    restaurant.orders_enabled = False
    db.commit()

    response = client.post(
        f"/r/{restaurant.slug}/order",
        data={"csrf_token": order_form(client, restaurant), "item_id": [item.id], "qty": [1]},
    )
    assert response.status_code == 403


def test_an_expired_restaurant_takes_no_orders(client, db, cafe):
    """Muddati tugagan restoranning menyusi ham, buyurtmasi ham yopiq."""
    restaurant, table, item = cafe
    scan(client, restaurant, table)
    restaurant.trial_ends_at = utcnow_naive() - timedelta(days=1)
    db.commit()

    response = client.post(
        f"/r/{restaurant.slug}/order",
        data={"csrf_token": order_form(client, restaurant), "item_id": [item.id], "qty": [1]},
    )
    assert response.status_code in (403, 503)
    assert db.query(Order).count() == 0


def test_a_table_cannot_flood_the_board(client, db, cafe):
    """Rasmga olingan QR bilan uydan spam qilayotgan odam shu yerda to'xtaydi."""
    restaurant, table, item = cafe
    scan(client, restaurant, table)

    codes = []
    for _ in range(orders.MAX_OPEN_PER_TABLE + 2):
        response = client.post(
            f"/r/{restaurant.slug}/order",
            data={"csrf_token": order_form(client, restaurant), "item_id": [item.id], "qty": [1]},
        )
        codes.append(response.status_code)

    assert db.query(Order).count() == orders.MAX_OPEN_PER_TABLE
    assert 429 in codes


# --- afitsant -------------------------------------------------------------


@pytest.fixture
def waiter(db, cafe):
    restaurant, _, _ = cafe
    user = User(
        username="afitsant",
        password_hash=hash_password("waiterpass123"),
        role=Role.waiter,
        restaurant_id=restaurant.id,
    )
    db.add(user)
    db.commit()
    return user


def test_a_waiter_sees_the_board(client, waiter):
    login(client, "afitsant", "waiterpass123")
    assert client.get("/zal").status_code == 200


def test_a_waiter_cannot_touch_the_menu(client, waiter):
    """Afitsantga egasining parolini bermaslikning butun ma'nosi shu."""
    login(client, "afitsant", "waiterpass123")
    for closed in ("/admin", "/admin/items", "/admin/settings", "/admin/tables"):
        assert client.get(closed).status_code == 403, closed


def test_login_sends_a_waiter_to_the_board(client, waiter):
    token = csrf(client, "/login")
    response = client.post(
        "/login",
        data={"username": "afitsant", "password": "waiterpass123", "csrf_token": token},
        follow_redirects=False,
    )
    assert response.headers["location"] == "/zal"


def test_a_waiter_cannot_touch_another_restaurants_order(client, db, cafe, tenant_b, waiter):
    other, _ = tenant_b
    stranger = Table(restaurant_id=other.id, label="1", code="begona2")
    db.add(stranger)
    db.flush()
    foreign = Order(
        restaurant_id=other.id,
        table_id=stranger.id,
        table_label="1",
        code="begonabuyurtma",
        note=None,
        total=1000,
    )
    db.add(foreign)
    db.commit()

    login(client, "afitsant", "waiterpass123")
    token = csrf(client, "/zal")
    response = client.post(
        f"/zal/orders/{foreign.id}/status",
        data={"csrf_token": token, "target": "served"},
    )
    assert response.status_code == 404
    assert db.get(Order, foreign.id).status is OrderStatus.new


def test_the_waiter_moves_an_order_through_its_states(client, db, cafe, waiter):
    restaurant, table, item = cafe
    scan(client, restaurant, table)
    client.post(
        f"/r/{restaurant.slug}/order",
        data={"csrf_token": order_form(client, restaurant), "item_id": [item.id], "qty": [1]},
    )
    order = db.query(Order).one()

    login(client, "afitsant", "waiterpass123")
    token = csrf(client, "/zal")
    client.post(f"/zal/orders/{order.id}/status", data={"csrf_token": token, "target": "accepted"})
    db.refresh(order)
    assert order.status is OrderStatus.accepted
    assert order.accepted_at is not None

    client.post(f"/zal/orders/{order.id}/status", data={"csrf_token": token, "target": "served"})
    db.refresh(order)
    assert order.status is OrderStatus.served
    assert order.closed_at is not None
    # Yopilgan buyurtma taxtadan tushadi
    assert orders.open_orders(db, restaurant.id) == []


def test_an_unknown_status_is_refused(client, db, cafe, waiter):
    restaurant, table, item = cafe
    scan(client, restaurant, table)
    client.post(
        f"/r/{restaurant.slug}/order",
        data={"csrf_token": order_form(client, restaurant), "item_id": [item.id], "qty": [1]},
    )
    order = db.query(Order).one()

    login(client, "afitsant", "waiterpass123")
    token = csrf(client, "/zal")
    response = client.post(
        f"/zal/orders/{order.id}/status", data={"csrf_token": token, "target": "bepul"}
    )
    assert response.status_code == 400


# --- stollar (egasi) ------------------------------------------------------


def test_bulk_create_numbers_the_room(client, db, cafe):
    restaurant, _, _ = cafe
    login(client, "osh", "adminpass123")
    client.post(
        "/admin/tables/bulk",
        data={"csrf_token": csrf(client, "/admin/tables"), "count": 5},
    )
    labels = sorted(table.label for table in tables.list_for(db, restaurant.id))
    assert labels == ["1", "2", "3", "4", "5", "7"]


def test_bulk_create_keeps_existing_codes(client, db, cafe):
    """Chop etilgan QR kodlar kuchini yo'qotmasligi kerak."""
    restaurant, table, _ = cafe
    before = table.code
    login(client, "osh", "adminpass123")
    client.post(
        "/admin/tables/bulk",
        data={"csrf_token": csrf(client, "/admin/tables"), "count": 10},
    )
    db.refresh(table)
    assert table.code == before


def test_every_table_gets_a_different_code(client, db, cafe):
    restaurant, _, _ = cafe
    login(client, "osh", "adminpass123")
    client.post(
        "/admin/tables/bulk",
        data={"csrf_token": csrf(client, "/admin/tables"), "count": 12},
    )
    codes = [table.code for table in tables.list_for(db, restaurant.id)]
    assert len(codes) == len(set(codes))


def test_refreshing_a_code_kills_the_old_qr(client, db, cafe):
    restaurant, table, _ = cafe
    old = table.code
    login(client, "osh", "adminpass123")
    client.post(
        f"/admin/tables/{table.id}/code",
        data={"csrf_token": csrf(client, "/admin/tables")},
    )
    db.refresh(table)
    assert table.code != old

    client.cookies.clear()
    client.get(f"/r/{restaurant.slug}/t/{old}", follow_redirects=False)
    assert 'id="cart"' not in client.get(f"/r/{restaurant.slug}").text


def test_the_print_sheet_carries_a_qr_per_table(client, db, cafe):
    restaurant, _, _ = cafe
    login(client, "osh", "adminpass123")
    client.post(
        "/admin/tables/bulk",
        data={"csrf_token": csrf(client, "/admin/tables"), "count": 3},
    )
    body = client.get("/admin/tables/print").text
    # Har stol uchun alohida SVG
    assert len(re.findall(r"<svg", body)) >= 3


def test_deleting_a_table_keeps_the_order_history(client, db, cafe):
    """Stol o'chsa ham tarixda "7" ko'rinib tursin."""
    restaurant, table, item = cafe
    scan(client, restaurant, table)
    client.post(
        f"/r/{restaurant.slug}/order",
        data={"csrf_token": order_form(client, restaurant), "item_id": [item.id], "qty": [1]},
    )

    client.cookies.clear()
    login(client, "osh", "adminpass123")
    client.post(
        f"/admin/tables/{table.id}/delete",
        data={"csrf_token": csrf(client, "/admin/tables")},
    )

    db.expire_all()
    order = db.query(Order).one()
    assert order.table_id is None
    assert order.table_label == "7"


def test_a_restaurant_cannot_reach_another_ones_table(client, db, cafe, tenant_b):
    other, _ = tenant_b
    stranger = Table(restaurant_id=other.id, label="1", code="begona3")
    db.add(stranger)
    db.commit()

    login(client, "osh", "adminpass123")
    assert client.get(f"/admin/tables/{stranger.id}/qr.png").status_code == 404


# --- xodimlar (egasi) -----------------------------------------------------


def test_the_owner_creates_a_waiter_account(client, db, cafe):
    login(client, "osh", "adminpass123")
    response = client.post(
        "/admin/staff",
        data={
            "csrf_token": csrf(client, "/admin/staff"),
            "username": "afitsant1",
            "password": "juda-uzun-parol",
        },
    )
    assert response.status_code == 200
    # Login restoran nomi bilan boshlanadi — buni tizim o'zi qo'shadi
    created = db.query(User).filter(User.username == "osh-markazi-afitsant1").one()
    assert created.role is Role.waiter
    assert created.restaurant_id == cafe[0].id


def test_a_short_password_is_refused(client, db, cafe):
    login(client, "osh", "adminpass123")
    response = client.post(
        "/admin/staff",
        data={"csrf_token": csrf(client, "/admin/staff"), "username": "qisqa", "password": "123"},
    )
    # Xato sahifasiga otvormaydi — xodimlar sahifasida sabab bilan qoladi
    assert response.status_code == 200
    assert response.url.path == "/admin/staff"
    assert "Parol kamida" in response.text
    assert db.query(User).filter(User.username == "qisqa").count() == 0


def test_the_owner_cannot_delete_their_own_account_through_staff(client, db, cafe):
    """Marshrut faqat `waiter` rolini qabul qiladi.

    Aks holda egasi shu yerdan o'z hisobini o'chirib, restoraniga kira
    olmay qolardi.
    """
    restaurant, _, _ = cafe
    owner = db.query(User).filter(User.username == "osh").one()

    login(client, "osh", "adminpass123")
    response = client.post(
        f"/admin/staff/{owner.id}/delete",
        data={"csrf_token": csrf(client, "/admin/staff")},
    )
    assert response.status_code == 404
    assert db.get(User, owner.id) is not None


def test_a_blocked_waiter_cannot_sign_in(client, db, cafe, waiter):
    waiter.is_active = False
    db.commit()

    token = csrf(client, "/login")
    response = client.post(
        "/login",
        data={"username": "afitsant", "password": "waiterpass123", "csrf_token": token},
    )
    assert response.status_code == 401


def test_a_waiter_of_another_restaurant_is_out_of_reach(client, db, cafe, tenant_b):
    other, _ = tenant_b
    stranger = User(
        username="begona-afitsant",
        password_hash=hash_password("waiterpass123"),
        role=Role.waiter,
        restaurant_id=other.id,
    )
    db.add(stranger)
    db.commit()

    login(client, "osh", "adminpass123")
    response = client.post(
        f"/admin/staff/{stranger.id}/delete",
        data={"csrf_token": csrf(client, "/admin/staff")},
    )
    assert response.status_code == 404


# --- sahifalar ------------------------------------------------------------


@pytest.mark.parametrize("path", ["/admin/tables", "/admin/staff", "/admin/orders"])
def test_owner_order_pages_render(client, cafe, path):
    login(client, "osh", "adminpass123")
    assert client.get(path).status_code == 200


def test_the_status_page_shows_the_order(client, db, cafe):
    restaurant, table, item = cafe
    scan(client, restaurant, table)
    client.post(
        f"/r/{restaurant.slug}/order",
        data={"csrf_token": order_form(client, restaurant), "item_id": [item.id], "qty": [3]},
    )
    order = db.query(Order).one()

    body = client.get(f"/r/{restaurant.slug}/order/{order.code}").text
    assert "Osh" in body
    assert "114 000" in body        # 38 000 × 3
    assert "7-stol" in body


def test_an_unknown_order_code_is_not_found(client, cafe):
    restaurant, _, _ = cafe
    assert client.get(f"/r/{restaurant.slug}/order/yolgon").status_code == 404


def test_an_order_code_from_another_restaurant_is_not_found(client, db, cafe, tenant_b):
    """Kod global unikal — lekin uni boshqa restoran manzilidan ochib bo'lmasin."""
    restaurant, _, _ = cafe
    other, _ = tenant_b
    foreign = Order(
        restaurant_id=other.id, table_label="1", code="begonakod9", note=None, total=100
    )
    db.add(foreign)
    db.commit()

    assert client.get(f"/r/{restaurant.slug}/order/begonakod9").status_code == 404


# --- forma xatosi sahifadan chiqarib yubormasin -----------------------------


def test_a_duplicate_table_keeps_you_on_the_page(client, db, cafe):
    """Takror raqam xato sahifasiga otvormasin.

    Egasi stollarni ketma-ket kiritib o'tirgan bo'ladi — bitta takror raqam
    uni ishidan uzib, boshqa sahifaga tashlab yuborishi kerak emas.
    """
    restaurant, table, _ = cafe

    response = client.post("/admin/tables", data={"label": table.label})  # login yo'q
    assert response.status_code in (303, 403)

    login(client, "osh", "adminpass123")
    response = client.post(
        "/admin/tables",
        data={"csrf_token": csrf(client, "/admin/tables"), "label": table.label},
    )

    assert response.status_code == 200
    assert response.url.path == "/admin/tables"          # xato sahifasi EMAS
    assert "allaqachon bor" in html.unescape(response.text)
    assert len(tables.list_for(db, restaurant.id)) == 1  # ikkinchisi qo'shilmadi


def test_the_message_is_shown_only_once(client, db, cafe):
    """Xabar sahifadan sahifaga ergashib yurmasin."""
    restaurant, table, _ = cafe
    login(client, "osh", "adminpass123")
    client.post(
        "/admin/tables",
        data={"csrf_token": csrf(client, "/admin/tables"), "label": table.label},
    )
    assert "allaqachon bor" not in html.unescape(client.get("/admin/tables").text)


def test_a_bad_table_count_keeps_you_on_the_page(client, cafe):
    login(client, "osh", "adminpass123")
    response = client.post(
        "/admin/tables",
        data={"csrf_token": csrf(client, "/admin/tables"), "label": "   "},
    )
    assert response.status_code == 200
    assert response.url.path == "/admin/tables"
    assert "bo'sh bo'lmasin" in html.unescape(response.text)


def test_a_taken_waiter_login_keeps_you_on_the_page(client, cafe):
    login(client, "osh", "adminpass123")
    # Bir xil nom bilan ikki marta — ikkinchisi band bo'lishi kerak
    for _ in range(2):
        response = client.post(
            "/admin/staff",
            data={
                "csrf_token": csrf(client, "/admin/staff"),
                "username": "afitsant",
                "password": "juda-uzun-parol",
            },
        )
    assert response.status_code == 200
    assert response.url.path == "/admin/staff"
    assert "band" in html.unescape(response.text)


def test_a_real_forbidden_still_reaches_the_error_page(client, db, cafe, tenant_b):
    """Yumshoq xabar FAQAT forma xatosi uchun.

    403/404 ni ham xabarga aylantirish haqiqiy muammoni yashirardi — masalan
    boshqa restoranning stoliga tegishga urinishni.
    """
    other, _ = tenant_b
    stranger = Table(restaurant_id=other.id, label="9", code="begona9")
    db.add(stranger)
    db.commit()

    login(client, "osh", "adminpass123")
    response = client.post(
        f"/admin/tables/{stranger.id}/delete",
        data={"csrf_token": csrf(client, "/admin/tables")},
    )
    assert response.status_code == 404


# --- xato sahifasidagi "Orqaga" --------------------------------------------


def test_the_error_page_goes_back_where_you_came_from(client, cafe):
    """Ilgari doim "/" edi — panelda ishlayotgan odam reklama sahifasiga tushardi."""
    login(client, "osh", "adminpass123")
    response = client.get(
        "/admin/items/999999/edit", headers={"referer": "http://testserver/admin/items"}
    )
    assert response.status_code == 404
    assert 'href="http://testserver/admin/items"' in response.text


def test_the_back_link_ignores_a_foreign_referer(client, cafe):
    """Referer brauzerdan keladi.

    Uni tekshirmasak sahifamiz boshqa saytga yo'naltirish quroliga aylanardi.
    """
    login(client, "osh", "adminpass123")
    response = client.get(
        "/admin/items/999999/edit", headers={"referer": "https://yomon-sayt.example/tuzoq"}
    )
    assert "yomon-sayt.example" not in response.text
    # Panelda ishlayotgan odam reklama sahifasiga emas, panelga qaytadi
    assert 'href="/admin"' in response.text


def test_the_back_link_falls_back_without_a_referer(client, cafe):
    """Referer bo'lmasa ham panelda qolinadi.

    Ilgari bosh sahifaga tashlanardi: panelda ishlayotgan odam bitta
    noto'g'ri havoladan keyin reklama sahifasida paydo bo'lardi.
    """
    login(client, "osh", "adminpass123")
    response = client.get("/admin/items/999999/edit")
    assert 'href="/admin"' in response.text


# --- chop etilgan QR nimadan o'ladi, nimadan o'lmaydi ----------------------
#
# Bu mahsulotning asosiy va'dasi: menyu o'zgarsa QR qayta chop etilmaydi.
# Shuning uchun uni testda qulflab qo'yamiz.


def test_changing_the_menu_never_changes_the_qr(db, cafe):
    """Taom qo'shilsa, narx o'zgarsa, taom o'chirilsa — QR o'sha-o'sha."""
    from app.services import qr

    restaurant, table, item = cafe
    menu_before = qr.svg_bytes(qr.menu_url(restaurant.slug))
    table_before = qr.svg_bytes(qr.table_url(restaurant.slug, table.code))

    category = db.query(Category).filter(Category.restaurant_id == restaurant.id).one()
    db.add_all(
        MenuItem(
            restaurant_id=restaurant.id,
            category_id=category.id,
            name={"uz": f"Yangi {n}"},
            price=20000,
        )
        for n in range(5)
    )
    item.price = 99000
    item.name = {"uz": "Boshqa nom"}
    db.commit()

    assert qr.svg_bytes(qr.menu_url(restaurant.slug)) == menu_before
    assert qr.svg_bytes(qr.table_url(restaurant.slug, table.code)) == table_before


def test_adding_tables_later_keeps_the_printed_ones(client, db, cafe):
    """Egasi keyin stol qo'shsa, chop etilgan kodlar o'zgarmasin."""
    restaurant, table, _ = cafe
    printed = table.code

    login(client, "osh", "adminpass123")
    client.post(
        "/admin/tables/bulk",
        data={"csrf_token": csrf(client, "/admin/tables"), "count": 20},
    )

    db.refresh(table)
    assert table.code == printed
    assert len(tables.list_for(db, restaurant.id)) == 20


def test_the_slug_is_out_of_the_owners_reach(client, db, cafe):
    """Egasi slug'ni o'zgartira olmasin.

    Slug QR ichidagi manzilning bir qismi — u o'zgarsa stollardagi hamma kod
    o'ladi. Egasi buni bilmasdan qilib qo'yishi mumkin edi.
    """
    restaurant, _, _ = cafe
    before = restaurant.slug

    login(client, "osh", "adminpass123")
    assert 'name="slug"' not in client.get("/admin/settings").text

    client.post(
        "/admin/settings",
        data={"csrf_token": csrf(client, "/admin/settings"), "name": restaurant.name, "slug": "boshqa-manzil"},
    )
    db.refresh(restaurant)
    assert restaurant.slug == before


def test_the_superadmin_is_warned_before_breaking_printed_codes(client, superadmin, cafe):
    """Superadmin slug'ni o'zgartira oladi — lekin oqibatini bilib tursin."""
    restaurant, _, _ = cafe
    login(client, "root", "rootpass123")

    body = html.unescape(client.get(f"/superadmin/restaurants/{restaurant.id}/edit").text)
    assert "chop etilgan QR kodlar ishlamay qoladi" in body

    # Yangi restoran qo'shishda bu ogohlantirish o'rinsiz — hali QR yo'q
    assert "chop etilgan QR kodlar ishlamay qoladi" not in html.unescape(
        client.get("/superadmin/restaurants/new").text
    )


# --- javobsiz buyurtma eslatmasi -------------------------------------------
#
# Shovqinli zalda bitta bildirishnoma yetarli emas: afitsant telefonni
# eshitmasligi, qo'lida laganda bo'lishi mumkin. Buyurtma javobsiz qolsa
# yana turtki yuboriladi — lekin faqat javobsiz bo'lsa.


def test_an_unanswered_order_is_reminded(db, cafe, monkeypatch):
    restaurant, table, item = cafe
    order = orders.place(db, restaurant=restaurant, table=table, wanted=[(item.id, 1)])

    from app.services import push

    yuborilgan = []
    monkeypatch.setattr(
        push, "notify_restaurant", lambda rid, tid=None, oid=None: yuborilgan.append(rid)
    )

    push._remind_once(restaurant.id, order.id, table.id)

    assert yuborilgan == [restaurant.id]


def test_an_answered_order_is_left_alone(db, cafe, monkeypatch):
    """Afitsant "Qabul qildim" bosgan bo'lsa telefon qayta jiringlamasin."""
    restaurant, table, item = cafe
    order = orders.place(db, restaurant=restaurant, table=table, wanted=[(item.id, 1)])
    orders.set_status(db, order, OrderStatus.accepted)

    from app.services import push

    yuborilgan = []
    monkeypatch.setattr(
        push, "notify_restaurant", lambda rid, tid=None, oid=None: yuborilgan.append(rid)
    )

    push._remind_once(restaurant.id, order.id, table.id)

    assert yuborilgan == []


def test_a_deleted_order_does_not_crash_the_reminder(db, cafe, monkeypatch):
    """Buyurtma o'chirilgan bo'lsa eslatma jimgina to'xtasin."""
    restaurant, table, _ = cafe
    from app.services import push

    yuborilgan = []
    monkeypatch.setattr(
        push, "notify_restaurant", lambda rid, tid=None, oid=None: yuborilgan.append(rid)
    )

    push._remind_once(restaurant.id, 999999, table.id)

    assert yuborilgan == []
