"""Afitsant ilovasi uchun JSON API.

Brauzer taxtasi (`/zal`) o'z holicha qoladi — bu qatlam undan ALOHIDA va
ikkalasi bitta servisdan (`app/services/orders.py`) foydalanadi. Shunday
qilinganining sababi: mantiq ikki joyda takrorlansa, ular albatta bir-biridan
uzoqlashadi va bir kun ilova bilan brauzer boshqacha ish qila boshlaydi.

**Bu qatlam sessiya cookie'sini UMUMAN o'qimaydi.** Faqat `Authorization`
sarlavhasi. Aks holda brauzerda ochiq sessiyasi bor odamning cookie'si
API'ga avtomatik ketardi va CSRF himoyasi yo'q bu yerda teshik ochilardi.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import AppDevice, Order, OrderStatus, Restaurant, Role, User
from app.security import (
    LOGIN,
    MAX_ATTEMPTS,
    WINDOW_SECONDS,
    attempt_allowed,
    record_attempt,
    verify_password,
)
from app.services import areas, orders, tokens
from app.templating import localtime

router = APIRouter(prefix="/api/v1", tags=["api"])

DbSession = Annotated[Session, Depends(get_db)]

# Eng past mos versiya — bu KOD masalasi: API o'zgarib eski ilova ishlamay
# qolsa shu son ko'tariladi. Shuning uchun u shu yerda turadi.
APP_MIN_VERSION = "1.0.0"

# Eng oxirgi chiqarilgan versiya esa SOZLAMA: yangi APK serverga qo'yilganda
# `.env` dagi APP_VERSION ko'tariladi, kod o'zgarmaydi. Ilgari bu ham shu
# yerda qotib turardi va `.env` dagi qiymat hech qayerda ishlatilmasdi —
# ya'ni yangi APK qo'yilgani bilan ilova "yangilanish bor" demasdi.


def require_api_user(
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """`Authorization: Bearer <token>` bo'yicha xodimni topadi.

    Sessiya cookie'si ATAYLAB qaralmaydi — yuqoridagi modul izohiga qarang.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Kalit yo'q")

    user = tokens.resolve(db, authorization[7:].strip())
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Kalit yaroqsiz")
    if user.role not in (Role.waiter, Role.restaurant_admin):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ruxsat yo'q")
    return user


ApiUser = Annotated[User, Depends(require_api_user)]


def _bearer(authorization: str | None) -> str:
    return authorization[7:].strip() if authorization else ""


def _order_json(order: Order) -> dict:
    return {
        "id": order.id,
        "table": order.table_label,
        "kind": order.table_kind,
        "status": order.status.value,
        "note": order.note or "",
        "total": float(order.total),
        # ISO + Z: ilova uni o'z mintaqasida emas, UTC deb o'qishi kerak
        "created_at": order.created_at.isoformat() + "Z",
        "created_local": localtime(order.created_at).strftime("%H:%M"),
        "lines": [
            {"name": line.name, "quantity": line.quantity, "price": float(line.unit_price)}
            for line in order.lines
        ],
    }


@router.post("/login")
def login(request: Request, db: DbSession, payload: dict):
    """Login va parol → kalit.

    Cheklov brauzer login'i bilan BIR XIL hisoblagichda (`kind="login"`):
    aks holda ilova orqali cheksiz parol terish yo'li ochiq qolardi.
    """
    client_ip = request.client.host if request.client else "unknown"
    if not attempt_allowed(db, client_ip, LOGIN, MAX_ATTEMPTS, WINDOW_SECONDS):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Juda ko'p urinish. Bir necha daqiqadan so'ng qayta urinib ko'ring.",
        )

    username = str(payload.get("username", "")).strip().lower()
    password = str(payload.get("password", ""))
    user = db.scalar(select(User).where(User.username == username))

    if (
        user is None
        or not user.is_active
        or user.restaurant_id is None
        or user.role not in (Role.waiter, Role.restaurant_admin)
        or not verify_password(password, user.password_hash)
    ):
        record_attempt(db, client_ip, LOGIN, WINDOW_SECONDS)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Login yoki parol noto'g'ri")

    restaurant = db.get(Restaurant, user.restaurant_id)
    token = tokens.issue(db, user, label=str(payload.get("device", "")))
    return {
        "token": token,
        "user": {"username": user.username, "role": user.role.value},
        "restaurant": {
            "name": restaurant.name if restaurant else "",
            "currency": restaurant.currency if restaurant else "",
        },
    }


@router.post("/logout")
def logout(
    db: DbSession,
    user: ApiUser,
    authorization: Annotated[str | None, Header()] = None,
):
    """Shu qurilmaning kalitini bekor qiladi — boshqalari joyida qoladi."""
    tokens.revoke(db, _bearer(authorization))
    return {"ok": True}


@router.get("/orders")
def order_list(db: DbSession, user: ApiUser, all: bool = False):
    """Ochiq buyurtmalar.

    Sukut bo'yicha faqat xodimning O'Z bo'limi — brauzer taxtasi bilan bir xil
    qoida. `?all=1` bilan butun zal ko'rinadi: hamkasbi band bo'lsa afitsant
    yordam bera oladi.

    `has_area` ilovaga tugmani ko'rsatish kerakmi yo'qmi degan javob beradi:
    biriktirilmagan afitsantda tanlov ham bo'lmasin.
    """
    mine = areas.assigned_table_ids(db, user)
    rows = orders.open_orders(db, user.restaurant_id, None if all else mine)
    return {
        "orders": [_order_json(o) for o in rows],
        "has_area": mine is not None,
        "showing_all": bool(all) or mine is None,
    }


@router.post("/orders/{order_id}/status")
def change_status(db: DbSession, user: ApiUser, order_id: int, payload: dict):
    """Holatni o'zgartiradi.

    `orders.owned()` buyurtmani xodimning restorani bo'yicha qidiradi — bir
    restoran afitsanti boshqasinikiga tega olmaydi.
    """
    try:
        wanted = OrderStatus(str(payload.get("status", "")))
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Noma'lum holat")

    order = orders.owned(db, user.restaurant_id, order_id)
    orders.set_status(db, order, wanted)
    return _order_json(order)


@router.post("/devices")
def register_device(db: DbSession, user: ApiUser, payload: dict):
    """Bildirishnoma uchun qurilmani yozadi.

    Bir qurilma qayta yozilsa yozuv KO'PAYMAYDI. Qurilma boshqa xodimga
    o'tsa egasi almashadi — aks holda ishdan ketgan afitsant o'z telefonida
    buyurtmalarni ko'rib turardi.
    """
    token = str(payload.get("expo_token", "")).strip()
    if not token.startswith("ExponentPushToken[") and not token.startswith("ExpoPushToken["):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Noto'g'ri qurilma tokeni")

    row = db.scalar(select(AppDevice).where(AppDevice.expo_token == token))
    if row is None:
        row = AppDevice(expo_token=token)
        db.add(row)
    row.user_id = user.id
    row.platform = str(payload.get("platform", ""))[:16]
    db.commit()
    return {"ok": True}


@router.delete("/devices")
def forget_device(db: DbSession, user: ApiUser, expo_token: str = ""):
    db.execute(
        delete(AppDevice).where(
            AppDevice.expo_token == expo_token.strip(), AppDevice.user_id == user.id
        )
    )
    db.commit()
    return {"ok": True}


@router.get("/app/latest")
def app_version():
    """Ilova yangilanish borligini shu yerdan biladi.

    APK do'kondan emas, saytdan tarqatiladi — ya'ni yangilanish haqida
    ilovaning o'ziga aytish kerak, buni hech kim boshqa qilmaydi.

    Havola `/ilova/yuklash` ga qarab turadi, `/static/...` ga emas: Caddy
    `/static/*` ga 30 kunlik kesh qo'yadi (`Caddyfile`), ya'ni yangi APK
    o'sha manzilda turgani bilan telefon eskisini olib kelaverardi —
    yangilanish borligini aytib, eskisini bergan bo'lardik.
    """
    base = settings.base_url.rstrip("/")
    return {
        "version": settings.app_version,
        "min_version": APP_MIN_VERSION,
        "apk_url": f"{base}/ilova/yuklash",
        "page_url": f"{base}/ilova",
    }
