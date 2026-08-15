"""Boshqaruv paneli.

Panel "bugun ishlar qalay" degan savolga javob berishi kerak. Ilgari u
faqat menyu ochilishlarini ko'rsatardi: buyurtma qabul qiladigan restoran
uchun eng muhim raqam — "nechta buyurtma javob kutyapti" — umuman yo'q
edi va egasi buni bilish uchun afitsant taxtasini ochib ko'rishi kerak
edi.
"""

from datetime import timedelta
from decimal import Decimal

import pytest

from app.models import Category, MenuItem, Order, OrderLine, OrderStatus, Table, utcnow_naive
from app.services import orders, stats

from tests.conftest import login


def make_order(db, restaurant, table, *, status, total, minutes_ago=5, reply_after=None):
    created = utcnow_naive() - timedelta(minutes=minutes_ago)
    order = Order(
        restaurant_id=restaurant.id,
        table_id=table.id,
        table_label=table.label,
        table_kind="stol",
        code=f"kod{db.query(Order).count()}-{minutes_ago}",
        status=status,
        total=Decimal(total),
        created_at=created,
        accepted_at=created + timedelta(seconds=reply_after) if reply_after else None,
    )
    order.lines.append(OrderLine(item_id=None, name="Osh", unit_price=Decimal(total), quantity=1))
    db.add(order)
    db.commit()
    return order


@pytest.fixture
def kafe(db, tenant_a):
    restaurant, _ = tenant_a
    restaurant.orders_enabled = True
    category = Category(restaurant_id=restaurant.id, name={"uz": "Taomlar"})
    db.add(category)
    db.flush()
    db.add(MenuItem(restaurant_id=restaurant.id, category_id=category.id,
                    name={"uz": "Osh"}, price=Decimal("45000")))
    table = Table(restaurant_id=restaurant.id, label="1", code="sinovkod")
    db.add(table)
    db.commit()
    return restaurant, table


# --------------------------------------------------------------- bir kunlik xulosa


def test_the_day_summary_counts_each_state(db, kafe):
    restaurant, table = kafe
    make_order(db, restaurant, table, status=OrderStatus.new, total="10000")
    make_order(db, restaurant, table, status=OrderStatus.served, total="20000", reply_after=60)
    make_order(db, restaurant, table, status=OrderStatus.cancelled, total="99000")

    xulosa = orders.day_summary(db, restaurant.id, stats.today())

    assert xulosa.total_orders == 3
    assert xulosa.waiting == 1
    assert xulosa.served == 1
    assert xulosa.cancelled == 1


def test_cancelled_orders_do_not_count_as_revenue(db, kafe):
    """Bekor qilingan buyurtma pul keltirmaydi.

    Uni tushumga qo'shish egasini aldardi — kechqurun hisobni ochib
    ko'rganda raqam kassadagidan katta chiqardi.
    """
    restaurant, table = kafe
    make_order(db, restaurant, table, status=OrderStatus.served, total="30000", reply_after=30)
    make_order(db, restaurant, table, status=OrderStatus.cancelled, total="500000")

    assert orders.day_summary(db, restaurant.id, stats.today()).revenue == Decimal("30000")


def test_yesterdays_orders_stay_out_of_todays_summary(db, kafe):
    restaurant, table = kafe
    make_order(db, restaurant, table, status=OrderStatus.served,
               total="70000", minutes_ago=60 * 30, reply_after=20)

    bugun = orders.day_summary(db, restaurant.id, stats.today())
    assert bugun.total_orders == 0
    assert bugun.revenue == Decimal("0")


def test_the_reply_time_is_measured_only_where_there_was_a_reply(db, kafe):
    """Javob berilmagan buyurtma o'rtachani pasaytirmasin.

    Uni nol deb hisoblash "bir soniyada javob beramiz" degan yolg'on
    raqam berardi.
    """
    restaurant, table = kafe
    make_order(db, restaurant, table, status=OrderStatus.served, total="1", reply_after=100)
    make_order(db, restaurant, table, status=OrderStatus.new, total="1")

    assert orders.day_summary(db, restaurant.id, stats.today()).avg_reply == 100


def test_a_quiet_day_is_all_zeros(db, kafe):
    restaurant, _ = kafe
    xulosa = orders.day_summary(db, restaurant.id, stats.today())

    assert xulosa == orders.BOSH_KUN
    assert xulosa.avg_reply is None


def test_the_summary_ignores_another_restaurants_orders(db, kafe, tenant_b):
    restaurant, table = kafe
    boshqa, _ = tenant_b
    boshqa.orders_enabled = True
    begona_stol = Table(restaurant_id=boshqa.id, label="1", code="begonakod")
    db.add(begona_stol)
    db.commit()
    make_order(db, boshqa, begona_stol, status=OrderStatus.new, total="80000")

    assert orders.day_summary(db, restaurant.id, stats.today()) == orders.BOSH_KUN


# --------------------------------------------------------------------- sahifa


def test_the_add_dish_button_is_gone_from_the_top(client, kafe):
    """Talab: tepadagi "taom qo'shish" tugmasi panelda bo'lmasin.

    Panel — holatni ko'rsatadigan joy, taom qo'shiladigan joy emas. Uning
    o'rni Menyu bo'limida va u yerda kategoriyaning yonida turadi, ya'ni
    taom qayerga tushishi ko'rinib turadi.
    """
    login(client, "osh", "adminpass123")
    body = client.get("/admin").text

    assert "/admin/items/new" not in body


def test_the_dashboard_shows_todays_orders(client, db, kafe):
    restaurant, table = kafe
    make_order(db, restaurant, table, status=OrderStatus.new, total="45000")

    login(client, "osh", "adminpass123")
    body = client.get("/admin").text

    assert "Javob kutyapti" in body
    # Kutayotgan buyurtma taxtaga olib borsin
    assert 'href="/zal"' in body


def test_a_restaurant_without_ordering_sees_no_order_block(client, db, kafe):
    """Buyurtma yoqilmagan restoranda blok umuman chizilmasin.

    Aks holda panel har doim to'rtta nol ko'rsatib turardi va egasi
    nimadir buzuq deb o'ylardi.
    """
    restaurant, _ = kafe
    restaurant.orders_enabled = False
    db.commit()

    login(client, "osh", "adminpass123")
    body = client.get("/admin").text

    assert "Javob kutyapti" not in body


def test_every_number_links_somewhere(client, kafe):
    """Raqam shunchaki yozuv bo'lib qolmasin.

    Ilgari egasi "12 ta yashirilgan taom" ni ko'rardi-yu, qaysilari
    ekanini topish uchun menyuni qo'lda titardi.
    """
    login(client, "osh", "adminpass123")
    body = client.get("/admin").text

    for manzil in ("/admin/menu", "/admin/combos", "/admin/orders"):
        assert manzil in body, manzil


def test_the_quick_links_do_not_point_at_removed_pages(client, kafe):
    """Eski bo'limlar birlashtirilgan — havolalar ularga qolib ketmasin.

    `/admin/categories` va `/admin/items` endi yo'naltirish, ya'ni havola
    ishlaydi, lekin bir sakrash ortiqcha va manzil noto'g'ri ko'rinadi.
    """
    login(client, "osh", "adminpass123")
    body = client.get("/admin").text

    assert 'href="/admin/categories"' not in body
    assert 'href="/admin/items"' not in body


def test_a_past_day_does_not_swallow_todays_orders(db, kafe):
    """Kechagi kunni so'raganda bugungi buyurtmalar kirmasin.

    Xulosa ikki chegara bilan qisiladi. Pastki chegara o'z-o'zidan
    ko'rinadi, yuqorigisi esa — yo'q: uni olib tashlaganda "bugun" to'g'ri
    chiqaveradi va xato faqat O'TGAN kunni so'raganda bilinadi. Mutatsiya
    sinovi aynan shuni ko'rsatdi — bu tekshiruv o'sha bo'shliqni yopadi.
    """
    restaurant, table = kafe
    make_order(db, restaurant, table, status=OrderStatus.served, total="50000", reply_after=15)

    kecha = stats.today() - timedelta(days=1)
    xulosa = orders.day_summary(db, restaurant.id, kecha)

    assert xulosa.total_orders == 0
    assert xulosa.revenue == Decimal("0")
