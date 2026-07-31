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


def daily_menu_views(db: Session, restaurant_id: int, days: int = 30) -> list[tuple[date, int]]:
    """Oxirgi N kun uchun (sana, soni) — bo'sh kunlar ham nol bilan to'ldiriladi."""
    first = today() - timedelta(days=days - 1)
    rows = db.execute(
        select(MenuView.day, func.sum(MenuView.count))
        .where(
            MenuView.restaurant_id == restaurant_id,
            MenuView.item_id.is_(None),
            MenuView.day >= first,
        )
        .group_by(MenuView.day)
    ).all()

    counts = {row[0]: int(row[1] or 0) for row in rows}
    return [(first + timedelta(days=offset), counts.get(first + timedelta(days=offset), 0))
            for offset in range(days)]


def top_items(db: Session, restaurant_id: int, days: int = 30, limit: int = 10):
    """Eng ko'p ochilgan taomlar: [(MenuItem, soni), ...]"""
    first = today() - timedelta(days=days - 1)
    total = func.sum(MenuView.count).label("total")
    rows = db.execute(
        select(MenuItem, total)
        .join(MenuView, MenuView.item_id == MenuItem.id)
        .where(MenuView.restaurant_id == restaurant_id, MenuView.day >= first)
        .group_by(MenuItem.id)
        .order_by(total.desc())
        .limit(limit)
    ).all()
    return [(row[0], int(row[1] or 0)) for row in rows]


def total_views(db: Session, restaurant_id: int, days: int = 30) -> int:
    first = today() - timedelta(days=days - 1)
    result = db.scalar(
        select(func.sum(MenuView.count)).where(
            MenuView.restaurant_id == restaurant_id,
            MenuView.item_id.is_(None),
            MenuView.day >= first,
        )
    )
    return int(result or 0)
