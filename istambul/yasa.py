"""Buyuk Istambul restoranini menyusi bilan yaratadi.

Setlar KOMBO emas, oddiy TAOM qilib qo'yiladi va tarkibi texkartaga
yoziladi. Sabab: kombo tarkibidagi har taomning menyuda alohida narxi
bo'lishi kerak — u yerdan "qancha tejaysiz" hisoblanadi. Lahmacun va
mercimekning alohida narxi berilmagan, ya'ni kombo qilinsa tejash
raqami o'ylab topilgan bo'lardi. Mijozga ko'rsatiladigan son esa
haqiqiy bo'lishi shart.

Ikki marta ishga tushirilsa mavjud restoranni yangilaydi, ikkinchi
nusxa yasamaydi.
"""

import asyncio
import pathlib
import sys
from decimal import Decimal

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.models import Category, MenuItem, Restaurant, Role, User
from app.plans import start_trial
from app.security import hash_password
from app.services.images import save_image

RASM = pathlib.Path(__file__).parent

SLUG = "buyuk-istambul"
LOGIN = "istambul"

BIR_KISHILIK = [
    ("Tovuqli set", 49000, "tovuqli",
     "1 lahmacun, 1 mercimek, 120 g tovuq doner + garnir",
     "1 лахмаджун, 1 мерджимек, 120 г куриный донер + гарнир",
     "1 lahmacun, 1 mercimek, 120 g chicken doner + side"),
    ("Perzola set", 40000, "perzola",
     "1 lahmacun, 1 mercimek, 1 porsiya tovuq pirzola + garnir",
     "1 лахмаджун, 1 мерджимек, 1 порция куриной котлеты + гарнир",
     "1 lahmacun, 1 mercimek, 1 portion chicken cutlet + side"),
    ("Qanot set", 49000, "qanot",
     "1 lahmacun, 1 mercimek, 1 porsiya tovuq qanot + garnir",
     "1 лахмаджун, 1 мерджимек, 1 порция куриных крылышек + гарнир",
     "1 lahmacun, 1 mercimek, 1 portion chicken wings + side"),
    ("Tovuq shish set", 49000, "tovuq-shish",
     "1 lahmacun, 1 mercimek, 1 porsiya tovuq shish + garnir",
     "1 лахмаджун, 1 мерджимек, 1 порция куриного шиша + гарнир",
     "1 lahmacun, 1 mercimek, 1 portion chicken shish + side"),
    ("Izgara set", 49000, "izgara",
     "1 mercimek, 1 lahmacun, 5 ta kotlet, 1 choy",
     "1 мерджимек, 1 лахмаджун, 5 котлет, 1 чай",
     "1 mercimek, 1 lahmacun, 5 kofte, 1 tea"),
    ("Go'shtli set", 58000, "goshtli",
     "1 mercimek, 1 lahmacun, donerli taom, 1 choy",
     "1 мерджимек, 1 лахмаджун, блюдо с донером, 1 чай",
     "1 mercimek, 1 lahmacun, doner dish, 1 tea"),
]

KOP_KISHILIK = [
    ("Ozod shef 4 kishilik", 300000, "ozod-shef",
     "4 mercimek, 4 lahmacun, choban, mol go'shtli steyk, tovuq qanot, "
     "4 kotlet, beyti sarma, qiymali shashlik",
     "4 мерджимек, 4 лахмаджун, чобан, стейк из говядины, куриные крылышки, "
     "4 котлеты, бейти сарма, шашлык из фарша",
     "4 mercimek, 4 lahmacun, choban salad, beef steak, chicken wings, "
     "4 kofte, beyti sarma, minced kebab"),
    ("Giyos shef set 4 kishilik", 300000, "giyos-shef",
     "4 mercimek, 4 lahmacun, 2 iskandar, 2 shef doner beyti, chiroqchi salat, ezme",
     "4 мерджимек, 4 лахмаджун, 2 искандер, 2 шеф-донер бейти, салат чирокчи, эзме",
     "4 mercimek, 4 lahmacun, 2 iskender, 2 chef doner beyti, chirokchi salad, ezme"),
    ("Gap assorti", 426000, "gap-assorti",
     "6 lahmacun, 6 mercimek, sezar, choban, haydari, ezme, 6 kulcha non, "
     "2×1 l cola, urfa, beyti sarma, biftek, kasap kofte, tovuq qanot, tovuq pirzola",
     "6 лахмаджун, 6 мерджимек, цезарь, чобан, хайдари, эзме, 6 лепёшек, "
     "2×1 л кола, урфа, бейти сарма, бифштекс, касап кёфте, куриные крылышки, куриная котлета",
     "6 lahmacun, 6 mercimek, caesar, choban, haydari, ezme, 6 flatbreads, "
     "2×1 l cola, urfa, beyti sarma, steak, kasap kofte, chicken wings, chicken cutlet"),
    ("3 kishilik assorti", 237000, None,
     "3 lahmacun, 3 mercimek, ezme, urfa, tovuq mangal, adana, mangal qanot, 3 choy",
     "3 лахмаджун, 3 мерджимек, эзме, урфа, куриный мангал, адана, мангал крылышки, 3 чая",
     "3 lahmacun, 3 mercimek, ezme, urfa, grilled chicken, adana, grilled wings, 3 teas"),
]


class Yuklama:
    """`save_image` UploadFile kutadi — bizda esa oddiy fayl."""

    def __init__(self, yol: pathlib.Path):
        self.filename = yol.name
        self._baytlar = yol.read_bytes()

    async def read(self, n: int = -1) -> bytes:
        return self._baytlar


async def rasm_qoy(nom: str | None, restaurant_id: int) -> str | None:
    if not nom:
        return None
    yol = RASM / f"{nom}.webp"
    if not yol.exists():
        print(f"    rasm topilmadi: {yol.name}")
        return None
    return await save_image(Yuklama(yol), restaurant_id, max_width=1000)


async def main(parol: str) -> None:
    with SessionLocal() as db:
        restaurant = db.query(Restaurant).filter(Restaurant.slug == SLUG).one_or_none()
        if restaurant is None:
            restaurant = Restaurant(name="Buyuk Istambul", slug=SLUG)
            start_trial(restaurant)
            db.add(restaurant)
            db.flush()
            print(f"restoran yaratildi: {SLUG}")
        else:
            print(f"restoran bor edi: {SLUG} — menyusi yangilanadi")

        restaurant.description = {
            "uz": "Turk oshxonasi: setlar, lahmacun va mangal taomlari",
            "ru": "Турецкая кухня: сеты, лахмаджун и блюда на мангале",
            "en": "Turkish kitchen: sets, lahmacun and grilled dishes",
        }
        restaurant.theme = "skeyo"
        restaurant.theme_color = "#a41e22"
        restaurant.currency = "so'm"

        egasi = db.query(User).filter(User.username == LOGIN).one_or_none()
        if egasi is None:
            db.add(User(username=LOGIN, password_hash=hash_password(parol),
                        role=Role.restaurant_admin, restaurant_id=restaurant.id))
            print(f"egasi yaratildi: {LOGIN}")
        else:
            egasi.password_hash = hash_password(parol)
            print(f"egasi bor edi: {LOGIN} — paroli yangilandi")

        bolimlar = [
            ({"uz": "1 kishilik setlar", "ru": "Сеты на одного", "en": "Sets for one"},
             BIR_KISHILIK, 1),
            ({"uz": "3–4 kishilik setlar", "ru": "Сеты на 3–4 человек", "en": "Sets for 3–4"},
             KOP_KISHILIK, 2),
        ]
        for nomlar, setlar, tartib in bolimlar:
            kat = db.query(Category).filter(
                Category.restaurant_id == restaurant.id,
                Category.sort_order == tartib,
            ).one_or_none()
            if kat is None:
                kat = Category(restaurant_id=restaurant.id, sort_order=tartib)
                db.add(kat)
            kat.name = nomlar
            kat.is_active = True
            db.flush()
            print(f"\n{nomlar['uz']}:")

            for index, (nom, narx, rasm, t_uz, t_ru, t_en) in enumerate(setlar, 1):
                taom = db.query(MenuItem).filter(
                    MenuItem.restaurant_id == restaurant.id,
                    MenuItem.name["uz"].as_string() == nom,
                ).one_or_none()
                if taom is None:
                    taom = MenuItem(restaurant_id=restaurant.id, category_id=kat.id)
                    db.add(taom)
                taom.category_id = kat.id
                taom.name = {"uz": nom, "ru": nom, "en": nom}
                taom.price = Decimal(narx)
                taom.sort_order = index
                taom.is_available = True
                # Tarkib TEXKARTAGA yoziladi — menyuda ro'yxat bo'lib chiqadi
                taom.ingredients = {"uz": t_uz, "ru": t_ru, "en": t_en}
                if taom.image is None:
                    taom.image = await rasm_qoy(rasm, restaurant.id)
                belgi = "rasm bor" if taom.image else "RASMSIZ"
                print(f"  {nom:26} {narx:>7,} so'm  {belgi}".replace(",", " "))

        db.commit()
        print(f"\nmenyu: /r/{SLUG}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
