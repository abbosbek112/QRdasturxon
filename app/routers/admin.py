from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Category, MenuItem, Restaurant, User
from app.security import require_restaurant_admin, verify_csrf
from app.services import qr
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
    return restaurant


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
            "restaurant": get_restaurant(db, user),
            "categories": categories,
            "item": None,
        },
    )


@router.get("/items/{item_id}/edit")
def edit_item_form(request: Request, db: DbSession, user: AdminUser, item_id: int):
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
            "restaurant": get_restaurant(db, user),
            "categories": categories,
            "item": owned_item(db, user, item_id),
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
    sort_order: Annotated[int, Form()] = 0,
    is_popular: Annotated[bool, Form()] = False,
    image: Annotated[UploadFile | None, File()] = None,
):
    category = owned_category(db, user, category_id)
    if not name_uz.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Taom nomi bo'sh bo'lmasin")

    item = MenuItem(
        restaurant_id=user.restaurant_id,
        category_id=category.id,
        name=i18n_field(name_uz, name_ru, name_en),
        description=i18n_field(description_uz, description_ru, description_en),
        price=max(price, 0),
        sort_order=sort_order,
        is_popular=is_popular,
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
    sort_order: Annotated[int, Form()] = 0,
    is_popular: Annotated[bool, Form()] = False,
    is_available: Annotated[bool, Form()] = False,
    remove_image: Annotated[bool, Form()] = False,
    image: Annotated[UploadFile | None, File()] = None,
):
    item = owned_item(db, user, item_id)
    category = owned_category(db, user, category_id)

    item.category_id = category.id
    item.name = i18n_field(name_uz, name_ru, name_en) or item.name
    item.description = i18n_field(description_uz, description_ru, description_en)
    item.price = max(price, 0)
    item.sort_order = sort_order
    item.is_popular = is_popular
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
