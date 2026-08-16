from io import BytesIO

import pytest
from PIL import Image

from app.config import settings
from app.models import Category, MenuItem, Restaurant

from tests.conftest import csrf, login


def png_upload(size=(60, 40)) -> tuple[str, BytesIO, str]:
    buffer = BytesIO()
    Image.new("RGB", size, "red").save(buffer, "PNG")
    buffer.seek(0)
    return ("dish.png", buffer, "image/png")


@pytest.fixture
def admin_client(client, tenant_a):
    login(client, "osh", "adminpass123")
    return client


def make_category(client, db, restaurant_id) -> Category:
    client.post(
        "/admin/categories",
        data={
            "csrf_token": csrf(client, "/admin/categories"),
            "name_uz": "Issiq taomlar",
            "name_ru": "Горячее",
            "sort_order": 1,
        },
    )
    return db.query(Category).filter_by(restaurant_id=restaurant_id).one()


def test_category_is_created_with_translations(admin_client, db, tenant_a):
    restaurant, _ = tenant_a
    category = make_category(admin_client, db, restaurant.id)
    assert category.name == {"uz": "Issiq taomlar", "ru": "Горячее"}
    assert category.sort_order == 1


def test_item_ingredients_are_saved_and_editable(admin_client, db, tenant_a):
    restaurant, _ = tenant_a
    category = make_category(admin_client, db, restaurant.id)

    admin_client.post(
        "/admin/items",
        data={
            "csrf_token": csrf(admin_client, "/admin/items"),
            "category_id": category.id,
            "name_uz": "Osh",
            "price": 38000,
            "ingredients_uz": "Guruch, sabzi, zira",
            "ingredients_ru": "Рис, морковь, зира",
        },
    )
    item = db.query(MenuItem).filter_by(restaurant_id=restaurant.id).one()
    assert item.ingredients == {"uz": "Guruch, sabzi, zira", "ru": "Рис, морковь, зира"}

    admin_client.post(
        f"/admin/items/{item.id}",
        data={
            "csrf_token": csrf(admin_client, f"/admin/items/{item.id}/edit"),
            "category_id": category.id,
            "name_uz": "Osh",
            "price": 38000,
            "ingredients_uz": "Guruch, qo'y go'shti",
        },
    )
    db.refresh(item)
    assert item.ingredients == {"uz": "Guruch, qo'y go'shti"}


def test_item_upload_is_reencoded_to_webp(admin_client, db, tenant_a):
    restaurant, _ = tenant_a
    category = make_category(admin_client, db, restaurant.id)

    response = admin_client.post(
        "/admin/items",
        data={
            "csrf_token": csrf(admin_client, "/admin/items"),
            "category_id": category.id,
            "name_uz": "Osh",
            "price": 38000,
        },
        files={"image": png_upload()},
    )
    assert response.status_code == 200

    item = db.query(MenuItem).filter_by(restaurant_id=restaurant.id).one()
    assert item.image.endswith(".webp")
    stored = settings.media_path / item.image
    assert stored.exists()
    with Image.open(stored) as image:
        assert image.format == "WEBP"


def test_replacing_an_image_removes_the_old_file(admin_client, db, tenant_a):
    restaurant, _ = tenant_a
    category = make_category(admin_client, db, restaurant.id)
    admin_client.post(
        "/admin/items",
        data={
            "csrf_token": csrf(admin_client, "/admin/items"),
            "category_id": category.id,
            "name_uz": "Osh",
            "price": 38000,
        },
        files={"image": png_upload()},
    )
    item = db.query(MenuItem).filter_by(restaurant_id=restaurant.id).one()
    old_path = settings.media_path / item.image

    admin_client.post(
        f"/admin/items/{item.id}",
        data={
            "csrf_token": csrf(admin_client, "/admin/items"),
            "category_id": category.id,
            "name_uz": "Osh",
            "price": 40000,
            "is_available": "true",
        },
        files={"image": png_upload()},
    )
    db.expire_all()
    item = db.get(MenuItem, item.id)
    assert not old_path.exists()
    assert (settings.media_path / item.image).exists()
    assert int(item.price) == 40000


def test_deleting_an_item_removes_its_image(admin_client, db, tenant_a):
    restaurant, _ = tenant_a
    category = make_category(admin_client, db, restaurant.id)
    admin_client.post(
        "/admin/items",
        data={
            "csrf_token": csrf(admin_client, "/admin/items"),
            "category_id": category.id,
            "name_uz": "Osh",
            "price": 38000,
        },
        files={"image": png_upload()},
    )
    item = db.query(MenuItem).filter_by(restaurant_id=restaurant.id).one()
    path = settings.media_path / item.image

    admin_client.post(
        f"/admin/items/{item.id}/delete",
        data={"csrf_token": csrf(admin_client, "/admin/items")},
    )
    assert not path.exists()
    assert db.query(MenuItem).filter_by(id=item.id).count() == 0


def test_non_image_upload_is_rejected(admin_client, db, tenant_a):
    restaurant, _ = tenant_a
    category = make_category(admin_client, db, restaurant.id)

    response = admin_client.post(
        "/admin/items",
        data={
            "csrf_token": csrf(admin_client, "/admin/items"),
            "category_id": category.id,
            "name_uz": "Osh",
            "price": 38000,
        },
        files={"image": ("payload.png", BytesIO(b"<?php echo 1; ?>"), "image/png")},
        follow_redirects=False,
    )
    # Endi forma sahifasiga qaytariladi va xabar tepasida chiqadi —
    # ilgari bu yalang'och 400 sahifasi edi va odam yozganini yo'qotardi
    assert response.status_code == 303
    # Eng muhimi o'zgarmadi: soxta "rasm" saqlanmaydi
    assert db.query(MenuItem).count() == 0


def test_settings_save_translated_fields(admin_client, db, tenant_a):
    restaurant, _ = tenant_a
    admin_client.post(
        "/admin/settings",
        data={
            "csrf_token": csrf(admin_client, "/admin/settings"),
            "name": "Osh Markazi",
            "description_uz": "Milliy taomlar",
            "description_en": "Uzbek cuisine",
            "address_uz": "Toshkent",
            "phone": "+998901234567",
            "currency": "so'm",
        },
    )
    db.expire_all()
    restaurant = db.get(Restaurant, restaurant.id)
    assert restaurant.description == {"uz": "Milliy taomlar", "en": "Uzbek cuisine"}
    assert restaurant.address == {"uz": "Toshkent"}
    # Valyuta dizayn emas, ish sozlamasi — u shu yerda qoladi
    assert restaurant.currency == "so'm"


def test_deleting_a_category_removes_its_items(admin_client, db, tenant_a):
    restaurant, _ = tenant_a
    category = make_category(admin_client, db, restaurant.id)
    admin_client.post(
        "/admin/items",
        data={
            "csrf_token": csrf(admin_client, "/admin/items"),
            "category_id": category.id,
            "name_uz": "Osh",
            "price": 38000,
        },
    )
    assert db.query(MenuItem).count() == 1

    admin_client.post(
        f"/admin/categories/{category.id}/delete",
        data={"csrf_token": csrf(admin_client, "/admin/categories")},
    )
    assert db.query(MenuItem).count() == 0
    assert db.query(Category).count() == 0


# --- kategoriya va taomlar bitta sahifada ---------------------------------
#
# Foydalanuvchi talabi: ikkalasini birlashtirish, va taomni tartiblashda
# kategoriyadan chiqib ketilmasin. Ilgari tartib boshqa sahifada edi va
# qaysi taom qayerga tegishli ekani ko'rinmasdi.


def test_the_menu_shows_dishes_inside_their_category(admin_client, db, tenant_a):
    restaurant, _ = tenant_a
    ichimlik = Category(restaurant_id=restaurant.id, name={"uz": "Ichimliklar"})
    taomlar = Category(restaurant_id=restaurant.id, name={"uz": "Taomlar"})
    db.add_all([ichimlik, taomlar])
    db.flush()
    db.add_all([
        MenuItem(restaurant_id=restaurant.id, category_id=ichimlik.id,
                 name={"uz": "Choy"}, price=8000),
        MenuItem(restaurant_id=restaurant.id, category_id=taomlar.id,
                 name={"uz": "Osh"}, price=38000),
    ])
    db.commit()

    body = admin_client.get("/admin/menu").text

    ichimlik_bloki = body.split('data-category="%d"' % ichimlik.id)[1].split("</section>")[0]
    assert "Choy" in ichimlik_bloki
    assert "Osh" not in ichimlik_bloki      # boshqa kategoriyaning taomi


def test_a_dish_is_reordered_without_leaving_its_category(admin_client, db, tenant_a):
    restaurant, _ = tenant_a
    category = Category(restaurant_id=restaurant.id, name={"uz": "Taomlar"})
    db.add(category)
    db.flush()
    item = MenuItem(restaurant_id=restaurant.id, category_id=category.id,
                    name={"uz": "Osh"}, price=38000, sort_order=0)
    db.add(item)
    db.commit()

    response = admin_client.post(
        f"/admin/items/{item.id}/order",
        data={"csrf_token": csrf(admin_client, "/admin/menu"), "sort_order": "5"},
    )

    db.refresh(item)
    assert item.sort_order == 5
    assert item.category_id == category.id      # kategoriyasi o'zgarmadi
    assert response.url.path == "/admin/menu"


def test_another_restaurants_dish_cannot_be_reordered(admin_client, db, tenant_a, tenant_b):
    other, _ = tenant_b
    category = Category(restaurant_id=other.id, name={"uz": "Begona"})
    db.add(category)
    db.flush()
    item = MenuItem(restaurant_id=other.id, category_id=category.id,
                    name={"uz": "Begona osh"}, price=1, sort_order=0)
    db.add(item)
    db.commit()

    response = admin_client.post(
        f"/admin/items/{item.id}/order",
        data={"csrf_token": csrf(admin_client, "/admin/menu"), "sort_order": "9"},
    )

    assert response.status_code == 404
    db.refresh(item)
    assert item.sort_order == 0


def test_the_old_pages_still_lead_somewhere(admin_client, tenant_a):
    """Eski xatcho'plar 404 bo'lib qolmasin."""
    for eski in ("/admin/categories", "/admin/items"):
        response = admin_client.get(eski, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/admin/menu"
