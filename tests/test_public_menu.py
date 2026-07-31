import html

import pytest

from app.i18n import tr
from app.models import Category, MenuItem

from tests.conftest import login


@pytest.fixture
def menu(db, tenant_a):
    restaurant, _ = tenant_a
    category = Category(
        restaurant_id=restaurant.id, name={"uz": "Issiq taomlar", "ru": "Горячее"}
    )
    db.add(category)
    db.flush()
    db.add_all(
        [
            MenuItem(
                restaurant_id=restaurant.id,
                category_id=category.id,
                name={"uz": "Osh", "ru": "Плов", "en": "Pilaf"},
                description={"uz": "Qo'y go'shti bilan"},
                price=35000,
            ),
            MenuItem(
                restaurant_id=restaurant.id,
                category_id=category.id,
                name={"uz": "Lag'mon"},
                price=30000,
                is_available=False,
            ),
        ]
    )
    db.commit()
    return restaurant


def test_menu_renders_in_uzbek(client, menu):
    body = client.get(f"/r/{menu.slug}").text
    assert "Osh" in body
    assert "Issiq taomlar" in body


def test_menu_translates_to_russian(client, menu):
    body = client.get(f"/r/{menu.slug}?lang=ru").text
    assert "Плов" in body
    assert "Горячее" in body


def test_missing_translation_falls_back_to_uzbek(client, menu):
    body = client.get(f"/r/{menu.slug}?lang=en").text
    assert "Pilaf" in body
    assert "Issiq taomlar" in body  # kategoriyaning inglizchasi yo'q


def test_language_choice_is_remembered_in_cookie(client, menu):
    client.get(f"/r/{menu.slug}?lang=ru")
    assert "Плов" in client.get(f"/r/{menu.slug}").text


def test_unavailable_items_are_hidden(client, menu):
    assert "Lag'mon" not in client.get(f"/r/{menu.slug}").text


def test_search_filters_items(client, menu):
    assert "Issiq taomlar" in client.get(f"/r/{menu.slug}?q=osh").text
    empty = client.get(f"/r/{menu.slug}?q=zzz").text
    assert "Issiq taomlar" not in empty
    assert "Hech narsa topilmadi" in empty


def test_inactive_restaurant_is_not_public(client, db, menu):
    menu.is_active = False
    db.commit()
    assert client.get(f"/r/{menu.slug}").status_code == 404


def test_unknown_slug_returns_404(client):
    assert client.get("/r/yoq-restoran").status_code == 404


def test_item_detail_page_is_a_full_document(client, menu):
    item = menu.categories[0].items[0]
    body = client.get(f"/r/{menu.slug}/item/{item.id}").text
    assert "<html" in body
    assert "Osh" in body


def test_item_partial_returns_fragment_only(client, menu):
    """Bottom sheet ichiga joylash uchun \\<html\\> qobig'isiz bo'lak kerak."""
    item = menu.categories[0].items[0]
    body = client.get(f"/r/{menu.slug}/item/{item.id}?partial=1").text
    assert "<html" not in body
    assert "<body" not in body
    assert "Osh" in body
    assert "Qo'y go'shti bilan" in html.unescape(body)


def test_item_partial_still_enforces_availability_and_tenancy(client, db, menu, tenant_b):
    hidden = menu.categories[0].items[1]  # is_available=False
    assert client.get(f"/r/{menu.slug}/item/{hidden.id}?partial=1").status_code == 404

    other, _ = tenant_b
    visible = menu.categories[0].items[0]
    assert client.get(f"/r/{other.slug}/item/{visible.id}?partial=1").status_code == 404


def test_ingredients_show_in_both_page_and_partial(client, db, menu):
    item = menu.categories[0].items[0]
    item.ingredients = {"uz": "Guruch, sabzi, zira", "ru": "Рис, морковь, зира"}
    db.commit()

    page = client.get(f"/r/{menu.slug}/item/{item.id}").text
    assert "Guruch, sabzi, zira" in page
    assert "Tarkibi" in page

    partial = client.get(f"/r/{menu.slug}/item/{item.id}?partial=1&lang=ru").text
    assert "Рис, морковь, зира" in partial
    assert "Состав" in partial


def test_menu_page_ships_the_sheet_markup(client, menu):
    """Karta havolasi JS'siz ham ishlashi kerak — sheet faqat qo'shimcha qatlam."""
    body = client.get(f"/r/{menu.slug}").text
    assert 'id="sheetPanel"' in body
    assert f'href="/r/{menu.slug}/item/' in body


def test_tr_falls_back_when_language_missing():
    assert tr({"uz": "Osh"}, "ru") == "Osh"
    assert tr({}, "uz") == ""
    assert tr(None, "en") == ""


def test_qr_endpoints_serve_downloads(client, tenant_a):
    login(client, "osh", "adminpass123")

    png = client.get("/admin/qr.png")
    assert png.status_code == 200
    assert png.content.startswith(b"\x89PNG")

    svg = client.get("/admin/qr.svg")
    assert svg.status_code == 200
    assert b"<svg" in svg.content
