"""Stoldan kelgan buyurtmalar.

Buyurtma — to'lov emas, XABAR. Restoranda o'z POS tizimi bor va biz unga
tegmaymiz: bu yerda afitsantga "7-stol nima so'radi" degan ma'lumot yetkaziladi.

Ishonchning butun yuki shu modulda. Mijoz brauzeridan kelgan hech narsaga
ishonilmaydi: narx bazadan olinadi, taomning restoranga tegishliligi
tekshiriladi, miqdor qisiladi. Formadan kelgan `price` umuman o'qilmaydi ham.
"""

import secrets
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    MenuItem,
    Order,
    OrderLine,
    OrderStatus,
    Restaurant,
    Table,
    utcnow_naive,
)
from app.plans import menu_is_live

MAX_LINES = 40
MAX_QTY = 20
MAX_NOTE = 280

# Cheklov IP bo'yicha EMAS, stol bo'yicha. Sabab oddiy: kafedagi hamma mijoz
# bitta Wi-Fi ortida o'tiradi, ya'ni ular uchun IP bitta. IP bo'yicha cheklov
# gavjum kafeni to'liq to'sib qo'yardi.
MAX_PER_TABLE = 5
COOLDOWN_MINUTES = 10
# Afitsant javob bermaguncha yangi buyurtma qabul qilinmaydi — rasmga olingan
# QR bilan uydan spam qilayotgan odam shu yerda to'xtaydi, chunki uning
# buyurtmalari bekor qilinmaguncha ko'paymaydi.
MAX_OPEN_PER_TABLE = 3


def new_code() -> str:
    return secrets.token_urlsafe(8)


def window_open(restaurant: Restaurant, opened_at) -> bool:
    """QR skanerlangan vaqtdan beri buyurtma oynasi hali ochiqmi.

    Bu qulf faqat bitta narsani to'xtatadi: manzil qatoridan nusxa olib
    tashqariga yuborilgan havolani. QR'ni RASMGA olgan odamni to'xtatmaydi —
    u rasmni qayta skanerlab yangi oyna oladi. Tashqaridan kelgan buyurtmani
    aslida afitsantning tasdig'i to'xtatadi.
    """
    minutes = restaurant.order_window_minutes
    if minutes <= 0:  # 0 = cheksiz
        return True
    if opened_at is None:
        return False
    return utcnow_naive() - opened_at <= timedelta(minutes=minutes)


def _check_can_order(restaurant: Restaurant) -> None:
    if not menu_is_live(restaurant):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Menyu hozir yopiq")
    if not restaurant.orders_enabled:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Bu restoran menyudan buyurtma qabul qilmaydi"
        )


def _check_table_flood(db: Session, table: Table) -> None:
    since = utcnow_naive() - timedelta(minutes=COOLDOWN_MINUTES)
    recent = db.scalar(
        select(func.count(Order.id)).where(
            Order.table_id == table.id, Order.created_at >= since
        )
    )
    if (recent or 0) >= MAX_PER_TABLE:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Ketma-ket juda ko'p buyurtma. Biroz kuting yoki afitsantni chaqiring.",
        )

    waiting = db.scalar(
        select(func.count(Order.id)).where(
            Order.table_id == table.id,
            Order.status.in_((OrderStatus.new, OrderStatus.accepted)),
        )
    )
    if (waiting or 0) >= MAX_OPEN_PER_TABLE:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Oldingi buyurtmangiz hali yopilmagan. Afitsant javob bergach yana yuborasiz.",
        )


def _resolve(db: Session, restaurant_id: int, wanted: list[tuple[int, int]]):
    """(taom, miqdor) juftliklari — faqat SHU restoranning mavjud taomlari.

    Bir taom bir necha marta yuborilsa miqdorlari qo'shiladi. Topilmagan yoki
    boshqa restoranning taomi jimgina tashlanadi: mijozga "5-taom yo'q" deb
    xato ko'rsatishning ma'nosi yo'q, u baribir savatini o'zi yig'magan.
    """
    merged: dict[int, int] = {}
    for item_id, quantity in wanted[:MAX_LINES]:
        quantity = max(1, min(quantity, MAX_QTY))
        merged[item_id] = min(merged.get(item_id, 0) + quantity, MAX_QTY)

    if not merged:
        return []

    items = db.scalars(
        select(MenuItem).where(
            MenuItem.id.in_(merged),
            MenuItem.restaurant_id == restaurant_id,
            MenuItem.is_available.is_(True),
        )
    ).all()
    by_id = {item.id: item for item in items}
    # Mijoz yuborgan tartib saqlanadi — chekda savatdagidek ko'rinsin
    return [(by_id[item_id], merged[item_id]) for item_id in merged if item_id in by_id]


def place(
    db: Session,
    *,
    restaurant: Restaurant,
    table: Table,
    wanted: list[tuple[int, int]],
    combos: list[tuple[int, int]] | None = None,
    note: str = "",
) -> Order:
    _check_can_order(restaurant)
    _check_table_flood(db, table)

    resolved = _resolve(db, restaurant.id, wanted)
    resolved_combos = _resolve_combos(db, restaurant.id, combos or [])
    if not resolved and not resolved_combos:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Savat bo'sh")

    order = Order(
        restaurant_id=restaurant.id,
        table_id=table.id,
        table_label=table.label,
        table_kind=table.kind.value,
        code=new_code(),
        status=OrderStatus.new,
        note=" ".join(note.split())[:MAX_NOTE] or None,
        total=Decimal("0"),
    )
    total = Decimal("0")
    for item, quantity in resolved:
        # Nom va narx NUSXA bo'lib ketadi: taom o'chsa yoki narxi o'zgarsa ham
        # bu buyurtmaning hisobi o'zgarmaydi
        order.lines.append(
            OrderLine(
                item_id=item.id,
                name=_first_name(item),
                unit_price=item.price,
                quantity=quantity,
            )
        )
        total += item.price * quantity

    for combo, quantity in resolved_combos:
        # Kombo BITTA qator bo'lib tushadi. Tarkibiga yoyish afitsant
        # taxtasini uzaytirib, "bular bitta to'plam" degan ma'noni
        # yo'qotardi — oshxonaga esa aynan shu ma'no kerak.
        order.lines.append(
            OrderLine(
                item_id=None,
                name=_first_text(combo.name),
                unit_price=combo.price,
                quantity=quantity,
            )
        )
        total += combo.price * quantity

    order.total = total
    db.add(order)
    db.commit()
    return order


def _resolve_combos(db: Session, restaurant_id: int, wanted: list[tuple[int, int]]):
    """(kombo, miqdor) juftliklari — faqat SHU restoranning tayyor kombolari.

    Tarkibidagi taomlardan bittasi yashirilgan kombo tashlanadi: mijozga
    va'da qilingan narsani berib bo'lmaydi va uni buyurtmaga qo'shish
    oshxonaga bajarib bo'lmaydigan vazifa berardi.
    """
    from app.services import combos as combo_service

    merged: dict[int, int] = {}
    for combo_id, quantity in wanted[:MAX_LINES]:
        quantity = max(1, min(quantity, MAX_QTY))
        merged[combo_id] = min(merged.get(combo_id, 0) + quantity, MAX_QTY)

    if not merged:
        return []

    found = {
        combo.id: combo
        for combo in combo_service.visible(db, restaurant_id)
        if combo.id in merged
    }
    return [(found[cid], merged[cid]) for cid in merged if cid in found]


def _first_text(value: dict | None) -> str:
    """i18n maydondan restoran o'z tilidagi nomni oladi."""
    value = value or {}
    for lang in ("uz", "ru", "en"):
        if value.get(lang):
            return value[lang][:120]
    return "—"


def _first_name(item: MenuItem) -> str:
    """Taom nomi — restoran o'z tilida ko'rsin.

    Mijoz menyuni ruscha ko'rgan bo'lsa ham afitsant taxtasida o'zbekcha nom
    turgani qulayroq: oshxonaga aytiladigan nom bitta bo'lishi kerak.
    """
    return _first_text(item.name)


def by_code(db: Session, restaurant_id: int, code: str) -> Order | None:
    return db.scalar(
        select(Order)
        .where(Order.code == code, Order.restaurant_id == restaurant_id)
        .options(selectinload(Order.lines))
    )


def owned(db: Session, restaurant_id: int, order_id: int) -> Order:
    order = db.scalar(
        select(Order)
        .where(Order.id == order_id, Order.restaurant_id == restaurant_id)
        .options(selectinload(Order.lines))
    )
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Buyurtma topilmadi")
    return order


def open_orders(
    db: Session, restaurant_id: int, table_ids: set[int] | None = None
) -> list[Order]:
    """Afitsant taxtasi: hali yopilmagan buyurtmalar, eng eskisi tepada.

    Eskisi tepada — chunki uzoq kutgan stol birinchi navbatda javob olishi
    kerak, aks holda taxta to'lganda aynan o'sha unutiladi.

    `table_ids` berilsa faqat o'sha stollar ko'rinadi (afitsant o'z bo'limi).
    `None` — hammasi.

    Stoli o'chirilgan buyurtma (`table_id is NULL`) HAR DOIM ko'rinadi:
    u hech kimning bo'limiga tegishli emas va filtr uni butunlay
    yo'qotib yuborardi.
    """
    match = [
        Order.restaurant_id == restaurant_id,
        Order.status.in_((OrderStatus.new, OrderStatus.accepted)),
    ]
    if table_ids is not None:
        match.append(or_(Order.table_id.in_(table_ids), Order.table_id.is_(None)))

    return list(
        db.scalars(
            select(Order)
            .where(*match)
            .options(selectinload(Order.lines))
            .order_by(Order.created_at)
        ).all()
    )


def new_count(db: Session, restaurant_id: int, table_ids: set[int] | None = None) -> int:
    match = [Order.restaurant_id == restaurant_id, Order.status == OrderStatus.new]
    if table_ids is not None:
        match.append(or_(Order.table_id.in_(table_ids), Order.table_id.is_(None)))
    return db.scalar(select(func.count(Order.id)).where(*match)) or 0


def set_status(db: Session, order: Order, target: OrderStatus) -> None:
    now = utcnow_naive()
    order.status = target
    if target is OrderStatus.accepted:
        order.accepted_at = order.accepted_at or now
        order.closed_at = None
    elif target in (OrderStatus.served, OrderStatus.cancelled):
        order.closed_at = now
    else:  # yangiga qaytarish — xato bosilganini orqaga qaytarish uchun
        order.accepted_at = None
        order.closed_at = None
    db.commit()


def history(db: Session, restaurant_id: int, start, end) -> list[Order]:
    """Egasi uchun tarix. `start`/`end` — sana, oxirgi kun to'liq kiradi."""
    return list(
        db.scalars(
            select(Order)
            .where(
                Order.restaurant_id == restaurant_id,
                Order.created_at >= _day_start(start),
                Order.created_at < _day_start(end) + timedelta(days=1),
            )
            .options(selectinload(Order.lines))
            .order_by(Order.created_at.desc())
            .limit(300)
        ).all()
    )


def _day_start(day) -> datetime:
    return datetime(day.year, day.month, day.day)
