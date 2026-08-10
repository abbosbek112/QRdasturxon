"""Restoranni tizimga ulash: hisob yaratish va birinchi kunlarda yo'l ko'rsatish.

Ikki joyda ishlatiladi: superadmin qo'lda qo'shganda va restoran o'zi
ro'yxatdan o'tganda. Tekshiruvlar bitta joyda turishi uchun shu yerga ajratildi.
"""

from dataclasses import dataclass

from fastapi import HTTPException, status
from slugify import slugify
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Category, MenuItem, Restaurant, Role, User
from app.plans import start_trial
from app.security import hash_password

# Bu so'zlar marshrut sifatida ishlatilgan — slug bo'lib qolsa manzillar to'qnashadi
RESERVED_SLUGS = {
    "admin",
    "superadmin",
    "login",
    "logout",
    "signup",
    "static",
    "media",
    "healthz",
    "r",
    "api",
    "narxlar",
    "demo",
}

MIN_USERNAME_LENGTH = 3
MIN_PASSWORD_LENGTH = 8


class FieldError(HTTPException):
    """Forma xatosi va u QAYSI maydonga tegishli.

    Maydonsiz xato foydalanuvchini adashtiradi: "'admin' logini band" degan
    yozuv forma tepasida turganda, odam uni restoran nomiga tegishli deb
    o'ylashi mumkin — ayniqsa login maydonini brauzer o'zi to'ldirib qo'ygan
    va u unga qaramagan bo'lsa.
    """

    def __init__(self, message: str, field: str = ""):
        super().__init__(status.HTTP_400_BAD_REQUEST, message)
        self.field = field


def _bad(message: str, field: str = "") -> HTTPException:
    return FieldError(message, field)


def clean_slug(raw: str, db: Session, exclude_id: int | None = None) -> str:
    slug = slugify(raw)[:64]
    if not slug:
        raise _bad("Manzil (slug) noto'g'ri", "slug")
    if slug in RESERVED_SLUGS:
        raise _bad(f"'{slug}' band so'z, boshqasini tanlang", "slug")
    query = select(Restaurant.id).where(Restaurant.slug == slug)
    if exclude_id is not None:
        query = query.where(Restaurant.id != exclude_id)
    if db.scalar(query):
        raise _bad(f"'{slug}' allaqachon band", "slug")
    return slug


def create_restaurant_with_admin(
    db: Session,
    *,
    name: str,
    slug: str,
    username: str,
    password: str,
    email: str = "",
    phone: str = "",
    with_trial: bool = False,
) -> Restaurant:
    name = name.strip()
    if not name:
        raise _bad("Restoran nomi bo'sh bo'lmasin", "name")

    username = username.strip().lower()
    if len(username) < MIN_USERNAME_LENGTH:
        raise _bad(f"Login kamida {MIN_USERNAME_LENGTH} belgidan iborat bo'lsin", "username")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise _bad(f"Parol kamida {MIN_PASSWORD_LENGTH} belgidan iborat bo'lsin", "password")
    if db.scalar(select(User.id).where(User.username == username)):
        raise _bad(f"'{username}' logini band", "username")

    restaurant = Restaurant(
        name=name,
        slug=clean_slug(slug or name, db),
        phone=phone.strip() or None,
    )
    if with_trial:
        start_trial(restaurant)

    db.add(restaurant)
    db.flush()
    db.add(
        User(
            username=username,
            email=email.strip() or None,
            password_hash=hash_password(password),
            role=Role.restaurant_admin,
            restaurant_id=restaurant.id,
        )
    )
    db.commit()
    return restaurant


def create_waiter(db: Session, restaurant: Restaurant, username: str, password: str) -> User:
    """Zal xodimi uchun hisob.

    Egasidan farqi bitta: roli `waiter`, ya'ni u faqat buyurtmalar taxtasini
    ko'radi. Menyu, narx va sozlamalarga yo'li yo'q — shuning uchun egasi o'z
    parolini afitsantga berishi shart emas.

    Login butun tizimda yagona bo'lishi kerak, shuning uchun forma odatda
    restoran slug'i bilan boshlanadigan nom taklif qiladi.
    """
    username = username.strip().lower()
    if len(username) < MIN_USERNAME_LENGTH:
        raise _bad(f"Login kamida {MIN_USERNAME_LENGTH} belgidan iborat bo'lsin", "username")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise _bad(f"Parol kamida {MIN_PASSWORD_LENGTH} belgidan iborat bo'lsin", "password")
    if db.scalar(select(User.id).where(User.username == username)):
        raise _bad(f"'{username}' logini band", "username")

    user = User(
        username=username,
        password_hash=hash_password(password),
        role=Role.waiter,
        restaurant_id=restaurant.id,
    )
    db.add(user)
    db.commit()
    return user


@dataclass(frozen=True)
class Step:
    key: str
    title: str
    detail: str
    action_url: str
    action_label: str
    done: bool


def setup_steps(db: Session, restaurant: Restaurant) -> list[Step]:
    """Yangi restoran uchun qadamlar ro'yxati.

    Alohida ustun saqlanmaydi — har qadam bajarilgani ma'lumotning o'zidan
    aniqlanadi. Shuning uchun restoran bazani boshqa yo'l bilan to'ldirsa ham
    ro'yxat to'g'ri ko'rsatadi va "bajarilgan" bayrog'i haqiqatdan ajralib qolmaydi.
    """
    categories = db.scalar(
        select(func.count(Category.id)).where(Category.restaurant_id == restaurant.id)
    )
    items = db.scalar(
        select(func.count(MenuItem.id)).where(MenuItem.restaurant_id == restaurant.id)
    )

    return [
        Step(
            key="category",
            title="Kategoriya qo'shing",
            detail="Menyu bo'limlari: Issiq taomlar, Salatlar, Ichimliklar…",
            action_url="/admin/categories",
            action_label="Kategoriya qo'shish",
            done=bool(categories),
        ),
        Step(
            key="item",
            title="Birinchi taomni kiriting",
            detail="Nomi, narxi va rasmi. Qolganini keyin ham qo'shasiz.",
            action_url="/admin/items/new",
            action_label="Taom qo'shish",
            done=bool(items),
        ),
        Step(
            key="profile",
            title="Restoran ma'lumotlarini to'ldiring",
            detail="Ish vaqti va telefon — mijoz menyuning tepasida ko'radi.",
            action_url="/admin/settings",
            action_label="Sozlamalarga o'tish",
            done=bool(restaurant.working_hours and restaurant.phone),
        ),
    ]
