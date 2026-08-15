"""Kombo to'plamlar: bir necha taom birga, arzonroq.

Uch narsa alohida sinaladi, chunki uchalasi ham jimgina buziladi:

* tarkibga QO'SHNI restoranning taomini solib bo'lmasin;
* tarkibida yashirilgan taom bo'lgan kombo mijozga ko'rinmasin — aks
  holda oshxonaga bajarib bo'lmaydigan buyurtma tushardi;
* buyurtma narxi bazadan olinsin, brauzerdan kelgan qiymatdan emas.
"""

import html
from decimal import Decimal

import pytest

from app.models import Category, Combo, ComboLine, MenuItem, Table
from app.services import combos, orders

from tests.conftest import csrf, login


def make_item(db, restaurant, category, name, price, available=True):
    item = MenuItem(
        restaurant_id=restaurant.id,
        category_id=category.id,
        name={"uz": name},
        price=Decimal(price),
        is_available=available,
    )
    db.add(item)
    db.flush()
    return item


@pytest.fixture
def kafe(db, tenant_a):
    """Ikkita taomi va bitta stoli bor restoran."""
    restaurant, _ = tenant_a
    restaurant.orders_enabled = True

    category = Category(restaurant_id=restaurant.id, name={"uz": "Taomlar"})
    db.add(category)
    db.flush()

    burger = make_item(db, restaurant, category, "Burger", "30000")
    kola = make_item(db, restaurant, category, "Kola", "10000")
    db.add(Table(restaurant_id=restaurant.id, label="1", code="sinovkod"))
    db.commit()
    return restaurant, category, burger, kola


@pytest.fixture
def kombo(db, kafe):
    """Burger + kola = 35 000 (alohida 40 000 turadi)."""
    restaurant, _, burger, kola = kafe
    combo = combos.create(
        db,
        restaurant.id,
        name={"uz": "Ikki kishilik"},
        description={},
        price=Decimal("35000"),
        lines=[(burger.id, 1), (kola.id, 1)],
    )
    return combo


# ------------------------------------------------------------------ hisob


def test_saving_is_the_difference_from_buying_separately(db, kombo):
    assert combos.full_price(kombo) == Decimal("40000")
    assert combos.saving(kombo) == Decimal("5000")


def test_saving_follows_todays_prices(db, kafe, kombo):
    """Tejash MUZLATILMAYDI — tarkibdagi narx o'zgarsa u ham o'zgaradi.

    Aks holda "5 000 tejaysiz" yozuvi ertaga yolg'onga aylanardi.
    """
    _, _, burger, _ = kafe
    burger.price = Decimal("50000")
    db.commit()

    assert combos.saving(kombo) == Decimal("25000")


def test_a_combo_dearer_than_its_parts_shows_no_saving(db, kombo):
    """Manfiy tejash ko'rsatilmasin.

    Egasi narxni xato qo'yishi mumkin, lekin "-5 000 tejaysiz" degan
    yozuv xatoning o'zidan ham yomon ko'rinardi.
    """
    kombo.price = Decimal("60000")
    db.commit()

    assert combos.saving(kombo) == Decimal("0")


def test_quantity_counts_towards_the_full_price(db, kafe, kombo):
    _, _, burger, kola = kafe
    combos.set_lines(db, kombo, [(burger.id, 2), (kola.id, 1)])
    db.commit()

    assert combos.full_price(kombo) == Decimal("70000")


# -------------------------------------------------------------- tegishlilik


def test_another_restaurants_dish_cannot_be_put_in(db, kafe, kombo, tenant_b):
    """Formadagi raqamni almashtirib qo'shni restoranning taomini solib bo'lmasin."""
    boshqa, _ = tenant_b
    category = Category(restaurant_id=boshqa.id, name={"uz": "Ular"})
    db.add(category)
    db.flush()
    begona = make_item(db, boshqa, category, "Begona taom", "99000")
    db.commit()

    combos.set_lines(db, kombo, [(begona.id, 1)])
    db.commit()

    assert kombo.lines == []
    assert combos.full_price(kombo) == Decimal("0")


def test_owned_refuses_someone_elses_combo(db, kombo, tenant_b):
    boshqa, _ = tenant_b
    with pytest.raises(Exception) as xato:
        combos.owned(db, boshqa.id, kombo.id)
    assert "404" in str(xato.value) or "topilmadi" in str(xato.value)


# ----------------------------------------------------------- ko'rinishi


def test_a_combo_with_a_hidden_dish_disappears_from_the_menu(db, kafe, kombo):
    """Tarkibidagi taom yashirilsa kombo ham ko'rinmasin.

    Bu eng muhim qoida: aks holda mijoz buyurtma bergan bo'lardi va
    oshxona uni bajara olmasdi.
    """
    _, _, burger, _ = kafe
    assert combos.is_orderable(kombo)

    burger.is_available = False
    db.commit()

    assert not combos.is_orderable(kombo)
    assert combos.visible(db, kombo.restaurant_id) == []


def test_an_empty_combo_is_not_offered(db, kafe, kombo):
    """Tarkibi bo'sh kombo — hech nima. U menyuda turmasin."""
    combos.set_lines(db, kombo, [])
    db.commit()

    assert not combos.is_orderable(kombo)


def test_a_switched_off_combo_stays_out_of_the_menu(db, kombo):
    kombo.is_active = False
    db.commit()

    assert combos.visible(db, kombo.restaurant_id) == []


def test_deleting_a_dish_takes_it_out_of_the_combo(db, kafe, kombo):
    """Taom o'chirilsa kombo tarkibida "yo'q taom" qolib ketmasin."""
    _, _, burger, _ = kafe
    db.delete(burger)
    db.commit()
    db.expire_all()

    qayta = combos.owned(db, kombo.restaurant_id, kombo.id)
    assert [line.item_id for line in qayta.lines] != []
    assert all(line.item is not None for line in qayta.lines)
    assert len(qayta.lines) == 1


# -------------------------------------------------------------- buyurtma


def test_a_combo_can_be_ordered(db, kafe, kombo):
    restaurant, _, _, _ = kafe
    table = db.query(Table).filter(Table.restaurant_id == restaurant.id).one()

    order = orders.place(
        db, restaurant=restaurant, table=table, wanted=[], combos=[(kombo.id, 2)]
    )

    assert len(order.lines) == 1
    line = order.lines[0]
    assert line.name == "Ikki kishilik"
    assert line.quantity == 2
    # Narx BAZADAN olinadi
    assert line.unit_price == Decimal("35000")
    assert order.total == Decimal("70000")


def test_a_combo_arrives_as_one_line_not_its_parts(db, kafe, kombo):
    """Afitsant taxtasida kombo bitta qator bo'lib tursin.

    Tarkibiga yoyilsa "bular bitta to'plam" degan ma'no yo'qolardi va
    oshxona ularni alohida buyurtma deb tushunardi.
    """
    restaurant, _, _, _ = kafe
    table = db.query(Table).filter(Table.restaurant_id == restaurant.id).one()

    order = orders.place(
        db, restaurant=restaurant, table=table, wanted=[], combos=[(kombo.id, 1)]
    )

    assert [line.name for line in order.lines] == ["Ikki kishilik"]
    assert order.lines[0].item_id is None


def test_a_hidden_combo_cannot_be_ordered(db, kafe, kombo):
    """Yashirilgan kombo buyurtmaga tushmasin — narxi ham qo'shilmasin."""
    restaurant, _, burger, _ = kafe
    table = db.query(Table).filter(Table.restaurant_id == restaurant.id).one()
    burger.is_available = False
    db.commit()

    with pytest.raises(Exception):
        orders.place(
            db, restaurant=restaurant, table=table, wanted=[], combos=[(kombo.id, 1)]
        )


@pytest.fixture
def qoshni_kombo(db, tenant_b):
    """Qo'shni restoranning TO'LIQ ishlaydigan kombosi.

    Ataylab to'liq: bo'sh kombo baribir hech qayerda ko'rinmaydi, ya'ni
    u bilan sinalgan tekshiruv tegishlilik haqida hech nima aytmasdi.
    Aynan shu xato mening birinchi variantimda bor edi.
    """
    boshqa, _ = tenant_b
    boshqa.orders_enabled = True
    category = Category(restaurant_id=boshqa.id, name={"uz": "Ular"})
    db.add(category)
    db.flush()
    taom = make_item(db, boshqa, category, "Qo'shni taom", "20000")
    db.commit()
    return combos.create(
        db,
        boshqa.id,
        name={"uz": "Qo'shni kombo"},
        description={},
        price=Decimal("15000"),
        lines=[(taom.id, 1)],
    )


def test_another_restaurants_combo_cannot_be_ordered(db, kafe, qoshni_kombo):
    """Qo'shni restoranning kombosi raqami bilan buyurtma bermasin."""
    restaurant, _, _, _ = kafe
    # Qo'shnining o'zida kombo ishlaydi — ya'ni u rad etilishi tegishlilik
    # tufayli, "baribir buzuq" bo'lgani uchun emas
    assert combos.is_orderable(qoshni_kombo)

    table = db.query(Table).filter(Table.restaurant_id == restaurant.id).one()
    with pytest.raises(Exception):
        orders.place(
            db,
            restaurant=restaurant,
            table=table,
            wanted=[],
            combos=[(qoshni_kombo.id, 1)],
        )


def test_the_menu_never_shows_a_neighbours_combo(client, kafe, kombo, qoshni_kombo):
    """Mijoz menyusida faqat SHU restoranning kombosi tursin."""
    restaurant, _, _, _ = kafe
    body = html.unescape(client.get(f"/r/{restaurant.slug}").text)

    assert "Ikki kishilik" in body
    assert "Qo'shni kombo" not in body


def test_visible_is_scoped_to_one_restaurant(db, kafe, kombo, qoshni_kombo):
    restaurant, _, _, _ = kafe
    korinadigan = combos.visible(db, restaurant.id)

    assert [c.id for c in korinadigan] == [kombo.id]


def test_dishes_and_combos_can_be_ordered_together(db, kafe, kombo):
    restaurant, _, burger, _ = kafe
    table = db.query(Table).filter(Table.restaurant_id == restaurant.id).one()

    order = orders.place(
        db,
        restaurant=restaurant,
        table=table,
        wanted=[(burger.id, 1)],
        combos=[(kombo.id, 1)],
    )

    assert {line.name for line in order.lines} == {"Burger", "Ikki kishilik"}
    assert order.total == Decimal("65000")


# ------------------------------------------------------------------ sahifa


def test_the_menu_shows_the_combo(client, kafe, kombo):
    restaurant, _, _, _ = kafe
    body = client.get(f"/r/{restaurant.slug}").text

    assert "Ikki kishilik" in body
    # Tarkibi ham ko'rinsin — mijoz nimani olayotganini bilishi kerak
    assert "Burger" in body
    assert "Kola" in body


def test_the_menu_hides_a_combo_whose_dish_is_hidden(client, db, kafe, kombo):
    restaurant, _, burger, _ = kafe
    burger.is_available = False
    db.commit()

    assert "Ikki kishilik" not in client.get(f"/r/{restaurant.slug}").text


def test_a_search_does_not_show_combos(client, kafe, kombo):
    """Qidiruv aniq taom izlayotgan odam uchun — kombo aralashmasin."""
    restaurant, _, _, _ = kafe
    assert "Ikki kishilik" not in client.get(f"/r/{restaurant.slug}?q=kola").text


# ------------------------------------------------------------- admin sahifa


def test_the_owner_sees_their_combos(client, kafe, kombo):
    login(client, "osh", "adminpass123")
    body = client.get("/admin/combos").text

    assert "Ikki kishilik" in body
    assert body.count("Burger") >= 1


def test_the_owner_cannot_see_someone_elses(client, db, kombo, qoshni_kombo):
    """Qo'shni egasi o'z kombosini ko'radi, bu restorannikini emas.

    Qo'shnida ham taom, ham kombo BO'LISHI shart: taomsiz restoranda
    sahifa "avval taom qo'shing" ekranini ko'rsatadi va kombolar ro'yxati
    umuman chizilmaydi — bunday tekshiruv hech nima isbotlamasdi.
    """
    login(client, "choy", "adminpass123")
    body = html.unescape(client.get("/admin/combos").text)

    assert "Qo'shni kombo" in body
    assert "Ikki kishilik" not in body


def test_quantities_stay_with_their_own_dish(client, db, kafe):
    """Belgilanmagan taom sonini QO'SHNISIGA yopishtirmasin.

    Katakcha belgilanmasa brauzer uni yubormaydi, son maydonini esa
    yuboradi. Ikki parallel ro'yxatda bu siljish berardi: birinchi taomni
    tashlab ikkinchisini tanlasangiz, ikkinchisiga birinchisining soni
    tushardi va egasi buni faqat narx noto'g'ri chiqqanda payqardi.
    """
    restaurant, _, burger, kola = kafe

    login(client, "osh", "adminpass123")
    token = csrf(client, "/admin/combos")
    response = client.post(
        "/admin/combos",
        data={
            "csrf_token": token,
            "name_uz": "Sinov",
            "price": "1000",
            # Faqat KOLA belgilangan, lekin ikkala son ham yuboriladi
            "item_id": [str(kola.id)],
            f"qty_{burger.id}": "7",
            f"qty_{kola.id}": "3",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    yangi = db.query(Combo).filter(Combo.name["uz"].as_string() == "Sinov").one()
    assert [(line.item_id, line.quantity) for line in yangi.lines] == [(kola.id, 3)]
