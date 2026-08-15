"""Afitsant taxtasi.

Alohida marshrut daraxti, chunki bu yerga kiradigan odam admin paneliga
kirmasligi kerak: `require_hall_access` afitsantni ham, egasini ham o'tkazadi,
lekin `require_restaurant_admin` afitsantni rad etadi. Ya'ni zal xodimi menyu
va narxlarga umuman yaqinlasha olmaydi.

Taxta o'zi yangilanadi: `/zal/list` faqat ro'yxat bo'lagini qaytaradi va
brauzer uni bir necha soniyada bir tortib oladi. Uzun ulanish (SSE/WebSocket)
ataylab ishlatilmadi — bir nechta ishchi jarayon va oddiy sinxron baza bilan
u qo'shadigan murakkablik bu yerda o'zini oqlamaydi.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config import BASE_DIR
from app.database import get_db
from app.models import OrderStatus, Restaurant, User
from app.security import require_hall_access, verify_csrf
from app.i18n import resolve_lang, t
from app.services import areas, orders, push
from app.templating import templates

# Service worker prefiksdan TASHQARIDA: u ildizdan berilishi kerak.
# `/static/js/sw.js` dan bersak ikki muammo bo'lardi:
#   * Caddy `/static/*` ga 30 kunlik kesh qo'yadi (Caddyfile dagi @static),
#     ya'ni yangilangan worker afitsantga bir oygacha yetib bormasdi;
#   * worker faqat o'z papkasi va undan pastini boshqara oladi, ya'ni
#     `/static/js/` dan tashqarisiga ta'sir qilolmasdi.
root = APIRouter(tags=["hall"])


@root.get("/sw.js", include_in_schema=False)
def service_worker() -> FileResponse:
    return FileResponse(
        BASE_DIR / "app" / "static" / "js" / "sw.js",
        media_type="text/javascript",
        headers={
            # Brauzer worker'ni har safar qayta tekshirsin: eski nusxa qolib
            # ketsa yangilanish umuman yetib bormaydi
            "Cache-Control": "no-cache",
            "Service-Worker-Allowed": "/",
        },
    )


router = APIRouter(prefix="/zal", tags=["hall"])

DbSession = Annotated[Session, Depends(get_db)]
HallUser = Annotated[User, Depends(require_hall_access)]


def _restaurant(db: Session, user: User) -> Restaurant:
    restaurant = db.get(Restaurant, user.restaurant_id)
    if restaurant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Restoran topilmadi")
    return restaurant


def _board(request: Request, db: Session, user: User, template: str, show_all: bool):
    """Taxta.

    Afitsant sukut bo'yicha FAQAT o'z bo'limini ko'radi — gavjum kunda
    yigirmata begona buyurtma orasidan o'zinikini qidirmasin. Lekin
    "Hammasi" tugmasi bor: hamkasbi band bo'lsa yordam bera oladi.
    """
    restaurant = _restaurant(db, user)
    mine = areas.assigned_table_ids(db, user)
    return templates.TemplateResponse(
        request,
        template,
        {
            "user": user,
            "restaurant": restaurant,
            "orders": orders.open_orders(db, restaurant.id, None if show_all else mine),
            # Biriktirilmagan afitsantga tugma keraksiz — u baribir hammasini ko'radi
            "has_area": mine is not None,
            "show_all": show_all,
            "mine_count": orders.new_count(db, restaurant.id, mine),
            # Bo'sh bo'lsa bildirishnoma jimgina o'chiq qoladi
            "vapid_key": push.public_key(),
        },
    )


@router.get("")
def board(request: Request, db: DbSession, user: HallUser, hammasi: bool = False):
    return _board(request, db, user, "hall/board.html", hammasi)


@router.get("/list")
def board_list(request: Request, db: DbSession, user: HallUser, hammasi: bool = False):
    """Faqat ro'yxat bo'lagi — sahifa uni o'rniga qo'yadi."""
    return _board(request, db, user, "hall/_list.html", hammasi)


@router.post("/orders/{order_id}/status", dependencies=[Depends(verify_csrf)])
def change_status(
    db: DbSession,
    user: HallUser,
    order_id: int,
    target: Annotated[str, Form()],
):
    """Buyurtma holatini o'zgartiradi.

    `orders.owned()` buyurtmani xodimning restorani bo'yicha qidiradi, ya'ni
    bir restoran afitsanti boshqasining buyurtmasiga tega olmaydi — noto'g'ri
    raqam kiritilsa 404 chiqadi.
    """
    try:
        wanted = OrderStatus(target)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Noma'lum holat")

    order = orders.owned(db, user.restaurant_id, order_id)
    orders.set_status(db, order, wanted, by=user)
    return RedirectResponse("/zal", status.HTTP_303_SEE_OTHER)


# --- bildirishnoma --------------------------------------------------------


@router.post("/push/subscribe", dependencies=[Depends(verify_csrf)])
def push_subscribe(
    db: DbSession,
    user: HallUser,
    endpoint: Annotated[str, Form()],
    p256dh: Annotated[str, Form()],
    auth: Annotated[str, Form()],
):
    """Qurilmani obuna qiladi.

    `require_hall_access` ortida: begona odam boshqa restoran afitsantiga
    bildirishnoma yozdira olmaydi.
    """
    if not endpoint.startswith("https://"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Noto'g'ri manzil")
    push.save(db, user, endpoint.strip(), p256dh.strip(), auth.strip())
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/push/unsubscribe", dependencies=[Depends(verify_csrf)])
def push_unsubscribe(db: DbSession, user: HallUser, endpoint: Annotated[str, Form()]):
    push.forget(db, endpoint.strip())
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/ping")
def ping(db: DbSession, user: HallUser, request: Request):
    """Service worker turtki olgach shu yerdan matn oladi.

    Push MAZMUNSIZ yuboriladi — buyurtma tafsiloti uchinchi tomon
    serverlaridan o'tmasin. Matn shu yerda, o'z serverimizda yasaladi va
    sessiya bilan himoyalangan, ya'ni worker faqat o'z restoranining
    ma'lumotini oladi.
    """
    restaurant = _restaurant(db, user)
    mine = areas.assigned_table_ids(db, user)
    waiting = [
        o for o in orders.open_orders(db, restaurant.id, mine)
        if o.status is OrderStatus.new
    ]
    lang = resolve_lang(request)

    newest = waiting[-1] if waiting else None
    if newest is None:
        text = ""
    else:
        dishes = ", ".join(f"{line.quantity}× {line.name}" for line in newest.lines[:3])
        table = t("order_table", lang).replace("{n}", newest.table_label)
        text = f"{table} · {dishes}" if dishes else table

    return JSONResponse(
        {"new": len(waiting), "title": t("app_new_order", lang), "text": text}
    )
