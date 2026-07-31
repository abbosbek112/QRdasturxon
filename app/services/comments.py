"""Taomlarga qoldiriladigan izohlar.

Izoh restoran tasdiqlagandan keyingina menyuda ko'rinadi. Spamdan himoya:
bitta IP bitta taomga kuniga bitta izoh — bu login cheklovi bilan bir xil
yondashuv (`app/security.py`), ya'ni hisob bazada yuritiladi.
"""

from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ItemComment, MenuItem, utcnow_naive

MAX_NAME = 64
MAX_BODY = 500
MIN_BODY = 3
COOLDOWN_HOURS = 24


def visible_for(db: Session, item_id: int) -> list[ItemComment]:
    return list(
        db.scalars(
            select(ItemComment)
            .where(ItemComment.item_id == item_id, ItemComment.is_approved.is_(True))
            .order_by(ItemComment.created_at.desc())
        ).all()
    )


def counts_by_item(db: Session, item_ids: list[int]) -> dict[int, int]:
    if not item_ids:
        return {}
    rows = db.execute(
        select(ItemComment.item_id, func.count(ItemComment.id))
        .where(ItemComment.item_id.in_(item_ids), ItemComment.is_approved.is_(True))
        .group_by(ItemComment.item_id)
    ).all()
    return {item_id: count for item_id, count in rows}


def add(db: Session, *, item: MenuItem, author_name: str, body: str, ip: str) -> ItemComment:
    author_name = author_name.strip()[:MAX_NAME]
    body = body.strip()[:MAX_BODY]

    if not author_name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ismingizni yozing")
    if len(body) < MIN_BODY:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Izoh juda qisqa")

    recent = db.scalar(
        select(func.count())
        .select_from(ItemComment)
        .where(
            ItemComment.item_id == item.id,
            ItemComment.ip == ip,
            ItemComment.created_at >= utcnow_naive() - timedelta(hours=COOLDOWN_HOURS),
        )
    )
    if recent:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Bu taomga bugun izoh qoldirgansiz. Ertaga yana yozishingiz mumkin.",
        )

    comment = ItemComment(
        restaurant_id=item.restaurant_id,
        item_id=item.id,
        author_name=author_name,
        body=body,
        ip=ip,
    )
    db.add(comment)
    db.commit()
    return comment
