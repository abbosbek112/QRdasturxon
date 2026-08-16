"""Ikkinchi hujjatdagi kichik tuzatishlar.

Har biri egasi PANELDA ko'rgan va tushunmagan narsadan chiqqan.
"""

import html

import pytest

from app.models import Category, MenuItem, Order, OrderLine, OrderStatus, Role, Table, User
from app.models import utcnow_naive
from app.security import hash_password

from tests.conftest import csrf, login


def kategoriya_yubor(client, **maydonlar):
    token = csrf(client, "/admin/menu")
    return client.post(
        "/admin/categories", data={"csrf_token": token, **maydonlar},
        follow_redirects=False,
    )


# --- 4. Kategoriya nomi uch tilda majburiy -------------------------------


@pytest.mark.parametrize(
    "yetishmaydigan, kutilgan_soz",
    [("name_ru", "ruscha"), ("name_en", "inglizcha"), ("name_uz", "o'zbekcha")],
)
def test_a_category_needs_all_three_languages(client, db, tenant_a, yetishmaydigan, kutilgan_soz):
    """Bittasi bo'sh qolsa o'sha tildagi menyuda bo'lim o'zbekcha turadi.

    Mijoz uchun bu menyu chala tarjima qilingandek ko'rinadi. Kategoriya
    — mijoz ko'radigan birinchi narsa, shuning uchun bu yerda talab
    qattiq.
    """
    login(client, "osh", "adminpass123")
    maydonlar = {"name_uz": "Ichimlik", "name_ru": "Напитки", "name_en": "Drinks"}
    maydonlar[yetishmaydigan] = "   "

    response = kategoriya_yubor(client, **maydonlar)

    assert response.status_code == 303
    assert db.query(Category).count() == 0
    xabar = html.unescape(client.get("/admin/menu").text)
    assert kutilgan_soz in xabar


def test_a_complete_category_is_accepted(client, db, tenant_a):
    login(client, "osh", "adminpass123")
    kategoriya_yubor(client, name_uz="Ichimlik", name_ru="Напитки", name_en="Drinks")

    category = db.query(Category).one()
    assert category.name == {"uz": "Ichimlik", "ru": "Напитки", "en": "Drinks"}


def test_editing_also_requires_three_languages(client, db, tenant_a):
    """Yangilashda ham qo'riqlansin — aks holda nomni bo'shatib yuborish mumkin."""
    restaurant, _ = tenant_a
    category = Category(restaurant_id=restaurant.id,
                        name={"uz": "A", "ru": "Б", "en": "C"})
    db.add(category)
    db.commit()

    login(client, "osh", "adminpass123")
    token = csrf(client, "/admin/menu")
    client.post(f"/admin/categories/{category.id}",
                data={"csrf_token": token, "name_uz": "A", "name_ru": "", "name_en": "C"},
                follow_redirects=False)

    db.refresh(category)
    assert category.name == {"uz": "A", "ru": "Б", "en": "C"}


# --- 5. Buyurtmada qaysi afitsant javob bergani --------------------------


@pytest.fixture
def buyurtma(db, tenant_a):
    restaurant, _ = tenant_a
    restaurant.orders_enabled = True
    waiter = User(username="osh-afitsant", password_hash=hash_password("parol12345"),
                  role=Role.waiter, restaurant_id=restaurant.id)
    table = Table(restaurant_id=restaurant.id, label="7", code="kod7")
    db.add_all([waiter, table])
    db.flush()
    order = Order(restaurant_id=restaurant.id, table_id=table.id, table_label="7",
                  table_kind="stol", code="buyurtmakod", status=OrderStatus.served,
                  total=45000, created_at=utcnow_naive(), accepted_at=utcnow_naive(),
                  handled_by_id=waiter.id)
    order.lines.append(OrderLine(item_id=None, name="Osh", unit_price=45000, quantity=1))
    db.add(order)
    db.commit()
    return restaurant, waiter, order


def test_the_order_history_names_the_waiter(client, buyurtma):
    """Egasi kim javob berganini ko'rsin.

    Ilgari jadvalda bu ustun umuman yo'q edi va "kim ulgurdi" degan
    savolga javob berib bo'lmasdi.
    """
    _, waiter, _ = buyurtma
    login(client, "osh", "adminpass123")
    body = client.get("/admin/orders").text

    assert waiter.username in body
    # Ismi xodim sahifasiga olib borsin
    assert f'/admin/staff/{waiter.id}' in body


def test_an_unanswered_order_shows_a_dash(client, db, buyurtma):
    """Javobgar yo'q bo'lsa bo'sh chiziqcha — yolg'on ism emas."""
    _, _, order = buyurtma
    order.handled_by_id = None
    db.commit()

    login(client, "osh", "adminpass123")
    body = client.get("/admin/orders").text
    assert "osh-afitsant" not in body


# --- 2. Yashirilgan taom va kategoriya ko'rinishi ------------------------


def test_hidden_things_look_switched_off(client, db, tenant_a):
    """Yashirilgan — mijoz KO'RMAYDIGAN narsa.

    Ilgari farq bor-yo'g'i biroz oqarish edi va egasi ro'yxatga qarab
    qaysi biri menyuda turganini ayta olmasdi.
    """
    restaurant, _ = tenant_a
    category = Category(restaurant_id=restaurant.id,
                        name={"uz": "A", "ru": "Б", "en": "C"}, is_active=False)
    db.add(category)
    db.flush()
    db.add(MenuItem(restaurant_id=restaurant.id, category_id=category.id,
                    name={"uz": "Osh"}, price=1000, is_available=False))
    db.commit()

    login(client, "osh", "adminpass123")
    body = client.get("/admin/menu").text

    # Kategoriya ham, taom ham belgilangan bo'lsin
    assert body.count("is-hidden") >= 2

    css = client.get("/static/css/style.css").text
    # Faqat rang emas: chiziq va kulranglik ham bor, chunki rangni
    # ajrata olmaydigan odam uchun rang hech nima demaydi
    assert "grayscale(1)" in css
    assert "line-through" in css


# --- 3. Kategoriya ochilish belgisi --------------------------------------


def test_a_category_shows_it_can_be_opened(client, db, tenant_a):
    """Sarlavha bosilishini odam ko'rib bilsin.

    Ilgari hech qanday belgi yo'q edi va kategoriyani tahrirlash uchun
    qayerni bosishni faqat tasodifan topish mumkin edi.
    """
    restaurant, _ = tenant_a
    db.add(Category(restaurant_id=restaurant.id, name={"uz": "A", "ru": "Б", "en": "C"}))
    db.commit()

    login(client, "osh", "adminpass123")
    assert "cat-toggle" in client.get("/admin/menu").text

    css = client.get("/static/css/style.css").text
    assert ".menu-cat-edit[open] > summary .cat-toggle" in css
    assert "cat-open" in css  # ochilish animatsiyasi


# --- 10. Sozlamalarda dizayn qolmasin ------------------------------------


def test_the_settings_page_has_no_design_left(client, tenant_a):
    """Dizayn butunlay alohida bo'limda.

    Ilgari sozlamalarda unga havola qolgan edi — bo'lim ikki joyda
    ko'rinib, qaysi biri asosiy ekani tushunarsiz edi.
    """
    login(client, "osh", "adminpass123")
    body = html.unescape(client.get("/admin/settings").text)

    # Sahifaning O'Z mazmuni tekshiriladi, qobiq emas: chap menyudagi
    # "Dizayn" havolasi har sahifada turadi va u joyida
    mazmun = body.split("<main", 1)[-1]
    forma = mazmun.split("<form", 1)[-1].split("</form>", 1)[0]

    assert "/admin/design" not in forma
    assert 'name="theme"' not in forma
    assert 'name="logo"' not in forma
    # Ish sozlamalari esa joyida qoldi
    assert 'name="currency"' in forma
    assert 'name="wifi_name"' in forma
