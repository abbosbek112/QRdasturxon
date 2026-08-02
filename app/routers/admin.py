from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Category, ItemComment, MenuItem, Restaurant, User
from app.plans import limits_for, refresh_status, trial_days_left
from app.security import require_restaurant_admin, verify_csrf
from app import themes
from app.services import comments, onboarding, qr, stats
from app.services.images import delete_image, save_image
from app.templating import templates

router = APIRouter(prefix="/admin", tags=["admin"])

DbSession = Annotated[Session, Depends(get_db)]
AdminUser = Annotated[User, Depends(require_restaurant_admin)]


def i18n_field(uz: str, ru: str, en: str) -> dict:
    return {
        lang: text.strip()
        for lang, text in (("uz", uz), ("ru", ru), ("en", en))
        if text and text.strip()
    }


def get_restaurant(db: Session, user: User) -> Restaurant:
    restaurant = db.get(Restaurant, user.restaurant_id)
    if restaurant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Restoran topilmadi")
    # Sinov muddati tugagan bo'lsa holatni shu yerda yangilaymiz — alohida
    # fon vazifasi kerak bo'lmaydi, admin panelga kirganda o'zi tekshiriladi
    if refresh_status(restaurant):
        db.commit()
    return restaurant


def check_item_limit(db: Session, restaurant: Restaurant) -> None:
    limit = limits_for(restaurant).max_items
    if limit is None:
        return
    used = db.scalar(
        select(func.count(MenuItem.id)).where(MenuItem.restaurant_id == restaurant.id)
    )
    if used >= limit:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Tarifingizda {limit} tagacha taom qo'shish mumkin. "
            "Ko'proq kerak bo'lsa tarifni ko'taring.",
        )


def check_category_limit(db: Session, restaurant: Restaurant) -> None:
    limit = limits_for(restaurant).max_categories
    if limit is None:
        return
    used = db.scalar(
        select(func.count(Category.id)).where(Category.restaurant_id == restaurant.id)
    )
    if used >= limit:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Tarifingizda {limit} tagacha kategoriya mumkin. "
            "Ko'proq kerak bo'lsa tarifni ko'taring.",
        )


def owned_category(db: Session, user: User, category_id: int) -> Category:
    category = db.scalar(
        select(Category).where(
            Category.id == category_id, Category.restaurant_id == user.restaurant_id
        )
    )
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kategoriya topilmadi")
    return category


def owned_item(db: Session, user: User, item_id: int) -> MenuItem:
    item = db.scalar(
        select(MenuItem).where(
            MenuItem.id == item_id, MenuItem.restaurant_id == user.restaurant_id
        )
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Taom topilmadi")
    return item


@router.get("")
def dashboard(request: Request, db: DbSession, user: AdminUser):
    restaurant = get_restaurant(db, user)
    category_count = db.scalar(
        select(func.count(Category.id)).where(Category.restaurant_id == restaurant.id)
    )
    item_count = db.scalar(
        select(func.count(MenuItem.id)).where(MenuItem.restaurant_id == restaurant.id)
    )
    hidden_count = db.scalar(
        select(func.count(MenuItem.id)).where(
            MenuItem.restaurant_id == restaurant.id, MenuItem.is_available.is_(False)
        )
    )
    limits = limits_for(restaurant)
    # Kunlik ustunlar 30 tadan oshsa ingichkalashib ko'rinmay qoladi — bosh
    # sahifadagi grafikni shu bilan cheklaymiz. To'liq tahlil /admin/stats da.
    chart_days = min(limits.stats_days, 30)
    chart_end = stats.today()
    chart_start = chart_end - timedelta(days=chart_days - 1)
    window_start = chart_end - timedelta(days=limits.stats_days - 1)
    daily = stats.daily_series(db, restaurant.id, chart_start, chart_end)
    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {
            "user": user,
            "restaurant": restaurant,
            "category_count": category_count,
            "item_count": item_count,
            "hidden_count": hidden_count,
            "menu_url": qr.menu_url(restaurant.slug),
            "daily_views": daily,
            "views_total": stats.total_views(db, restaurant.id, window_start, chart_end),
            "views_peak": max((count for _, count in daily), default=0),
            "top_items": stats.top_items(db, restaurant.id, window_start, chart_end),
            "limits": limits,
            "chart_days": chart_days,
            "trial_days": trial_days_left(restaurant),
            # Barcha qadam bajarilgach ro'yxat o'zi yo'qoladi
            "steps": [s for s in onboarding.setup_steps(db, restaurant)],
        },
    )


@router.get("/stats")
def statistics(
    request: Request,
    db: DbSession,
    user: AdminUser,
    period: str = "oy",
    start: str | None = None,
    end: str | None = None,
):
    """Analitika: ixtiyoriy muddat ichida nima necha marta ochilgan."""
    restaurant = get_restaurant(db, user)
    limits = limits_for(restaurant)
    first, last, preset = stats.resolve_range(period, start, end, limits.stats_days)

    daily = stats.daily_series(db, restaurant.id, first, last)
    ranked = stats.top_items(db, restaurant.id, first, last, limit=25)
    # Baho izohlar bilan keladi, ochilish esa MenyuView bilan — ikkalasini
    # taom bo'yicha birlashtiramiz, shunda bitta jadvalda ko'rinadi
    ratings = comments.rating_summary(db, [item.id for item, _ in ranked])

    return templates.TemplateResponse(
        request,
        "admin/stats.html",
        {
            "user": user,
            "restaurant": restaurant,
            "limits": limits,
            "presets": stats.PRESETS,
            "preset": preset,
            "start": first,
            "end": last,
            "daily_views": daily,
            "views_peak": max((count for _, count in daily), default=0),
            "views_total": stats.total_views(db, restaurant.id, first, last),
            "top_items": ranked,
            "ratings": ratings,
            "best_rated": comments.best_rated(db, restaurant.id, limit=10),
        },
    )


@router.get("/settings")
def settings_form(request: Request, db: DbSession, user: AdminUser):
    return templates.TemplateResponse(
        request,
        "admin/settings.html",
        {"user": user, "restaurant": get_restaurant(db, user)},
    )


@router.post("/settings", dependencies=[Depends(verify_csrf)])
async def update_settings(
    db: DbSession,
    user: AdminUser,
    name: Annotated[str, Form()],
    description_uz: Annotated[str, Form()] = "",
    description_ru: Annotated[str, Form()] = "",
    description_en: Annotated[str, Form()] = "",
    address_uz: Annotated[str, Form()] = "",
    address_ru: Annotated[str, Form()] = "",
    address_en: Annotated[str, Form()] = "",
    phone: Annotated[str, Form()] = "",
    working_hours: Annotated[str, Form()] = "",
    instagram: Annotated[str, Form()] = "",
    telegram: Annotated[str, Form()] = "",
    wifi_name: Annotated[str, Form()] = "",
    wifi_password: Annotated[str, Form()] = "",
    theme: Annotated[str, Form()] = "",
    theme_color: Annotated[str, Form()] = "#c2410c",
    currency: Annotated[str, Form()] = "so'm",
    logo: Annotated[UploadFile | None, File()] = None,
    cover_image: Annotated[UploadFile | None, File()] = None,
):
    restaurant = get_restaurant(db, user)
    restaurant.name = name.strip() or restaurant.name
    restaurant.description = i18n_field(description_uz, description_ru, description_en)
    restaurant.address = i18n_field(address_uz, address_ru, address_en)
    restaurant.phone = phone.strip() or None
    restaurant.working_hours = working_hours.strip() or None
    restaurant.instagram = instagram.strip() or None
    restaurant.telegram = telegram.strip() or None
    restaurant.wifi_name = wifi_name.strip() or None
    restaurant.wifi_password = wifi_password.strip() or None
    if theme in themes.THEMES:
        restaurant.theme = theme
    restaurant.theme_color = theme_color.strip() or restaurant.theme_color
    restaurant.currency = currency.strip() or restaurant.currency

    if logo is not None and logo.filename:
        old = restaurant.logo
        restaurant.logo = await save_image(logo, restaurant.id, max_width=400)
        delete_image(old)
    if cover_image is not None and cover_image.filename:
        old = restaurant.cover_image
        restaurant.cover_image = await save_image(cover_image, restaurant.id, max_width=1600)
        delete_image(old)

    db.commit()
    return RedirectResponse("/admin/settings", status.HTTP_303_SEE_OTHER)


@router.get("/categories")
def categories_page(request: Request, db: DbSession, user: AdminUser):
    categories = db.scalars(
        select(Category)
        .where(Category.restaurant_id == user.restaurant_id)
        .options(selectinload(Category.items))
        .order_by(Category.sort_order, Category.id)
    ).all()
    return templates.TemplateResponse(
        request,
        "admin/categories.html",
        {"user": user, "restaurant": get_restaurant(db, user), "categories": categories},
    )


@router.post("/categories", dependencies=[Depends(verify_csrf)])
def create_category(
    db: DbSession,
    user: AdminUser,
    name_uz: Annotated[str, Form()],
    name_ru: Annotated[str, Form()] = "",
    name_en: Annotated[str, Form()] = "",
    sort_order: Annotated[int, Form()] = 0,
):
    if not name_uz.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Kategoriya nomi bo'sh bo'lmasin")
    check_category_limit(db, get_restaurant(db, user))
    db.add(
        Category(
            restaurant_id=user.restaurant_id,
            name=i18n_field(name_uz, name_ru, name_en),
            sort_order=sort_order,
        )
    )
    db.commit()
    return RedirectResponse("/admin/categories", status.HTTP_303_SEE_OTHER)


@router.post("/categories/{category_id}", dependencies=[Depends(verify_csrf)])
def update_category(
    db: DbSession,
    user: AdminUser,
    category_id: int,
    name_uz: Annotated[str, Form()],
    name_ru: Annotated[str, Form()] = "",
    name_en: Annotated[str, Form()] = "",
    sort_order: Annotated[int, Form()] = 0,
    is_active: Annotated[bool, Form()] = False,
):
    category = owned_category(db, user, category_id)
    category.name = i18n_field(name_uz, name_ru, name_en) or category.name
    category.sort_order = sort_order
    category.is_active = is_active
    db.commit()
    return RedirectResponse("/admin/categories", status.HTTP_303_SEE_OTHER)


@router.post("/categories/{category_id}/delete", dependencies=[Depends(verify_csrf)])
def delete_category(db: DbSession, user: AdminUser, category_id: int):
    category = owned_category(db, user, category_id)
    for item in category.items:
        delete_image(item.image)
    db.delete(category)
    db.commit()
    return RedirectResponse("/admin/categories", status.HTTP_303_SEE_OTHER)


@router.get("/items")
def items_page(request: Request, db: DbSession, user: AdminUser, category_id: int | None = None):
    query = select(MenuItem).where(MenuItem.restaurant_id == user.restaurant_id)
    if category_id is not None:
        query = query.where(MenuItem.category_id == category_id)
    items = db.scalars(
        query.options(selectinload(MenuItem.category)).order_by(
            MenuItem.category_id, MenuItem.sort_order, MenuItem.id
        )
    ).all()
    categories = db.scalars(
        select(Category)
        .where(Category.restaurant_id == user.restaurant_id)
        .order_by(Category.sort_order, Category.id)
    ).all()
    return templates.TemplateResponse(
        request,
        "admin/items.html",
        {
            "user": user,
            "restaurant": get_restaurant(db, user),
            "items": items,
            "categories": categories,
            "active_category_id": category_id,
        },
    )


@router.get("/items/new")
def new_item_form(request: Request, db: DbSession, user: AdminUser):
    restaurant = get_restaurant(db, user)
    categories = db.scalars(
        select(Category)
        .where(Category.restaurant_id == user.restaurant_id)
        .order_by(Category.sort_order, Category.id)
    ).all()
    return templates.TemplateResponse(
        request,
        "admin/item_form.html",
        {
            "user": user,
            "restaurant": restaurant,
            "categories": categories,
            "item": None,
            "limits": limits_for(restaurant),
        },
    )


@router.get("/items/{item_id}/edit")
def edit_item_form(request: Request, db: DbSession, user: AdminUser, item_id: int):
    restaurant = get_restaurant(db, user)
    categories = db.scalars(
        select(Category)
        .where(Category.restaurant_id == user.restaurant_id)
        .order_by(Category.sort_order, Category.id)
    ).all()
    return templates.TemplateResponse(
        request,
        "admin/item_form.html",
        {
            "user": user,
            "restaurant": restaurant,
            "categories": categories,
            "item": owned_item(db, user, item_id),
            "limits": limits_for(restaurant),
        },
    )


@router.post("/items", dependencies=[Depends(verify_csrf)])
async def create_item(
    db: DbSession,
    user: AdminUser,
    category_id: Annotated[int, Form()],
    name_uz: Annotated[str, Form()],
    price: Annotated[float, Form()],
    name_ru: Annotated[str, Form()] = "",
    name_en: Annotated[str, Form()] = "",
    description_uz: Annotated[str, Form()] = "",
    description_ru: Annotated[str, Form()] = "",
    description_en: Annotated[str, Form()] = "",
    ingredients_uz: Annotated[str, Form()] = "",
    ingredients_ru: Annotated[str, Form()] = "",
    ingredients_en: Annotated[str, Form()] = "",
    allergens_uz: Annotated[str, Form()] = "",
    allergens_ru: Annotated[str, Form()] = "",
    allergens_en: Annotated[str, Form()] = "",
    prep_minutes: Annotated[int, Form()] = 0,
    sort_order: Annotated[int, Form()] = 0,
    is_popular: Annotated[bool, Form()] = False,
    is_special: Annotated[bool, Form()] = False,
    is_spicy: Annotated[bool, Form()] = False,
    is_vegetarian: Annotated[bool, Form()] = False,
    is_halal: Annotated[bool, Form()] = False,
    image: Annotated[UploadFile | None, File()] = None,
):
    category = owned_category(db, user, category_id)
    if not name_uz.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Taom nomi bo'sh bo'lmasin")
    check_item_limit(db, get_restaurant(db, user))

    item = MenuItem(
        restaurant_id=user.restaurant_id,
        category_id=category.id,
        name=i18n_field(name_uz, name_ru, name_en),
        description=i18n_field(description_uz, description_ru, description_en),
        ingredients=i18n_field(ingredients_uz, ingredients_ru, ingredients_en),
        allergens=i18n_field(allergens_uz, allergens_ru, allergens_en),
        price=max(price, 0),
        prep_minutes=max(prep_minutes, 0),
        sort_order=sort_order,
        is_popular=is_popular,
        is_special=is_special,
        is_spicy=is_spicy,
        is_vegetarian=is_vegetarian,
        is_halal=is_halal,
    )
    if image is not None and image.filename:
        item.image = await save_image(image, user.restaurant_id, max_width=1000)
    db.add(item)
    db.commit()
    return RedirectResponse("/admin/items", status.HTTP_303_SEE_OTHER)


@router.post("/items/{item_id}", dependencies=[Depends(verify_csrf)])
async def update_item(
    db: DbSession,
    user: AdminUser,
    item_id: int,
    category_id: Annotated[int, Form()],
    name_uz: Annotated[str, Form()],
    price: Annotated[float, Form()],
    name_ru: Annotated[str, Form()] = "",
    name_en: Annotated[str, Form()] = "",
    description_uz: Annotated[str, Form()] = "",
    description_ru: Annotated[str, Form()] = "",
    description_en: Annotated[str, Form()] = "",
    ingredients_uz: Annotated[str, Form()] = "",
    ingredients_ru: Annotated[str, Form()] = "",
    ingredients_en: Annotated[str, Form()] = "",
    allergens_uz: Annotated[str, Form()] = "",
    allergens_ru: Annotated[str, Form()] = "",
    allergens_en: Annotated[str, Form()] = "",
    prep_minutes: Annotated[int, Form()] = 0,
    sort_order: Annotated[int, Form()] = 0,
    is_popular: Annotated[bool, Form()] = False,
    is_special: Annotated[bool, Form()] = False,
    is_spicy: Annotated[bool, Form()] = False,
    is_vegetarian: Annotated[bool, Form()] = False,
    is_halal: Annotated[bool, Form()] = False,
    is_available: Annotated[bool, Form()] = False,
    remove_image: Annotated[bool, Form()] = False,
    image: Annotated[UploadFile | None, File()] = None,
):
    item = owned_item(db, user, item_id)
    category = owned_category(db, user, category_id)

    item.category_id = category.id
    item.name = i18n_field(name_uz, name_ru, name_en) or item.name
    item.description = i18n_field(description_uz, description_ru, description_en)
    item.ingredients = i18n_field(ingredients_uz, ingredients_ru, ingredients_en)
    item.allergens = i18n_field(allergens_uz, allergens_ru, allergens_en)
    item.price = max(price, 0)
    item.prep_minutes = max(prep_minutes, 0)
    item.sort_order = sort_order
    item.is_popular = is_popular
    item.is_special = is_special
    item.is_spicy = is_spicy
    item.is_vegetarian = is_vegetarian
    item.is_halal = is_halal
    item.is_available = is_available

    if image is not None and image.filename:
        old = item.image
        item.image = await save_image(image, user.restaurant_id, max_width=1000)
        delete_image(old)
    elif remove_image:
        delete_image(item.image)
        item.image = None

    db.commit()
    return RedirectResponse("/admin/items", status.HTTP_303_SEE_OTHER)


@router.post("/items/{item_id}/toggle", dependencies=[Depends(verify_csrf)])
def toggle_item(db: DbSession, user: AdminUser, item_id: int):
    item = owned_item(db, user, item_id)
    item.is_available = not item.is_available
    db.commit()
    return RedirectResponse("/admin/items", status.HTTP_303_SEE_OTHER)


@router.post("/items/{item_id}/delete", dependencies=[Depends(verify_csrf)])
def delete_item(db: DbSession, user: AdminUser, item_id: int):
    item = owned_item(db, user, item_id)
    delete_image(item.image)
    db.delete(item)
    db.commit()
    return RedirectResponse("/admin/items", status.HTTP_303_SEE_OTHER)


@router.get("/comments")
def comments_page(request: Request, db: DbSession, user: AdminUser):
    restaurant = get_restaurant(db, user)
    rows = db.scalars(
        select(ItemComment)
        .where(ItemComment.restaurant_id == restaurant.id)
        .options(selectinload(ItemComment.item))
        .order_by(ItemComment.is_approved, ItemComment.created_at.desc())
    ).all()
    return templates.TemplateResponse(
        request,
        "admin/comments.html",
        {
            "user": user,
            "restaurant": restaurant,
            "comments": rows,
            "pending": sum(1 for row in rows if not row.is_approved),
            "limits": limits_for(restaurant),
        },
    )


def owned_comment(db: Session, user: User, comment_id: int) -> ItemComment:
    comment = db.scalar(
        select(ItemComment).where(
            ItemComment.id == comment_id,
            ItemComment.restaurant_id == user.restaurant_id,
        )
    )
    if comment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Izoh topilmadi")
    return comment


@router.post("/comments/{comment_id}/approve", dependencies=[Depends(verify_csrf)])
def approve_comment(db: DbSession, user: AdminUser, comment_id: int):
    comment = owned_comment(db, user, comment_id)
    comment.is_approved = True
    db.commit()
    return RedirectResponse("/admin/comments", status.HTTP_303_SEE_OTHER)


@router.post("/comments/{comment_id}/delete", dependencies=[Depends(verify_csrf)])
def delete_comment(db: DbSession, user: AdminUser, comment_id: int):
    db.delete(owned_comment(db, user, comment_id))
    db.commit()
    return RedirectResponse("/admin/comments", status.HTTP_303_SEE_OTHER)


@router.get("/menu/print")
def print_menu(request: Request, db: DbSession, user: AdminUser):
    """Qog'ozga chiqarish uchun menyu.

    Server tomonda PDF yasamaymiz: brauzerning "Chop etish -> PDF saqlash"
    funksiyasi shu sahifadan aynan shunday natija beradi va qo'shimcha
    kutubxona talab qilmaydi.
    """
    restaurant = get_restaurant(db, user)
    if not limits_for(restaurant).printable:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Chop etish uchun menyu To'liq tarifda mavjud",
        )

    categories = db.scalars(
        select(Category)
        .where(Category.restaurant_id == restaurant.id, Category.is_active.is_(True))
        .options(selectinload(Category.items))
        .order_by(Category.sort_order, Category.id)
    ).all()
    sections = [
        (category, [item for item in category.items if item.is_available])
        for category in categories
    ]
    return templates.TemplateResponse(
        request,
        "admin/menu_print.html",
        {
            "restaurant": restaurant,
            "sections": [(c, items) for c, items in sections if items],
        },
    )


@router.get("/qr")
def qr_page(request: Request, db: DbSession, user: AdminUser):
    restaurant = get_restaurant(db, user)
    return templates.TemplateResponse(
        request,
        "admin/qr.html",
        {"user": user, "restaurant": restaurant, "menu_url": qr.menu_url(restaurant.slug)},
    )


@router.get("/qr.png")
def qr_png(db: DbSession, user: AdminUser):
    restaurant = get_restaurant(db, user)
    return Response(
        qr.png_bytes(restaurant.slug),
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{restaurant.slug}-qr.png"'},
    )


@router.get("/qr.svg")
def qr_svg(db: DbSession, user: AdminUser):
    restaurant = get_restaurant(db, user)
    return Response(
        qr.svg_bytes(restaurant.slug),
        media_type="image/svg+xml",
        headers={"Content-Disposition": f'attachment; filename="{restaurant.slug}-qr.svg"'},
    )
