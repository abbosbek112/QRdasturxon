"""Kombo — bir necha taomdan iborat to'plam, birga arzonroq.

Ikki narsa ataylab shunday qilingan.

**Narx alohida saqlanadi.** Uni tarkibdagi taomlar yig'indisidan
hisoblash mumkin edi, lekin kombo'ning butun ma'nosi chegirmada: qancha
arzon bo'lishini egasi biladi. Ayni paytda tarkibdagi bitta taom narxi
ko'tarilganda kombo narxi o'z-o'zidan sakrab ketmasligi kerak.

**Tejalgan pul esa har safar qaytadan hisoblanadi.** Mijozga aynan shu
raqam ko'rsatiladi va u bugungi narxlarga mos bo'lishi shart — muzlatib
qo'yilgan "40 000 tejaysiz" yozuvi ertaga yolg'onga aylanardi.
"""

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Combo, ComboLine, MenuItem

MAX_COMBOS = 50
MAX_LINES = 12
MAX_QTY = 20


def list_for(db: Session, restaurant_id: int, only_active: bool = False) -> list[Combo]:
    """Restoranning kombolari, egasi belgilagan tartibda."""
    query = (
        select(Combo)
        .where(Combo.restaurant_id == restaurant_id)
        .options(
            selectinload(Combo.lines)
            .selectinload(ComboLine.item)
            .selectinload(MenuItem.category)
        )
        .order_by(Combo.sort_order, Combo.id)
    )
    if only_active:
        query = query.where(Combo.is_active.is_(True))
    return list(db.scalars(query).all())


def owned(db: Session, restaurant_id: int, combo_id: int) -> Combo:
    combo = db.scalar(
        select(Combo)
        .where(Combo.id == combo_id, Combo.restaurant_id == restaurant_id)
        .options(
            selectinload(Combo.lines)
            .selectinload(ComboLine.item)
            .selectinload(MenuItem.category)
        )
    )
    if combo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kombo topilmadi")
    return combo


def full_price(combo: Combo) -> Decimal:
    """Tarkibdagi taomlar alohida olinganda qancha turishi.

    Egasi qo'shgan qo'shimchalar ("cheksiz choy") bu hisobga KIRMAYDI:
    ular menyuda turmaydi, ya'ni ularning narxi yo'q. Ularga narx
    o'ylab qo'shish "tejaysiz" raqamini shishirardi va mijozga
    ko'rsatiladigan son yolg'on bo'lardi.
    """
    return sum(
        (line.item.price * line.quantity for line in combo.lines if line.item is not None),
        Decimal("0"),
    )


def saving(combo: Combo) -> Decimal:
    """Kombo qancha tejaydi. Manfiy chiqmaydi.

    Egasi kombo narxini tarkibidan qimmat qilib qo'yishi mumkin — bu xato,
    lekin "-5 000 tejaysiz" degan yozuv undan ham yomon. Bunday holatda
    tejash ko'rsatilmaydi.
    """
    return max(full_price(combo) - combo.price, Decimal("0"))


def is_orderable(combo: Combo) -> bool:
    """Kombo buyurtma qilinadimi.

    Tarkibidagi taomlardan bittasi yashirilgan bo'lsa kombo ham
    ishlamaydi: mijozga va'da qilingan narsani berib bo'lmaydi. Bo'sh
    kombo ham shunday — u hech nima emas.

    Taomning KATEGORIYASI ham tekshiriladi. Ilgari faqat taomning o'zi
    qaralardi va kategoriya yashirilganda kombo qolib ketardi: oshpaz
    yo'q deb "Issiq taomlar" o'chiriladi, taomlar menyudan ketadi, kombo
    esa buyurtma qilinaveradi va oshxonaga bajarib bo'lmaydigan vazifa
    tushadi. Mijoz uchun natija bir xil — u va'da qilingan taomni
    kutib o'tiradi.
    """
    taomlar = [line for line in combo.lines if line.item_id is not None]
    # Faqat qo'shimchadan iborat kombo — taomsiz to'plam, ya'ni sotiladigan
    # narsa yo'q. U mijozga ko'rsatilmaydi.
    if not taomlar:
        return False
    return all(
        line.item is not None
        and line.item.is_available
        and (line.item.category is None or line.item.category.is_active)
        for line in taomlar
    )


def visible(db: Session, restaurant_id: int) -> list[Combo]:
    """Mijoz menyusida ko'rinadigan kombolar."""
    return [c for c in list_for(db, restaurant_id, only_active=True) if is_orderable(c)]


def _check_limit(db: Session, restaurant_id: int) -> None:
    used = len(db.scalars(select(Combo.id).where(Combo.restaurant_id == restaurant_id)).all())
    if used >= MAX_COMBOS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"{MAX_COMBOS} tadan ortiq kombo bo'lmaydi"
        )


MAX_EXTRA_NAME = 120


def set_lines(
    db: Session,
    combo: Combo,
    wanted: list[tuple[int, int]],
    extras: list[tuple[str, int]] | None = None,
) -> None:
    """Kombo tarkibini almashtiradi.

    Ikki xil qator bo'ladi. `wanted` — menyudagi taomlar; ular SHU
    restoranga tegishliligi tekshiriladi, aks holda formadagi raqamni
    o'zgartirib qo'shni restoranning taomini solib qo'yish mumkin
    bo'lardi. `extras` — egasi o'zi yozgan qo'shimchalar; ular menyuga
    bog'lanmaydi, shuning uchun tekshiradigan narsa faqat matnning o'zi.
    """
    merged: dict[int, int] = {}
    for item_id, quantity in wanted[:MAX_LINES]:
        quantity = max(1, min(quantity, MAX_QTY))
        merged[item_id] = min(merged.get(item_id, 0) + quantity, MAX_QTY)

    allowed = set()
    if merged:
        allowed = set(
            db.scalars(
                select(MenuItem.id).where(
                    MenuItem.id.in_(merged),
                    MenuItem.restaurant_id == combo.restaurant_id,
                )
            ).all()
        )

    combo.lines.clear()
    db.flush()
    for item_id, quantity in merged.items():
        if item_id in allowed:
            combo.lines.append(ComboLine(item_id=item_id, quantity=quantity))

    for nom, quantity in (extras or [])[:MAX_LINES]:
        nom = " ".join(nom.split())[:MAX_EXTRA_NAME]
        if not nom:
            continue
        combo.lines.append(
            ComboLine(
                item_id=None,
                custom_name=nom,
                quantity=max(1, min(quantity, MAX_QTY)),
            )
        )


def create(
    db: Session,
    restaurant_id: int,
    *,
    name: dict,
    description: dict,
    price: Decimal,
    sort_order: int = 0,
    image: str | None = None,
    lines: list[tuple[int, int]] | None = None,
    extras: list[tuple[str, int]] | None = None,
) -> Combo:
    if not name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Kombo nomi bo'sh bo'lmasin")
    _check_limit(db, restaurant_id)

    combo = Combo(
        restaurant_id=restaurant_id,
        name=name,
        description=description,
        price=max(price, Decimal("0")),
        sort_order=sort_order,
        image=image,
    )
    db.add(combo)
    db.flush()
    set_lines(db, combo, lines or [], extras)
    db.commit()
    return combo
