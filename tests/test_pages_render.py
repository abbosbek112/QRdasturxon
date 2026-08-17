import re
import html

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



@pytest.fixture
def menu_with_items(db, tenant_a, item):
    restaurant, _ = tenant_a
    return restaurant


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
    assert '.carousel-slide[data-theme="klassik"]' in body
    assert 'Iowan Old Style' in body
    # Palitra hech qachon inline atributda bo'lmasin
    assert 'style="--page' not in body


def test_every_template_appears_in_the_carousel(client):
    """Shablon qo'shilsa karuselga o'zi tushsin.

    Ro'yxat qo'lda yozilgan bo'lsa, yangi shablon qo'shgan odam bosh
    sahifani yangilashni unitib qo'yardi va sahifa kam ko'rsatib turardi.
    """
    from app.themes import THEMES

    body = client.get("/").text
    for key in THEMES:
        assert f'data-theme="{key}"' in body, key
    # Har shablonga bittadan nuqta.
    #
    # `data-go` bo'yicha sanaladi, sinf nomi bo'yicha emas: konteyner
    # `carousel-dots` deb ataladi va oddiy sanoq uni ham qo'shib
    # yuborardi — test bir dona ortiq ko'rsatardi.
    assert len(re.findall(r'data-go="\d+"', body)) == len(THEMES)


def test_the_dark_template_card_sets_its_own_text_colour(client):
    """Qorong'i shablonda taom nomi ko'rinib tursin.

    `.dish-name` menyuda rang o'rnatmaydi — u meros oladi. Bosh sahifada
    meros QORA bo'lgani uchun qorong'i kartochkada qora fonda qora yozuv
    chiqib, taom nomi butunlay yo'qolgandi. Faqat "Tungi" da bilinardi,
    chunki qolgan shablonlarning foni och.
    """
    css = client.get("/static/css/style.css").text

    # Qoida bor va u rangni SHABLONNING o'z siyohidan oladi
    qoida = re.search(
        r"\.carousel-slide \.dish-name\s*\{([^}]*)\}", css
    )
    assert qoida, "`.carousel-slide .dish-name` qoidasi yo'q"
    assert "color: var(--ink)" in qoida.group(1)

    # Qorong'i shablon palitrasi sahifada bor — usiz qoida ish bermasdi
    body = client.get("/").text
    assert '.carousel-slide[data-theme="tungi"]' in body


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


# --- robots.txt va sitemap.xml ---

def test_robots_closes_the_panel_and_points_to_the_sitemap(client):
    body = client.get("/robots.txt").text
    for closed in ("/admin", "/superadmin", "/login", "/signup"):
        assert f"Disallow: {closed}" in body
    assert "Sitemap: http://testserver/sitemap.xml" in body


def test_sitemap_lists_working_menus(client, tenant_a):
    restaurant, _ = tenant_a
    body = client.get("/sitemap.xml").text
    assert "http://testserver/" in body
    assert f"http://testserver/r/{restaurant.slug}" in body


def test_sitemap_leaves_out_a_closed_menu(client, db, tenant_a):
    """Muddati tugagan menyu 503 qaytaradi — Google'ni buzuq manzilga
    yuborishning ma'nosi yo'q."""
    from datetime import timedelta

    from app.models import utcnow_naive

    restaurant, _ = tenant_a
    restaurant.trial_ends_at = utcnow_naive() - timedelta(days=1)
    db.commit()

    assert f"/r/{restaurant.slug}" not in client.get("/sitemap.xml").text


def test_login_tells_you_what_to_do_about_a_lost_password(client):
    """Parolni faqat tizim admini tiklaydi — odam nima qilishni bilsin."""
    body = html.unescape(client.get("/login").text)
    assert "Parolni unutdingizmi" in body
    assert "t.me/" in body


# --- ko'p tilli SEO ---

def test_pages_link_their_language_versions(client):
    """hreflang bo'lmasa Google uch tilni bir-biriga bog'lay olmaydi."""
    from app.i18n import LANGUAGES

    body = client.get("/").text
    for code in LANGUAGES:
        assert f'hreflang="{code}" href="http://testserver/?lang={code}"' in body
    assert 'rel="canonical"' in body
    assert 'hreflang="x-default"' in body


def test_the_landing_title_follows_the_language(client):
    assert "QR-меню для кафе" in client.get("/?lang=ru").text
    assert "QR menu for cafes" in client.get("/?lang=en").text


def test_a_menu_ships_structured_data_for_google(client, db, menu_with_items):
    """Bu bo'lmasa qidiruvda oddiy havola chiqadi, restoran ma'lumoti emas."""
    import json
    import re

    restaurant = menu_with_items
    body = client.get(f"/r/{restaurant.slug}").text
    found = re.search(r'<script type="application/ld\+json">(.*?)</script>', body, re.S)
    assert found, "JSON-LD topilmadi"

    data = json.loads(found.group(1))       # buzuq JSON bo'lsa shu yerda yiqiladi
    assert data["@type"] == "Restaurant"
    assert data["name"] == restaurant.name
    assert data["hasMenu"]["hasMenuSection"]


def test_structured_data_survives_a_quote_in_the_name(client, db, menu_with_items):
    """Restoran nomida qo'shtirnoq bo'lsa JSON buzilib, Google uni tashlab yuborardi."""
    import json
    import re

    restaurant = menu_with_items
    restaurant.name = 'Kafe "Bahor"'
    db.commit()

    body = client.get(f"/r/{restaurant.slug}").text
    found = re.search(r'<script type="application/ld\+json">(.*?)</script>', body, re.S)
    assert json.loads(found.group(1))["name"] == 'Kafe "Bahor"'


UZBEKCHA_NAMUNA = [
    "Ikki kishilik", "Guruch", "Choyxona oshidan", "Ko'k choy",
    "Qo'y go'shti bilan", "Issiq taomlar", "Qahva va uy",
]


@pytest.mark.parametrize("lang", ["ru", "en"])
def test_the_landing_demo_content_is_translated(client, lang):
    """Ko'rgazma mazmuni ham tarjima qilinsin.

    Bu matnlar mijozning ma'lumoti emas — biz yozgan namuna. Ular
    shablonga o'zbekcha qotirilgan edi va ruscha sahifada yarmi
    o'zbekcha chiqib turardi: rus tilida o'qiyotgan restoran egasi
    "Ikki kishilik" va "Guruch · Qo'y go'shti" degan yozuvlarni ko'rardi.
    """
    body = html.unescape(client.get(f"/?lang={lang}").text)

    qolgan = [matn for matn in UZBEKCHA_NAMUNA if matn in body]
    assert not qolgan, f"{lang} sahifasida o'zbekcha qolgan: {qolgan}"


def test_the_russian_landing_really_says_it_in_russian(client):
    """Tekshiruv bo'sh bo'lmasin: ruscha matn CHINDAN bor.

    Faqat "o'zbekcha yo'q" deb tekshirish yetarli emas — matn butunlay
    yo'qolib qolsa ham o'sha tekshiruv o'tib ketardi.
    """
    body = html.unescape(client.get("/?lang=ru").text)

    for kutilgan in ("Плов", "На двоих", "Рис · Баранина", "Горячие блюда"):
        assert kutilgan in body, kutilgan


def test_the_carousel_controls_sit_below_the_track(client):
    """Strelka kartochka ustida turmasin.

    O'lchov shuni ko'rsatgan edi: 444px tasmada qo'shni kartochkaning
    atigi 64 piksel ko'rinar, strelka esa aynan o'sha ustiga tushardi.
    Chap strelka esa umuman bo'sh joyda osilib turardi.

    Endi ikkalasi ham nuqtalar bilan bitta qatorda, tasmaning OSTIDA.
    """
    body = client.get("/").text

    # Boshqaruv qatori bor va strelkalar uning ichida
    assert "carousel-bar" in body
    bar = body.split('class="carousel-bar"', 1)[1].split("</div>\n        </div>", 1)[0]
    assert "data-carousel-prev" in bar
    assert "data-carousel-next" in bar
    assert "carousel-dot" in bar

    css = client.get("/static/css/style.css").text
    # Strelka endi mutlaq joylashtirilmaydi — u oddiy qatorda turadi
    qoida = re.search(r"\.astra \.carousel-arrow\s*\{([^}]*)\}", css)
    assert qoida and "position: absolute" not in qoida.group(1)
