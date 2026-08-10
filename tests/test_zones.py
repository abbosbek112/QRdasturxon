"""Zal bo'limlari va afitsantlarning javobgarlik doirasi.

Eng muhim qoida shu yerda qulflanadi: **biriktirilmagan afitsant hammasini
ko'radi.** Bitta afitsantli kafeda hech narsa sozlanmaydi va bo'limlar
qo'shilgani mavjud restoranlarni buzmaydi.

Ikkinchi qoida: buyurtma hech qachon javobsiz qolmasin. Stolga hech kim
biriktirilmagan bo'lsa bildirishnoma HAMMAGA ketadi — sozlash xatosi
jimgina yutilib ketmasin.
"""

import html

import pytest

from app.models import (
    Category,
    MenuItem,
    Order,
    Role,
    Table,
    TableKind,
    User,
    Zone,
)
from app.security import hash_password
from app.services import areas, orders

from tests.conftest import csrf, login


@pytest.fixture
def cafe(db, tenant_a):
    """Ikki bo'limli restoran: 1–2 stol chapda, 3–4 o'ngda, bitta VIP xona."""
    restaurant, _ = tenant_a
    restaurant.orders_enabled = True

    chap = Zone(restaurant_id=restaurant.id, name="Chap tomon", sort_order=1)
    ong = Zone(restaurant_id=restaurant.id, name="O'ng tomon", sort_order=2)
    db.add_all([chap, ong])
    db.flush()

    category = Category(restaurant_id=restaurant.id, name={"uz": "Taomlar"})
    db.add(category)
    db.flush()
    db.add(
        MenuItem(
            restaurant_id=restaurant.id,
            category_id=category.id,
            name={"uz": "Osh"},
            price=38000,
        )
    )

    seats = [
        Table(restaurant_id=restaurant.id, label="1", code="k1", zone_id=chap.id),
        Table(restaurant_id=restaurant.id, label="2", code="k2", zone_id=chap.id),
        Table(restaurant_id=restaurant.id, label="3", code="k3", zone_id=ong.id),
        Table(restaurant_id=restaurant.id, label="4", code="k4", zone_id=ong.id),
        Table(
            restaurant_id=restaurant.id,
            label="1",
            code="kvip",
            kind=TableKind.vip,
            zone_id=None,
        ),
    ]
    # "1" ikki marta bo'lmasin — VIP xonaning nomi boshqacha
    seats[-1].label = "VIP-1"
    db.add_all(seats)

    db.add_all(
        User(
            username=name,
            password_hash=hash_password("waiterpass123"),
            role=Role.waiter,
            restaurant_id=restaurant.id,
        )
        for name in ("anvar", "bobur")
    )
    db.commit()
    return restaurant, chap, ong


def cards(body: str) -> int:
    """Sahifadagi buyurtma kartalari soni.

    `<article` bilan sanaladi: shunchaki `class="hall-card` deb qidirilsa
    ichkaridagi `hall-card-top` ham mos kelib, har karta ikki marta
    sanalardi.
    """
    return body.count('<article class="hall-card')


def waiter(db, username):
    return db.query(User).filter(User.username == username).one()


def order_from(client, restaurant, code, db):
    """Mijoz bo'lib shu stoldan buyurtma beradi."""
    import re

    client.cookies.clear()
    client.get(f"/r/{restaurant.slug}/t/{code}")
    body = client.get(f"/r/{restaurant.slug}").text
    token = re.search(r'name="csrf_token" value="([^"]+)"', body).group(1)
    item = db.query(MenuItem).filter(MenuItem.restaurant_id == restaurant.id).one()
    client.post(
        f"/r/{restaurant.slug}/order",
        data={"csrf_token": token, "item_id": [item.id], "qty": [1]},
    )
    client.cookies.clear()


# --- javobgarlik doirasi ---------------------------------------------------


def test_an_unassigned_waiter_sees_everything(db, cafe):
    """Bitta afitsantli kafeda hech narsa sozlanmasin."""
    restaurant, _, _ = cafe
    assert areas.assigned_table_ids(db, waiter(db, "anvar")) is None


def test_a_zone_assignment_narrows_the_view(db, cafe):
    restaurant, chap, _ = cafe
    anvar = waiter(db, "anvar")
    areas.set_assignment(db, anvar, [chap.id], [])

    scope = areas.assigned_table_ids(db, anvar)
    labels = {db.get(Table, tid).label for tid in scope}
    assert labels == {"1", "2"}


def test_zone_and_single_tables_add_up(db, cafe):
    """Ikkalasi birga ishlaydi: bo'lim + alohida VIP xona."""
    restaurant, chap, _ = cafe
    vip = db.query(Table).filter(Table.label == "VIP-1").one()
    anvar = waiter(db, "anvar")
    areas.set_assignment(db, anvar, [chap.id], [vip.id])

    scope = areas.assigned_table_ids(db, anvar)
    labels = {db.get(Table, tid).label for tid in scope}
    assert labels == {"1", "2", "VIP-1"}


def test_the_owner_always_sees_the_whole_room(db, cafe):
    owner = db.query(User).filter(User.username == "osh").one()
    assert areas.assigned_table_ids(db, owner) is None


def test_an_empty_zone_falls_back_to_everything(db, cafe):
    """Biriktirish bor, lekin ortida stol yo'q — bu sozlash xatosi.

    Afitsantni bo'sh taxta oldida qoldirgandan ko'ra hammasini ko'rsatamiz.
    """
    restaurant, _, _ = cafe
    empty = Zone(restaurant_id=restaurant.id, name="Bo'sh bo'lim")
    db.add(empty)
    db.commit()

    anvar = waiter(db, "anvar")
    areas.set_assignment(db, anvar, [empty.id], [])
    assert areas.assigned_table_ids(db, anvar) is None


def test_another_restaurants_zone_is_refused(db, cafe, tenant_b):
    """Formadan begona raqam kelsa u jimgina tashlanadi."""
    other, _ = tenant_b
    stranger = Zone(restaurant_id=other.id, name="Begona")
    db.add(stranger)
    db.commit()

    anvar = waiter(db, "anvar")
    areas.set_assignment(db, anvar, [stranger.id], [])
    assert areas.assignment_of(db, anvar) == (set(), set())


# --- taxtadagi ko'rinish ---------------------------------------------------


def test_the_board_shows_only_your_own_area(client, db, cafe):
    restaurant, chap, ong = cafe
    areas.set_assignment(db, waiter(db, "anvar"), [chap.id], [])

    order_from(client, restaurant, "k1", db)   # Anvar bo'limi
    order_from(client, restaurant, "k3", db)   # Bobur bo'limi

    login(client, "anvar", "waiterpass123")
    assert cards(client.get("/zal").text) == 1
    # "Hammasi" bosilganda ikkalasi ham ko'rinadi
    assert cards(client.get("/zal?hammasi=1").text) == 2


def test_the_filter_is_hidden_without_an_area(client, db, cafe):
    """Biriktirilmagan afitsantga tanlov tugmasi keraksiz."""
    restaurant, _, _ = cafe
    login(client, "anvar", "waiterpass123")
    body = html.unescape(client.get("/zal?lang=uz").text)
    assert "Mening bo'limim" not in body


def test_the_filter_appears_once_an_area_is_set(client, db, cafe):
    restaurant, chap, _ = cafe
    areas.set_assignment(db, waiter(db, "anvar"), [chap.id], [])
    login(client, "anvar", "waiterpass123")
    body = html.unescape(client.get("/zal?lang=uz").text)
    assert "Mening bo'limim" in body and "Hammasi" in body


def test_polling_keeps_the_chosen_view(client, db, cafe):
    """Avtomatik yangilash "Hammasi" ni o'z bo'limiga qaytarib yubormasin."""
    restaurant, chap, _ = cafe
    areas.set_assignment(db, waiter(db, "anvar"), [chap.id], [])
    login(client, "anvar", "waiterpass123")

    assert 'data-list-url="/zal/list"' in client.get("/zal").text
    assert 'data-list-url="/zal/list?hammasi=1"' in client.get("/zal?hammasi=1").text


def test_an_orphan_order_is_visible_to_everyone(client, db, cafe):
    """Stoli o'chirilgan buyurtma hech kimning bo'limiga tegishli emas.

    Filtr uni butunlay yo'qotib yuborsa, buyurtma javobsiz qolardi.
    """
    restaurant, chap, _ = cafe
    order_from(client, restaurant, "k3", db)          # Bobur bo'limidan
    db.query(Order).one().table_id = None             # stol o'chirildi
    db.commit()

    areas.set_assignment(db, waiter(db, "anvar"), [chap.id], [])
    login(client, "anvar", "waiterpass123")
    assert cards(client.get("/zal").text) == 1


# --- bildirishnoma manzili -------------------------------------------------


def test_a_notification_reaches_only_the_responsible_waiter(db, cafe):
    restaurant, chap, ong = cafe
    anvar, bobur = waiter(db, "anvar"), waiter(db, "bobur")
    areas.set_assignment(db, anvar, [chap.id], [])
    areas.set_assignment(db, bobur, [ong.id], [])

    left = db.query(Table).filter(Table.label == "1").one()
    people = areas.responsible_for(db, restaurant.id, left.id)

    assert anvar.id in people
    assert bobur.id not in people


def test_the_owner_is_always_told(db, cafe):
    restaurant, chap, ong = cafe
    areas.set_assignment(db, waiter(db, "anvar"), [chap.id], [])
    owner = db.query(User).filter(User.username == "osh").one()

    left = db.query(Table).filter(Table.label == "1").one()
    assert owner.id in areas.responsible_for(db, restaurant.id, left.id)


def test_an_unclaimed_table_wakes_everyone(db, cafe):
    """Stolga hech kim biriktirilmagan — buyurtma javobsiz qolmasin."""
    restaurant, chap, ong = cafe
    anvar, bobur = waiter(db, "anvar"), waiter(db, "bobur")
    areas.set_assignment(db, anvar, [chap.id], [])
    areas.set_assignment(db, bobur, [ong.id], [])

    vip = db.query(Table).filter(Table.label == "VIP-1").one()   # bo'limsiz
    people = areas.responsible_for(db, restaurant.id, vip.id)
    assert anvar.id in people and bobur.id in people


def test_a_blocked_waiter_gets_nothing(db, cafe):
    restaurant, chap, _ = cafe
    anvar = waiter(db, "anvar")
    areas.set_assignment(db, anvar, [chap.id], [])
    anvar.is_active = False
    db.commit()

    left = db.query(Table).filter(Table.label == "1").one()
    assert anvar.id not in areas.responsible_for(db, restaurant.id, left.id)


# --- o'tirish joyi turi ----------------------------------------------------


def test_the_guest_sees_the_right_word(client, db, cafe):
    """VIP xona "1-stol" bo'lib ko'rinmasin."""
    restaurant, _, _ = cafe
    client.get(f"/r/{restaurant.slug}/t/kvip")
    body = html.unescape(client.get(f"/r/{restaurant.slug}?lang=uz").text)
    assert "VIP VIP-1" in body

    client.cookies.clear()
    client.get(f"/r/{restaurant.slug}/t/k1")
    assert "1-stol" in html.unescape(client.get(f"/r/{restaurant.slug}?lang=uz").text)


def test_the_kind_is_copied_onto_the_order(client, db, cafe):
    """Stol o'chirilsa ham taxtada turi ko'rinib tursin."""
    restaurant, _, _ = cafe
    order_from(client, restaurant, "kvip", db)
    assert db.query(Order).one().table_kind == "vip"


def test_an_unknown_kind_becomes_a_plain_table(client, db, cafe):
    restaurant, _, _ = cafe
    login(client, "osh", "adminpass123")
    client.post(
        "/admin/tables",
        data={
            "csrf_token": csrf(client, "/admin/tables"),
            "label": "99",
            "kind": "yolgon-tur",
        },
    )
    assert db.query(Table).filter(Table.label == "99").one().kind is TableKind.stol


# --- bo'limlar sahifasi ----------------------------------------------------


def test_the_owner_manages_zones(client, db, cafe):
    restaurant, _, _ = cafe
    login(client, "osh", "adminpass123")

    assert client.get("/admin/zones").status_code == 200
    client.post(
        "/admin/zones",
        data={"csrf_token": csrf(client, "/admin/zones"), "name": "Terasa"},
    )
    assert db.query(Zone).filter(Zone.name == "Terasa").count() == 1


def test_a_duplicate_zone_keeps_you_on_the_page(client, db, cafe):
    """Xato zal sahifasining o'zida chiqadi, boshqa yoqqa otvormaydi."""
    restaurant, _, _ = cafe
    login(client, "osh", "adminpass123")
    response = client.post(
        "/admin/zones",
        data={"csrf_token": csrf(client, "/admin/zones"), "name": "Chap tomon"},
    )
    assert response.status_code == 200
    assert response.url.path == "/admin/tables"
    assert "allaqachon bor" in html.unescape(response.text)


def test_the_old_areas_link_still_leads_somewhere(client, cafe):
    """Bo'limlar "Zal" ichiga ko'chdi — eski xatcho'p 404 bo'lib qolmasin."""
    login(client, "osh", "adminpass123")
    response = client.get("/admin/zones", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/tables"


def test_deleting_a_zone_keeps_the_tables_and_their_codes(client, db, cafe):
    """Bo'limni o'chirish chop etilgan QR kodlarni o'ldirmasin."""
    restaurant, chap, _ = cafe
    before = {t.id: t.code for t in db.query(Table).filter(Table.zone_id == chap.id).all()}

    login(client, "osh", "adminpass123")
    client.post(
        f"/admin/zones/{chap.id}/delete",
        data={"csrf_token": csrf(client, "/admin/zones")},
    )

    db.expire_all()
    for table_id, code in before.items():
        seat = db.get(Table, table_id)
        assert seat is not None
        assert seat.code == code
        assert seat.zone_id is None


def test_another_restaurants_zone_is_out_of_reach(client, db, cafe, tenant_b):
    other, _ = tenant_b
    stranger = Zone(restaurant_id=other.id, name="Begona")
    db.add(stranger)
    db.commit()

    login(client, "osh", "adminpass123")
    response = client.post(
        f"/admin/zones/{stranger.id}/delete",
        data={"csrf_token": csrf(client, "/admin/zones")},
    )
    assert response.status_code == 404
    assert db.get(Zone, stranger.id) is not None


# --- qavat -----------------------------------------------------------------


def test_zones_carry_a_floor(client, db, cafe):
    """Qavat bo'limda saqlanadi, stolda emas: bo'lim ikki qavatga bo'linmaydi."""
    restaurant, _, _ = cafe
    login(client, "osh", "adminpass123")
    client.post(
        "/admin/zones",
        data={
            "csrf_token": csrf(client, "/admin/zones"),
            "name": "Ikkinchi qavat zali",
            "floor": 2,
        },
    )
    zone = db.query(Zone).filter(Zone.name == "Ikkinchi qavat zali").one()
    assert zone.floor == 2


def test_existing_zones_land_on_the_first_floor(db, cafe):
    """Migratsiya mavjud bo'limlarni birinchi qavatga qo'yadi."""
    restaurant, chap, _ = cafe
    assert chap.floor == 1


def test_the_page_groups_zones_by_floor(client, db, cafe):
    restaurant, _, _ = cafe
    areas.create_zone(db, restaurant, "Terasa", floor=2)

    login(client, "osh", "adminpass123")
    body = html.unescape(client.get("/admin/zones?lang=uz").text)
    assert "1-qavat" in body and "2-qavat" in body
    # Bino kesim kabi chiziladi: yuqori qavat tepada
    assert body.index("2-qavat") < body.index("1-qavat")


def test_a_basement_sits_at_the_bottom(client, db, cafe):
    """Yerto'la eng pastda — binoning haqiqiy tartibi."""
    restaurant, _, _ = cafe
    areas.create_zone(db, restaurant, "Sovutgich", floor=-1)
    areas.create_zone(db, restaurant, "Terasa", floor=2)

    login(client, "osh", "adminpass123")
    body = html.unescape(client.get("/admin/zones?lang=uz").text)
    assert body.index("2-qavat") < body.index("1-qavat") < body.index("1-yerto'la")


def test_a_basement_reads_as_a_word(client, db, cafe):
    """Yerto'la darajasi so'z bilan: "-1-qavat" degan yozuv g'alati ko'rinardi.

    Zona nomi ataylab "yerto'la" so'zisiz — aks holda test qavat yorlig'i
    umuman chiqmasa ham nom tufayli o'tib ketardi.
    """
    restaurant, _, _ = cafe
    areas.create_zone(db, restaurant, "Sovutgich", floor=-2)

    login(client, "osh", "adminpass123")
    assert "2-yerto'la" in html.unescape(client.get("/admin/zones?lang=uz").text)


def test_a_silly_floor_falls_back_to_the_first(client, db, cafe):
    """Formadan aql bovar qilmaydigan son kelsa xato ko'rsatmaymiz."""
    restaurant, _, _ = cafe
    login(client, "osh", "adminpass123")
    for number, name in ((999, "Baland"), (-99, "Chuqur"), (0, "Nol")):
        client.post(
            "/admin/zones",
            data={"csrf_token": csrf(client, "/admin/zones"), "name": name, "floor": number},
        )
        assert db.query(Zone).filter(Zone.name == name).one().floor == 1


def test_the_floor_shows_on_the_printed_card(client, db, cafe):
    """Afitsant kartochkani qaysi qavatga olib chiqishini bilsin."""
    restaurant, chap, _ = cafe
    chap.floor = 2
    db.commit()

    login(client, "osh", "adminpass123")
    body = html.unescape(client.get("/admin/tables/print").text)
    assert "2-qavat · Chap tomon" in body
