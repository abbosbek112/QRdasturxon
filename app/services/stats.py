"""Menyu ko'rishlarining kunlik hisobi.

**Bazada shaxsiy ma'lumot saqlanmaydi** — na IP, na qurilma haqida narsa,
faqat "shu kuni shuncha marta ochildi" degan son.

Takroriy ochilishlar imzolangan sessiya cookie'si yordamida ajratiladi
(`viewed()` ga qarang). Cookie brauzerda yashaydi va u yerda ham faqat
qisqa kalitlar bilan vaqt turadi — bazaga hech narsa qo'shilmaydi.

Busiz ko'rsatkich yolg'on chiqardi: mijoz tilni uch marta almashtirsa
"menyu 4 marta ochildi" deb yozilardi.

Sanalar UTC bo'yicha — restoran vaqt mintaqasi hisobga olinmaydi.
"""

import logging
import time
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import MenuItem, MenuView

log = logging.getLogger(__name__)


def today() -> date:
    return datetime.now(timezone.utc).date()


# Bir mijozning bitta tashrifi shuncha vaqt davomida BITTA ochilish sanaladi.
# Yarim soat — odam kafeda o'tirib menyuni bir necha marta ochishi mumkin
# bo'lgan oraliq; ertaga qaytib kelsa yangi tashrif deb hisoblanadi.
VIEW_WINDOW_SECONDS = 30 * 60
# Sessiya cookie'si har so'rov bilan yuriladi — uni shishirib yubormaymiz
MAX_SEEN = 30


def viewed(seen: dict, key: str, now: int | None = None) -> tuple[bool, dict]:
    """(hisoblansinmi, yangilangan ro'yxat).

    `key` — "m3" (3-restoran menyusi) yoki "i42" (42-taom). Shu kalit oxirgi
    yarim soatda uchragan bo'lsa ochilish TAKRORIY deb hisoblanadi va sanoq
    oshmaydi. Vaqt esa yangilanadi: kafede uzoq o'tirgan mijoz 31-daqiqada
    ikkinchi marta sanalib qolmasin.
    """
    if now is None:
        now = int(time.time())

    fresh = {
        name: at
        for name, at in (seen or {}).items()
        if isinstance(at, int) and now - at < VIEW_WINDOW_SECONDS
    }
    first_time = key not in fresh
    fresh[key] = now

    if len(fresh) > MAX_SEEN:
        newest = sorted(fresh.items(), key=lambda pair: pair[1], reverse=True)
        fresh = dict(newest[:MAX_SEEN])
    return first_time, fresh


def record_view(db: Session, restaurant_id: int, item_id: int | None = None) -> None:
    """Bugungi hisobni bittaga oshiradi.

    Statistika hech qachon sahifani buzmasligi kerak — shuning uchun har qanday
    baza xatosi yutiladi va faqat logga yoziladi.
    """
    try:
        _bump(db, restaurant_id, item_id)
    except SQLAlchemyError:
        db.rollback()
        log.warning("Ko'rishni yozib bo'lmadi", exc_info=True)


def _bump(db: Session, restaurant_id: int, item_id: int | None) -> None:
    """Bugungi qatorni bittaga oshiradi — bitta ATOMIK amal bilan.

    Ilgari bu ikki qadam edi: avval UPDATE, qator topilmasa INSERT. Bir
    vaqtda kelgan mijozlarda u ikki xil buzilardi:

    * menyu qatori (item_id NULL) hech qanday cheklov bilan himoyalanmagan
      edi, ya'ni ikkala so'rov ham qator qo'shib qo'yardi. Shundan keyin
      keyingi HAR BIR ochilish ikkalasini ham oshirib, son ikki barobar
      shishardi;
    * taom qatorida cheklov bor edi va ikkinchi so'rov `IntegrityError`
      olardi. Xato yuqorida yutilgani uchun o'sha ochilish YO'QOLARDI —
      bir vaqtda bitta taomni ochgan 10 mijozdan 1 tasi sanalardi.

    `INSERT ... ON CONFLICT DO UPDATE` ikkalasini ham yopadi: bazaning o'zi
    qatorni qulflab, sonni oshiradi. Ikki dialekt uchun ham bir xil ishlaydi.
    """
    day = today()
    make_insert = (
        pg_insert if db.get_bind().dialect.name == "postgresql" else sqlite_insert
    )
    statement = make_insert(MenuView).values(
        restaurant_id=restaurant_id, item_id=item_id, day=day, count=1
    )

    # Qaysi qisman indeksga tegishli ekanini aniq ko'rsatamiz — `models.py`
    # dagi `uq_menu_views_menu` va `uq_menu_views_item` bilan bir xil shart
    if item_id is None:
        statement = statement.on_conflict_do_update(
            index_elements=["restaurant_id", "day"],
            index_where=text("item_id IS NULL"),
            set_={"count": MenuView.__table__.c.count + 1},
        )
    else:
        statement = statement.on_conflict_do_update(
            index_elements=["restaurant_id", "item_id", "day"],
            index_where=text("item_id IS NOT NULL"),
            set_={"count": MenuView.__table__.c.count + 1},
        )

    db.execute(statement)
    db.commit()


# --- muddat oralig'i --------------------------------------------------------
#
# Hamma so'rov (boshlanish, tugash) juftligi bilan ishlaydi, "oxirgi N kun"
# bilan emas. Sabab: foydalanuvchi ixtiyoriy oraliq tanlashi mumkin, "N kun"
# esa faqat bugundan orqaga sanaydi va o'tgan oyni ko'rsata olmaydi.
# Ikkala chegara ham oraliqqa KIRADI.


def clamp_range(start: date, end: date, max_days: int) -> tuple[date, date]:
    """Oraliqni tartibga soladi va tarif ruxsat etgan chuqurlikka qisqartiradi.

    Bepul tarifda 7 kunlik tarix bor — shuning uchun bir yillik oraliq
    so'ralsa ham u oxirgi 7 kunga kesiladi. Chegarani shu yerda qo'yamiz,
    aks holda har bir sahifa uni o'zicha tekshirishi kerak bo'lardi.
    """
    if start > end:
        start, end = end, start
    last = today()
    if end > last:
        end = last
    earliest = last - timedelta(days=max_days - 1)
    if start < earliest:
        start = earliest
    if start > end:
        start = end
    return start, end


# Sahifadagi tayyor tugmalar. Kalit manzilga tushadi, shuning uchun qisqa.
PRESETS: dict[str, tuple[str, int]] = {
    "kun": ("Bugun", 1),
    "hafta": ("7 kun", 7),
    "oy": ("30 kun", 30),
    "yil": ("365 kun", 365),
}
DEFAULT_PRESET = "oy"


def resolve_range(
    period: str | None, start_raw: str | None, end_raw: str | None, max_days: int
) -> tuple[date, date, str]:
    """Manzildagi parametrlarni (boshlanish, tugash, tanlangan tugma) ga o'giradi.

    Sana foydalanuvchidan keladi — noto'g'ri yozilgani xato bermaydi, oddiy
    30 kunga qaytadi. Statistika sahifasi buzilib turgandan ko'ra taxminiy
    oraliq ko'rsatgani yaxshiroq.
    """
    if period == "custom":
        try:
            start = date.fromisoformat(start_raw or "")
            end = date.fromisoformat(end_raw or "")
        except ValueError:
            period = DEFAULT_PRESET
        else:
            return (*clamp_range(start, end, max_days), "custom")

    key = period if period in PRESETS else DEFAULT_PRESET
    span = PRESETS[key][1]
    end = today()
    return (*clamp_range(end - timedelta(days=span - 1), end, max_days), key)


def daily_series(db: Session, restaurant_id: int, start: date, end: date) -> list[tuple[date, int]]:
    """Oraliqdagi har bir kun uchun (sana, soni). Bo'sh kunlar nol bilan to'ladi."""
    rows = db.execute(
        select(MenuView.day, func.sum(MenuView.count))
        .where(
            MenuView.restaurant_id == restaurant_id,
            MenuView.item_id.is_(None),
            MenuView.day >= start,
            MenuView.day <= end,
        )
        .group_by(MenuView.day)
    ).all()

    counts = {row[0]: int(row[1] or 0) for row in rows}
    span = (end - start).days + 1
    return [(start + timedelta(days=offset), counts.get(start + timedelta(days=offset), 0))
            for offset in range(span)]


def top_items(db: Session, restaurant_id: int, start: date, end: date, limit: int = 10):
    """Oraliqda eng ko'p ochilgan taomlar: [(MenuItem, soni), ...]"""
    total = func.sum(MenuView.count).label("total")
    rows = db.execute(
        select(MenuItem, total)
        .join(MenuView, MenuView.item_id == MenuItem.id)
        .where(
            MenuView.restaurant_id == restaurant_id,
            MenuView.day >= start,
            MenuView.day <= end,
        )
        .group_by(MenuItem.id)
        .order_by(total.desc())
        .limit(limit)
    ).all()
    return [(row[0], int(row[1] or 0)) for row in rows]


def total_views(db: Session, restaurant_id: int, start: date, end: date) -> int:
    result = db.scalar(
        select(func.sum(MenuView.count)).where(
            MenuView.restaurant_id == restaurant_id,
            MenuView.item_id.is_(None),
            MenuView.day >= start,
            MenuView.day <= end,
        )
    )
    return int(result or 0)


def platform_totals(db: Session, start: date, end: date) -> tuple[int, int]:
    """Butun platforma bo'yicha (menyu ochilishi, taom ochilishi).

    Superadmin uchun: bitta restoran emas, hammasi birga.
    """
    menu = db.scalar(
        select(func.sum(MenuView.count)).where(
            MenuView.item_id.is_(None), MenuView.day >= start, MenuView.day <= end
        )
    )
    items = db.scalar(
        select(func.sum(MenuView.count)).where(
            MenuView.item_id.is_not(None), MenuView.day >= start, MenuView.day <= end
        )
    )
    return int(menu or 0), int(items or 0)


def views_by_restaurant(db: Session, start: date, end: date) -> dict[int, int]:
    """Restoran id → oraliqdagi menyu ochilishi soni."""
    rows = db.execute(
        select(MenuView.restaurant_id, func.sum(MenuView.count))
        .where(MenuView.item_id.is_(None), MenuView.day >= start, MenuView.day <= end)
        .group_by(MenuView.restaurant_id)
    ).all()
    return {row[0]: int(row[1] or 0) for row in rows}
