"""Xodim: faoliyat tarixi va baho.

Eng nozik joyi javobgarlikni belgilash. Buyurtmani BIRINCHI qabul qilgan
odam unga javobgar bo'ladi va keyin uni boshqa afitsant yopib qo'ysa ham
javobgarlik ko'chmaydi — aks holda tarix "kim ulgurdi" ni emas, "kim
oxirgi tegdi" ni ko'rsatardi.
"""

import html
from datetime import timedelta
from decimal import Decimal

import pytest

from app.models import (
    Category,
    MenuItem,
    Order,
    OrderStatus,
    Role,
    StaffReview,
    Table,
    User,
    utcnow_naive,
)
from app.security import hash_password
from app.services import orders, staff

from tests.conftest import csrf, login


def make_waiter(db, restaurant, username):
    person = User(
        username=username,
        password_hash=hash_password("afitsant123"),
        role=Role.waiter,
        restaurant_id=restaurant.id,
    )
    db.add(person)
    db.flush()
    return person


@pytest.fixture
def kafe(db, tenant_a):
    """Ikkita afitsanti, bitta stoli va bitta taomi bor restoran."""
    restaurant, _ = tenant_a
    restaurant.orders_enabled = True

    category = Category(restaurant_id=restaurant.id, name={"uz": "Taomlar"})
    db.add(category)
    db.flush()
    item = MenuItem(
        restaurant_id=restaurant.id,
        category_id=category.id,
        name={"uz": "Osh"},
        price=Decimal("45000"),
    )
    db.add(item)
    table = Table(restaurant_id=restaurant.id, label="7", code="sinovkod")
    db.add(table)
    ali = make_waiter(db, restaurant, "osh-ali")
    vali = make_waiter(db, restaurant, "osh-vali")
    db.commit()
    return restaurant, table, item, ali, vali


def place(db, restaurant, table, item, qty=1):
    return orders.place(db, restaurant=restaurant, table=table, wanted=[(item.id, qty)])


# ------------------------------------------------------------- javobgarlik


def test_the_first_waiter_to_accept_becomes_the_owner_of_the_order(db, kafe):
    restaurant, table, item, ali, _ = kafe
    order = place(db, restaurant, table, item)

    orders.set_status(db, order, OrderStatus.accepted, by=ali)

    assert order.handled_by_id == ali.id


def test_responsibility_does_not_move_to_whoever_touches_it_last(db, kafe):
    """Boshqa afitsant yopsa ham javobgar birinchi qabul qilgan bo'lib qoladi.

    Aks holda tarix "kim ulgurdi" ni emas, "kim oxirgi tegdi" ni
    ko'rsatardi va tez javob bergan odamning mehnati boshqasiga yozilardi.
    """
    restaurant, table, item, ali, vali = kafe
    order = place(db, restaurant, table, item)

    orders.set_status(db, order, OrderStatus.accepted, by=ali)
    orders.set_status(db, order, OrderStatus.served, by=vali)

    assert order.handled_by_id == ali.id


def test_re_accepting_after_an_undo_does_not_steal_the_credit(db, kafe):
    """Xato bosilib orqaga qaytarilsa ham javobgar o'zgarmasin.

    Bu HAQIQIY yo'l: afitsant qabul qiladi, keyin kimdir uni "yangi"ga
    qaytaradi va boshqa afitsant qabul qiladi. Javobgarlikni faqat
    `set_status` dagi shart qo'riqlasa, shu yerda u ikkinchi odamga
    o'tib ketardi.
    """
    restaurant, table, item, ali, vali = kafe
    order = place(db, restaurant, table, item)

    orders.set_status(db, order, OrderStatus.accepted, by=ali)
    orders.set_status(db, order, OrderStatus.new, by=ali)
    orders.set_status(db, order, OrderStatus.accepted, by=vali)

    assert order.handled_by_id == ali.id


def test_the_owner_touching_the_board_is_not_recorded_as_staff(db, kafe, tenant_a):
    """Egasi ham taxtaga tegishi mumkin — u xodim emas.

    Uning tegishi javobgarlik deb yozilsa, xodim hisoboti egasining
    ishlari bilan aralashib ketardi.
    """
    restaurant, table, item, _, _ = kafe
    _, egasi = tenant_a
    order = place(db, restaurant, table, item)

    orders.set_status(db, order, OrderStatus.accepted, by=egasi)

    assert order.handled_by_id is None


def test_status_change_without_a_person_still_works(db, kafe):
    """Eski chaqiruvlar buzilmasin — `by` ixtiyoriy."""
    restaurant, table, item, _, _ = kafe
    order = place(db, restaurant, table, item)

    orders.set_status(db, order, OrderStatus.accepted)

    assert order.status is OrderStatus.accepted
    assert order.handled_by_id is None


# ---------------------------------------------------------------- faoliyat


def test_activity_counts_what_the_waiter_actually_did(db, kafe):
    restaurant, table, item, ali, vali = kafe

    birinchi = place(db, restaurant, table, item)
    orders.set_status(db, birinchi, OrderStatus.accepted, by=ali)
    orders.set_status(db, birinchi, OrderStatus.served, by=ali)

    ikkinchi = place(db, restaurant, table, item, qty=2)
    orders.set_status(db, ikkinchi, OrderStatus.accepted, by=ali)

    uchinchi = place(db, restaurant, table, item)
    orders.set_status(db, uchinchi, OrderStatus.accepted, by=vali)

    natija = staff.activity_for(db, restaurant.id, [ali.id, vali.id])

    assert natija[ali.id].accepted == 2
    assert natija[ali.id].served == 1
    assert natija[ali.id].total == Decimal("135000")
    assert natija[vali.id].accepted == 1
    assert natija[vali.id].served == 0


def test_average_reply_time_is_measured_from_arrival_to_acceptance(db, kafe):
    """Mijoz aynan shu vaqtni kutib o'tiradi — o'lchov shu bo'lishi kerak."""
    restaurant, table, item, ali, _ = kafe
    now = utcnow_naive()

    for kechikish in (30, 90):
        order = place(db, restaurant, table, item)
        order.created_at = now - timedelta(minutes=5)
        order.accepted_at = order.created_at + timedelta(seconds=kechikish)
        order.status = OrderStatus.accepted
        order.handled_by_id = ali.id
    db.commit()

    natija = staff.activity_for(db, restaurant.id, [ali.id])
    assert natija[ali.id].avg_seconds == 60


def test_an_untouched_order_is_not_counted(db, kafe):
    """Javob berilmagan buyurtma hech kimning hisobiga yozilmasin."""
    restaurant, table, item, ali, _ = kafe
    place(db, restaurant, table, item)

    assert staff.activity_for(db, restaurant.id, [ali.id]) == {}


def test_an_undone_acceptance_stops_counting(db, kafe):
    """Qabul qilish orqaga qaytarilsa u hisobda qolmasin.

    Xodim buyurtmaga bog'langan bo'lib qoladi (javobgarlik ko'chmasligi
    uchun), lekin qabul qilish vaqti o'chadi. Faoliyat aynan shu vaqtga
    tayanadi — usiz "qabul qildim" degan raqam ish qilinmagan holda ham
    o'sib boraverardi.
    """
    restaurant, table, item, ali, _ = kafe
    order = place(db, restaurant, table, item)
    orders.set_status(db, order, OrderStatus.accepted, by=ali)
    orders.set_status(db, order, OrderStatus.new, by=ali)

    assert order.handled_by_id == ali.id
    assert order.accepted_at is None
    assert staff.activity_for(db, restaurant.id, [ali.id]) == {}


def test_old_orders_fall_out_of_the_window(db, kafe):
    """Faoliyat oxirgi oyni ko'rsatadi — bir yil oldingi ish emas."""
    restaurant, table, item, ali, _ = kafe
    order = place(db, restaurant, table, item)
    eski = utcnow_naive() - timedelta(days=staff.ACTIVITY_DAYS + 5)
    order.created_at = eski
    order.accepted_at = eski + timedelta(seconds=30)
    order.status = OrderStatus.accepted
    order.handled_by_id = ali.id
    db.commit()

    assert staff.activity_for(db, restaurant.id, [ali.id]) == {}


def test_activity_is_scoped_to_one_restaurant(db, kafe, tenant_b):
    """Qo'shni restoranning buyurtmasi bu xodimning hisobiga tushmasin."""
    restaurant, table, item, ali, _ = kafe
    boshqa, _ = tenant_b
    boshqa.orders_enabled = True

    order = place(db, restaurant, table, item)
    orders.set_status(db, order, OrderStatus.accepted, by=ali)

    assert staff.activity_for(db, boshqa.id, [ali.id]) == {}


def test_recent_orders_lists_only_this_persons_work(db, kafe):
    restaurant, table, item, ali, vali = kafe

    meniki = place(db, restaurant, table, item)
    orders.set_status(db, meniki, OrderStatus.accepted, by=ali)
    boshqaniki = place(db, restaurant, table, item)
    orders.set_status(db, boshqaniki, OrderStatus.accepted, by=vali)

    topilgan = staff.recent_orders(db, restaurant.id, ali.id)
    assert [o.id for o in topilgan] == [meniki.id]


def test_history_survives_the_person_being_deleted(db, kafe):
    """Xodim ishdan ketsa buyurtma tarixi qolishi kerak.

    Buyurtma summasi hisobotning bir qismi — u xodim bilan birga
    o'chib ketsa kunlik jami raqam o'zgarib qolardi.
    """
    restaurant, table, item, ali, _ = kafe
    order = place(db, restaurant, table, item)
    orders.set_status(db, order, OrderStatus.accepted, by=ali)
    order_id = order.id

    db.delete(ali)
    db.commit()
    db.expire_all()

    qolgan = db.get(Order, order_id)
    assert qolgan is not None
    assert qolgan.handled_by_id is None
    assert qolgan.total == Decimal("45000")


# -------------------------------------------------------------------- baho


def test_a_review_is_kept_with_its_date_and_author(db, kafe, tenant_a):
    restaurant, _, _, ali, _ = kafe
    _, egasi = tenant_a

    staff.add_review(db, restaurant.id, ali, rating=4, note="  Tez   javob beradi ", author=egasi)

    yozuvlar = staff.reviews_for(db, restaurant.id, ali.id)
    assert len(yozuvlar) == 1
    assert yozuvlar[0].rating == 4
    # Ortiqcha bo'shliqlar tozalanadi
    assert yozuvlar[0].note == "Tez javob beradi"
    assert yozuvlar[0].author_id == egasi.id


def test_reviews_are_a_history_not_a_single_number(db, kafe):
    """Baho ustiga yozilmaydi: o'sish yoki tushish ko'rinishi kerak."""
    restaurant, _, _, ali, _ = kafe

    staff.add_review(db, restaurant.id, ali, rating=3)
    staff.add_review(db, restaurant.id, ali, rating=5)

    assert len(staff.reviews_for(db, restaurant.id, ali.id)) == 2
    assert staff.rating_summary(db, restaurant.id, [ali.id])[ali.id] == (4.0, 2)


@pytest.mark.parametrize("bad", [0, 6, -1, 99])
def test_a_rating_outside_one_to_five_is_refused(db, kafe, bad):
    restaurant, _, _, ali, _ = kafe
    with pytest.raises(Exception):
        staff.add_review(db, restaurant.id, ali, rating=bad)


def test_a_person_without_reviews_has_no_score(db, kafe):
    restaurant, _, _, ali, _ = kafe
    assert staff.rating_summary(db, restaurant.id, [ali.id]) == {}


def test_reviews_are_scoped_to_one_restaurant(db, kafe, tenant_b):
    restaurant, _, _, ali, _ = kafe
    boshqa, _ = tenant_b
    staff.add_review(db, restaurant.id, ali, rating=5)

    assert staff.reviews_for(db, boshqa.id, ali.id) == []
    assert staff.rating_summary(db, boshqa.id, [ali.id]) == {}


def test_deleting_a_person_takes_their_reviews_with_them(db, kafe):
    """Baho xodimga tegishli — u ketsa baho ham qolmasin."""
    restaurant, _, _, ali, _ = kafe
    staff.add_review(db, restaurant.id, ali, rating=5)

    db.delete(ali)
    db.commit()

    assert db.query(StaffReview).count() == 0


# ------------------------------------------------------------------ sahifa


def test_the_staff_page_shows_activity(client, db, kafe):
    restaurant, table, item, ali, _ = kafe
    order = place(db, restaurant, table, item)
    orders.set_status(db, order, OrderStatus.accepted, by=ali)

    login(client, "osh", "adminpass123")
    body = html.unescape(client.get("/admin/staff").text)

    assert "osh-ali" in body
    assert "buyurtma qabul qilgan" in body


def test_the_detail_page_shows_history_and_reviews(client, db, kafe):
    restaurant, table, item, ali, _ = kafe
    order = place(db, restaurant, table, item)
    orders.set_status(db, order, OrderStatus.accepted, by=ali)
    staff.add_review(db, restaurant.id, ali, rating=5, note="Yaxshi ishlaydi")

    login(client, "osh", "adminpass123")
    body = html.unescape(client.get(f"/admin/staff/{ali.id}").text)

    assert "7-stol" in body
    assert "Osh" in body
    assert "Yaxshi ishlaydi" in body


def test_a_review_can_be_added_from_the_page(client, db, kafe):
    restaurant, _, _, ali, _ = kafe

    login(client, "osh", "adminpass123")
    token = csrf(client, f"/admin/staff/{ali.id}")
    response = client.post(
        f"/admin/staff/{ali.id}/review",
        data={"csrf_token": token, "rating": "4", "note": "Band kunlarda ham ulguradi"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    yozuvlar = staff.reviews_for(db, restaurant.id, ali.id)
    assert [r.rating for r in yozuvlar] == [4]


def test_another_owner_cannot_open_this_persons_page(client, db, kafe, tenant_b):
    """Qo'shni restoran egasi bu xodimning tarixini ko'rmasin."""
    _, _, _, ali, _ = kafe
    boshqa, _ = tenant_b
    db.commit()

    login(client, "choy", "adminpass123")
    assert client.get(f"/admin/staff/{ali.id}").status_code == 404


def test_another_owner_cannot_rate_this_person(client, db, kafe, tenant_b):
    restaurant, _, _, ali, _ = kafe
    db.commit()

    login(client, "choy", "adminpass123")
    token = csrf(client, "/admin/staff")
    response = client.post(
        f"/admin/staff/{ali.id}/review",
        data={"csrf_token": token, "rating": "1", "note": "Yomon"},
    )

    assert response.status_code == 404
    assert staff.reviews_for(db, restaurant.id, ali.id) == []


def test_a_review_cannot_be_deleted_across_restaurants(client, db, kafe, tenant_b):
    restaurant, _, _, ali, _ = kafe
    review = staff.add_review(db, restaurant.id, ali, rating=5)
    boshqa, _ = tenant_b
    qoshni_afitsant = make_waiter(db, boshqa, "choy-bek")
    db.commit()

    login(client, "choy", "adminpass123")
    token = csrf(client, "/admin/staff")
    response = client.post(
        f"/admin/staff/{qoshni_afitsant.id}/review/{review.id}/delete",
        data={"csrf_token": token},
    )

    assert response.status_code == 404
    assert len(staff.reviews_for(db, restaurant.id, ali.id)) == 1
