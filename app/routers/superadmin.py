from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from slugify import slugify
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Category, MenuItem, Restaurant, Role, User
from app.security import hash_password, require_superadmin, verify_csrf
from app.templating import templates

router = APIRouter(
    prefix="/superadmin",
    tags=["superadmin"],
    dependencies=[Depends(require_superadmin)],
)

DbSession = Annotated[Session, Depends(get_db)]

RESERVED_SLUGS = {"admin", "superadmin", "login", "logout", "static", "media", "healthz", "r", "api"}


def clean_slug(raw: str, db: Session, exclude_id: int | None = None) -> str:
    slug = slugify(raw)[:64]
    if not slug:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Manzil (slug) noto'g'ri")
    if slug in RESERVED_SLUGS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"'{slug}' band so'z, boshqasini tanlang")
    query = select(Restaurant.id).where(Restaurant.slug == slug)
    if exclude_id is not None:
        query = query.where(Restaurant.id != exclude_id)
    if db.scalar(query):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"'{slug}' allaqachon band")
    return slug


def get_restaurant_or_404(db: Session, restaurant_id: int) -> Restaurant:
    restaurant = db.get(Restaurant, restaurant_id)
    if restaurant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Restoran topilmadi")
    return restaurant


@router.get("")
def dashboard(request: Request, db: DbSession):
    restaurants = db.scalars(select(Restaurant).order_by(Restaurant.created_at.desc())).all()
    item_counts = dict(
        db.execute(
            select(MenuItem.restaurant_id, func.count(MenuItem.id)).group_by(MenuItem.restaurant_id)
        ).all()
    )
    category_counts = dict(
        db.execute(
            select(Category.restaurant_id, func.count(Category.id)).group_by(Category.restaurant_id)
        ).all()
    )
    return templates.TemplateResponse(
        request,
        "superadmin/dashboard.html",
        {
            "restaurants": restaurants,
            "item_counts": item_counts,
            "category_counts": category_counts,
        },
    )


@router.get("/restaurants/new")
def new_restaurant_form(request: Request):
    return templates.TemplateResponse(
        request, "superadmin/restaurant_form.html", {"restaurant": None}
    )


@router.post("/restaurants", dependencies=[Depends(verify_csrf)])
def create_restaurant(
    db: DbSession,
    name: Annotated[str, Form()],
    slug: Annotated[str, Form()],
    admin_username: Annotated[str, Form()],
    admin_password: Annotated[str, Form()],
    phone: Annotated[str, Form()] = "",
    admin_email: Annotated[str, Form()] = "",
):
    name = name.strip()
    if not name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Restoran nomi bo'sh bo'lmasin")

    username = admin_username.strip().lower()
    if len(username) < 3:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Login kamida 3 belgidan iborat bo'lsin")
    if len(admin_password) < 8:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Parol kamida 8 belgidan iborat bo'lsin")
    if db.scalar(select(User.id).where(User.username == username)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"'{username}' logini band")

    restaurant = Restaurant(name=name, slug=clean_slug(slug or name, db), phone=phone.strip() or None)
    db.add(restaurant)
    db.flush()
    db.add(
        User(
            username=username,
            email=admin_email.strip() or None,
            password_hash=hash_password(admin_password),
            role=Role.restaurant_admin,
            restaurant_id=restaurant.id,
        )
    )
    db.commit()
    return RedirectResponse("/superadmin", status.HTTP_303_SEE_OTHER)


@router.get("/restaurants/{restaurant_id}/edit")
def edit_restaurant_form(request: Request, db: DbSession, restaurant_id: int):
    return templates.TemplateResponse(
        request,
        "superadmin/restaurant_form.html",
        {"restaurant": get_restaurant_or_404(db, restaurant_id)},
    )


@router.post("/restaurants/{restaurant_id}", dependencies=[Depends(verify_csrf)])
def update_restaurant(
    db: DbSession,
    restaurant_id: int,
    name: Annotated[str, Form()],
    slug: Annotated[str, Form()],
    phone: Annotated[str, Form()] = "",
):
    restaurant = get_restaurant_or_404(db, restaurant_id)
    restaurant.name = name.strip() or restaurant.name
    restaurant.slug = clean_slug(slug or name, db, exclude_id=restaurant.id)
    restaurant.phone = phone.strip() or None
    db.commit()
    return RedirectResponse("/superadmin", status.HTTP_303_SEE_OTHER)


@router.post("/restaurants/{restaurant_id}/toggle", dependencies=[Depends(verify_csrf)])
def toggle_restaurant(db: DbSession, restaurant_id: int):
    restaurant = get_restaurant_or_404(db, restaurant_id)
    restaurant.is_active = not restaurant.is_active
    db.commit()
    return RedirectResponse("/superadmin", status.HTTP_303_SEE_OTHER)


@router.post("/restaurants/{restaurant_id}/delete", dependencies=[Depends(verify_csrf)])
def delete_restaurant(db: DbSession, restaurant_id: int):
    db.delete(get_restaurant_or_404(db, restaurant_id))
    db.commit()
    return RedirectResponse("/superadmin", status.HTTP_303_SEE_OTHER)


@router.get("/users")
def users_list(request: Request, db: DbSession):
    users = db.scalars(select(User).order_by(User.role, User.username)).all()
    return templates.TemplateResponse(request, "superadmin/users.html", {"users": users})


@router.post("/users/{user_id}/password", dependencies=[Depends(verify_csrf)])
def reset_password(db: DbSession, user_id: int, new_password: Annotated[str, Form()]):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Foydalanuvchi topilmadi")
    if len(new_password) < 8:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Parol kamida 8 belgidan iborat bo'lsin")
    user.password_hash = hash_password(new_password)
    db.commit()
    return RedirectResponse("/superadmin/users", status.HTTP_303_SEE_OTHER)


@router.post("/users/{user_id}/toggle", dependencies=[Depends(verify_csrf)])
def toggle_user(
    db: DbSession, user_id: int, current: Annotated[User, Depends(require_superadmin)]
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Foydalanuvchi topilmadi")
    if user.id == current.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "O'zingizni o'chira olmaysiz")
    user.is_active = not user.is_active
    db.commit()
    return RedirectResponse("/superadmin/users", status.HTTP_303_SEE_OTHER)
