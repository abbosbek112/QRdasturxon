"""Xizmat haqi.

Ko'p restoran hisobga 10-15% qo'shadi. Uni jimgina jamiga qo'shib
qo'yish mijoz uchun yoqimsiz kutilmagan bo'ladi: u taomlar narxini
hisoblab o'tiradi, chek esa boshqa raqam ko'rsatadi. Shuning uchun u
alohida qator bo'lib ko'rinadi.
"""

import html
from decimal import Decimal

import pytest

from app.models import Category, MenuItem, Order, Table
from app.services import orders

from tests.conftest import csrf, login


@pytest.fixture
def kafe(db, tenant_a):
    """45 000 so'mlik bitta taomi va bitta stoli bor restoran."""
    restaurant, _ = tenant_a
    restaurant.orders_enabled = True
    category = Category(restaurant_id=restaurant.id, name={"uz": "Taomlar"})
    db.add(category)
    db.flush()
    osh = MenuItem(restaurant_id=restaurant.id, category_id=category.id,
                   name={"uz": "Osh"}, price=Decimal("45000"))
    table = Table(restaurant_id=restaurant.id, label="1", code="sinovkod")
    db.add_all([osh, table])
    db.commit()
    return restaurant, osh, table


def buyurtma_ber(db, kafe, qty=2):
    restaurant, osh, table = kafe
    return orders.place(db, restaurant=restaurant, table=table,
                        wanted=[(osh.id, qty)])


# --------------------------------------------------------------------- hisob


def test_no_service_charge_by_default(db, kafe):
    """Standart holat — foiz nol, hisob taomlarning o'zi.

    Mavjud restoranlarda hech narsa o'zgarmasligi kerak edi.
    """
    order = buyurtma_ber(db, kafe)

    assert order.service_percent == 0
    assert order.total == Decimal("90000")
    assert order.service_amount == Decimal("0")


def test_the_charge_is_added_to_the_total(db, kafe):
    restaurant, _, _ = kafe
    restaurant.service_percent = 15
    db.commit()

    order = buyurtma_ber(db, kafe)

    assert order.subtotal == Decimal("90000")
    assert order.service_amount == Decimal("13500")
    assert order.total == Decimal("103500")


def test_the_percent_is_frozen_at_order_time(db, kafe):
    """Foiz buyurtma paytidagi holicha saqlanadi.

    Egasi ertaga 10 dan 20 ga ko'tarsa, kechagi buyurtmaning hisobi
    o'zgarib ketmasligi kerak — xuddi taom narxi nusxa bo'lib
    saqlangani kabi.
    """
    restaurant, _, _ = kafe
    restaurant.service_percent = 10
    db.commit()
    order = buyurtma_ber(db, kafe)
    oldingi_jami = order.total

    restaurant.service_percent = 20
    db.commit()
    db.refresh(order)

    assert order.service_percent == 10
    assert order.total == oldingi_jami


def test_rounding_never_goes_against_the_guest(db, kafe):
    """Kasr MIJOZ FOYDASIGA yaxlitlanadi.

    Tepaga yaxlitlash har buyurtmada bir necha so'm qo'shib, chekdagi
    raqamni "g'alati" qilardi.
    """
    restaurant, osh, table = kafe
    osh.price = Decimal("33333")
    restaurant.service_percent = 15
    db.commit()

    order = orders.place(db, restaurant=restaurant, table=table, wanted=[(osh.id, 1)])

    # 33333 * 0.15 = 4999.95 -> 4999
    assert order.service_amount == Decimal("4999")
    assert order.total == Decimal("38332")


@pytest.mark.parametrize("qiymat, kutilgan", [(-5, 0), (0, 0), (15, 15), (99, 30)])
def test_the_percent_is_kept_inside_safe_limits(db, kafe, qiymat, kutilgan):
    """Chegara HIMOYA uchun: nol bilan adashib ketgan qiymat mijozga
    ulkan hisob chiqarmasin."""
    restaurant, _, _ = kafe
    restaurant.service_percent = qiymat
    db.commit()

    assert buyurtma_ber(db, kafe).service_percent == kutilgan


# --------------------------------------------------------------------- sahifa


def test_the_guest_sees_the_charge_as_its_own_line(client, db, kafe):
    restaurant, _, _ = kafe
    restaurant.service_percent = 15
    db.commit()
    order = buyurtma_ber(db, kafe)

    body = html.unescape(client.get(f"/r/{restaurant.slug}/order/{order.code}").text)

    assert "Xizmat haqi" in body
    assert "15%" in body
    # Taomlarning o'z summasi ham ko'rinsin — jami qaydan kelganini bilsin
    assert "90 000" in body
    assert "103 500" in body


def test_without_a_charge_the_extra_lines_stay_out(client, db, kafe):
    """Foiz nol bo'lsa qo'shimcha qatorlar chizilmasin — ular bo'sh
    joyni egallab, hisobni chalkashtirardi."""
    restaurant, _, _ = kafe
    order = buyurtma_ber(db, kafe)

    body = html.unescape(client.get(f"/r/{restaurant.slug}/order/{order.code}").text)
    assert "Xizmat haqi" not in body


def test_the_owner_can_set_it_in_settings(client, db, kafe):
    restaurant, _, _ = kafe
    login(client, "osh", "adminpass123")

    client.post("/admin/settings", data={
        "csrf_token": csrf(client, "/admin/settings"),
        "name": restaurant.name, "currency": "so'm",
        "orders_enabled": "true", "order_window_minutes": "30",
        "service_percent": "12",
    })
    db.refresh(restaurant)

    assert restaurant.service_percent == 12


def test_a_hand_sent_percent_cannot_escape_the_limit(client, db, kafe):
    """Formadagi `max` faqat brauzerni to'xtatadi — server ham qo'riqlasin."""
    restaurant, _, _ = kafe
    login(client, "osh", "adminpass123")

    client.post("/admin/settings", data={
        "csrf_token": csrf(client, "/admin/settings"),
        "name": restaurant.name, "currency": "so'm",
        "orders_enabled": "true", "order_window_minutes": "30",
        "service_percent": "900",
    })
    db.refresh(restaurant)

    assert restaurant.service_percent == orders.MAX_SERVICE_PERCENT
