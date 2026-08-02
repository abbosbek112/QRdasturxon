"""Menyu ko'rishlarining kunlik hisobi.

Shaxsiy ma'lumot saqlanmaydi — na IP, na cookie, na qurilma haqida narsa.
Faqat "shu kuni shuncha marta ochildi" degan son. Shuning uchun bu ko'rsatkich
"necha kishi" emas, "necha marta ochildi" deb ataladi.

Sanalar UTC bo'yicha — restoran vaqt mintaqasi hisobga olinmaydi.
"""

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import MenuItem, MenuView

log = logging.getLogger(__name__)


def today() -> date:
    return datetime.now(timezone.utc).date()


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
    day = today()
    match = [MenuView.restaurant_id == restaurant_id, MenuView.day == day]
    match.append(MenuView.item_id.is_(None) if item_id is None else MenuView.item_id == item_id)

    result = db.execute(
        update(MenuView).where(*match).values(count=MenuView.count + 1)
    )
    if result.rowcount == 0:
        db.add(MenuView(restaurant_id=restaurant_id, item_id=item_id, day=day, count=1))
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
