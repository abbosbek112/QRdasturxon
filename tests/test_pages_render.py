import pytest

from app.models import Category, MenuItem

from tests.conftest import login, make_restaurant


@pytest.fixture
def item(db, tenant_a):
    restaurant, _ = tenant_a
    category = Category(restaurant_id=restaurant.id, name={"uz": "Taomlar"})
    db.add(category)
    db.flush()
    menu_item = MenuItem(
        restaurant_id=restaurant.id, category_id=category.id, name={"uz": "Osh"}, price=38000
    )
    db.add(menu_item)
    db.commit()
    return menu_item


@pytest.mark.parametrize(
    "path",
    [
        "/admin", "/admin/settings", "/admin/categories", "/admin/items",
        "/admin/items/new", "/admin/qr", "/admin/stats",
    ],
)
def test_admin_pages_render(client, tenant_a, item, path):
    login(client, "osh", "adminpass123")
    assert client.get(path).status_code == 200


def test_item_edit_page_renders(client, tenant_a, item):
    login(client, "osh", "adminpass123")
    response = client.get(f"/admin/items/{item.id}/edit")
    assert response.status_code == 200
    assert "Osh" in response.text


@pytest.mark.parametrize(
    "path", ["/superadmin", "/superadmin/users", "/superadmin/restaurants/new"]
)
def test_superadmin_pages_render(client, superadmin, path):
    login(client, "root", "rootpass123")
    assert client.get(path).status_code == 200


def test_superadmin_restaurant_edit_renders(client, superadmin, tenant_a):
    restaurant, _ = tenant_a
    login(client, "root", "rootpass123")
    response = client.get(f"/superadmin/restaurants/{restaurant.id}/edit")
    assert response.status_code == 200
    assert restaurant.slug in response.text


def test_public_pages_render(client, item, tenant_a):
    restaurant, _ = tenant_a
    assert client.get("/").status_code == 200
    assert client.get(f"/r/{restaurant.slug}").status_code == 200
    assert client.get(f"/r/{restaurant.slug}/item/{item.id}").status_code == 200


# --- superadmin: ro'yxat va bitta restoran sahifasi ---

def test_superadmin_detail_page_renders(client, superadmin, tenant_a):
    restaurant, _ = tenant_a
    login(client, "root", "rootpass123")

    response = client.get(f"/superadmin/restaurants/{restaurant.id}")
    assert response.status_code == 200
    assert restaurant.name in response.text
    assert "Obuna" in response.text


def test_superadmin_detail_404s_for_a_missing_restaurant(client, superadmin):
    login(client, "root", "rootpass123")
    assert client.get("/superadmin/restaurants/9999").status_code == 404


def test_new_restaurant_form_is_not_swallowed_by_the_detail_route(client, superadmin):
    """/restaurants/new marshruti /restaurants/{id} dan OLDIN turishi kerak.

    Aks holda "new" so'zi id deb o'qilib, forma o'rniga 422 qaytadi.
    """
    login(client, "root", "rootpass123")
    assert client.get("/superadmin/restaurants/new").status_code == 200


def test_superadmin_search_filters_the_list(client, superadmin, tenant_a, tenant_b):
    first, _ = tenant_a
    second, _ = tenant_b
    login(client, "root", "rootpass123")

    body = client.get(f"/superadmin?q={first.slug}").text
    assert first.name in body
    assert second.name not in body


def test_superadmin_status_filter_narrows_the_list(client, db, superadmin, tenant_a, tenant_b):
    from datetime import timedelta

    from app.models import utcnow_naive

    expired, _ = tenant_a
    expired.trial_ends_at = utcnow_naive() - timedelta(days=1)
    db.commit()
    login(client, "root", "rootpass123")

    body = client.get("/superadmin?status_filter=tugagan").text
    assert expired.name in body
    assert tenant_b[0].name not in body


def test_a_restaurant_admin_cannot_open_the_superadmin_panel(client, tenant_a):
    login(client, "osh", "adminpass123")
    restaurant, _ = tenant_a
    assert client.get("/superadmin").status_code in (403, 404)
    assert client.get(f"/superadmin/restaurants/{restaurant.id}").status_code in (403, 404)


# --- bosh sahifadagi ko'rgazma ---

def test_the_showcase_renders_every_theme(client, superadmin):
    """Uslub kartalari THEMES bo'yicha aylanadi — yangisi qo'shilsa o'zi chiqadi."""
    from app.themes import THEMES

    body = client.get("/").text
    for key in THEMES:
        assert f'data-theme="{key}"' in body


def test_theme_palettes_go_into_a_style_block_not_an_attribute(client):
    """Uslub shriftlari ichida qo'shtirnoq bor ("Iowan Old Style").

    Agar palitra style="..." atributiga yozilsa, atribut o'sha qo'shtirnoqda
    uzilib qoladi va undan keyingi o'zgaruvchilar — burchak radiusi, shrift —
    umuman qo'llanmaydi.
    """
    body = client.get("/").text
    assert '.show-theme[data-theme="klassik"]' in body
    assert 'Iowan Old Style' in body
    # Palitra hech qachon inline atributda bo'lmasin
    assert 'style="--page' not in body


def test_the_landing_embeds_a_real_qr_for_the_demo(client, db, monkeypatch):
    from app.config import settings
    from app.services import qr

    monkeypatch.setattr(settings, "demo_slug", "namuna")
    make_restaurant(db, slug="namuna", username="namunaadmin")

    body = client.get("/").text
    assert qr.svg_markup("namuna") in body


def test_the_landing_has_no_qr_without_a_demo(client):
    """Namuna bo'lmasa QR ham bo'lmasin — ishlamaydigan kodni ko'rsatmaymiz."""
    body = client.get("/").text
    assert "show-qr-code" not in body
    assert client.get("/").status_code == 200


# --- havola kartochkasi (Telegram/Facebook) ---

def test_the_landing_ships_a_share_card(client):
    body = client.get("/").text
    assert '<meta property="og:image" content="http://testserver/static/img/og.jpg' in body
    assert '<meta name="twitter:card" content="summary_large_image">' in body
    assert '<meta name="description"' in body


def test_a_menu_link_shows_the_restaurants_own_name_and_cover(client, db, tenant_a):
    """Restoran menyusini o'z mijozlariga havola bilan tarqatadi.

    O'sha yerda QRdasturxon emas, restoranning o'zi ko'rinishi kerak.
    """
    restaurant, _ = tenant_a
    restaurant.description = {"uz": "Uy taomlari va qahva"}
    restaurant.cover_image = "1/muqova.webp"
    db.commit()

    body = client.get(f"/r/{restaurant.slug}").text
    assert f'<meta property="og:title" content="{restaurant.name}">' in body
    assert '<meta property="og:image" content="http://testserver/media/1/muqova.webp">' in body
    assert "Uy taomlari va qahva" in body


def test_a_menu_without_a_cover_falls_back_to_the_product_card(client, tenant_a):
    restaurant, _ = tenant_a
    body = client.get(f"/r/{restaurant.slug}").text
    assert "/static/img/og.jpg" in body


def test_a_dish_link_shows_that_dish(client, db, tenant_a, item):
    restaurant, _ = tenant_a
    item.image = "1/osh.webp"
    db.commit()

    body = client.get(f"/r/{restaurant.slug}/item/{item.id}").text
    assert 'content="Osh — ' in body
    assert '/media/1/osh.webp' in body


def test_share_urls_are_absolute(client):
    """Nisbiy yo'lni Telegram ham, Facebook ham tanimaydi."""
    body = client.get("/").text
    assert '<meta property="og:url" content="http://testserver/">' in body
