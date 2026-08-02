from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Category,
    ItemComment,
    MenuItem,
    Plan,
    Restaurant,
    SubscriptionStatus,
    User,
    utcnow_naive,
)
from app.plans import LIMITS, limits_for, menu_is_live, refresh_status, trial_days_left
from app.security import hash_password, require_superadmin, verify_csrf
from app.services import comments as comment_service
from app.services import stats
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


# Ro'yxatni saralash. Kalit manzilga tushadi, shuning uchun qisqa.
SORTS = {
    "yangi": "Yangi qo'shilgan",
    "ochilish": "Ko'p ochilgan",
    "nom": "Nomi bo'yicha",
    "tugaydi": "Muddati yaqin",
}
STATUS_FILTERS = {
    "hammasi": "Hammasi",
    "sinov": "Sinovda",
    "faol": "To'lagan",
    "tugagan": "Muddati tugagan",
    "bloklangan": "Bloklangan",
}


@router.get("")
def dashboard(
    request: Request,
    db: DbSession,
    q: str = "",
    status_filter: str = "hammasi",
    sort: str = "yangi",
):
    restaurants = db.scalars(select(Restaurant)).all()
    # Holatni ro'yxat chizilishidan OLDIN yangilaymiz, aks holda muddati
    # tugagan restoran "sinovda" bo'lib ko'rinib, filtr ham yanglishardi
    for restaurant in restaurants:
        refresh_status(restaurant)
    db.commit()

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

    end = stats.today()
    month_start = end - timedelta(days=29)
    views = stats.views_by_restaurant(db, month_start, end)

    needle = q.strip().lower()
    if needle:
        restaurants = [
            r for r in restaurants
            if needle in r.name.lower() or needle in r.slug.lower()
        ]
    if status_filter in STATUS_FILTERS and status_filter != "hammasi":
        restaurants = [r for r in restaurants if _status_key(r) == status_filter]

    sort = sort if sort in SORTS else "yangi"
    orderings = {
        "yangi": lambda r: (r.created_at is None, r.created_at),
        "ochilish": lambda r: views.get(r.id, 0),
        "nom": lambda r: r.name.lower(),
        "tugaydi": lambda r: (_ends_at(r) is None, _ends_at(r)),
    }
    restaurants = sorted(restaurants, key=orderings[sort], reverse=sort in ("yangi", "ochilish"))

    pending_comments = db.scalar(
        select(func.count(ItemComment.id)).where(ItemComment.is_approved.is_(False))
    )
    menu_opens, item_opens = stats.platform_totals(db, month_start, end)

    return templates.TemplateResponse(
        request,
        "superadmin/dashboard.html",
        {
            "restaurants": restaurants,
            "item_counts": item_counts,
            "category_counts": category_counts,
            "views": views,
            "plans": list(Plan),
            "limits": LIMITS,
            "trial_days_left": trial_days_left,
            "status_key": _status_key,
            "ends_at": _ends_at,
            # filtr holati
            "q": q,
            "status_filter": status_filter if status_filter in STATUS_FILTERS else "hammasi",
            "sort": sort,
            "sorts": SORTS,
            "status_filters": STATUS_FILTERS,
            # platforma ko'rsatkichlari
            "totals": {
                "restaurants": len(db.scalars(select(Restaurant.id)).all()),
                "live": sum(1 for r in db.scalars(select(Restaurant)).all() if menu_is_live(r)),
                "menu_opens": menu_opens,
                "item_opens": item_opens,
                "pending_comments": int(pending_comments or 0),
            },
        },
    )


def _status_key(restaurant: Restaurant) -> str:
    """Ro'yxatdagi holat yorlig'i — filtr ham shu kalitlar bilan ishlaydi."""
    if not restaurant.is_active:
        return "bloklangan"
    if restaurant.subscription_status is SubscriptionStatus.expired:
        return "tugagan"
    if restaurant.subscription_status is SubscriptionStatus.trial:
        return "sinov"
    return "faol"


def _ends_at(restaurant: Restaurant):
    """Obuna qachon tugaydi — sinovda trial, to'laganda paid_until."""
    if restaurant.subscription_status is SubscriptionStatus.trial:
        return restaurant.trial_ends_at
    return restaurant.paid_until


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


@router.get("/restaurants/{restaurant_id}")
def restaurant_detail(
    request: Request,
    db: DbSession,
    restaurant_id: int,
    period: str = "oy",
    start: str | None = None,
    end: str | None = None,
):
    """Bitta restoranning to'liq ko'rinishi: statistika, obuna, xodimlar.

    Superadmin uchun tarif cheklovi qo'llanmaydi — bepul tarifdagi restoran
    ham to'liq tarixi bilan ko'rinadi, aks holda "nega bu mijoz ketdi" degan
    savolga javob topib bo'lmasdi.
    """
    restaurant = get_restaurant_or_404(db, restaurant_id)
    refresh_status(restaurant)
    db.commit()

    first, last, preset = stats.resolve_range(period, start, end, max_days=365 * 3)
    daily = stats.daily_series(db, restaurant.id, first, last)
    ranked = stats.top_items(db, restaurant.id, first, last, limit=15)

    users = db.scalars(
        select(User).where(User.restaurant_id == restaurant.id).order_by(User.id)
    ).all()
    pending = db.scalar(
        select(func.count(ItemComment.id)).where(
            ItemComment.restaurant_id == restaurant.id, ItemComment.is_approved.is_(False)
        )
    )

    return templates.TemplateResponse(
        request,
        "superadmin/restaurant_detail.html",
        {
            "restaurant": restaurant,
            "limits": limits_for(restaurant),
            "is_live": menu_is_live(restaurant),
            "status_key": _status_key(restaurant),
            "ends_at": _ends_at(restaurant),
            "trial_left": trial_days_left(restaurant),
            "users": users,
            "pending_comments": int(pending or 0),
            "presets": stats.PRESETS,
            "preset": preset,
            "start": first,
            "end": last,
            "daily_views": daily,
            "views_peak": max((count for _, count in daily), default=0),
            "views_total": stats.total_views(db, restaurant.id, first, last),
            "top_items": ranked,
            "ratings": comment_service.rating_summary(db, [i.id for i, _ in ranked]),
            "best_rated": comment_service.best_rated(db, restaurant.id, limit=10),
            "item_count": db.scalar(
                select(func.count(MenuItem.id)).where(MenuItem.restaurant_id == restaurant.id)
            ),
            "category_count": db.scalar(
                select(func.count(Category.id)).where(Category.restaurant_id == restaurant.id)
            ),
            "plans": list(Plan),
            "limits_by_plan": LIMITS,
        },
    )


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
