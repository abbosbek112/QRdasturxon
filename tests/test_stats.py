import html
from datetime import timedelta

import pytest

from app.models import Category, MenuItem, MenuView
from app.plans import limits_for
from app.services import stats

from tests.conftest import login


def window(days: int = 30):
    """Oxirgi N kunlik oraliq — stats endi (boshlanish, tugash) bilan ishlaydi."""
    end = stats.today()
    return end - timedelta(days=days - 1), end


@pytest.fixture
def menu(db, tenant_a):
    restaurant, _ = tenant_a
    category = Category(restaurant_id=restaurant.id, name={"uz": "Issiq taomlar"})
    db.add(category)
    db.flush()
    item = MenuItem(
        restaurant_id=restaurant.id,
        category_id=category.id,
        name={"uz": "Osh"},
        price=38000,
    )
    db.add(item)
    db.commit()
    return restaurant, item


def test_opening_the_menu_is_counted(client, db, menu):
    restaurant, _ = menu
    client.get(f"/r/{restaurant.slug}")
    assert stats.total_views(db, restaurant.id, *window()) == 1


def test_the_same_guest_is_counted_once(client, db, menu):
    """Til almashtirish yangi ochilish EMAS.

    Ilgari mijoz tilni uch marta almashtirsa "menyu 4 marta ochildi" deb
    yozilardi va restoran egasi soxta songa qarab qaror qabul qilardi.
    """
    restaurant, _ = menu
    client.get(f"/r/{restaurant.slug}")
    for lang in ("ru", "en", "uz"):
        client.get(f"/r/{restaurant.slug}?lang={lang}")
    client.get(f"/r/{restaurant.slug}")           # sahifani yangiladi

    assert stats.total_views(db, restaurant.id, *window()) == 1


def test_a_different_guest_is_counted_again(client, db, menu):
    """Ajratish sessiya bo'yicha — boshqa telefon boshqa mijoz."""
    restaurant, _ = menu
    client.get(f"/r/{restaurant.slug}")
    client.cookies.clear()
    client.get(f"/r/{restaurant.slug}")

    assert stats.total_views(db, restaurant.id, *window()) == 2


def test_search_is_not_counted_as_an_opening(client, db, menu):
    """Aks holda bitta mijoz qidiruv bilan sonni shishirib yuboradi."""
    restaurant, _ = menu
    client.get(f"/r/{restaurant.slug}?q=osh")
    assert stats.total_views(db, restaurant.id, *window()) == 0


def test_item_views_are_counted_for_both_page_and_sheet(client, db, menu):
    """Pastki oyna ham to'liq sahifa kabi hisoblanadi.

    Ikki xil mijoz: har biri o'z sessiyasida bir marta ochadi.
    """
    restaurant, item = menu
    client.get(f"/r/{restaurant.slug}/item/{item.id}")
    client.cookies.clear()
    client.get(f"/r/{restaurant.slug}/item/{item.id}?partial=1")

    top = stats.top_items(db, restaurant.id, *window())
    assert top[0][0].id == item.id
    assert top[0][1] == 2


def test_reopening_the_same_dish_is_counted_once(client, db, menu):
    """Mijoz taomni yopib qayta ochsa — bu qiziqish o'smagani."""
    restaurant, item = menu
    for _ in range(4):
        client.get(f"/r/{restaurant.slug}/item/{item.id}")

    assert stats.top_items(db, restaurant.id, *window())[0][1] == 1


# --- takrorni ajratish mantiqi (sof funksiya) ------------------------------


def test_a_repeat_inside_the_window_is_not_counted():
    seen = {}
    first, seen = stats.viewed(seen, "m1", now=1_000)
    again, seen = stats.viewed(seen, "m1", now=1_060)
    assert first is True and again is False


def test_a_visit_after_the_window_counts_again():
    seen = {}
    _, seen = stats.viewed(seen, "m1", now=1_000)
    later, seen = stats.viewed(seen, "m1", now=1_000 + stats.VIEW_WINDOW_SECONDS + 1)
    assert later is True


def test_browsing_keeps_the_visit_alive():
    """Kafeda uzoq o'tirgan mijoz 31-daqiqada ikkinchi marta sanalmasin."""
    seen = {}
    _, seen = stats.viewed(seen, "m1", now=0)
    for minute in range(1, 60):
        counted, seen = stats.viewed(seen, "m1", now=minute * 60)
        assert counted is False, f"{minute}-daqiqada qayta sanaldi"


def test_different_dishes_are_tracked_apart():
    seen = {}
    first, seen = stats.viewed(seen, "i1", now=1_000)
    second, seen = stats.viewed(seen, "i2", now=1_000)
    assert first is True and second is True


def test_the_cookie_does_not_grow_without_limit():
    """Sessiya cookie'si har so'rov bilan yuriladi — u shishib ketmasin."""
    seen = {}
    for n in range(stats.MAX_SEEN * 3):
        _, seen = stats.viewed(seen, f"i{n}", now=1_000 + n)
    assert len(seen) <= stats.MAX_SEEN
    # Eng so'nggilari qoladi
    assert f"i{stats.MAX_SEEN * 3 - 1}" in seen


def test_repeated_views_share_one_row_per_day(db, menu):
    """Kunlik yig'ma — jadval yillar davomida ham kichik qolishi kerak."""
    restaurant, _ = menu
    for _ in range(50):
        stats.record_view(db, restaurant.id)

    assert db.query(MenuView).count() == 1
    assert stats.total_views(db, restaurant.id, *window()) == 50


def test_daily_series_fills_empty_days_with_zero(db, menu):
    restaurant, _ = menu
    stats.record_view(db, restaurant.id)

    series = stats.daily_series(db, restaurant.id, *window(7))
    assert len(series) == 7
    assert series[-1] == (stats.today(), 1)
    assert all(count == 0 for _, count in series[:-1])


def test_old_days_fall_outside_the_window(db, menu):
    restaurant, _ = menu
    db.add(
        MenuView(
            restaurant_id=restaurant.id,
            item_id=None,
            day=stats.today() - timedelta(days=40),
            count=99,
        )
    )
    db.commit()
    assert stats.total_views(db, restaurant.id, *window(30)) == 0


def test_a_broken_counter_never_breaks_the_menu(client, db, menu, monkeypatch):
    """Statistika ikkinchi darajali — u yiqilsa ham mijoz menyuni ko'rishi kerak."""
    restaurant, _ = menu

    def explode(*args, **kwargs):
        from sqlalchemy.exc import OperationalError

        raise OperationalError("stats", {}, Exception("baza band"))

    monkeypatch.setattr(stats, "_bump", explode)
    response = client.get(f"/r/{restaurant.slug}")
    assert response.status_code == 200
    assert "Osh" in response.text


def test_dashboard_shows_the_counter(client, db, menu):
    restaurant, _ = menu
    client.get(f"/r/{restaurant.slug}")

    login(client, "osh", "adminpass123")
    body = html.unescape(client.get("/admin").text)
    assert f"{limits_for(restaurant).stats_days} kunda ochilgan" in body
    assert "Eng ko'p ochilgan taomlar" not in body  # taom hali ochilmagan


# --- muddat oralig'i ---

def test_a_custom_range_is_honoured(db, menu):
    restaurant, _ = menu
    for offset in (0, 3, 10):
        db.add(MenuView(
            restaurant_id=restaurant.id, item_id=None,
            day=stats.today() - timedelta(days=offset), count=5,
        ))
    db.commit()

    end = stats.today()
    # Faqat 0..5 kun oralig'i — 10 kun oldingisi tashqarida qolsin
    assert stats.total_views(db, restaurant.id, end - timedelta(days=5), end) == 10


def test_the_range_includes_both_edges(db, menu):
    restaurant, _ = menu
    day = stats.today() - timedelta(days=4)
    db.add(MenuView(restaurant_id=restaurant.id, item_id=None, day=day, count=7))
    db.commit()

    assert stats.total_views(db, restaurant.id, day, day) == 7


def test_a_backwards_range_is_straightened(db):
    """Foydalanuvchi sanalarni teskari kiritsa xato bermaymiz, joyini almashtiramiz."""
    end = stats.today()
    start = end - timedelta(days=3)
    assert stats.clamp_range(end, start, max_days=365) == (start, end)


def test_the_plan_caps_how_far_back_you_can_look(db):
    """Bepul tarifda 7 kun tarix bor — bir yil so'ralsa ham shunga kesiladi."""
    end = stats.today()
    start, _ = stats.clamp_range(end - timedelta(days=300), end, max_days=7)
    assert start == end - timedelta(days=6)


def test_the_future_is_trimmed_to_today(db):
    end = stats.today()
    _, stop = stats.clamp_range(end - timedelta(days=3), end + timedelta(days=50), max_days=365)
    assert stop == end


def test_a_broken_date_falls_back_instead_of_erroring(db):
    """Sana manzildan keladi — noto'g'ri yozilgani sahifani yiqitmasligi kerak."""
    start, end, key = stats.resolve_range("custom", "salom", "dunyo", max_days=365)
    assert key == stats.DEFAULT_PRESET
    assert (end - start).days == 29


@pytest.mark.parametrize("preset,span", [("kun", 1), ("hafta", 7), ("oy", 30), ("yil", 365)])
def test_each_preset_spans_its_own_window(db, preset, span):
    start, end, key = stats.resolve_range(preset, None, None, max_days=365)
    assert key == preset
    assert (end - start).days == span - 1


def test_an_unknown_preset_falls_back(db):
    _, _, key = stats.resolve_range("qandaydir", None, None, max_days=365)
    assert key == stats.DEFAULT_PRESET


# --- analitika sahifasi ---

def test_the_stats_page_ranks_dishes(client, db, menu):
    restaurant, item = menu
    for _ in range(3):
        stats.record_view(db, restaurant.id, item.id)

    login(client, "osh", "adminpass123")
    body = html.unescape(client.get("/admin/stats").text)
    assert "Osh" in body
    assert "Eng ko'p ochilgan taomlar" in body


def test_the_stats_page_honours_a_custom_range(client, db, menu):
    restaurant, _ = menu
    old = stats.today() - timedelta(days=5)
    db.add(MenuView(restaurant_id=restaurant.id, item_id=None, day=old, count=11))
    db.commit()

    login(client, "osh", "adminpass123")
    inside = client.get(f"/admin/stats?period=custom&start={old}&end={old}").text
    assert "11" in inside

    # O'sha kundan keyingi oraliqda o'sha son chiqmasligi kerak
    after = stats.today()
    outside = client.get(f"/admin/stats?period=custom&start={after}&end={after}").text
    assert "Bu oraliqda ochilish yo'q" in html.unescape(outside)


def test_the_free_plan_cannot_look_past_its_window(client, db, menu):
    """Bepul tarifda 7 kunlik tarix bor — bir yillik so'rov ham shunga kesiladi."""
    from app.models import Plan, SubscriptionStatus

    restaurant, _ = menu
    restaurant.plan = Plan.free
    restaurant.subscription_status = SubscriptionStatus.active
    old = stats.today() - timedelta(days=40)
    db.add(MenuView(restaurant_id=restaurant.id, item_id=None, day=old, count=999))
    db.commit()

    login(client, "osh", "adminpass123")
    body = html.unescape(client.get("/admin/stats?period=yil").text)
    assert "999" not in body


def test_one_restaurant_never_sees_another_ones_numbers(client, db, menu, tenant_b):
    restaurant, _ = menu
    other, _ = tenant_b
    db.add(MenuView(restaurant_id=other.id, item_id=None, day=stats.today(), count=777))
    db.commit()

    login(client, "osh", "adminpass123")
    assert "777" not in client.get("/admin/stats").text


# --- bir vaqtda kelgan mijozlar --------------------------------------------
#
# Bu yerdagi xatolar faqat yuk ostida ko'rinadi va jimgina noto'g'ri son
# beradi — shuning uchun ular testda qulflab qo'yilgan.


def test_the_menu_row_is_protected_even_though_item_id_is_null(db, menu):
    """SQL'da NULL != NULL.

    Oddiy `UNIQUE(restaurant_id, item_id, day)` menyu qatorini himoya
    qilmaydi va bir vaqtda kelgan ikki mijoz ikkita qator yasab qo'yardi.
    Shundan keyin har bir ochilish IKKALASINI ham oshirib, son ikki barobar
    shishardi. Himoya — qisman indeks.
    """
    from sqlalchemy.exc import IntegrityError

    restaurant, _ = menu
    day = stats.today()
    db.add(MenuView(restaurant_id=restaurant.id, item_id=None, day=day, count=1))
    db.commit()

    db.add(MenuView(restaurant_id=restaurant.id, item_id=None, day=day, count=1))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    assert db.query(MenuView).filter(MenuView.item_id.is_(None)).count() == 1


def test_a_second_view_updates_instead_of_failing(db, menu):
    """Qator allaqachon bo'lsa ikkinchi ochilish xato bermay sonni oshirsin.

    Ilgari u `IntegrityError` berardi va xato yuqorida yutilib, ochilish
    umuman yo'qolardi.
    """
    restaurant, item = menu
    for _ in range(5):
        stats.record_view(db, restaurant.id, item.id)

    rows = db.query(MenuView).filter(MenuView.item_id == item.id).all()
    assert len(rows) == 1
    assert rows[0].count == 5


def test_menu_and_item_views_do_not_collide(db, menu):
    """Menyu qatori va taom qatori bir-birini bosib ketmasin."""
    restaurant, item = menu
    stats.record_view(db, restaurant.id)
    stats.record_view(db, restaurant.id, item.id)

    assert db.query(MenuView).count() == 2
    assert all(row.count == 1 for row in db.query(MenuView).all())
