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
    assert "Tarkibi" in page
    # Vergulli ro'yxat alohida chiplarga bo'linadi — bir qarashda o'qiladi
    for part in ("Guruch", "Sabzi", "Zira"):
        assert f"<li>{part}</li>" in page

    partial = client.get(f"/r/{menu.slug}/item/{item.id}?partial=1&lang=ru").text
    assert "Состав" in partial
    assert "<li>Рис</li>" in partial


def test_ingredients_written_as_a_sentence_stay_a_paragraph(client, db, menu):
    """Har bir vergulni chipga aylantirib bo'lmaydi.

    Restoran tarkibni gap qilib ham yozishi mumkin. Uzun bo'laklar chip
    ichida xunuk cho'zilib ketardi — shuning uchun bunda oddiy matn qoladi.
    """
    item = menu.categories[0].items[0]
    item.ingredients = {"uz": "Guruch va sabzi, sekin olovda uzoq qaynatilgan qo'y go'shti"}
    db.commit()

    page = client.get(f"/r/{menu.slug}/item/{item.id}").text
    assert "sekin olovda uzoq qaynatilgan" in page
    assert 'class="tags' not in page


def test_a_closed_menu_hides_the_dishes_too(client, db, menu):
    """Menyu yopiq bo'lsa taom sahifasi ham ochilmasligi kerak.

    Aks holda bitta taomga havolasi bor odam yopiq menyuni chetlab o'tardi.
    """
    from datetime import timedelta

    from app.models import utcnow_naive

    item = menu.categories[0].items[0]
    menu.trial_ends_at = utcnow_naive() - timedelta(days=1)
    db.commit()

    assert client.get(f"/r/{menu.slug}/item/{item.id}").status_code == 503
    assert client.get(f"/r/{menu.slug}/item/{item.id}?partial=1").status_code == 503


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


# --- inline QR (bosh sahifadagi ko'rgazma uchun) ---

def test_inline_qr_keeps_the_code_pattern_untouched():
    """SVG tozalanganda kod naqshi o'zgarmasligi kerak.

    `svg_markup` kutubxona chiqargan fayldan XML e'loni va qat'iy `mm`
    o'lchamini olib tashlaydi. Agar tozalash `path` ma'lumotiga tegib
    ketsa, QR skanerlanmay qoladi va buni ko'z bilan sezib bo'lmaydi.
    """
    from app.services import qr

    raw = qr.svg_bytes("namuna", 6).decode("utf-8")
    cleaned = qr.svg_markup("namuna", 6)

    start = raw.index('<path')
    assert raw[start:] == cleaned[cleaned.index('<path'):]


def test_inline_qr_is_ready_for_html():
    from app.services import qr

    markup = qr.svg_markup("namuna")
    assert not markup.lstrip().startswith("<?xml")   # HTML ichida matn bo'lib qolardi
    assert 'mm"' not in markup                        # o'lchamni CSS boshqarsin
    assert "viewBox" in markup                        # lekin nisbati saqlansin


def test_each_restaurant_gets_its_own_qr():
    """Bezak rasm emas — har bir menyu uchun boshqacha kod."""
    from app.services import qr

    assert qr.svg_markup("birinchi") != qr.svg_markup("ikkinchi")


# --- tarjima katalogi ---

def test_every_ui_string_exists_in_all_three_languages():
    """Yetishmagan tarjima sahifada o'zbekcha bo'lib chiqadi va sezilmay qoladi.

    Katalog kalit-birinchi tuzilgan (uch tili yonma-yon) aynan shuning uchun —
    bu test esa unutilganini darrov aytadi.
    """
    from app.i18n import LANGUAGES, UI

    gaps = {
        key: [lang for lang in LANGUAGES if not entry.get(lang)]
        for key, entry in UI.items()
    }
    assert not {k: v for k, v in gaps.items() if v}


def test_an_unknown_key_returns_itself_instead_of_breaking():
    from app.i18n import t

    assert t("bunday_kalit_yoq", "uz") == "bunday_kalit_yoq"
