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
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    UniqueConstraint,
    text,
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
    # Zal xodimi: faqat buyurtmalar taxtasini ko'radi. Egasining parolini
    # afitsantga berish kerak emasligi uchun bor — aks holda u menyu narxlarini
    # ham tahrirlay olardi.
    waiter = "waiter"


class Plan(str, enum.Enum):
    free = "free"
    full = "full"


class SubscriptionStatus(str, enum.Enum):
    trial = "trial"  # sinov muddati ketyapti
    active = "active"  # to'langan
    expired = "expired"  # sinov tugadi yoki to'lov to'xtadi


class TableKind(str, enum.Enum):
    """O'tirish joyining turi.

    Restoranda faqat stol bo'lmaydi: alohida xona, divanli burchak, VIP
    xona ham bor. Tur mijoz ko'radigan yozuvni ("7-stol" yoki "VIP 2") va
    chop etiladigan kartochkani belgilaydi.
    """

    stol = "stol"
    xona = "xona"
    divan = "divan"
    vip = "vip"


class OrderStatus(str, enum.Enum):
    new = "new"  # afitsant hali ko'rmagan
    accepted = "accepted"  # qabul qilindi, tayyorlanmoqda
    served = "served"  # berildi — yopiq
    cancelled = "cancelled"  # rad etildi — yopiq

    @property
    def is_open(self) -> bool:
        return self in (OrderStatus.new, OrderStatus.accepted)


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

    # Stoldan buyurtma qabul qilinadimi. Standart — yo'q: ko'p kafe faqat
    # menyu uchun keladi va u yerda javobgar odam bo'lmasa buyurtma javobsiz
    # qolib, mijozda yomon taassurot qoldiradi.
    orders_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    # QR skanerlangandan keyin necha daqiqa buyurtma berish mumkin. 0 = cheksiz.
    order_window_minutes: Mapped[int] = mapped_column(Integer, default=30)

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
    # 1-5 yulduz. 0 = baho qo'yilmagan (eski izohlar shunday qoladi) va
    # o'rtachani hisoblashda bunday izohlar umuman qatnashmaydi.
    rating: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)

    item: Mapped[MenuItem] = relationship()


class Zone(Base):
    """Zaldagi bo'lim: "Asosiy zal", "VIP xonalar", "Terasa".

    Afitsantlar aynan shu birlik bo'yicha bo'linadi. Kimdir kasal bo'lib
    qolsa egasi bitta zonani boshqasiga o'tkazadi — yigirmata stolni
    birma-bir qayta belgilamaydi.
    """

    __tablename__ = "zones"
    __table_args__ = (UniqueConstraint("restaurant_id", "name", name="uq_zones_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(64))
    # Qavat bo'limning O'ZIDA turadi, stolda emas: bitta bo'lim ikki qavatga
    # bo'linib ketmaydi, ya'ni bu tabiiy joy va uchinchi daraja qo'shilmaydi.
    floor: Mapped[int] = mapped_column(Integer, default=1)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)

    tables: Mapped[list[Table]] = relationship(back_populates="zone")


class Table(Base):
    """Zaldagi bitta o'tirish joyi va uning QR kodi.

    `code` — manzilga tushadigan taxmin qilib bo'lmaydigan kalit. Ataylab stol
    raqami emas: `/t/7` bo'lganida uydagi odam raqamni terib kirar va restoran
    tashqarisidan buyurtma bera olardi.
    """

    __tablename__ = "tables"
    __table_args__ = (
        UniqueConstraint("restaurant_id", "label", name="uq_tables_label"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), index=True
    )
    # Zona o'chirilsa stol qolaveradi, faqat bo'limsiz bo'lib qoladi —
    # chop etilgan QR kodi shu bilan omon qoladi
    zone_id: Mapped[int | None] = mapped_column(
        ForeignKey("zones.id", ondelete="SET NULL"), index=True
    )
    # Egasi yozgani: "7", "VIP-2", "Terasa 3"
    label: Mapped[str] = mapped_column(String(32))
    kind: Mapped[TableKind] = mapped_column(
        Enum(TableKind, native_enum=False), default=TableKind.stol
    )
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)

    zone: Mapped[Zone | None] = relationship(back_populates="tables")


class WaiterZone(Base):
    """Afitsant qaysi bo'limga javobgar.

    Alohida jadval, chunki bir afitsant bir necha zonani olishi mumkin va
    bir zonada bir necha afitsant ishlashi mumkin (gavjum kunda).
    """

    __tablename__ = "waiter_zones"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    zone_id: Mapped[int] = mapped_column(
        ForeignKey("zones.id", ondelete="CASCADE"), primary_key=True
    )


class WaiterTable(Base):
    """Alohida stol biriktirish — zonadan tashqari qo'shimcha.

    Zona asosiy birlik, lekin ba'zan bitta VIP xona alohida odamga
    biriktiriladi va u zonaga to'g'ri kelmaydi.
    """

    __tablename__ = "waiter_tables"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    table_id: Mapped[int] = mapped_column(
        ForeignKey("tables.id", ondelete="CASCADE"), primary_key=True
    )


class Order(Base):
    """Stoldan kelgan buyurtma.

    Bu to'lov emas, XABAR: restoranda o'z POS tizimi bor va biz unga tegmaymiz.
    Buyurtma afitsantga "7-stol nima so'radi" degan ma'lumotni yetkazadi,
    xolos. Shuning uchun u `new` holatida turadi va odam qabul qilmaguncha
    hech qayerga ketmaydi — tashqaridan kelgan soxta buyurtma aynan shu
    yerda to'xtaydi.
    """

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), index=True
    )
    # Stol o'chirilsa buyurtma tarixi qolsin — shuning uchun SET NULL
    table_id: Mapped[int | None] = mapped_column(
        ForeignKey("tables.id", ondelete="SET NULL")
    )
    # Stol nomining NUSXASI: stol o'chirilgandan keyin ham "7" ko'rinib tursin
    table_label: Mapped[str] = mapped_column(String(32))
    # Turi ham nusxa — taxtada "7-stol" va "VIP 2" bir xil ko'rinmasin
    table_kind: Mapped[str] = mapped_column(String(16), default="stol")
    # Mijoz o'z buyurtmasini shu kod bilan kuzatadi
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, native_enum=False), default=OrderStatus.new, index=True
    )
    note: Mapped[str | None] = mapped_column(String(280))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow_naive, index=True
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)

    lines: Mapped[list[OrderLine]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderLine.id"
    )


class OrderLine(Base):
    """Buyurtmadagi bitta qator.

    Nom va narx NUSXA bo'lib saqlanadi. Mahsulotning butun va'dasi "narxni bir
    joyda o'zgartirasiz" — agar buyurtma o'sha paytdagi narxni muzlatmasa,
    kechqurun narx ko'tarilganda ertalabki buyurtmalar summasi o'zgarib ketardi.
    """

    __tablename__ = "order_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    item_id: Mapped[int | None] = mapped_column(
        ForeignKey("menu_items.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(120))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    order: Mapped[Order] = relationship(back_populates="lines")

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity


class PushSubscription(Base):
    """Afitsant qurilmasining bildirishnoma obunasi.

    Bitta xodimning bir nechta qurilmasi bo'lishi mumkin — har biri alohida
    yozuv. `endpoint` brauzer bergan manzil va u yagona: bir qurilma ikki
    marta obuna bo'lsa yozuv yangilanadi, ko'paymaydi.

    `p256dh` va `auth` — xabarni shifrlash kalitlari. Biz MAZMUNSIZ push
    yuboramiz, ya'ni hozir ular ishlatilmaydi; keyinchalik mazmun kerak
    bo'lsa qayta obuna qildirmaslik uchun saqlab qo'yiladi.
    """

    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    endpoint: Mapped[str] = mapped_column(String(512), unique=True)
    p256dh: Mapped[str] = mapped_column(String(255))
    auth: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)

    user: Mapped[User] = relationship()


class ApiToken(Base):
    """Afitsant ilovasining kirish kaliti.

    JWT emas, bazadagi token — ataylab. Sabab bekor qilish: egasi afitsantni
    bloklaganda yoki hisobini o'chirganda kalit O'SHA ZAHOTI ishlamay qolishi
    kerak. JWT muddati tugagunicha amal qilaverardi va ishdan bo'shagan odam
    telefonida buyurtmalarni ko'rib turardi.

    Xesh sha256, argon2 emas: token — 32 tasodifiy bayt, ya'ni 256 bit
    entropiya. Bu yerda taxmin qilinadigan narsa yo'q, argon2 esa har bir
    so'rovga ~50 ms qo'shardi.
    """

    __tablename__ = "api_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # Qurilma nomi — egasi qaysi telefon ekanini ko'rsin
    label: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime)

    user: Mapped[User] = relationship()


class AppDevice(Base):
    """Ilova o'rnatilgan qurilma — bildirishnoma uchun.

    `PushSubscription` dan alohida: u brauzer obunasi (Web Push), bu esa
    Expo tokeni. Token shakli ham, yuborish yo'li ham boshqa, shuning uchun
    bitta jadvalga tiqishtirish faqat chalkashtirardi.
    """

    __tablename__ = "app_devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    expo_token: Mapped[str] = mapped_column(String(255), unique=True)
    platform: Mapped[str] = mapped_column(String(16), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)

    user: Mapped[User] = relationship()


class LoginAttempt(Base):
    """IP bo'yicha cheklanadigan urinishlar: login va ro'yxatdan o'tish.

    Xotirada emas, bazada saqlanadi — shunda server qayta ishga tushganda ham
    cheklov kuchida qoladi va bir nechta ishchi jarayon bitta hisobni ko'radi.
    """

    __tablename__ = "login_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    ip: Mapped[str] = mapped_column(String(64), index=True)
    # Turini ajratish shart. Muvaffaqiyatli login o'z IP'sining yozuvlarini
    # tozalaydi — agar signup ham shu yerda aralash yotsa, hujumchi chegaraga
    # yetgach bitta login qilib hisoblagichni nolga tushirib olardi.
    kind: Mapped[str] = mapped_column(String(16), default="login", index=True)
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
    # Ikkita QISMAN indeks, bitta oddiy cheklov emas. Sabab: SQL'da
    # NULL != NULL, ya'ni `UNIQUE(restaurant_id, item_id, day)` menyu
    # qatorini (item_id NULL) umuman himoya qilmaydi. Bir vaqtda kelgan
    # ikki mijoz ikkita qator yasab qo'yardi va shundan keyin HAR BIR
    # ochilish ikkalasini ham oshirib, son ikki barobar shishardi.
    __table_args__ = (
        Index(
            "uq_menu_views_menu",
            "restaurant_id",
            "day",
            unique=True,
            sqlite_where=text("item_id IS NULL"),
            postgresql_where=text("item_id IS NULL"),
        ),
        Index(
            "uq_menu_views_item",
            "restaurant_id",
            "item_id",
            "day",
            unique=True,
            sqlite_where=text("item_id IS NOT NULL"),
            postgresql_where=text("item_id IS NOT NULL"),
        ),
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
