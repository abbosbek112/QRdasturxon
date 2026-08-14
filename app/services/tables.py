"""Zaldagi stollar va ularning QR kodlari.

Har stolning o'z kodi bor, shuning uchun afitsant buyurtma qaysi stoldan
kelganini biladi. Kod ataylab tasodifiy: agar manzilda stol raqami tursa
(`/t/7`), restoran tashqarisidagi odam raqamni terib buyurtma bera olardi.
"""

import re
import secrets

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Restaurant, Table, TableKind

# Tarif cheklovi emas, aql chegarasi: shuncha stol bo'lgan joy bizga
# shunchaki formadan xato son kiritilganini bildiradi
MAX_TABLES = 200
MAX_LABEL = 32
CODE_BYTES = 8


def new_code() -> str:
    """Taxmin qilib bo'lmaydigan stol kaliti (~11 belgi)."""
    return secrets.token_urlsafe(CODE_BYTES)


def _clean_label(raw: str) -> str:
    label = " ".join(raw.split())[:MAX_LABEL]
    if not label:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Stol nomi bo'sh bo'lmasin")
    return label


def _count(db: Session, restaurant_id: int) -> int:
    return db.scalar(
        select(func.count(Table.id)).where(Table.restaurant_id == restaurant_id)
    ) or 0


def _labels(db: Session, restaurant_id: int) -> set[str]:
    return set(
        db.scalars(select(Table.label).where(Table.restaurant_id == restaurant_id)).all()
    )


def list_for(db: Session, restaurant_id: int) -> list[Table]:
    """Stollar ro'yxati, raqam bo'yicha inson tartibida.

    "2" "10" dan oldin tursin: oddiy matn tartibida "10" oldin kelardi va
    30 ta stoli bor zal ro'yxati o'qib bo'lmas holga tushardi.
    """
    rows = list(
        db.scalars(select(Table).where(Table.restaurant_id == restaurant_id)).all()
    )
    return sorted(rows, key=_natural_key)


def _natural_key(table: Table) -> tuple:
    parts = re.split(r"(\d+)", table.label)
    return tuple((1, int(p)) if p.isdigit() else (0, p.lower()) for p in parts if p)


def create(
    db: Session,
    restaurant: Restaurant,
    label: str,
    kind: str = "stol",
    zone_id: int | None = None,
) -> Table:
    label = _clean_label(label)
    if _count(db, restaurant.id) >= MAX_TABLES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"{MAX_TABLES} tadan ortiq stol qo'shib bo'lmaydi"
        )
    if label in _labels(db, restaurant.id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"'{label}' stoli allaqachon bor")

    table = Table(
        restaurant_id=restaurant.id,
        label=label,
        kind=_clean_kind(kind),
        zone_id=_clean_zone(db, restaurant.id, zone_id),
        code=new_code(),
    )
    db.add(table)
    db.commit()
    return table


def _clean_kind(value) -> TableKind:
    """Formadan kelgan turni tekshiradi — noma'lum qiymat oddiy stolga aylanadi."""
    try:
        return TableKind(getattr(value, "value", value) or "stol")
    except ValueError:
        return TableKind.stol


def _clean_zone(db: Session, restaurant_id: int, zone_id) -> int | None:
    """Bo'lim FAQAT shu restoranniki bo'lsa qabul qilinadi.

    Formadan begona raqam kelsa stol bo'limsiz qoladi — boshqa restoranning
    bo'limiga tirkalib qolmaydi.
    """
    from app.models import Zone

    if not zone_id:
        return None
    return db.scalar(
        select(Zone.id).where(Zone.id == int(zone_id), Zone.restaurant_id == restaurant_id)
    )


def update(db: Session, table: Table, label: str, kind: str, zone_id) -> None:
    label = _clean_label(label)
    if label != table.label:
        taken = _labels(db, table.restaurant_id) - {table.label}
        if label in taken:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"'{label}' stoli allaqachon bor"
            )
        table.label = label
    table.kind = _clean_kind(kind)
    table.zone_id = _clean_zone(db, table.restaurant_id, zone_id)
    db.commit()


def bulk_create(
    db: Session,
    restaurant: Restaurant,
    count: int,
    kind: str = "stol",
    zone_id: int | None = None,
) -> list[Table]:
    """1 dan `count` gacha raqamlangan stollar.

    Allaqachon bor raqamlar jimgina o'tkazib yuboriladi — egasi "20 ta stol"
    deb yozib, keyin "25 ta" desa yana beshtasi qo'shiladi, borlari esa
    joyida qoladi (ya'ni chop etilgan QR kodlar kuchini yo'qotmaydi).
    """
    if count < 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Stol soni kamida 1 bo'lsin")

    have = _labels(db, restaurant.id)
    wanted = [str(n) for n in range(1, count + 1) if str(n) not in have]
    if len(have) + len(wanted) > MAX_TABLES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"{MAX_TABLES} tadan ortiq stol qo'shib bo'lmaydi"
        )

    chosen_kind = _clean_kind(kind)
    chosen_zone = _clean_zone(db, restaurant.id, zone_id)
    created = [
        Table(
            restaurant_id=restaurant.id,
            label=label,
            kind=chosen_kind,
            zone_id=chosen_zone,
            code=new_code(),
        )
        for label in wanted
    ]
    db.add_all(created)
    db.commit()
    return created


def add_next(
    db: Session,
    restaurant: Restaurant,
    count: int,
    kind: str = "stol",
    zone_id: int | None = None,
    start: int | None = None,
) -> list[Table]:
    """Bo'limga "yana N ta stol" — mavjud raqamlardan keyin davom etadi.

    `bulk_create` dan farqi: u "1 dan N gacha" degani va boshlang'ich
    sozlash uchun. Bu esa zal allaqachon yig'ilgandan keyin ishlatiladi —
    VIP xonaga uchta stol qo'shsangiz ular 1, 2, 3 emas, keyingi bo'sh
    raqamlardan boshlanadi va borlari bilan urishmaydi.
    """
    if count < 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Stol soni kamida 1 bo'lsin")

    have = _labels(db, restaurant.id)
    if len(have) + count > MAX_TABLES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"{MAX_TABLES} tadan ortiq stol qo'shib bo'lmaydi"
        )

    # Eng katta raqamdan davom etamiz. Raqam bo'lmagan nomlar ("Terasa A")
    # hisobga olinmaydi — ular alohida qatorda yashaydi.
    # Raqamlashni EGASI belgilashi mumkin. Restoranlar buni har xil qiladi:
    # birida har qavat 1 dan boshlanadi, boshqasida 1-qavatda 10 stol bo'lsa
    # 2-qavatniki 11 dan ketadi — afitsant chalkashmasin degan.
    # Ko'rsatilmasa eng katta raqamdan davom etadi.
    if start is None or start < 1:
        numbers = [int(label) for label in have if label.isdigit()]
        start = max(numbers, default=0) + 1

    chosen_kind = _clean_kind(kind)
    chosen_zone = _clean_zone(db, restaurant.id, zone_id)
    created, number = [], start
    while len(created) < count:
        label = str(number)
        number += 1
        if label in have:
            continue
        created.append(
            Table(
                restaurant_id=restaurant.id,
                label=label,
                kind=chosen_kind,
                zone_id=chosen_zone,
                code=new_code(),
            )
        )
    db.add_all(created)
    db.commit()
    return created


def move_many(db: Session, restaurant_id: int, table_ids: list[int], zone_id) -> int:
    """Bir necha stolni bitta bo'limga ko'chiradi. Nechtasi ko'chganini qaytaradi.

    Ikkala tomon ham tekshiriladi: stollar ham, bo'lim ham SHU restoranniki
    bo'lishi kerak. Begona raqam jimgina tashlanadi — `areas.set_assignment`
    va `_clean_zone` dagi bir xil yondashuv.

    `zone_id` bo'sh bo'lsa stollar bo'limdan chiqariladi. Bu xato emas,
    ataylab: "bo'limsiz stollar" javonga qaytarish shu bilan bo'ladi.
    """
    if not table_ids:
        return 0

    target = _clean_zone(db, restaurant_id, zone_id)
    ours = list(
        db.scalars(
            select(Table).where(
                Table.restaurant_id == restaurant_id, Table.id.in_(table_ids)
            )
        ).all()
    )
    for table in ours:
        table.zone_id = target
    db.commit()
    return len(ours)


def regenerate_code(db: Session, table: Table) -> None:
    """Stolga yangi kod beradi — eski QR o'sha zahoti ishlamay qoladi.

    Chop etilgan QR rasmga olinib tarqalib ketgan bo'lsa kerak bo'ladi:
    yangi kod bilan eski rasm bo'yicha buyurtma bera olmaydi.
    """
    table.code = new_code()
    db.commit()


def owned(db: Session, restaurant_id: int, table_id: int) -> Table:
    table = db.scalar(
        select(Table).where(Table.id == table_id, Table.restaurant_id == restaurant_id)
    )
    if table is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Stol topilmadi")
    return table


def by_code(db: Session, restaurant_id: int, code: str) -> Table | None:
    """Kod bo'yicha stol — faqat SHU restoranniki va faol bo'lsa."""
    return db.scalar(
        select(Table).where(
            Table.code == code,
            Table.restaurant_id == restaurant_id,
            Table.is_active.is_(True),
        )
    )
