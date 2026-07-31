from app.models import Category, MenuItem

from tests.conftest import csrf, login


def add_menu(db, restaurant_id: int) -> tuple[Category, MenuItem]:
    category = Category(restaurant_id=restaurant_id, name={"uz": "Taomlar"})
    db.add(category)
    db.flush()
    item = MenuItem(
        restaurant_id=restaurant_id,
        category_id=category.id,
        name={"uz": "Osh"},
        price=35000,
    )
    db.add(item)
    db.commit()
    return category, item


def test_admin_cannot_edit_other_restaurants_item(client, db, tenant_a, tenant_b):
    restaurant_b, _ = tenant_b
    _, foreign_item = add_menu(db, restaurant_b.id)

    login(client, "osh", "adminpass123")
    response = client.get(f"/admin/items/{foreign_item.id}/edit")
    assert response.status_code == 404


def test_admin_cannot_delete_other_restaurants_item(client, db, tenant_a, tenant_b):
    restaurant_b, _ = tenant_b
    _, foreign_item = add_menu(db, restaurant_b.id)

    login(client, "osh", "adminpass123")
    token = csrf(client, "/admin/items")
    response = client.post(
        f"/admin/items/{foreign_item.id}/delete", data={"csrf_token": token}
    )
    assert response.status_code == 404
    assert db.get(MenuItem, foreign_item.id) is not None


def test_admin_cannot_move_item_into_other_restaurants_category(
    client, db, tenant_a, tenant_b
):
    restaurant_a, _ = tenant_a
    restaurant_b, _ = tenant_b
    _, own_item = add_menu(db, restaurant_a.id)
    foreign_category, _ = add_menu(db, restaurant_b.id)

    login(client, "osh", "adminpass123")
    token = csrf(client, "/admin/items")
    response = client.post(
        f"/admin/items/{own_item.id}",
        data={
            "csrf_token": token,
            "category_id": foreign_category.id,
            "name_uz": "Osh",
            "price": 40000,
        },
    )
    assert response.status_code == 404


def test_admin_only_sees_own_items(client, db, tenant_a, tenant_b):
    restaurant_a, _ = tenant_a
    restaurant_b, _ = tenant_b
    add_menu(db, restaurant_a.id)

    category_b = Category(restaurant_id=restaurant_b.id, name={"uz": "Ichimliklar"})
    db.add(category_b)
    db.flush()
    db.add(
        MenuItem(
            restaurant_id=restaurant_b.id,
            category_id=category_b.id,
            name={"uz": "Choy"},
            price=5000,
        )
    )
    db.commit()

    login(client, "osh", "adminpass123")
    body = client.get("/admin/items").text
    assert "Osh" in body
    assert "Choy" not in body
