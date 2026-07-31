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
    )
    assert response.status_code == 400
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
            "theme_color": "#b45309",
            "currency": "so'm",
        },
    )
    db.expire_all()
    restaurant = db.get(Restaurant, restaurant.id)
    assert restaurant.description == {"uz": "Milliy taomlar", "en": "Uzbek cuisine"}
    assert restaurant.address == {"uz": "Toshkent"}
    assert restaurant.theme_color == "#b45309"


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
