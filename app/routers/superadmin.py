from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Category,
    MenuItem,
    Plan,
    Restaurant,
    SubscriptionStatus,
    User,
    utcnow_naive,
)
from app.plans import LIMITS, refresh_status, trial_days_left
from app.security import hash_password, require_superadmin, verify_csrf
from app.services.onboarding import clean_slug, create_restaurant_with_admin
from app.templating import templates

router = APIRouter(
    prefix="/superadmin",
    tags=["superadmin"],
    dependencies=[Depends(require_superadmin)],
)

DbSession = Annotated[Session, Depends(get_db)]

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
    for restaurant in restaurants:
        refresh_status(restaurant)
    db.commit()

    return templates.TemplateResponse(
        request,
        "superadmin/dashboard.html",
        {
            "restaurants": restaurants,
            "item_counts": item_counts,
            "category_counts": category_counts,
            "plans": list(Plan),
            "limits": LIMITS,
            "trial_days_left": trial_days_left,
        },
    )


@router.post("/restaurants/{restaurant_id}/plan", dependencies=[Depends(verify_csrf)])
def set_plan(
    db: DbSession,
    restaurant_id: int,
    plan: Annotated[str, Form()],
    years: Annotated[int, Form()] = 1,
):
    """Tarifni qo'lda o'zgartirish.

    To'lov tizimi ulanmagunicha pul qo'lda qabul qilinadi, superadmin esa shu
    yerdan obunani uzaytiradi. Muddat mavjud `paid_until` ustiga qo'shiladi —
    erta to'lagan restoran kunini yo'qotmasin.
    """
    restaurant = get_restaurant_or_404(db, restaurant_id)
    try:
        restaurant.plan = Plan(plan)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Bunday tarif yo'q")

    if restaurant.plan is Plan.free:
        restaurant.subscription_status = SubscriptionStatus.active
        restaurant.paid_until = None
    else:
        years = max(1, min(years, 5))
        start = max(restaurant.paid_until or utcnow_naive(), utcnow_naive())
        restaurant.paid_until = start + timedelta(days=365 * years)
        restaurant.subscription_status = SubscriptionStatus.active

    db.commit()
    return RedirectResponse("/superadmin", status.HTTP_303_SEE_OTHER)


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
    create_restaurant_with_admin(
        db,
        name=name,
        slug=slug,
        username=admin_username,
        password=admin_password,
        email=admin_email,
        phone=phone,
    )
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
