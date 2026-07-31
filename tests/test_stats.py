import html
from datetime import timedelta

import pytest

from app.models import Category, MenuItem, MenuView
from app.plans import limits_for
from app.services import stats

from tests.conftest import login


@pytest.fixture
def menu(db, tenant_a):
    restaurant, _ = tenant_a
    category = Category(restaurant_id=restaurant.id, name={"uz": "Issiq taomlar"})
    db.add(category)
    db.flush()
    item = MenuItem(
        restaurant_id=restaurant.id,
        category_id=category.id,
        name={"uz": "Osh"},
        price=38000,
    )
    db.add(item)
    db.commit()
    return restaurant, item


def test_opening_the_menu_is_counted(client, db, menu):
    restaurant, _ = menu
    client.get(f"/r/{restaurant.slug}")
    client.get(f"/r/{restaurant.slug}")
    assert stats.total_views(db, restaurant.id) == 2


def test_search_is_not_counted_as_an_opening(client, db, menu):
    """Aks holda bitta mijoz qidiruv bilan sonni shishirib yuboradi."""
    restaurant, _ = menu
    client.get(f"/r/{restaurant.slug}?q=osh")
    assert stats.total_views(db, restaurant.id) == 0


def test_item_views_are_counted_for_both_page_and_sheet(client, db, menu):
    restaurant, item = menu
    client.get(f"/r/{restaurant.slug}/item/{item.id}")
    client.get(f"/r/{restaurant.slug}/item/{item.id}?partial=1")

    top = stats.top_items(db, restaurant.id)
    assert top[0][0].id == item.id
    assert top[0][1] == 2


def test_repeated_views_share_one_row_per_day(db, menu):
    """Kunlik yig'ma — jadval yillar davomida ham kichik qolishi kerak."""
    restaurant, _ = menu
    for _ in range(50):
        stats.record_view(db, restaurant.id)

    assert db.query(MenuView).count() == 1
    assert stats.total_views(db, restaurant.id) == 50


def test_daily_series_fills_empty_days_with_zero(db, menu):
    restaurant, _ = menu
    stats.record_view(db, restaurant.id)

    series = stats.daily_menu_views(db, restaurant.id, days=7)
    assert len(series) == 7
    assert series[-1] == (stats.today(), 1)
    assert all(count == 0 for _, count in series[:-1])


def test_old_days_fall_outside_the_window(db, menu):
    restaurant, _ = menu
    db.add(
        MenuView(
            restaurant_id=restaurant.id,
            item_id=None,
            day=stats.today() - timedelta(days=40),
            count=99,
        )
    )
    db.commit()
    assert stats.total_views(db, restaurant.id, days=30) == 0


def test_a_broken_counter_never_breaks_the_menu(client, db, menu, monkeypatch):
    """Statistika ikkinchi darajali — u yiqilsa ham mijoz menyuni ko'rishi kerak."""
    restaurant, _ = menu

    def explode(*args, **kwargs):
        from sqlalchemy.exc import OperationalError

        raise OperationalError("stats", {}, Exception("baza band"))

    monkeypatch.setattr(stats, "_bump", explode)
    response = client.get(f"/r/{restaurant.slug}")
    assert response.status_code == 200
    assert "Osh" in response.text


def test_dashboard_shows_the_counter(client, db, menu):
    restaurant, _ = menu
    client.get(f"/r/{restaurant.slug}")

    login(client, "osh", "adminpass123")
    body = html.unescape(client.get("/admin").text)
    assert f"{limits_for(restaurant).stats_days} kunda ochilgan" in body
    assert "Eng ko'p ochilgan taomlar" not in body  # taom hali ochilmagan
