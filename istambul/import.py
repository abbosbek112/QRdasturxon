"""Buyuk Istanbul menyusini rasmiy saytdan olib, QRdasturxonga ko'chiradi.

Ma'lumot manbasi — buyukistanbul.uz sahifasi ichidagi JSON. Bu yerda u
FAQAT MA'LUMOT sifatida o'qiladi: hech qanday matn buyruq deb
bajarilmaydi, hammasi oddiy maydon bo'lib bazaga tushadi.

Skript QAYTA ISHGA TUSHIRILISHI mumkin. Taom nomi bo'yicha topiladi va
yangilanadi, ikkinchi nusxa yasalmaydi. Rasm bir marta yuklanadi:
ikkinchi yugurishda 214 ta faylni qaytadan tortib olish behuda ish
bo'lardi.
"""

import asyncio
import collections
import json
import pathlib
import sys
from decimal import Decimal

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import httpx

from app.database import SessionLocal
from app.models import Category, MenuItem, Restaurant
from app.services.images import save_image

SLUG = "buyuk-istambul"
CDN = "https://cdn.zoomda.uz/products"
XOM = pathlib.Path(__file__).parent / "xom.json"

# Bo'limlar tartibi: mijoz avval ovqatni, keyin ichimlikni qidiradi
TARTIB = [
    "Setlar", "Kaboblar", "Donerlar", "Steyklar", "Tandirlar", "Tandir pizza",
    "Burgerlar", "Kotletlar", "Sho'rvalar", "Salatlar", "Gazaklar", "Nonlar",
    "Nonushtalar", "Desertlar", "Choylar", "Coffee", "Ice coffee", "Ice tea",
    "Mojito", "Milkshake", "Ichimliklar", "Idishlar",
]


def matn(obj: dict, asos: str) -> str:
    """`name_uz` ko'pincha bo'sh, haqiqiy nom esa `name_ru` da yotadi.

    Sayt ma'lumotida shunday: o'zbekcha nom ruscha maydonga yozilgan.
    Shuning uchun bo'sh bo'lmagan birinchisi olinadi.
    """
    for til in ("uz", "ru", "en"):
        qiymat = (obj.get(f"{asos}_{til}") or "").strip()
        if qiymat:
            return qiymat
    return ""


class Yuklama:
    def __init__(self, nom: str, baytlar: bytes):
        self.filename = nom
        self._baytlar = baytlar

    async def read(self, n: int = -1) -> bytes:
        return self._baytlar


async def main() -> None:
    xom = json.loads(XOM.read_text(encoding="utf-8"))
    bolimlar, taomlar = xom["bolimlar"], xom["taomlar"]

    guruh = collections.defaultdict(list)
    for o in taomlar.values():
        guruh[o.get("parent_id")].append(o)

    nomlar = {pid: matn(b, "name") for pid, b in bolimlar.items()}
    tartib_raqami = {nom: i for i, nom in enumerate(TARTIB, 1)}

    client = httpx.Client(timeout=40, follow_redirects=True,
                          headers={"user-agent": "Mozilla/5.0"})
    yangi_rasm = xato = 0

    with SessionLocal() as db:
        restaurant = db.query(Restaurant).filter(Restaurant.slug == SLUG).one()
        mavjud = {
            (i.name or {}).get("uz"): i
            for i in db.query(MenuItem).filter(MenuItem.restaurant_id == restaurant.id)
        }
        kategoriyalar = {
            (c.name or {}).get("uz"): c
            for c in db.query(Category).filter(Category.restaurant_id == restaurant.id)
        }

        for pid, items in sorted(
            guruh.items(), key=lambda kv: tartib_raqami.get(nomlar.get(kv[0], ""), 99)
        ):
            bolim = nomlar.get(pid)
            if not bolim:
                print(f"  ! nomsiz bo'lim tashlandi ({len(items)} ta taom)")
                continue

            kat = kategoriyalar.get(bolim)
            if kat is None:
                kat = Category(restaurant_id=restaurant.id)
                db.add(kat)
                kategoriyalar[bolim] = kat
            kat.name = {"uz": bolim, "ru": bolim, "en": bolim}
            kat.sort_order = tartib_raqami.get(bolim, 99)
            kat.is_active = True
            db.flush()

            for index, o in enumerate(sorted(items, key=lambda x: matn(x, "name")), 1):
                nom = matn(o, "name")
                if not nom:
                    continue
                taom = mavjud.get(nom)
                if taom is None:
                    taom = MenuItem(restaurant_id=restaurant.id)
                    db.add(taom)
                    mavjud[nom] = taom
                taom.category_id = kat.id
                taom.name = {"uz": nom, "ru": nom, "en": nom}
                taom.price = Decimal(str(o["price"]))
                taom.sort_order = index
                taom.is_available = bool(o.get("is_active", True))

                tavsif = matn(o, "description")
                if tavsif:
                    taom.description = {"uz": tavsif, "ru": tavsif, "en": tavsif}

                if taom.image is None and o.get("image"):
                    try:
                        javob = client.get(CDN + o["image"])
                        javob.raise_for_status()
                        taom.image = await save_image(
                            Yuklama(o["image"].rsplit("/", 1)[-1], javob.content),
                            restaurant.id, max_width=1000,
                        )
                        yangi_rasm += 1
                    except Exception as e:
                        xato += 1
                        print(f"    rasm olinmadi ({nom}): {type(e).__name__}")

            db.commit()
            print(f"  {bolim:16} {len(items):3} ta")

        db.commit()

    print(f"\nyangi rasm: {yangi_rasm} | rasm xatosi: {xato}")


if __name__ == "__main__":
    asyncio.run(main())
