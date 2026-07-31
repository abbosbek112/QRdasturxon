from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.i18n import LANGUAGES, LANG_COOKIE, resolve_lang, tr
from app.models import Category, MenuItem, Restaurant
from app.templating import templates

router = APIRouter(tags=["public"])

DbSession = Annotated[Session, Depends(get_db)]


def _get_restaurant(db: Session, slug: str) -> Restaurant:
    restaurant = db.scalar(select(Restaurant).where(Restaurant.slug == slug))
    if restaurant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Restoran topilmadi")
    return restaurant


@router.get("/")
def index(request: Request, db: DbSession):
    lang = resolve_lang(request)
    restaurants = db.scalars(
        select(Restaurant).where(Restaurant.is_active.is_(True)).order_by(Restaurant.name)
    ).all()
    return templates.TemplateResponse(
        request, "public/index.html", {"lang": lang, "restaurants": restaurants}
    )


@router.get("/r/{slug}")
def menu(request: Request, db: DbSession, slug: str, q: str = ""):
    lang = resolve_lang(request)
    restaurant = _get_restaurant(db, slug)
    if not restaurant.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Restoran topilmadi")

    categories = db.scalars(
        select(Category)
        .where(Category.restaurant_id == restaurant.id, Category.is_active.is_(True))
        .options(selectinload(Category.items))
        .order_by(Category.sort_order, Category.id)
    ).all()

    needle = q.strip().lower()
    sections = []
    for category in categories:
        items = [item for item in category.items if item.is_available]
        if needle:
            items = [
                item
                for item in items
                if needle in tr(item.name, lang).lower()
                or needle in tr(item.description, lang).lower()
            ]
        if items:
            sections.append((category, items))

    response = templates.TemplateResponse(
        request,
        "public/menu.html",
        {"lang": lang, "restaurant": restaurant, "sections": sections, "q": q},
    )
    _remember_language(request, response, lang)
    return response


@router.get("/r/{slug}/item/{item_id}")
def item_detail(request: Request, db: DbSession, slug: str, item_id: int):
    lang = resolve_lang(request)
    restaurant = _get_restaurant(db, slug)
    item = db.scalar(
        select(MenuItem).where(
            MenuItem.id == item_id,
            MenuItem.restaurant_id == restaurant.id,
            MenuItem.is_available.is_(True),
        )
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Taom topilmadi")

    response = templates.TemplateResponse(
        request, "public/item.html", {"lang": lang, "restaurant": restaurant, "item": item}
    )
    _remember_language(request, response, lang)
    return response


def _remember_language(request: Request, response, lang: str) -> None:
    if request.query_params.get("lang") in LANGUAGES:
        response.set_cookie(
            LANG_COOKIE, lang, max_age=60 * 60 * 24 * 365, httponly=False, samesite="lax"
        )
