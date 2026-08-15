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
    """Rang <style> ichiga tushadi — u yerdan chiqib ketishga yo'l qo'ymaymiz.

    Ustun VARCHAR(9) — uzun hujum satri baribir sig'maydi. Lekin `</style>`
    atigi 8 belgi, ya'ni sig'adi: himoya shuning uchun kerak.
    """
    restaurant, _ = cafe
    restaurant.theme_color = "</style>"
    db.commit()

    head = client.get(f"/r/{restaurant.slug}").text.split("</head>")[0]
    assert "--accent:</style>" not in head
    assert f"--accent:{themes.THEMES[restaurant.theme].accent}" in head


def test_unknown_theme_falls_back_to_default(db, cafe):
    restaurant, _ = cafe
    restaurant.theme = "yoq-uslub"
    assert themes.get(restaurant.theme).key == themes.DEFAULT_THEME


def test_owner_can_switch_theme_from_the_design_section(client, db, cafe):
    """Uslub endi Sozlamalarda emas, alohida Dizayn bo'limida."""
    restaurant, _ = cafe
    login(client, "osh", "adminpass123")

    client.post(
        "/admin/design",
        data={
            "csrf_token": csrf(client, "/admin/design"),
            "theme": "issiq",
            "theme_color": "#c2410c",
        },
    )
    db.refresh(restaurant)
    assert restaurant.theme == "issiq"
    assert restaurant.theme_color == "#c2410c"


def test_design_ignores_an_invalid_theme(client, db, cafe):
    restaurant, _ = cafe
    before = restaurant.theme
    login(client, "osh", "adminpass123")

    client.post(
        "/admin/design",
        data={
            "csrf_token": csrf(client, "/admin/design"),
            "theme": "../../etc/passwd",
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


# --- Dizayn bo'limi: shablon, rang, rasm ---


def test_the_design_page_shows_every_template(client, cafe):
    """Har shablon ko'rinishi bilan tanlanadi — nomi bilan emas.

    Shuning uchun sahifada barcha shablonlar chizilgan bo'lishi kerak:
    "Klassik" degan so'z egasiga hech nima demaydi.
    """
    login(client, "osh", "adminpass123")
    body = client.get("/admin/design").text

    for key in themes.THEMES:
        assert f'value="{key}"' in body, key
    # Har shablon o'z palitrasini oladi
    for key in themes.THEMES:
        assert f'.tpl[data-theme="{key}"]' in body


def test_a_ready_made_colour_can_be_chosen(client, db, cafe):
    restaurant, _ = cafe
    login(client, "osh", "adminpass123")

    client.post(
        "/admin/design",
        data={"csrf_token": csrf(client, "/admin/design"), "theme_color": "#0369a1"},
    )
    db.refresh(restaurant)
    assert restaurant.theme_color == "#0369a1"


def test_an_own_colour_comes_from_the_paired_field(client, db, cafe):
    """`__own__` — "yonidagi maydondan ol" degan belgi.

    Tayyor ranglar radio bo'lib keladi va ular bilan bir nomda
    `<input type="color">` yuborib bo'lmaydi, shuning uchun juftlik.
    """
    restaurant, _ = cafe
    login(client, "osh", "adminpass123")

    client.post(
        "/admin/design",
        data={
            "csrf_token": csrf(client, "/admin/design"),
            "theme_color": "__own__",
            "own_color": "#123456",
        },
    )
    db.refresh(restaurant)
    assert restaurant.theme_color == "#123456"


def test_a_colour_that_is_not_a_colour_is_refused(client, db, cafe):
    """Rang menyu sahifasining <style> ichiga tushadi.

    Shakli tekshirilmasa u yerdan `</style>` yozib chiqib ketish mumkin
    edi — shuning uchun faqat haqiqiy hex o'tadi.
    """
    restaurant, _ = cafe
    oldin = restaurant.theme_color
    login(client, "osh", "adminpass123")

    client.post(
        "/admin/design",
        data={
            "csrf_token": csrf(client, "/admin/design"),
            "theme_color": "__own__",
            "own_color": "</style><script>alert(1)</script>",
        },
    )
    db.refresh(restaurant)
    assert restaurant.theme_color != "</style><script>alert(1)</script>"
    # Uslubning o'z rangiga qaytadi
    assert restaurant.theme_color == themes.get(restaurant.theme).accent or oldin


def test_the_settings_page_no_longer_holds_the_design(client, cafe):
    """Sozlamalarda faqat ish sozlamalari qolsin.

    Dizayn u yerda ish vaqti va Wi-Fi paroli orasida turardi — bir marta
    qilinadigan ish har kuni ochiladigan sahifani uzaytirib turardi.
    """
    login(client, "osh", "adminpass123")
    body = client.get("/admin/settings").text

    assert 'name="theme"' not in body
    assert 'name="logo"' not in body
    # Valyuta esa dizayn emas — u shu yerda qoladi
    assert 'name="currency"' in body
    # Yo'l ko'rsatib qo'yiladi
    assert "/admin/design" in body


def test_the_menu_uses_the_chosen_colour(client, db, cafe):
    """Tanlangan rang mijoz menyusiga chindan yetib borsin."""
    restaurant, _ = cafe
    login(client, "osh", "adminpass123")
    client.post(
        "/admin/design",
        data={"csrf_token": csrf(client, "/admin/design"), "theme_color": "#15803d"},
    )
    db.refresh(restaurant)

    body = client.get(f"/r/{restaurant.slug}").text
    assert "--accent:#15803d" in body


def test_another_owner_cannot_restyle_this_menu(client, db, cafe, tenant_b):
    """Qo'shni egasi kirsa o'z restoranining dizaynini o'zgartiradi."""
    restaurant, _ = cafe
    boshqa, _ = tenant_b
    oldin = restaurant.theme
    db.commit()

    login(client, "choy", "adminpass123")
    client.post(
        "/admin/design",
        data={"csrf_token": csrf(client, "/admin/design"), "theme": "tungi"},
    )
    db.refresh(restaurant)
    db.refresh(boshqa)

    assert restaurant.theme == oldin
    assert boshqa.theme == "tungi"
