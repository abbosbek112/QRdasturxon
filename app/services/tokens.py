"""Ilova uchun kirish kalitlari.

Brauzer sessiyasi cookie va CSRF bilan ishlaydi — ilovaga bu to'g'ri kelmaydi.
Shuning uchun alohida qatlam: `Authorization: Bearer <token>`.

Token bazada XESH holida yotadi. Baza o'g'irlansa ham undan ishlaydigan kalit
chiqmaydi — parollar bilan bir xil mantiq.
"""

import hashlib
import secrets

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import ApiToken, User, utcnow_naive

TOKEN_BYTES = 32
MAX_LABEL = 64
# Bitta xodimda shuncha faol qurilma bo'lishi mumkin. Chegara bor, chunki
# har kirish yangi yozuv qoldiradi va yillar davomida ular yig'ilib qolardi.
MAX_PER_USER = 10


def _digest(token: str) -> str:
    """sha256.

    Argon2 EMAS: token 32 tasodifiy baytdan iborat, ya'ni taxmin qilib
    bo'lmaydi va sekin xeshdan foyda yo'q. Argon2 esa har bir API so'roviga
    ~50 ms qo'shardi — taxta har necha soniyada so'raladi.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def issue(db: Session, user: User, label: str = "") -> str:
    """Yangi kalit yasaydi va ochiq qiymatini QAYTARADI.

    Ochiq qiymat faqat shu yerda ko'rinadi — bazada xeshi qoladi, ya'ni uni
    keyin hech qayerdan tiklab bo'lmaydi.
    """
    token = secrets.token_urlsafe(TOKEN_BYTES)
    db.add(
        ApiToken(
            user_id=user.id,
            token_hash=_digest(token),
            label=" ".join(label.split())[:MAX_LABEL],
        )
    )
    db.commit()
    _trim(db, user.id)
    return token


def _trim(db: Session, user_id: int) -> None:
    """Eng eski kalitlarni chegaradan oshganda o'chiradi."""
    rows = db.scalars(
        select(ApiToken)
        .where(ApiToken.user_id == user_id)
        .order_by(ApiToken.created_at.desc())
    ).all()
    extra = [row.id for row in rows[MAX_PER_USER:]]
    if extra:
        db.execute(delete(ApiToken).where(ApiToken.id.in_(extra)))
        db.commit()


def resolve(db: Session, token: str) -> User | None:
    """Token egasini qaytaradi.

    Bloklangan hisob rad etiladi — egasi afitsantni bloklaganda uning
    telefonidagi ilova O'SHA ZAHOTI ishlamay qolishi kerak.
    """
    if not token:
        return None
    row = db.scalar(select(ApiToken).where(ApiToken.token_hash == _digest(token)))
    if row is None:
        return None

    user = row.user
    if user is None or not user.is_active or user.restaurant_id is None:
        return None

    # Oxirgi ishlatilgan vaqt — egasiga "bu qurilma hali ishlatiladimi"
    # degan savolga javob beradi. Har so'rovda emas, sutkada bir marta
    # yoziladi: taxta har necha soniyada so'raydi va har safar yozish
    # bazaga keraksiz yuk bo'lardi.
    now = utcnow_naive()
    if row.last_used_at is None or (now - row.last_used_at).total_seconds() > 86400:
        row.last_used_at = now
        db.commit()
    return user


def revoke(db: Session, token: str) -> None:
    db.execute(delete(ApiToken).where(ApiToken.token_hash == _digest(token)))
    db.commit()
