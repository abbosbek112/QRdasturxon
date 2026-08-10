"""Zal bo'limlari va afitsantlarning javobgarlik doirasi.

Restoranda odatda bir necha afitsant ishlaydi va ular zalni bo'lib oladi:
biri 1–10 stol, boshqasi 11–20. Bu modul shu bo'linishni hisoblaydi.

Ikki daraja bor va ikkalasi birga ishlaydi:

* **zona** — asosiy birlik. Kimdir kasal bo'lsa egasi bitta zonani boshqasiga
  o'tkazadi, yigirmata stolni birma-bir belgilamaydi;
* **alohida stol** — qo'shimcha. Bitta VIP xona alohida odamga biriktirilishi
  mumkin va u zonaga to'g'ri kelmaydi.

Eng muhim qoida: **biriktirilmagan afitsant HAMMASINI ko'radi.** Bitta
afitsantli kafeda hech narsa sozlanmaydi va hammasi avvalgidek ishlayveradi.
"""

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Role, Table, User, WaiterTable, WaiterZone, Zone

MAX_ZONES = 30
MAX_NAME = 64


# --- zonalar --------------------------------------------------------------


def list_zones(db: Session, restaurant_id: int) -> list[Zone]:
    return list(
        db.scalars(
            select(Zone)
            .where(Zone.restaurant_id == restaurant_id)
            .order_by(Zone.floor, Zone.sort_order, Zone.id)
        ).all()
    )


def owned_zone(db: Session, restaurant_id: int, zone_id: int) -> Zone:
    zone = db.scalar(
        select(Zone).where(Zone.id == zone_id, Zone.restaurant_id == restaurant_id)
    )
    if zone is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bo'lim topilmadi")
    return zone


def create_zone(
    db: Session, restaurant, name: str, sort_order: int = 0, floor: int = 1
) -> Zone:
    name = " ".join(name.split())[:MAX_NAME]
    if not name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Bo'lim nomi bo'sh bo'lmasin")

    existing = list_zones(db, restaurant.id)
    if len(existing) >= MAX_ZONES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"{MAX_ZONES} tadan ortiq bo'lim bo'lmaydi"
        )
    if any(zone.name.lower() == name.lower() for zone in existing):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"'{name}' bo'limi allaqachon bor")

    zone = Zone(
        restaurant_id=restaurant.id,
        name=name,
        sort_order=sort_order,
        floor=_clean_floor(floor),
    )
    db.add(zone)
    db.commit()
    return zone


def rename_zone(db: Session, zone: Zone, name: str, sort_order: int, floor: int = 1) -> None:
    name = " ".join(name.split())[:MAX_NAME]
    if name:
        zone.name = name
    zone.sort_order = sort_order
    zone.floor = _clean_floor(floor)
    db.commit()


def _clean_floor(value) -> int:
    """Qavat 0 dan 50 gacha. Yerto'la uchun 0, aks holda odatdagi qavatlar.

    Formadan aql bovar qilmaydigan son kelsa birinchi qavatga tushiriladi —
    xato ko'rsatib egani ushlab turishning ma'nosi yo'q.
    """
    try:
        floor = int(value)
    except (TypeError, ValueError):
        return 1
    return floor if 0 <= floor <= 50 else 1


def by_floor(zones: list[Zone]) -> list[tuple[int, list[Zone]]]:
    """Bo'limlarni qavatlarga guruhlaydi — sahifada shunday ko'rinadi."""
    groups: dict[int, list[Zone]] = {}
    for zone in zones:
        groups.setdefault(zone.floor, []).append(zone)
    return sorted(groups.items())


def delete_zone(db: Session, zone: Zone) -> None:
    """Bo'limni o'chiradi.

    Stollar QOLADI — faqat bo'limsiz bo'lib qoladi (`ondelete=SET NULL`).
    Aks holda bo'limni o'chirish stollar bilan birga chop etilgan QR
    kodlarni ham o'ldirardi.
    """
    db.delete(zone)
    db.commit()


# --- afitsant javobgarligi -------------------------------------------------


def assigned_table_ids(db: Session, user: User) -> set[int] | None:
    """Xodim javobgar bo'lgan stollar. `None` — hammasi.

    `None` uch holatda qaytadi:
    * foydalanuvchi restoran egasi — u butun zalni ko'radi;
    * afitsantga hech narsa biriktirilmagan — bitta afitsantli kafeda
      hech narsa sozlanmasin;
    * biriktirilgan zonalar bo'sh bo'lib qolgan (stollari yo'q).
    """
    if user.role is not Role.waiter:
        return None

    zone_ids = set(
        db.scalars(select(WaiterZone.zone_id).where(WaiterZone.user_id == user.id)).all()
    )
    table_ids = set(
        db.scalars(select(WaiterTable.table_id).where(WaiterTable.user_id == user.id)).all()
    )
    if not zone_ids and not table_ids:
        return None

    covered = set(table_ids)
    if zone_ids:
        covered |= set(
            db.scalars(
                select(Table.id).where(
                    Table.restaurant_id == user.restaurant_id, Table.zone_id.in_(zone_ids)
                )
            ).all()
        )
    # Biriktirish bor, lekin ortida bitta ham stol yo'q — bu sozlash xatosi.
    # Afitsantni bo'sh taxta oldida qoldirgandan ko'ra hammasini ko'rsatamiz.
    return covered or None


def set_assignment(db: Session, user: User, zone_ids: list[int], table_ids: list[int]) -> None:
    """Xodimning javobgarligini butunlay qayta yozadi.

    Faqat SHU restoranning zonalari va stollari qabul qilinadi — formadan
    begona raqam kelsa u jimgina tashlanadi.
    """
    ours_zones = set(
        db.scalars(
            select(Zone.id).where(
                Zone.restaurant_id == user.restaurant_id, Zone.id.in_(zone_ids or [-1])
            )
        ).all()
    )
    ours_tables = set(
        db.scalars(
            select(Table.id).where(
                Table.restaurant_id == user.restaurant_id, Table.id.in_(table_ids or [-1])
            )
        ).all()
    )

    db.execute(delete(WaiterZone).where(WaiterZone.user_id == user.id))
    db.execute(delete(WaiterTable).where(WaiterTable.user_id == user.id))
    db.add_all(WaiterZone(user_id=user.id, zone_id=z) for z in ours_zones)
    db.add_all(WaiterTable(user_id=user.id, table_id=t) for t in ours_tables)
    db.commit()


def assignment_of(db: Session, user: User) -> tuple[set[int], set[int]]:
    """(zona raqamlari, stol raqamlari) — formani chizish uchun."""
    return (
        set(db.scalars(select(WaiterZone.zone_id).where(WaiterZone.user_id == user.id)).all()),
        set(db.scalars(select(WaiterTable.table_id).where(WaiterTable.user_id == user.id)).all()),
    )


def responsible_for(db: Session, restaurant_id: int, table_id: int | None) -> list[int]:
    """Shu stol uchun kimga bildirishnoma ketadi.

    Egasi doim kiradi. Afitsantlardan esa faqat shu stolga javobgarlari.

    Agar stolga HECH KIM biriktirilmagan bo'lsa — hammaga ketadi. Buyurtma
    javobsiz qolgandan ko'ra ortiqcha bildirishnoma yaxshiroq, va bu sozlash
    xatosini jimgina yutib yubormaydi.
    """
    staff = list(
        db.scalars(
            select(User).where(
                User.restaurant_id == restaurant_id,
                User.role.in_((Role.waiter, Role.restaurant_admin)),
                User.is_active.is_(True),
            )
        ).all()
    )

    owners = [person.id for person in staff if person.role is Role.restaurant_admin]
    waiters = [person for person in staff if person.role is Role.waiter]

    covering, unassigned = [], []
    for person in waiters:
        scope = assigned_table_ids(db, person)
        if scope is None:
            unassigned.append(person.id)
        elif table_id is not None and table_id in scope:
            covering.append(person.id)

    if covering:
        return owners + covering + unassigned
    # Bu stolga javobgar topilmadi — hammaga
    return owners + [person.id for person in waiters]
