"""Setlarni kishi soni bo'yicha ajratadi va menyuning boshiga chiqaradi.

Mijoz "to'rt kishimiz" deb keladi, "kabob bo'limi" deb emas. Shuning
uchun kishi soni BIRINCHI bo'linish bo'ladi: menyu ochilishi bilan
"1 kishilik", "2 kishilik", "4 kishilik" degan bo'limlar ko'rinadi.

Bo'linish faqat "Setlar" bo'limidan olinmaydi. Steyk va kabob
bo'limlarida ham "Asado 4 kisi", "Bon file 6 kisilik" kabi to'plamlar
bor va mijoz uchun ular ham xuddi shunday set. Restoran ularni boshqa
javonga qo'ygani mijozning muammosi emas.

Kishi soni NOM va TAVSIFdan o'qiladi, qo'lda yozilmaydi: menyu
yangilanganda yangi setlar o'zi to'g'ri joyga tushadi. Aniqlanmagani
"Setlar" da qoladi va ekranga yozib beriladi — jimgina noto'g'ri
guruhga tashlab yuborilmaydi.
"""

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.models import Category, MenuItem, Restaurant

# Nomdagi "4 kisilik" / "6 kishilik" / "2 kisi"
NOMDA = re.compile(r"(\d+)\s*ki[sş]h?i", re.I)
# Tavsifdagi "4 ta Mercimek", "6 ta Lahmacun" — porsiya soni kishi sonini
# beradi. Ikkalasi ham bo'lsa KATTAsi olinadi: to'plamda mercimek va
# lahmacun bir xil sonda bo'ladi.
TAVSIFDA = re.compile(r"(\d+)\s*ta\s*(?:merci?mek|merjemek|merjmek|lahmacun|lahmajun)", re.I)

GURUHLAR = [
    (1, {"uz": "1 kishilik setlar", "ru": "Сеты на 1 человека", "en": "Sets for 1"}),
    (2, {"uz": "2 kishilik setlar", "ru": "Сеты на 2 человек", "en": "Sets for 2"}),
    (3, {"uz": "3 kishilik setlar", "ru": "Сеты на 3 человек", "en": "Sets for 3"}),
    (4, {"uz": "4 kishilik setlar", "ru": "Сеты на 4 человек", "en": "Sets for 4"}),
    (6, {"uz": "Katta to'plamlar", "ru": "Большие наборы", "en": "Large sharing sets"}),
]

# Shu bo'limlardagi to'plamlar ham ko'chiriladi
QIDIRILADIGAN = {"Setlar", "Steyklar", "Kaboblar", "Nonushtalar"}


def kishi_soni(nom: str, tavsif: str) -> int | None:
    m = NOMDA.search(nom)
    if m:
        return int(m.group(1))
    sonlar = [int(x) for x in TAVSIFDA.findall(tavsif)]
    if sonlar:
        return max(sonlar)
    # Nomida "set" bor, lekin soni yo'q — bitta kishilik deb hisoblanmaydi
    return None


def guruh(soni: int) -> int:
    if soni >= 6:
        return 6
    return soni


with SessionLocal() as db:
    restaurant = db.query(Restaurant).filter(Restaurant.slug == "buyuk-istambul").one()
    bolimlar = {
        (c.name or {}).get("uz"): c
        for c in db.query(Category).filter(Category.restaurant_id == restaurant.id)
    }

    # 1. Takroriylarni yig'ishtiramiz. Qo'lda kiritilganlarida tavsif yo'q,
    #    saytdan kelganida bor — shuning uchun tavsifsizi o'chadi.
    setlar_kat = bolimlar.get("Setlar")
    barcha = db.query(MenuItem).filter(MenuItem.restaurant_id == restaurant.id).all()
    kalit = lambda i: (i.name or {}).get("uz", "").lower().replace("kishilik", "kisilik")
    korilgan: dict[str, MenuItem] = {}
    for i in sorted(barcha, key=lambda x: not (x.description or {}).get("uz")):
        k = kalit(i)
        if k in korilgan:
            print(f"  takror o'chirildi: {(i.name or {}).get('uz')}")
            db.delete(i)
        else:
            korilgan[k] = i
    db.flush()

    # 2. Guruh bo'limlarini yasaymiz — eng tepada
    yasalgan = {}
    for tartib, (soni, nomlar) in enumerate(GURUHLAR, 1):
        kat = bolimlar.get(nomlar["uz"])
        if kat is None:
            kat = Category(restaurant_id=restaurant.id)
            db.add(kat)
            bolimlar[nomlar["uz"]] = kat
        kat.name = nomlar
        kat.sort_order = tartib
        kat.is_active = True
        yasalgan[soni] = kat
    db.flush()

    # 3. Qolgan bo'limlar pastga suriladi
    for nom, kat in bolimlar.items():
        if nom not in [g[1]["uz"] for g in GURUHLAR]:
            kat.sort_order = 10 + kat.sort_order

    # 4. To'plamlarni joyiga qo'yamiz
    hisob = {soni: 0 for soni, _ in GURUHLAR}
    aniqlanmagan = []
    for i in korilgan.values():
        joriy = next((n for n, c in bolimlar.items() if c.id == i.category_id), None)
        if joriy not in QIDIRILADIGAN:
            continue
        nom = (i.name or {}).get("uz", "")
        tavsif = (i.description or {}).get("uz", "") or ""
        # Faqat TO'PLAM ko'chiriladi: nomida yoki tavsifida kishi soni bor
        soni = kishi_soni(nom, tavsif)
        if soni is None:
            if joriy == "Setlar":
                aniqlanmagan.append(nom)
            continue
        i.category_id = yasalgan[guruh(soni)].id
        hisob[guruh(soni)] += 1

    db.commit()

    print("\nkishi soni bo'yicha:")
    for soni, nomlar in GURUHLAR:
        print(f"  {nomlar['uz']:20} {hisob[soni]:3} ta")
    if aniqlanmagan:
        print(f"\naniqlanmadi ({len(aniqlanmagan)} ta) — \"Setlar\" da qoldi:")
        for n in aniqlanmagan:
            print(f"    {n}")

    bosh = [c for c in bolimlar.values()
            if not db.query(MenuItem).filter(MenuItem.category_id == c.id).count()]
    for c in bosh:
        print(f"  bo'sh bo'lim o'chirildi: {(c.name or {}).get('uz')}")
        db.delete(c)
    db.commit()
