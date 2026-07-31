from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.i18n import LANGUAGES, LANG_COOKIE, resolve_lang, tr
from app.models import Category, MenuItem, Plan, Restaurant
from app.plans import LIMITS, TRIAL_DAYS, limits_for, visible_languages
from app.security import verify_csrf
from app.services import comments
from app.services.stats import record_view
from app.templating import templates

router = APIRouter(tags=["public"])

DbSession = Annotated[Session, Depends(get_db)]


def _get_restaurant(db: Session, slug: str) -> Restaurant:
    restaurant = db.scalar(select(Restaurant).where(Restaurant.slug == slug))
    if restaurant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Restoran topilmadi")
    return restaurant


def _menu_languages(restaurant: Restaurant) -> tuple[dict[str, str], str]:
    """Tarifga ruxsat etilgan tillar va agar so'ralgan til ruxsat etilmagan bo'lsa — zaxira.

    Bepul tarifda faqat o'zbekcha ko'rinadi. Tarjimalar bazada saqlanib qoladi,
    restoran tarifni ko'targanda darrov paydo bo'ladi.
    """
    allowed = visible_languages(restaurant)
    return {code: LANGUAGES[code] for code in allowed if code in LANGUAGES}, allowed[0]


@router.get("/")
def index(request: Request, db: DbSession):
    """Reklama sahifasi — platformaga kelgan restoran egasi shu yerni ko'radi."""
    lang = resolve_lang(request)
    demo = db.scalar(
        select(Restaurant)
        .where(Restaurant.is_active.is_(True))
        .order_by(Restaurant.created_at)
        .limit(1)
    )
    return templates.TemplateResponse(
        request,
        "public/landing.html",
        {
            "lang": lang,
            "restaurant": None,
            "demo_slug": demo.slug if demo else None,
            "plans": [(plan, LIMITS[plan]) for plan in Plan],
            "trial_days": TRIAL_DAYS,
        },
    )


@router.get("/r/{slug}")
def menu(request: Request, db: DbSession, slug: str, q: str = ""):
    lang = resolve_lang(request)
    restaurant = _get_restaurant(db, slug)
    if not restaurant.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Restoran topilmadi")

    languages, fallback = _menu_languages(restaurant)
    if lang not in languages:
        lang = fallback

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

    # "Bugungi taklif" — kategoriyadan qat'i nazar menyuning eng tepasida
    limits = limits_for(restaurant)
    specials = []
    if limits.specials and not needle:
        specials = [
            item
            for _, items in sections
            for item in items
            if item.is_special
        ]

    # Qidiruvni alohida ochilish deb hisoblamaymiz — bir mijoz sonni shishirmasin
    if not needle:
        record_view(db, restaurant.id)

    response = templates.TemplateResponse(
        request,
        "public/menu.html",
        {
            "lang": lang,
            "restaurant": restaurant,
            "sections": sections,
            "specials": specials,
            "q": q,
            "languages": languages,
        },
    )
    _remember_language(request, response, lang)
    return response


def _get_item(db: Session, restaurant: Restaurant, item_id: int) -> MenuItem:
    item = db.scalar(
        select(MenuItem).where(
            MenuItem.id == item_id,
            MenuItem.restaurant_id == restaurant.id,
            MenuItem.is_available.is_(True),
        )
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Taom topilmadi")
    return item


@router.get("/r/{slug}/item/{item_id}")
def item_detail(
    request: Request,
    db: DbSession,
    slug: str,
    item_id: int,
    partial: bool = False,
    sent: bool = False,
):
    lang = resolve_lang(request)
    restaurant = _get_restaurant(db, slug)
    item = _get_item(db, restaurant, item_id)

    languages, fallback = _menu_languages(restaurant)
    if lang not in languages:
        lang = fallback

    record_view(db, restaurant.id, item.id)

    allow_comments = limits_for(restaurant).comments
    # ?partial=1 — bottom sheet ichiga joylash uchun faqat mazmun bo'lagi
    template = "public/_item_body.html" if partial else "public/item.html"
    response = templates.TemplateResponse(
        request,
        template,
        {
            "lang": lang,
            "restaurant": restaurant,
            "item": item,
            "languages": languages,
            "allow_comments": allow_comments,
            "comments": comments.visible_for(db, item.id) if allow_comments else [],
            "comment_sent": sent,
        },
    )
    _remember_language(request, response, lang)
    return response


@router.post("/r/{slug}/item/{item_id}/comment", dependencies=[Depends(verify_csrf)])
def add_comment(
    request: Request,
    db: DbSession,
    slug: str,
    item_id: int,
    author_name: Annotated[str, Form()],
    body: Annotated[str, Form()],
):
    lang = resolve_lang(request)
    restaurant = _get_restaurant(db, slug)
    if not limits_for(restaurant).comments:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Izohlar yoqilmagan")

    item = _get_item(db, restaurant, item_id)
    comments.add(
        db,
        item=item,
        author_name=author_name,
        body=body,
        ip=request.client.host if request.client else "unknown",
    )
    # ?sent=1 — "tasdiqlanishi kutilmoqda" xabari uchun
    suffix = f"?sent=1{'&lang=' + lang if lang != 'uz' else ''}"
    return RedirectResponse(
        f"/r/{slug}/item/{item_id}{suffix}", status.HTTP_303_SEE_OTHER
    )


def _remember_language(request: Request, response, lang: str) -> None:
    if request.query_params.get("lang") in LANGUAGES:
        response.set_cookie(
            LANG_COOKIE, lang, max_age=60 * 60 * 24 * 365, httponly=False, samesite="lax"
        )
