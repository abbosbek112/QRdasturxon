import html
from datetime import timedelta

import pytest

from app.models import (
    Category,
    MenuItem,
    Plan,
    Restaurant,
    SubscriptionStatus,
    User,
    utcnow_naive,
)
from app.plans import LIMITS, TRIAL_DAYS, effective_plan, limits_for, trial_days_left

from tests.conftest import csrf, login, make_restaurant


def signup(client, **overrides):
    data = {
        "csrf_token": csrf(client, "/signup"),
        "name": "Yangi Kafe",
        "slug": "yangi-kafe",
        "username": "yangikafe",
        "password": "parol12345",
        "phone": "+998901112233",
        "email": "",
    }
    data.update(overrides)
    return client.post("/signup", data=data)


# --- ro'yxatdan o'tish ---

def test_signup_creates_restaurant_admin_and_trial(client, db):
    response = signup(client)
    assert response.status_code == 200  # /admin ga ergashadi

    restaurant = db.query(Restaurant).filter_by(slug="yangi-kafe").one()
    assert restaurant.subscription_status is SubscriptionStatus.trial
    assert restaurant.trial_ends_at is not None
    assert trial_days_left(restaurant) == TRIAL_DAYS

    user = db.query(User).filter_by(username="yangikafe").one()
    assert user.restaurant_id == restaurant.id


def test_signup_logs_the_owner_straight_in(client, db):
    signup(client)
    # Qayta login qilmasdan admin panel ochilishi kerak
    assert "Yangi Kafe" in client.get("/admin").text


def test_signup_rejects_a_taken_username(client, db, tenant_a):
    response = signup(client, username="osh")
    assert response.status_code == 400
    assert "band" in html.unescape(response.text)
    assert db.query(Restaurant).filter_by(slug="yangi-kafe").first() is None


def test_signup_rejects_a_taken_slug(client, db, tenant_a):
    restaurant, _ = tenant_a
    response = signup(client, slug=restaurant.slug, username="boshqa")
    assert response.status_code == 400
    assert "band" in html.unescape(response.text)


def test_signup_rejects_reserved_slugs(client, db):
    response = signup(client, slug="admin")
    assert response.status_code == 400
    assert "band so'z" in html.unescape(response.text)


def test_signup_keeps_the_form_filled_after_an_error(client, db, tenant_a):
    """Xatodan keyin hamma maydonni qaytadan yozdirish — eng tez ketkazadigan narsa."""
    response = signup(client, username="osh")
    assert "Yangi Kafe" in response.text
    assert "+998901112233" in response.text


def test_signup_rejects_a_short_password(client, db):
    response = signup(client, password="qisqa")
    assert response.status_code == 400
    assert db.query(Restaurant).count() == 0


# --- tarif cheklovlari ---

@pytest.fixture
def free_tenant(db, tenant_a):
    restaurant, _ = tenant_a
    restaurant.plan = Plan.free
    restaurant.subscription_status = SubscriptionStatus.active
    db.commit()
    return restaurant


def test_free_plan_stops_at_the_category_limit(client, db, free_tenant):
    login(client, "osh", "adminpass123")
    limit = LIMITS[Plan.free].max_categories

    for index in range(limit):
        client.post(
            "/admin/categories",
            data={"csrf_token": csrf(client, "/admin/categories"), "name_uz": f"Bo'lim {index}"},
        )
    assert db.query(Category).count() == limit

    blocked = client.post(
        "/admin/categories",
        data={"csrf_token": csrf(client, "/admin/categories"), "name_uz": "Ortiqcha"},
    )
    assert blocked.status_code == 400
    assert db.query(Category).count() == limit


def test_free_plan_stops_at_the_item_limit(client, db, free_tenant):
    category = Category(restaurant_id=free_tenant.id, name={"uz": "Bo'lim"})
    db.add(category)
    db.commit()

    limit = LIMITS[Plan.free].max_items
    db.add_all(
        MenuItem(
            restaurant_id=free_tenant.id,
            category_id=category.id,
            name={"uz": f"Taom {i}"},
            price=1000,
        )
        for i in range(limit)
    )
    db.commit()

    login(client, "osh", "adminpass123")
    blocked = client.post(
        "/admin/items",
        data={
            "csrf_token": csrf(client, "/admin/items"),
            "category_id": category.id,
            "name_uz": "Ortiqcha taom",
            "price": 5000,
        },
    )
    assert blocked.status_code == 400
    assert db.query(MenuItem).count() == limit


def test_free_plan_menu_shows_only_uzbek(client, db, free_tenant):
    category = Category(restaurant_id=free_tenant.id, name={"uz": "Issiq", "ru": "Горячее"})
    db.add(category)
    db.flush()
    db.add(
        MenuItem(
            restaurant_id=free_tenant.id,
            category_id=category.id,
            name={"uz": "Osh", "ru": "Плов"},
            price=38000,
        )
    )
    db.commit()

    body = client.get(f"/r/{free_tenant.slug}?lang=ru").text
    assert "Плов" not in body  # tarjima bazada bor, lekin tarif ko'rsatmaydi
    assert "Osh" in body


def test_paid_plan_shows_every_language(client, db, tenant_a):
    restaurant, _ = tenant_a
    restaurant.plan = Plan.full
    restaurant.subscription_status = SubscriptionStatus.active
    category = Category(restaurant_id=restaurant.id, name={"uz": "Issiq", "ru": "Горячее"})
    db.add(category)
    db.flush()
    db.add(
        MenuItem(
            restaurant_id=restaurant.id,
            category_id=category.id,
            name={"uz": "Osh", "ru": "Плов"},
            price=38000,
        )
    )
    db.commit()

    assert "Плов" in client.get(f"/r/{restaurant.slug}?lang=ru").text


# --- sinov muddati ---

def test_trial_gives_full_features(db, tenant_a):
    restaurant, _ = tenant_a
    restaurant.subscription_status = SubscriptionStatus.trial
    restaurant.trial_ends_at = utcnow_naive() + timedelta(days=3)
    assert effective_plan(restaurant) is Plan.full
    assert limits_for(restaurant).max_items == LIMITS[Plan.full].max_items


def test_expired_trial_closes_the_menu(client, db, tenant_a):
    """Sinov tugagach QR kod ishlamay qolishi kerak — bepul rejim cho'zilmaydi."""
    restaurant, _ = tenant_a
    restaurant.trial_ends_at = utcnow_naive() - timedelta(minutes=1)
    db.commit()

    response = client.get(f"/r/{restaurant.slug}")
    assert response.status_code == 503
    assert "Menyu vaqtincha yopiq" in response.text
    # Mijozga tarif haqida gapirilmaydi — u aybdor emas
    assert "tarif" not in response.text.lower()


def test_the_menu_closes_even_if_the_owner_never_logs_in(client, db, tenant_a):
    """Eng muhim tarmoq: holat bazada emas, sanadan hisoblanadi.

    `refresh_status()` faqat panelga kirilganda ishlaydi. Agar menyu shu
    saqlangan holatga qarasa, egasi panelga kirmay qo'yish bilan sinovni
    cheksiz cho'zib yuborardi.
    """
    restaurant, _ = tenant_a
    restaurant.trial_ends_at = utcnow_naive() - timedelta(days=30)
    db.commit()

    # Bazadagi holat hamon "trial" — hech kim yangilamagan
    assert restaurant.subscription_status is SubscriptionStatus.trial
    assert client.get(f"/r/{restaurant.slug}").status_code == 503


def test_the_owner_still_reaches_the_panel_after_expiry(client, db, tenant_a):
    """Menyu yopiladi, hisob esa yopilmaydi — ma'lumot ham joyida qoladi."""
    restaurant, _ = tenant_a
    restaurant.trial_ends_at = utcnow_naive() - timedelta(minutes=1)
    db.commit()

    login(client, "osh", "adminpass123")
    panel = client.get("/admin")
    assert panel.status_code == 200
    assert "Menyungiz yopiq" in html.unescape(panel.text)

    # Ogohlantirish qobiqda — ya'ni bosh sahifadagina emas, hamma yerda
    assert "Menyungiz yopiq" in html.unescape(client.get("/admin/items").text)

    db.refresh(restaurant)
    assert restaurant.subscription_status is SubscriptionStatus.expired
    assert effective_plan(restaurant) is Plan.free


def test_paying_reopens_the_menu(client, db, tenant_a):
    """To'lovdan keyin menyu o'sha zahoti qayta ochilishi kerak."""
    restaurant, _ = tenant_a
    restaurant.trial_ends_at = utcnow_naive() - timedelta(days=1)
    db.commit()
    assert client.get(f"/r/{restaurant.slug}").status_code == 503

    restaurant.plan = Plan.full
    restaurant.subscription_status = SubscriptionStatus.active
    restaurant.paid_until = utcnow_naive() + timedelta(days=365)
    db.commit()
    assert client.get(f"/r/{restaurant.slug}").status_code == 200


def test_expired_paid_subscription_also_drops_to_free(db, tenant_a):
    restaurant, _ = tenant_a
    restaurant.plan = Plan.full
    restaurant.subscription_status = SubscriptionStatus.active
    restaurant.paid_until = utcnow_naive() - timedelta(days=1)
    db.commit()

    from app.plans import refresh_status

    assert refresh_status(restaurant) is True
    assert effective_plan(restaurant) is Plan.free


# --- superadmin tarifni boshqaradi ---

def test_superadmin_can_grant_a_paid_plan(client, db, tenant_a, superadmin):
    restaurant, _ = tenant_a
    login(client, "root", "rootpass123")

    client.post(
        f"/superadmin/restaurants/{restaurant.id}/plan",
        data={"csrf_token": csrf(client, "/superadmin"), "plan": "full", "years": 2},
    )
    db.refresh(restaurant)
    assert restaurant.plan is Plan.full
    assert restaurant.subscription_status is SubscriptionStatus.active
    assert restaurant.paid_until > utcnow_naive() + timedelta(days=720)


# --- landing ---

def test_landing_page_lists_every_plan(client):
    body = html.unescape(client.get("/").text)
    for limits in LIMITS.values():
        assert limits.name in body
    assert "499 000" in body  # yillik narx ko'rinishi
    assert "/signup" in body


def test_landing_shows_the_configured_demo(client, db, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "demo_slug", "namuna")
    make_restaurant(db, slug="namuna", username="namunaadmin")
    assert "/r/namuna" in client.get("/").text


def test_landing_never_offers_someone_elses_menu_as_the_demo(client, db, tenant_a):
    """Namuna sozlamada ko'rsatilgan menyu bo'lishi kerak.

    Avval eng eski restoran olinardi — ya'ni haqiqiy mijozning menyusi
    saytda "namuna" bo'lib turardi. Namuna bazada bo'lmasa havola umuman
    chiqmasligi kerak.
    """
    restaurant, _ = tenant_a
    body = client.get("/").text
    assert f"/r/{restaurant.slug}" not in body
    assert "Namunani ko'rish" not in html.unescape(body)


# --- yangi restoran uchun yo'l-yo'riq ---

def test_a_fresh_restaurant_sees_the_setup_checklist(client, db):
    signup(client)
    body = html.unescape(client.get("/admin").text)
    assert "Menyuni ishga tushiramiz" in body
    assert "0 / 3 bajarildi" in body


def test_the_checklist_ticks_off_each_finished_step(client, db, tenant_a):
    restaurant, _ = tenant_a
    login(client, "osh", "adminpass123")

    client.post(
        "/admin/categories",
        data={"csrf_token": csrf(client, "/admin/categories"), "name_uz": "Ichimliklar"},
    )
    assert "1 / 3 bajarildi" in html.unescape(client.get("/admin").text)


def test_the_checklist_disappears_once_everything_is_done(client, db, tenant_a):
    """Ro'yxat abadiy turib qolmasligi kerak — ish tugagach yo'qolsin."""
    restaurant, _ = tenant_a
    category = Category(restaurant_id=restaurant.id, name={"uz": "Ichimliklar"})
    db.add(category)
    db.flush()
    db.add(
        MenuItem(
            restaurant_id=restaurant.id,
            category_id=category.id,
            name={"uz": "Kapuchino"},
            price=25000,
        )
    )
    restaurant.working_hours = "08:00 – 22:00"
    restaurant.phone = "+998901112233"
    db.commit()

    login(client, "osh", "adminpass123")
    assert "Menyuni ishga tushiramiz" not in html.unescape(client.get("/admin").text)


def test_the_checklist_comes_back_if_the_menu_is_emptied(client, db, tenant_a):
    """Holat alohida ustunda emas — ma'lumotdan hisoblanadi, ya'ni haqiqatga ergashadi."""
    restaurant, _ = tenant_a
    restaurant.working_hours = "08:00 – 22:00"
    restaurant.phone = "+998901112233"
    db.commit()

    login(client, "osh", "adminpass123")
    body = html.unescape(client.get("/admin").text)
    assert "1 / 3 bajarildi" in body


def test_the_warning_banner_follows_you_across_the_panel(client, db, tenant_a):
    """Ogohlantirish bosh sahifadagina bo'lsa, taom tahrirlab yurgan odam
    menyusi o'chishidan bexabar qolardi."""
    restaurant, _ = tenant_a
    restaurant.trial_ends_at = utcnow_naive() + timedelta(days=2)
    db.commit()

    login(client, "osh", "adminpass123")
    for path in ("/admin", "/admin/items", "/admin/qr", "/admin/settings"):
        assert "2 kun qoldi" in html.unescape(client.get(path).text), path


def test_no_banner_while_there_is_still_time(client, db, tenant_a):
    """Har kuni ko'rinadigan ogohlantirish tez ko'zga ko'rinmas bo'lib qoladi."""
    restaurant, _ = tenant_a
    restaurant.trial_ends_at = utcnow_naive() + timedelta(days=6)
    db.commit()

    login(client, "osh", "adminpass123")
    assert "banner-fixed" not in client.get("/admin/items").text


def test_superadmin_sees_who_expires_this_week(client, db, superadmin, tenant_a, tenant_b):
    """Telegram bot yo'q — bog'lanishni o'zingiz qilasiz, ro'yxat kimligini aytadi."""
    soon, _ = tenant_a
    soon.trial_ends_at = utcnow_naive() + timedelta(days=2)
    later, _ = tenant_b
    later.trial_ends_at = utcnow_naive() + timedelta(days=40)
    db.commit()

    login(client, "root", "rootpass123")
    body = client.get("/superadmin?status_filter=tugayapti").text
    assert soon.name in body
    assert later.name not in body


def test_interface_language_is_separate_from_menu_language(client, db, free_tenant):
    """Bepul tarif menyu MAZMUNINI cheklaydi, interfeysni emas.

    Ikkisi bir o'zgaruvchida bo'lsa, interfeys tili menyu cheklovini bosib
    qo'yardi va bepul restoranning menyusi ruscha chiqib ketardi.
    """
    category = Category(restaurant_id=free_tenant.id, name={"uz": "Issiq", "ru": "Горячее"})
    db.add(category)
    db.flush()
    db.add(MenuItem(
        restaurant_id=free_tenant.id, category_id=category.id,
        name={"uz": "Osh", "ru": "Плов"}, price=38000,
    ))
    db.commit()

    body = client.get(f"/r/{free_tenant.slug}?lang=ru").text
    assert "Плов" not in body   # mazmun cheklangan
    assert "Osh" in body
