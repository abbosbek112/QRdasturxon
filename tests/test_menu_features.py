import html

import pytest

from app.models import Category, ItemComment, MenuItem, Plan, SubscriptionStatus
from app.services import comments

from tests.conftest import csrf, login


@pytest.fixture
def cafe(db, tenant_a):
    """To'liq tarifdagi restoran — yangi imkoniyatlar shu tarifda ochiq."""
    restaurant, _ = tenant_a
    restaurant.plan = Plan.full
    restaurant.subscription_status = SubscriptionStatus.active
    category = Category(restaurant_id=restaurant.id, name={"uz": "Ichimliklar"})
    db.add(category)
    db.flush()
    item = MenuItem(
        restaurant_id=restaurant.id,
        category_id=category.id,
        name={"uz": "Kapuchino"},
        price=25000,
    )
    db.add(item)
    db.commit()
    return restaurant, item


@pytest.fixture
def free_cafe(db, cafe):
    restaurant, item = cafe
    restaurant.plan = Plan.free
    db.commit()
    return restaurant, item


# --- Wi-Fi ---

def test_wifi_password_appears_on_the_menu(client, db, cafe):
    restaurant, _ = cafe
    restaurant.wifi_name = "Kafe_WiFi"
    restaurant.wifi_password = "salom1234"
    db.commit()

    body = client.get(f"/r/{restaurant.slug}").text
    assert "salom1234" in body
    assert "Kafe_WiFi" in body


def test_menu_has_no_wifi_block_when_unset(client, cafe):
    restaurant, _ = cafe
    assert 'class="wifi"' not in client.get(f"/r/{restaurant.slug}").text


# --- taom belgilari ---

def test_dietary_marks_show_on_card_and_detail(client, db, cafe):
    restaurant, item = cafe
    item.is_spicy = True
    item.is_vegetarian = True
    item.allergens = {"uz": "sut, yong'oq"}
    db.commit()

    menu = html.unescape(client.get(f"/r/{restaurant.slug}").text)
    assert "O'tkir" in menu
    assert "Vegetarian" in menu

    detail = html.unescape(client.get(f"/r/{restaurant.slug}/item/{item.id}").text)
    assert "sut, yong'oq" in detail
    assert "Allergenlar" in detail


# --- bugungi taklif ---

def test_special_dish_gets_its_own_section(client, db, cafe):
    restaurant, item = cafe
    item.is_special = True
    db.commit()

    body = html.unescape(client.get(f"/r/{restaurant.slug}").text)
    assert "Bugungi taklif" in body


def test_free_plan_hides_the_specials_section(client, db, free_cafe):
    restaurant, item = free_cafe
    item.is_special = True
    db.commit()

    body = html.unescape(client.get(f"/r/{restaurant.slug}").text)
    assert "Bugungi taklif" not in body
    assert "Kapuchino" in body  # taom o'zi menyuda qolaveradi


# --- izohlar ---

def post_comment(client, restaurant, item, name="Aziz", body="Juda mazali edi"):
    # Token sessiyaga bog'langan — bepul tarifda izoh formasi chiqmagani uchun
    # uni har doim mavjud bo'lgan ochiq sahifadan olamiz
    return client.post(
        f"/r/{restaurant.slug}/item/{item.id}/comment",
        data={
            "csrf_token": csrf(client, "/signup"),
            "author_name": name,
            "body": body,
        },
    )


def test_comment_waits_for_approval_before_showing(client, db, cafe):
    restaurant, item = cafe
    post_comment(client, restaurant, item)

    saved = db.query(ItemComment).one()
    assert saved.is_approved is False

    body = html.unescape(client.get(f"/r/{restaurant.slug}/item/{item.id}").text)
    assert "Juda mazali edi" not in body


def test_approved_comment_shows_on_the_dish(client, db, cafe):
    restaurant, item = cafe
    post_comment(client, restaurant, item)
    db.query(ItemComment).one().is_approved = True
    db.commit()

    body = html.unescape(client.get(f"/r/{restaurant.slug}/item/{item.id}").text)
    assert "Juda mazali edi" in body
    assert "Aziz" in body


def test_one_comment_per_dish_per_day(client, db, cafe):
    """Aks holda bitta odam taomni izohlar bilan to'ldirib tashlaydi."""
    restaurant, item = cafe
    assert post_comment(client, restaurant, item).status_code == 200

    blocked = post_comment(client, restaurant, item, body="Yana bir fikr")
    assert blocked.status_code == 429
    assert db.query(ItemComment).count() == 1


def test_a_different_dish_can_still_be_commented(client, db, cafe):
    restaurant, item = cafe
    other = MenuItem(
        restaurant_id=restaurant.id,
        category_id=item.category_id,
        name={"uz": "Choy"},
        price=8000,
    )
    db.add(other)
    db.commit()

    post_comment(client, restaurant, item)
    assert post_comment(client, restaurant, other).status_code == 200
    assert db.query(ItemComment).count() == 2


def test_free_plan_refuses_comments(client, db, free_cafe):
    restaurant, item = free_cafe
    assert post_comment(client, restaurant, item).status_code == 403
    assert db.query(ItemComment).count() == 0


def test_comment_needs_a_name_and_a_body(client, db, cafe):
    restaurant, item = cafe
    assert post_comment(client, restaurant, item, name="  ").status_code == 400
    assert post_comment(client, restaurant, item, body="a").status_code == 400
    assert db.query(ItemComment).count() == 0


def test_owner_approves_and_deletes_comments(client, db, cafe):
    restaurant, item = cafe
    comments.add(db, item=item, author_name="Aziz", body="Zo'r", ip="1.1.1.1")
    comment_id = db.query(ItemComment).one().id

    login(client, "osh", "adminpass123")
    client.post(
        f"/admin/comments/{comment_id}/approve",
        data={"csrf_token": csrf(client, "/admin/comments")},
    )
    db.expire_all()
    assert db.query(ItemComment).one().is_approved is True

    client.post(
        f"/admin/comments/{comment_id}/delete",
        data={"csrf_token": csrf(client, "/admin/comments")},
    )
    assert db.query(ItemComment).count() == 0


def test_owner_cannot_touch_another_restaurants_comment(client, db, cafe, tenant_b):
    restaurant, item = cafe
    comments.add(db, item=item, author_name="Aziz", body="Zo'r", ip="1.1.1.1")
    comment_id = db.query(ItemComment).one().id

    login(client, "choy", "adminpass123")  # boshqa restoran admini
    response = client.post(
        f"/admin/comments/{comment_id}/delete",
        data={"csrf_token": csrf(client, "/admin/comments")},
    )
    assert response.status_code == 404
    assert db.query(ItemComment).count() == 1


# --- chop etish uchun menyu ---

def test_print_page_lists_dishes_with_prices(client, db, cafe):
    restaurant, _ = cafe
    login(client, "osh", "adminpass123")

    body = client.get("/admin/menu/print").text
    assert "Kapuchino" in body
    assert "25 000" in body
    assert "Ichimliklar" in body


def test_free_plan_cannot_print(client, db, free_cafe):
    login(client, "osh", "adminpass123")
    assert client.get("/admin/menu/print").status_code == 403
