"""Xodim: faoliyat tarixi va baho.

Egasi xodim haqida ikki xil narsani bilishi kerak va ular bir-biriga
o'xshamaydi.

**Faoliyat** — o'lchanadigan haqiqat: nechta buyurtmaga javob berdi va
qancha tez javob berdi. Buni hech kim kiritmaydi, u ishning o'zidan
chiqadi.

**Baho** — egasining fikri. U o'lchov emas va shunday deb ko'rsatiladi
ham: alohida turadi, kim qo'ygani va qachon qo'ygani yozib boriladi.

Ikkalasini aralashtirib bitta "ball" qilish oson bo'lardi, lekin u
yolg'on aniqlik berardi — tez javob bergan odam yaxshi xodim degani
emas.
"""

from datetime import timedelta
from decimal import Decimal
from typing import NamedTuple

from fastapi import HTTPException, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Order, OrderStatus, Role, StaffReview, User, utcnow_naive

MIN_RATING = 1
MAX_RATING = 5
MAX_NOTE = 280

# Faoliyat oynasi: shunchadan eski buyurtma hisobga olinmaydi. Bir oy —
# smenalar, dam olish kunlari va band kunlar bir tekislanadigan eng qisqa
# muddat; undan qisqasi tasodifga bog'liq bo'lib qolardi.
ACTIVITY_DAYS = 30

# Tarixda ko'rsatiladigan oxirgi buyurtmalar soni
RECENT_LIMIT = 10


class Activity(NamedTuple):
    """Bitta xodimning o'lchanadigan ishi."""

    accepted: int  # qabul qilgan buyurtmalari
    served: int  # oxirigacha yetkazganlari
    avg_seconds: int | None  # o'rtacha javob vaqti; javob bo'lmasa None
    last_seen: object | None  # oxirgi marta qachon javob bergan
    total: Decimal  # javob bergan buyurtmalarining summasi


BOSH_FAOLIYAT = Activity(0, 0, None, None, Decimal("0"))


def owned_waiter(db: Session, restaurant_id: int, staff_id: int) -> User:
    person = db.scalar(
        select(User).where(
            User.id == staff_id,
            User.restaurant_id == restaurant_id,
            User.role == Role.waiter,
        )
    )
    if person is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Xodim topilmadi")
    return person


# ------------------------------------------------------------------ faoliyat


def remember_handler(order: Order, person: User) -> None:
    """Buyurtmaga javob berganni belgilaydi.

    BIRINCHI javob berganda yoziladi va keyin o'zgarmaydi. Sabab: buyurtmani
    qabul qilgan odam unga javobgar. Keyin uni boshqa afitsant yopib qo'ysa
    ham javobgarlik ko'chib ketmasligi kerak, aks holda tarix "kim ulgurdi"
    ni emas, "kim oxirgi tegdi" ni ko'rsatardi.

    Egasi ham taxtaga tegishi mumkin — u xodim emas, shuning uchun uning
    tegishi javobgarlik deb yozilmaydi.
    """
    if order.handled_by_id is not None:
        return
    if person.role is not Role.waiter:
        return
    order.handled_by_id = person.id


def _window_start():
    return utcnow_naive() - timedelta(days=ACTIVITY_DAYS)


def activity_for(db: Session, restaurant_id: int, staff_ids: list[int]) -> dict[int, Activity]:
    """Har xodim uchun oxirgi oydagi ish ko'rsatkichlari.

    Hamma xodim uchun BITTA so'rovda hisoblanadi: sahifada o'nlab xodim
    bo'lishi mumkin va har biriga alohida so'rov yuborish ro'yxatni
    sekinlashtirardi.
    """
    if not staff_ids:
        return {}

    rows = db.execute(
        select(
            Order.handled_by_id,
            func.count(Order.id),
            func.sum(case((Order.status == OrderStatus.served, 1), else_=0)),
            func.avg(
                func.julianday(Order.accepted_at) - func.julianday(Order.created_at)
            )
            if db.bind.dialect.name == "sqlite"
            else func.avg(
                func.extract("epoch", Order.accepted_at - Order.created_at)
            ),
            func.max(Order.accepted_at),
            func.sum(Order.total),
        )
        .where(
            Order.restaurant_id == restaurant_id,
            Order.handled_by_id.in_(staff_ids),
            Order.accepted_at.is_not(None),
            Order.created_at >= _window_start(),
        )
        .group_by(Order.handled_by_id)
    ).all()

    natija: dict[int, Activity] = {}
    for staff_id, accepted, served, avg_raw, last_seen, total in rows:
        seconds = None
        if avg_raw is not None:
            # SQLite `julianday` KUN beradi, PostgreSQL `epoch` soniya.
            #
            # `int()` emas, `round()`: kunni soniyaga aylantirishda kasr
            # yo'qoladi va kesib tashlash har safar bir soniya kam
            # ko'rsatardi — 60 soniyalik javob 59 bo'lib chiqardi.
            raw = float(avg_raw)
            seconds = round(raw * 86400) if db.bind.dialect.name == "sqlite" else round(raw)
            seconds = max(seconds, 0)
        natija[staff_id] = Activity(
            accepted=accepted or 0,
            served=int(served or 0),
            avg_seconds=seconds,
            last_seen=last_seen,
            total=total or Decimal("0"),
        )
    return natija


def recent_orders(db: Session, restaurant_id: int, staff_id: int) -> list[Order]:
    """Xodim javob bergan oxirgi buyurtmalar — tarixning o'zi."""
    return list(
        db.scalars(
            select(Order)
            .where(
                Order.restaurant_id == restaurant_id,
                Order.handled_by_id == staff_id,
            )
            .options(selectinload(Order.lines))
            .order_by(Order.accepted_at.desc().nulls_last(), Order.id.desc())
            .limit(RECENT_LIMIT)
        ).all()
    )


# --------------------------------------------------------------------- baho


def add_review(
    db: Session,
    restaurant_id: int,
    staff: User,
    *,
    rating: int,
    note: str = "",
    author: User | None = None,
) -> StaffReview:
    if not MIN_RATING <= rating <= MAX_RATING:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Baho {MIN_RATING} dan {MAX_RATING} gacha bo'lsin"
        )

    review = StaffReview(
        restaurant_id=restaurant_id,
        staff_id=staff.id,
        author_id=author.id if author else None,
        rating=rating,
        note=" ".join(note.split())[:MAX_NOTE] or None,
    )
    db.add(review)
    db.commit()
    return review


def reviews_for(db: Session, restaurant_id: int, staff_id: int) -> list[StaffReview]:
    return list(
        db.scalars(
            select(StaffReview)
            .where(
                StaffReview.restaurant_id == restaurant_id,
                StaffReview.staff_id == staff_id,
            )
            .order_by(StaffReview.created_at.desc(), StaffReview.id.desc())
        ).all()
    )


def rating_summary(db: Session, restaurant_id: int, staff_ids: list[int]) -> dict[int, tuple]:
    """Har xodim uchun (o'rtacha, soni). Bahosi yo'q xodim ro'yxatga kirmaydi."""
    if not staff_ids:
        return {}

    rows = db.execute(
        select(
            StaffReview.staff_id,
            func.avg(StaffReview.rating),
            func.count(StaffReview.id),
        )
        .where(
            StaffReview.restaurant_id == restaurant_id,
            StaffReview.staff_id.in_(staff_ids),
        )
        .group_by(StaffReview.staff_id)
    ).all()
    return {staff_id: (round(float(avg), 1), count) for staff_id, avg, count in rows}


def delete_review(db: Session, restaurant_id: int, review_id: int) -> None:
    review = db.scalar(
        select(StaffReview).where(
            StaffReview.id == review_id, StaffReview.restaurant_id == restaurant_id
        )
    )
    if review is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Baho topilmadi")
    db.delete(review)
    db.commit()
