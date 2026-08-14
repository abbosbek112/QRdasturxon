"""Zal sahifasi: stollarni bo'limlarga ko'chirish va qo'shish.

Egasi zalni bir marta yig'adi va keyin kamdan-kam tegadi, lekin o'sha bir
marta ishonchli bo'lishi kerak: 30 ta stolni bittalab ko'chirish bilan hech
kim shug'ullanmaydi.

Eng muhim qoida shu yerda qulflanadi: **ko'chirish faqat o'z restorani
ichida.** Stol ham, bo'lim ham begona bo'lsa amal bajarilmaydi.
"""

import html
import re

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


# --- qavat maydoni ---------------------------------------------------------


def test_the_owner_types_the_floor_instead_of_picking_it(client, db, hall):
    """Qavat tayyor ro'yxatdan tanlanmaydi — egasi o'zi yozadi.

    Ilgari bu yerda "5-qavat"dan "3-yerto'la"gacha tayyor ro'yxat turardi
    va u qavat sonini oldindan cheklab qo'yardi: balandroq binoli restoran
    o'z qavatini umuman qo'sha olmasdi.
    """
    restaurant, _, _ = hall
    login(client, "osh", "adminpass123")

    client.post(
        "/admin/zones",
        data={"csrf_token": csrf(client, "/admin/tables"), "name": "Yettinchi", "floor": "7"},
    )

    assert db.query(Zone).filter_by(name="Yettinchi").one().floor == 7


def test_the_basement_tick_makes_the_floor_negative(client, db, hall):
    """Egasiga manfiy son ko'rsatilmaydi: "2" + yerto'la belgisi."""
    restaurant, _, _ = hall
    login(client, "osh", "adminpass123")

    client.post(
        "/admin/zones",
        data={
            "csrf_token": csrf(client, "/admin/tables"),
            "name": "Sovutgich",
            "floor": "2",
            "basement": "1",
        },
    )

    zone = db.query(Zone).filter_by(name="Sovutgich").one()
    assert zone.floor == -2
    body = html.unescape(client.get("/admin/tables?lang=uz").text)
    assert "2-yerto'la" in body


def test_adding_an_area_to_a_basement_stays_in_the_basement(client, db, hall):
    """Yerto'ladagi "Bo'lim qo'shish" yangi bo'limni yuqoriga chiqarib yubormasin.

    Qavat ikki maydon bilan uzatiladi (musbat raqam + yerto'la belgisi).
    Yashirin maydonda manfiy son yuborilsa server uni musbatga aylantirib,
    yerto'lada yasalgan bo'lim 1-qavatga tushib qolardi.
    """
    restaurant, _, _ = hall
    areas.create_zone(db, restaurant, "Sovutgich", floor=-1)

    login(client, "osh", "adminpass123")
    body = html.unescape(client.get("/admin/tables?lang=uz").text)
    block = body.split("1-yerto'la")[1].split("</section>")[0]
    hidden = re.findall(r'<input type="hidden" name="(floor|basement)" value="([^"]*)"', block)

    assert dict(hidden) == {"floor": "1", "basement": "1"}

    client.post(
        "/admin/zones",
        data={
            "csrf_token": csrf(client, "/admin/tables"),
            "name": "Omborxona",
            **dict(hidden),
        },
    )
    assert db.query(Zone).filter_by(name="Omborxona").one().floor == -1


def test_editing_a_basement_keeps_it_underground(client, db, hall):
    """Yerto'ladagi bo'limni tahrirlaganda u yuqoriga sakrab chiqmasin."""
    restaurant, _, _ = hall
    zone = areas.create_zone(db, restaurant, "Sovutgich", floor=-2)

    login(client, "osh", "adminpass123")
    body = client.get("/admin/tables").text
    block = body.split('data-zone="%d"' % zone.id)[1].split("</article>")[0]

    # Forma katakchani belgilangan holda chizadi va raqamni musbat ko'rsatadi.
    # Aks holda egasi nomni tuzatib "Saqlash" bosishi bilan bo'lim jimgina
    # yerto'ladan 2-qavatga chiqib ketardi.
    tick = re.search(r'name="basement"[^>]*>', block, re.S).group(0)
    number = re.search(r'name="floor"[^>]*>', block, re.S).group(0)
    assert "checked" in tick
    assert 'value="2"' in number

    client.post(
        f"/admin/zones/{zone.id}",
        data={
            "csrf_token": csrf(client, "/admin/tables"),
            "name": "Sovutgich",
            "floor": "2",
            "basement": "1",
        },
    )
    db.refresh(zone)
    assert zone.floor == -2


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
    """Nol holatdan chiqish uchun egadan hech narsa o'ylab topish talab qilinmasin.

    Faqat QAVATLAR yasaladi. Ilgari "har qavatda nechta stol" ham
    so'ralardi va hamma qavatga bir xil son qo'yilardi — amalda qavatlar
    bir xil emas, shuning uchun stollarni egasi o'zi qo'shadi.
    """
    restaurant, _ = tenant_a
    restaurant.orders_enabled = True
    db.commit()

    login(client, "osh", "adminpass123")
    assert "hall-start" in client.get("/admin/tables").text

    client.post(
        "/admin/tables/build",
        data={"csrf_token": csrf(client, "/admin/tables"), "floors": "2"},
    )

    zones = db.query(Zone).filter_by(restaurant_id=restaurant.id).all()
    assert sorted(zone.floor for zone in zones) == [1, 2]
    assert db.query(Table).filter_by(restaurant_id=restaurant.id).count() == 0


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



# --- raqamlashni egasi belgilaydi ----------------------------------------
#
# Restoranlar buni har xil qiladi: birida har qavat 1 dan boshlanadi,
# boshqasida 1-qavatda 10 stol bo'lsa 2-qavatniki 11 dan ketadi. Avtomatik
# raqamlash ikkinchisiga to'g'ri kelmasdi.


def test_the_owner_chooses_the_starting_number(db, hall):
    restaurant, _, vip = hall

    created = tables.add_next(db, restaurant, 3, "stol", vip.id, start=11)

    assert [table.label for table in created] == ["11", "12", "13"]


def test_a_chosen_start_still_skips_taken_numbers(db, hall):
    """Egasi 3 dan boshlasa ham mavjud raqam ustiga yozilmasin."""
    restaurant, _, vip = hall   # 1-4 allaqachon bor

    created = tables.add_next(db, restaurant, 2, "stol", vip.id, start=3)

    assert [table.label for table in created] == ["5", "6"]


def test_without_a_start_it_continues_as_before(db, hall):
    restaurant, _, vip = hall

    created = tables.add_next(db, restaurant, 2, "stol", vip.id)

    assert [table.label for table in created] == ["5", "6"]


def test_the_page_offers_the_starting_number(client, db, hall):
    login(client, "osh", "adminpass123")

    assert 'name="start"' in client.get("/admin/tables").text
