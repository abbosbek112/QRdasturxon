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
MAX_RATING = 5


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


def rating_summary(db: Session, item_ids: list[int]) -> dict[int, tuple[float, int]]:
    """Taom bo'yicha (o'rtacha baho, baholar soni).

    Bahosiz izohlar (rating = 0) hisobga kirmaydi — aks holda "izoh yozdim,
    lekin yulduz qo'ymadim" degan odam o'rtachani nolga tortib tushirardi.
    """
    if not item_ids:
        return {}
    rows = db.execute(
        select(ItemComment.item_id, func.avg(ItemComment.rating), func.count(ItemComment.id))
        .where(
            ItemComment.item_id.in_(item_ids),
            ItemComment.is_approved.is_(True),
            ItemComment.rating > 0,
        )
        .group_by(ItemComment.item_id)
    ).all()
    return {item_id: (round(float(avg), 1), int(count)) for item_id, avg, count in rows}


def best_rated(db: Session, restaurant_id: int, limit: int = 10, min_votes: int = 1):
    """Eng yuqori baholi taomlar: [(MenuItem, o'rtacha, baholar soni), ...]

    `min_votes` ataylab sozlanadigan: bitta beshlik olgan taom o'nta to'rtlik
    olganidan yuqorida turishi adolatsiz ko'rinadi. Hozircha 1, chunki yangi
    restoranda baho kam bo'ladi va ro'yxat bo'sh qolib ketmasin.
    """
    average = func.avg(ItemComment.rating).label("average")
    votes = func.count(ItemComment.id).label("votes")
    rows = db.execute(
        select(MenuItem, average, votes)
        .join(ItemComment, ItemComment.item_id == MenuItem.id)
        .where(
            ItemComment.restaurant_id == restaurant_id,
            ItemComment.is_approved.is_(True),
            ItemComment.rating > 0,
        )
        .group_by(MenuItem.id)
        .having(votes >= min_votes)
        .order_by(average.desc(), votes.desc())
        .limit(limit)
    ).all()
    return [(row[0], round(float(row[1]), 1), int(row[2])) for row in rows]


def add(
    db: Session, *, item: MenuItem, author_name: str, body: str, ip: str, rating: int = 0
) -> ItemComment:
    author_name = author_name.strip()[:MAX_NAME]
    body = body.strip()[:MAX_BODY]
    # Baho forma orqali keladi, ya'ni istalgan son yuborilishi mumkin —
    # oraliqdan chiqqanini rad etmay, "baho yo'q" ga aylantiramiz
    rating = rating if 1 <= rating <= MAX_RATING else 0

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
        rating=rating,
    )
    db.add(comment)
    db.commit()
    return comment
