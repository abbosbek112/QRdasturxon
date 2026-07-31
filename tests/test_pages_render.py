import pytest

from app.models import Category, MenuItem

from tests.conftest import login


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
    ["/admin", "/admin/settings", "/admin/categories", "/admin/items", "/admin/items/new", "/admin/qr"],
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
