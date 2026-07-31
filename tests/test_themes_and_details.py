import html

import pytest

from app import themes
from app.models import Category, MenuItem, Plan, SubscriptionStatus

from tests.conftest import csrf, login


@pytest.fixture
def cafe(db, tenant_a):
    restaurant, _ = tenant_a
    restaurant.plan = Plan.full
    restaurant.subscription_status = SubscriptionStatus.active
    category = Category(restaurant_id=restaurant.id, name={"uz": "Issiq taomlar"})
    db.add(category)
    db.flush()
    item = MenuItem(
        restaurant_id=restaurant.id,
        category_id=category.id,
        name={"uz": "Osh"},
        price=38000,
        prep_minutes=25,
    )
    db.add(item)
    db.commit()
    return restaurant, item


# --- uslublar ---

def test_each_theme_sends_its_own_palette(client, db, cafe):
    """Uslublar bir-biridan rang, fon, shrift va burchak bilan farq qilishi kerak."""
    restaurant, _ = cafe
    palettes = set()

    for key, preset in themes.THEMES.items():
        restaurant.theme = key
        restaurant.theme_color = preset.accent
        db.commit()

        body = client.get(f"/r/{restaurant.slug}").text
        assert f'data-theme="{key}"' in body
        assert f"--accent:{preset.accent}" in body
        for name in ("--page", "--ink", "--font-head", "--r-lg"):
            assert f"{name}:{preset.variables[name]}" in body

        palettes.add(
            (preset.variables["--page"], preset.variables["--font-head"],
             preset.variables["--r-lg"])
        )

    assert len(palettes) == len(themes.THEMES), "har uslub o'ziga xos bo'lishi kerak"


def test_theme_fonts_are_not_html_escaped(client, db, cafe):
    """Qo'shtirnoq &#34; ga aylansa CSS buziladi va shrift umuman qo'llanmaydi."""
    restaurant, _ = cafe
    restaurant.theme = "klassik"
    db.commit()

    body = client.get(f"/r/{restaurant.slug}").text
    assert '"Iowan Old Style"' in body
    assert "&#34;" not in body.split("</head>")[0]


def test_a_broken_accent_falls_back_instead_of_injecting_css(client, db, cafe):
    """Rang <style> ichiga tushadi — u yerdan chiqib ketishga yo'l qo'ymaymiz."""
    restaurant, _ = cafe
    restaurant.theme_color = "red; } </style><script>alert(1)</script>"
    db.commit()

    body = client.get(f"/r/{restaurant.slug}").text
    assert "<script>alert(1)</script>" not in body
    assert f"--accent:{themes.THEMES[restaurant.theme].accent}" in body


def test_unknown_theme_falls_back_to_default(db, cafe):
    restaurant, _ = cafe
    restaurant.theme = "yoq-uslub"
    assert themes.get(restaurant.theme).key == themes.DEFAULT_THEME


def test_owner_can_switch_theme_from_settings(client, db, cafe):
    restaurant, _ = cafe
    login(client, "osh", "adminpass123")

    client.post(
        "/admin/settings",
        data={
            "csrf_token": csrf(client, "/admin/settings"),
            "name": restaurant.name,
            "theme": "issiq",
            "theme_color": "#c2410c",
            "currency": "so'm",
        },
    )
    db.refresh(restaurant)
    assert restaurant.theme == "issiq"


def test_settings_ignores_an_invalid_theme(client, db, cafe):
    restaurant, _ = cafe
    before = restaurant.theme
    login(client, "osh", "adminpass123")

    client.post(
        "/admin/settings",
        data={
            "csrf_token": csrf(client, "/admin/settings"),
            "name": restaurant.name,
            "theme": "../../etc/passwd",
            "currency": "so'm",
        },
    )
    db.refresh(restaurant)
    assert restaurant.theme == before


# --- aloqa ma'lumotlari hero ichida ---

def test_contact_details_sit_in_the_hero_not_the_sheet(client, db, cafe):
    restaurant, _ = cafe
    restaurant.working_hours = "09:00 – 23:00"
    restaurant.phone = "+998901234567"
    db.commit()

    body = client.get(f"/r/{restaurant.slug}").text
    hero = body.split('<div class="sheet">')[0]
    assert "09:00 – 23:00" in hero
    assert "+998901234567" in hero


# --- tayyorlanish vaqti ---

def test_prep_time_shows_on_card_and_detail(client, db, cafe):
    restaurant, item = cafe

    menu = html.unescape(client.get(f"/r/{restaurant.slug}").text)
    assert "25 daq" in menu

    detail = html.unescape(client.get(f"/r/{restaurant.slug}/item/{item.id}").text)
    assert "25 daq" in detail


def test_prep_time_is_hidden_when_not_set(client, db, cafe):
    restaurant, item = cafe
    item.prep_minutes = 0
    db.commit()

    assert "daq" not in client.get(f"/r/{restaurant.slug}").text


def test_prep_time_round_trips_through_the_form(client, db, cafe):
    restaurant, item = cafe
    login(client, "osh", "adminpass123")

    client.post(
        f"/admin/items/{item.id}",
        data={
            "csrf_token": csrf(client, f"/admin/items/{item.id}/edit"),
            "category_id": item.category_id,
            "name_uz": "Osh",
            "price": 38000,
            "prep_minutes": 40,
        },
    )
    db.refresh(item)
    assert item.prep_minutes == 40
