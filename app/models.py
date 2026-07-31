from __future__ import annotations

import enum
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def utcnow_naive() -> datetime:
    """Vaqt mintaqasisiz UTC.

    SQLite mintaqa ma'lumotini saqlamaydi, shuning uchun mintaqali qiymat bilan
    taqqoslash u yerda jimgina noto'g'ri natija beradi. Vaqt bo'yicha taqqoslash
    qilinadigan joylarda ikkala bazada bir xil ishlashi uchun UTC'ni mintaqasiz
    saqlaymiz.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


# Ko'p tilli matnlar {"uz": ..., "ru": ..., "en": ...} ko'rinishida saqlanadi.
# Postgres'da JSONB — tezroq va keyinchalik indekslash mumkin; SQLite'da oddiy JSON.
I18nText = JSON().with_variant(JSONB, "postgresql")


class Role(str, enum.Enum):
    superadmin = "superadmin"
    restaurant_admin = "restaurant_admin"


class Plan(str, enum.Enum):
    free = "free"
    full = "full"


class SubscriptionStatus(str, enum.Enum):
    trial = "trial"  # sinov muddati ketyapti
    active = "active"  # to'langan
    expired = "expired"  # sinov tugadi yoki to'lov to'xtadi


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False), default=Role.restaurant_admin)
    restaurant_id: Mapped[int | None] = mapped_column(ForeignKey("restaurants.id", ondelete="CASCADE"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    restaurant: Mapped[Restaurant | None] = relationship(back_populates="users")


class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[dict] = mapped_column(I18nText, default=dict)
    logo: Mapped[str | None] = mapped_column(String(255))
    cover_image: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32))
    address: Mapped[dict] = mapped_column(I18nText, default=dict)
    working_hours: Mapped[str | None] = mapped_column(String(120))
    instagram: Mapped[str | None] = mapped_column(String(255))
    telegram: Mapped[str | None] = mapped_column(String(255))
    # Mijoz menyuni ochganda Wi-Fi parolini ham shu yerdan ko'radi
    wifi_name: Mapped[str | None] = mapped_column(String(64))
    wifi_password: Mapped[str | None] = mapped_column(String(64))
    theme: Mapped[str] = mapped_column(String(32), default="zamonaviy")
    theme_color: Mapped[str] = mapped_column(String(9), default="#c2410c")
    currency: Mapped[str] = mapped_column(String(8), default="so'm")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    plan: Mapped[Plan] = mapped_column(Enum(Plan, native_enum=False), default=Plan.free)
    subscription_status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, native_enum=False), default=SubscriptionStatus.trial
    )
    # Mintaqasiz UTC — vaqt bo'yicha taqqoslanadi, utcnow_naive() izohiga qarang
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime)
    paid_until: Mapped[datetime | None] = mapped_column(DateTime)

    users: Mapped[list[User]] = relationship(back_populates="restaurant", cascade="all, delete-orphan")
    categories: Mapped[list[Category]] = relationship(
        back_populates="restaurant",
        cascade="all, delete-orphan",
        order_by="Category.sort_order",
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[dict] = mapped_column(I18nText, default=dict)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    restaurant: Mapped[Restaurant] = relationship(back_populates="categories")
    items: Mapped[list[MenuItem]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="MenuItem.sort_order",
    )


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), index=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[dict] = mapped_column(I18nText, default=dict)
    description: Mapped[dict] = mapped_column(I18nText, default=dict)
    ingredients: Mapped[dict] = mapped_column(I18nText, default=dict)
    allergens: Mapped[dict] = mapped_column(I18nText, default=dict)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    # Taxminiy tayyorlanish vaqti, daqiqada. 0 = ko'rsatilmaydi
    prep_minutes: Mapped[int] = mapped_column(Integer, default=0)
    image: Mapped[str | None] = mapped_column(String(255))
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    is_popular: Mapped[bool] = mapped_column(Boolean, default=False)
    # "Bugungi taklif" bo'limiga chiqadi — menyuning eng tepasida
    is_special: Mapped[bool] = mapped_column(Boolean, default=False)
    is_spicy: Mapped[bool] = mapped_column(Boolean, default=False)
    is_vegetarian: Mapped[bool] = mapped_column(Boolean, default=False)
    is_halal: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    category: Mapped[Category] = relationship(back_populates="items")


class ItemComment(Base):
    """Mijozning taomga qoldirgan izohi.

    Restoran tasdiqlagandan keyingina menyuda ko'rinadi. Bu restoranning asosiy
    qo'rquvini yopadi, lekin shuni bilib turaylik: moderatsiyadan o'tgan izoh
    haqiqiy sharh emas, tanlangan fikr. Uni "mijozlar fikri" deb sotmaslik kerak.

    `ip` faqat spamdan himoya uchun saqlanadi, hech qayerda ko'rsatilmaydi.
    """

    __tablename__ = "item_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), index=True
    )
    item_id: Mapped[int] = mapped_column(
        ForeignKey("menu_items.id", ondelete="CASCADE"), index=True
    )
    author_name: Mapped[str] = mapped_column(String(64))
    body: Mapped[str] = mapped_column(String(500))
    ip: Mapped[str] = mapped_column(String(64), index=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)

    item: Mapped[MenuItem] = relationship()


class LoginAttempt(Base):
    """Muvaffaqiyatsiz login urinishlari.

    Xotirada emas, bazada saqlanadi — shunda server qayta ishga tushganda ham
    cheklov kuchida qoladi va bir nechta ishchi jarayon bitta hisobni ko'radi.
    """

    __tablename__ = "login_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    ip: Mapped[str] = mapped_column(String(64), index=True)
    # Mintaqasiz UTC — sabab uchun utcnow_naive() izohiga qarang
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow_naive, index=True
    )


class MenuView(Base):
    """Menyu va taomlar ochilishining kunlik yig'masi.

    Har ochilishga alohida qator emas, kuniga bitta qator — jadval kichik qoladi.
    Shaxsiy ma'lumot saqlanmaydi: na IP, na cookie, faqat sonlar.
    `item_id` bo'sh bo'lsa — bu menyu sahifasining ochilishi.
    """

    __tablename__ = "menu_views"
    __table_args__ = (
        UniqueConstraint("restaurant_id", "item_id", "day", name="uq_menu_views_day"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), index=True
    )
    item_id: Mapped[int | None] = mapped_column(
        ForeignKey("menu_items.id", ondelete="CASCADE")
    )
    day: Mapped[date] = mapped_column(Date, index=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
