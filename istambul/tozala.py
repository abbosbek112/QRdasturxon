"""Import oldidan qo'lda kiritilgan bo'limlarni yig'ishtiradi.

Qo'lda kiritilganda "1 kishilik setlar" va "3–4 kishilik setlar" degan
bo'limlar yasalgan edi. Rasmiy saytda esa hammasi bitta "Setlar"
bo'limida turadi. Ikkalasi qolsa menyuda bir xil narsalar ikki joyda
ko'rinardi.

Taomlar O'CHIRILMAYDI — ular "Setlar" ga ko'chiriladi. Bo'sh qolgan
bo'lim esa olib tashlanadi.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.models import Category, MenuItem, Restaurant

ESKILAR = ("1 kishilik setlar", "3–4 kishilik setlar")

with SessionLocal() as db:
    restaurant = db.query(Restaurant).filter(Restaurant.slug == "buyuk-istambul").one()
    bolimlar = {
        (c.name or {}).get("uz"): c
        for c in db.query(Category).filter(Category.restaurant_id == restaurant.id)
    }
    setlar = bolimlar.get("Setlar")
    if setlar is None:
        raise SystemExit("\"Setlar\" bo'limi topilmadi — tozalash to'xtatildi")

    for nom in ESKILAR:
        eski = bolimlar.get(nom)
        if eski is None:
            continue
        kochdi = (
            db.query(MenuItem)
            .filter(MenuItem.category_id == eski.id)
            .update({MenuItem.category_id: setlar.id}, synchronize_session=False)
        )
        db.delete(eski)
        print(f"  {nom}: {kochdi} ta taom \"Setlar\" ga ko'chdi, bo'lim o'chirildi")

    db.commit()
    qoldi = db.query(Category).filter(Category.restaurant_id == restaurant.id).count()
    taom = db.query(MenuItem).filter(MenuItem.restaurant_id == restaurant.id).count()
    print(f"\nbo'limlar: {qoldi} | taomlar: {taom}")
