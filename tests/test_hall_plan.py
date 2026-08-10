"""Zal sahifasi: stollarni bo'limlarga ko'chirish va qo'shish.

Egasi zalni bir marta yig'adi va keyin kamdan-kam tegadi, lekin o'sha bir
marta ishonchli bo'lishi kerak: 30 ta stolni bittalab ko'chirish bilan hech
kim shug'ullanmaydi.

Eng muhim qoida shu yerda qulflanadi: **ko'chirish faqat o'z restorani
ichida.** Stol ham, bo'lim ham begona bo'lsa amal bajarilmaydi.
"""

import html

import pytest

from app.models import Table, TableKind, Zone
from app.services import areas, tables

from tests.conftest import csrf, login


@pytest.fixture
def hall(db, tenant_a):
    """Ikki qavatli restoran: 1-qavatda "Asosiy zal", 2-qavatda "VIP"."""
    restaurant, _ = tenant_a
    restaurant.orders_enabled = True

    asosiy = Zone(restaurant_id=restaurant.id, name="Asosiy zal", floor=1)
    vip = Zone(restaurant_id=restaurant.id, name="VIP xonalar", floor=2)
    db.add_all([asosiy, vip])
    db.flush()

    db.add_all(
        Table(restaurant_id=restaurant.id, label=str(n), code=f"kod{n}", zone_id=None)
        for n in range(1, 5)
    )
    db.commit()
    return restaurant, asosiy, vip


def seat(db, restaurant_id, label):
    return db.query(Table).filter_by(restaurant_id=restaurant_id, label=label).one()


# --- ko'chirish ------------------------------------------------------------


def test_several_tables_move_at_once(db, hall):
    """Belgilangan hammasi bitta bosishda ko'chadi."""
    restaurant, asosiy, _ = hall
    ids = [seat(db, restaurant.id, label).id for label in ("1", "2", "3")]

    moved = tables.move_many(db, restaurant.id, ids, asosiy.id)

    assert moved == 3
    assert all(seat(db, restaurant.id, l).zone_id == asosiy.id for l in ("1", "2", "3"))
    # Belgilanmagani joyida qoladi
    assert seat(db, restaurant.id, "4").zone_id is None


def test_an_empty_target_sends_them_back_to_the_shelf(db, hall):
    """Bo'sh `zone_id` — bu xato emas, "bo'limsiz" ga qaytarish."""
    restaurant, asosiy, _ = hall
    one = seat(db, restaurant.id, "1")
    tables.move_many(db, restaurant.id, [one.id], asosiy.id)

    tables.move_many(db, restaurant.id, [one.id], "")

    assert seat(db, restaurant.id, "1").zone_id is None


def test_another_restaurants_table_is_never_touched(db, hall, tenant_b):
    """Eng muhim qoida: begona stolga qo'l tegmaydi."""
    restaurant, asosiy, _ = hall
    other_restaurant, _ = tenant_b
    stranger = Table(restaurant_id=other_restaurant.id, label="1", code="begona")
    db.add(stranger)
    db.commit()

    moved = tables.move_many(db, restaurant.id, [stranger.id], asosiy.id)

    assert moved == 0
    assert db.get(Table, stranger.id).zone_id is None


def test_a_foreign_zone_leaves_the_table_unassigned(db, hall, tenant_b):
    """Begona bo'limga tirkab bo'lmaydi — stol bo'limsiz qoladi.

    `tables.create` va `update` da ham shunday: begona raqam jimgina
    tashlanadi va stol boshqa restoranning bo'limiga tushib qolmaydi.
    """
    restaurant, asosiy, _ = hall
    other_restaurant, _ = tenant_b
    foreign_zone = areas.create_zone(db, other_restaurant, "Begona bo'lim")
    one = seat(db, restaurant.id, "1")
    tables.move_many(db, restaurant.id, [one.id], asosiy.id)

    tables.move_many(db, restaurant.id, [one.id], foreign_zone.id)

    assert seat(db, restaurant.id, "1").zone_id is None


def test_moving_nothing_is_harmless(db, hall):
    """Hech narsa belgilanmasdan tugma bosilsa sahifa buzilmasin."""
    restaurant, asosiy, _ = hall
    assert tables.move_many(db, restaurant.id, [], asosiy.id) == 0


# --- bo'limga stol qo'shish ------------------------------------------------


def test_new_tables_continue_the_numbering(db, hall):
    """1–4 bor ekan, yangilari 5 dan boshlanadi — takror raqam chiqmaydi."""
    restaurant, _, vip = hall

    created = tables.add_next(db, restaurant, 3, "vip", vip.id)

    assert [table.label for table in created] == ["5", "6", "7"]
    assert all(table.zone_id == vip.id for table in created)
    assert all(table.kind is TableKind.vip for table in created)


def test_new_tables_skip_labels_already_taken(db, hall):
    """Oraliqda bo'sh raqam qolgan bo'lsa ham urishmasin."""
    restaurant, _, vip = hall
    db.add(Table(restaurant_id=restaurant.id, label="6", code="oldindan"))
    db.commit()

    created = tables.add_next(db, restaurant, 2, "stol", vip.id)

    assert [table.label for table in created] == ["7", "8"]


def test_word_labels_do_not_break_the_numbering(db, hall):
    """"Terasa A" kabi nom raqamlashga xalaqit qilmasin."""
    restaurant, _, vip = hall
    db.add(Table(restaurant_id=restaurant.id, label="Terasa A", code="matn"))
    db.commit()

    created = tables.add_next(db, restaurant, 1, "stol", vip.id)

    assert [table.label for table in created] == ["5"]


# --- marshrutlar -----------------------------------------------------------


def test_the_owner_moves_tables_from_the_page(client, db, hall):
    """Sahifadagi forma: belgilangan stollar + bo'lim tugmasi."""
    restaurant, asosiy, _ = hall
    ids = [seat(db, restaurant.id, label).id for label in ("1", "2")]

    login(client, "osh", "adminpass123")
    response = client.post(
        "/admin/tables/move",
        data={
            "csrf_token": csrf(client, "/admin/tables"),
            "table_id": [str(i) for i in ids],
            "zone_id": str(asosiy.id),
        },
    )

    assert response.status_code == 200
    assert seat(db, restaurant.id, "1").zone_id == asosiy.id
    assert seat(db, restaurant.id, "2").zone_id == asosiy.id


def test_a_stranger_cannot_move_our_tables(client, db, hall, tenant_b):
    """Boshqa restoran egasi bizning stolimizni ko'chira olmaydi."""
    restaurant, asosiy, _ = hall
    one = seat(db, restaurant.id, "1")

    login(client, "choy", "adminpass123")
    client.post(
        "/admin/tables/move",
        data={
            "csrf_token": csrf(client, "/admin/tables"),
            "table_id": [str(one.id)],
            "zone_id": str(asosiy.id),
        },
    )

    assert seat(db, restaurant.id, "1").zone_id is None


def test_adding_tables_to_a_zone_from_the_page(client, db, hall):
    restaurant, _, vip = hall

    login(client, "osh", "adminpass123")
    client.post(
        f"/admin/tables/zone/{vip.id}/add",
        data={"csrf_token": csrf(client, "/admin/tables"), "count": "2", "kind": "xona"},
    )

    added = db.query(Table).filter_by(restaurant_id=restaurant.id, zone_id=vip.id).all()
    assert sorted(table.label for table in added) == ["5", "6"]


def test_another_restaurants_zone_cannot_be_filled(client, db, hall, tenant_b):
    """Begona bo'limga stol qo'shib bo'lmaydi — 404."""
    other_restaurant, _ = tenant_b
    foreign_zone = areas.create_zone(db, other_restaurant, "Begona bo'lim")

    login(client, "osh", "adminpass123")
    response = client.post(
        f"/admin/tables/zone/{foreign_zone.id}/add",
        data={"csrf_token": csrf(client, "/admin/tables"), "count": "1"},
    )

    assert response.status_code == 404
    assert db.query(Table).filter_by(zone_id=foreign_zone.id).count() == 0


# --- bino ko'rinishi -------------------------------------------------------


def test_the_building_reads_from_the_top_floor_down(client, db, hall):
    """Sahifa binoning kesimi: yuqori qavat tepada, yerto'la pastda."""
    restaurant, _, _ = hall
    areas.create_zone(db, restaurant, "Sovutgich", floor=-1)

    login(client, "osh", "adminpass123")
    body = html.unescape(client.get("/admin/tables?lang=uz").text)

    assert body.index("2-qavat") < body.index("1-qavat") < body.index("1-yerto'la")


def test_tables_sit_inside_their_own_area(client, db, hall):
    """Stol qaysi bo'limda turgani ko'rinib tursin — avval buni bilib bo'lmasdi."""
    restaurant, asosiy, vip = hall
    tables.move_many(db, restaurant.id, [seat(db, restaurant.id, "1").id], vip.id)

    login(client, "osh", "adminpass123")
    body = client.get("/admin/tables?lang=uz").text
    vip_block = body.split('data-zone="%d"' % vip.id)[1].split("</article>")[0]

    assert 'value="%d"' % seat(db, restaurant.id, "1").id in vip_block


def test_unassigned_tables_wait_on_the_shelf(client, db, hall):
    """Bo'limsiz stollar alohida javonda — ular afitsantga biriktirilmaydi."""
    login(client, "osh", "adminpass123")
    body = html.unescape(client.get("/admin/tables?lang=uz").text)

    assert "Bo'limsiz stollar" in body
    assert 'class="zone zone-loose"' in body


def test_an_empty_restaurant_gets_a_one_click_start(client, db, tenant_a):
    """Nol holatdan chiqish uchun egadan hech narsa o'ylab topish talab qilinmasin."""
    restaurant, _ = tenant_a
    restaurant.orders_enabled = True
    db.commit()

    login(client, "osh", "adminpass123")
    assert "hall-start" in client.get("/admin/tables").text

    client.post(
        "/admin/tables/build",
        data={"csrf_token": csrf(client, "/admin/tables"), "floors": "2", "per_floor": "3"},
    )

    zones = db.query(Zone).filter_by(restaurant_id=restaurant.id).all()
    assert sorted(zone.floor for zone in zones) == [1, 2]
    assert db.query(Table).filter_by(restaurant_id=restaurant.id).count() == 6
    # Har qavatning stollari o'z bo'limida
    for zone in zones:
        assert db.query(Table).filter_by(zone_id=zone.id).count() == 3


def test_the_starter_refuses_a_silly_building(client, db, tenant_a):
    """"200 qavat" degan son binoni emas, formani buzardi."""
    restaurant, _ = tenant_a
    restaurant.orders_enabled = True
    db.commit()

    login(client, "osh", "adminpass123")
    client.post(
        "/admin/tables/build",
        data={"csrf_token": csrf(client, "/admin/tables"), "floors": "200", "per_floor": "2"},
    )

    assert db.query(Zone).filter_by(restaurant_id=restaurant.id).count() == 5
