"""Namuna restoran — "Bodom Kafe".

Bosh sahifadagi "Namunani ko'rish" havolasi shu menyuga olib boradi. Maqsad:
kirgan odam to'liq to'ldirilgan, tirik menyuni ko'rsin — bo'sh qolgan joy
bo'lmasin.

Ishlatish:

    .venv/bin/python -m scripts.seed_demo

Qayta ishga tushirsa bo'ladi: eski namuna butunlay o'chirilib, yangisi
quriladi. Faqat DEMO_SLUG'ga tegadi, boshqa restoranlarga umuman tegmaydi.

Rasmlar scripts/demo_art.py da chiziladi — internetdan hech narsa yuklanmaydi.
Haqiqiy foto qo'yilsa menyu albatta chiroyliroq chiqadi; admin paneldan
istalgan taomning rasmini almashtirsa bo'ladi.
"""

from __future__ import annotations

import os
import random
import secrets
import sys
import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import (
    Category,
    ItemComment,
    MenuItem,
    MenuView,
    Plan,
    Restaurant,
    Role,
    SubscriptionStatus,
    User,
)
from app.security import hash_password
from scripts import demo_art

DEMO_SLUG = "bodom"
DEMO_USERNAME = "bodom"
ACCENT = "#b45309"


def demo_password() -> str:
    """Namuna restoranning admin paroli.

    Kodga yozib qo'yib bo'lmaydi: bu fayl ochiq repozitoriyda turadi va
    o'sha parol bilan istalgan odam namuna menyusining paneliga kirib,
    bosh sahifadagi ko'rgazmani buzib ketardi.

    Shuning uchun har safar tasodifiy yasaladi va ekranga chiqariladi.
    Kerak bo'lsa DEMO_PASSWORD bilan o'zingiznikini berasiz.
    """
    return os.environ.get("DEMO_PASSWORD") or secrets.token_urlsafe(12)


RESTAURANT = {
    "name": "Bodom Kafe",
    "description": {
        "uz": "Uy taomlari va qahva. Har kuni yangi pishiriladi.",
        "ru": "Домашняя кухня и кофе. Готовим каждый день заново.",
        "en": "Home cooking and coffee. Freshly made every day.",
    },
    "address": {
        "uz": "Toshkent, Shota Rustaveli ko'chasi, 24",
        "ru": "Ташкент, улица Шота Руставели, 24",
        "en": "24 Shota Rustaveli St, Tashkent",
    },
    "phone": "+998901234567",
    "working_hours": "08:00 – 23:00",
    "instagram": "https://instagram.com/bodomkafe",
    "telegram": "https://t.me/bodomkafe",
    "wifi_name": "Bodom Kafe",
    "wifi_password": "bodom2024",
    "theme": "zamonaviy",
    "theme_color": ACCENT,
}

# (kategoriya, [taomlar]). Har bir taom: art kaliti, nom, tavsif, tarkib,
# narx, daqiqa, belgilar.
MENU: list[tuple[dict, list[dict]]] = [
    (
        {"uz": "Issiq taomlar", "ru": "Горячие блюда", "en": "Hot dishes"},
        [
            {
                "art": "osh",
                "name": {"uz": "Osh", "ru": "Плов", "en": "Plov"},
                "description": {
                    "uz": "Devzira guruch, qo'y go'shti va sariq sabzi. Choyxona usulida.",
                    "ru": "Рис девзира, баранина и жёлтая морковь. По-чайханному.",
                    "en": "Devzira rice, lamb and yellow carrot. Chaikhana style.",
                },
                "ingredients": {
                    "uz": "Guruch, qo'y go'shti, sabzi, piyoz, zira, mayiz",
                    "ru": "Рис, баранина, морковь, лук, зира, изюм",
                    "en": "Rice, lamb, carrot, onion, cumin, raisins",
                },
                "price": 45000, "prep": 25,
                "popular": True, "special": True, "halal": True,
            },
            {
                "art": "lagmon",
                "name": {"uz": "Lag'mon", "ru": "Лагман", "en": "Lagman"},
                "description": {
                    "uz": "Qo'lda cho'zilgan ugra, mol go'shti va sabzavot qaynatmasi.",
                    "ru": "Тянутая вручную лапша, говядина и овощная подлива.",
                    "en": "Hand-pulled noodles, beef and vegetable broth.",
                },
                "ingredients": {
                    "uz": "Ugra, mol go'shti, bulg'or qalampiri, pomidor, sarimsoq",
                    "ru": "Лапша, говядина, болгарский перец, помидор, чеснок",
                    "en": "Noodles, beef, bell pepper, tomato, garlic",
                },
                "price": 38000, "prep": 20,
                "popular": True, "halal": True, "spicy": True,
            },
            {
                "art": "norin",
                "name": {"uz": "Norin", "ru": "Нарын", "en": "Norin"},
                "description": {
                    "uz": "Qo'lda kesilgan xamir va qaynatilgan go'sht. Sovuq uzatiladi.",
                    "ru": "Тонко нарезанное тесто и отварное мясо. Подаётся холодным.",
                    "en": "Thinly cut dough with boiled meat. Served cold.",
                },
                "ingredients": {
                    "uz": "Xamir, qo'y go'shti, qazi, piyoz",
                    "ru": "Тесто, баранина, казы, лук",
                    "en": "Dough, lamb, horse sausage, onion",
                },
                "price": 42000, "prep": 15, "halal": True,
            },
            {
                "art": "manti",
                "name": {"uz": "Manti", "ru": "Манты", "en": "Manti"},
                "description": {
                    "uz": "Bug'da pishirilgan, qo'y go'shti va piyoz bilan. Besh dona.",
                    "ru": "На пару, с бараниной и луком. Пять штук.",
                    "en": "Steamed, with lamb and onion. Five pieces.",
                },
                "ingredients": {
                    "uz": "Xamir, qo'y go'shti, piyoz, dum yog'i",
                    "ru": "Тесто, баранина, лук, курдючный жир",
                    "en": "Dough, lamb, onion, tail fat",
                },
                "price": 35000, "prep": 30, "halal": True,
            },
            {
                "art": "mastava",
                "name": {"uz": "Mastava", "ru": "Мастава", "en": "Mastava"},
                "description": {
                    "uz": "Guruchli issiq sho'rva. Qatiq va ko'kat bilan uzatiladi.",
                    "ru": "Горячий суп с рисом. Подаётся с катыком и зеленью.",
                    "en": "Hot rice soup. Served with yoghurt and herbs.",
                },
                "ingredients": {
                    "uz": "Guruch, mol go'shti, kartoshka, sabzi, pomidor",
                    "ru": "Рис, говядина, картофель, морковь, помидор",
                    "en": "Rice, beef, potato, carrot, tomato",
                },
                "price": 28000, "prep": 15, "halal": True,
            },
        ],
    ),
    (
        {"uz": "Nonushta", "ru": "Завтрак", "en": "Breakfast"},
        [
            {
                "art": "somsa",
                "name": {"uz": "Tandir somsa", "ru": "Тандырная самса", "en": "Tandoor samsa"},
                "description": {
                    "uz": "Tandirda pishirilgan, go'shtli. Ertalab 08:00 dan.",
                    "ru": "Печётся в тандыре, с мясом. С 08:00 утра.",
                    "en": "Baked in a tandoor, with meat. From 8am.",
                },
                "ingredients": {
                    "uz": "Xamir, mol go'shti, piyoz, kunjut",
                    "ru": "Тесто, говядина, лук, кунжут",
                    "en": "Dough, beef, onion, sesame",
                },
                "price": 15000, "prep": 5,
                "popular": True, "halal": True,
            },
        ],
    ),
    (
        {"uz": "Salatlar", "ru": "Салаты", "en": "Salads"},
        [
            {
                "art": "achichuk",
                "name": {"uz": "Achichuk", "ru": "Ачичук", "en": "Achichuk"},
                "description": {
                    "uz": "Yupqa to'g'ralgan pomidor va piyoz. Oshning yonida.",
                    "ru": "Тонко нарезанные помидоры и лук. К плову.",
                    "en": "Thinly sliced tomato and onion. Goes with plov.",
                },
                "ingredients": {
                    "uz": "Pomidor, piyoz, ko'k rayhon, qora murch",
                    "ru": "Помидор, лук, базилик, чёрный перец",
                    "en": "Tomato, onion, basil, black pepper",
                },
                "price": 18000, "prep": 5,
                "vegetarian": True, "halal": True,
            },
        ],
    ),
    (
        {"uz": "Shirinliklar", "ru": "Десерты", "en": "Desserts"},
        [
            {
                "art": "chakchak",
                "name": {"uz": "Chak-chak", "ru": "Чак-чак", "en": "Chak-chak"},
                "description": {
                    "uz": "Asalga botirilgan xamir tayoqchalari. Choy bilan.",
                    "ru": "Тесто в меду. К чаю.",
                    "en": "Honey-soaked dough sticks. With tea.",
                },
                "ingredients": {
                    "uz": "Un, tuxum, asal, shakar",
                    "ru": "Мука, яйцо, мёд, сахар",
                    "en": "Flour, egg, honey, sugar",
                },
                "price": 22000, "prep": 5,
                "vegetarian": True, "halal": True,
            },
        ],
    ),
    (
        {"uz": "Ichimliklar", "ru": "Напитки", "en": "Drinks"},
        [
            {
                "art": "kapuchino",
                "name": {"uz": "Kapuchino", "ru": "Капучино", "en": "Cappuccino"},
                "description": {
                    "uz": "Ikki qavat espresso va bug'langan sut.",
                    "ru": "Двойной эспрессо и вспененное молоко.",
                    "en": "Double espresso with steamed milk.",
                },
                "ingredients": {
                    "uz": "Espresso, sut",
                    "ru": "Эспрессо, молоко",
                    "en": "Espresso, milk",
                },
                "price": 25000, "prep": 5,
                "popular": True, "vegetarian": True, "halal": True,
            },
            {
                "art": "choy",
                "name": {"uz": "Ko'k choy", "ru": "Зелёный чай", "en": "Green tea"},
                "description": {
                    "uz": "Bir choynak. Qaytadan quyish bepul.",
                    "ru": "Чайник. Долив бесплатно.",
                    "en": "A full pot. Refills are free.",
                },
                "ingredients": {"uz": "Ko'k choy", "ru": "Зелёный чай", "en": "Green tea"},
                "price": 8000, "prep": 5,
                "vegetarian": True, "halal": True,
            },
        ],
    ),
]

# (taom, ism, izoh, yulduz). Baholar ataylab bir xil emas — namunada
# "hammasi 5" degan ishonarsiz manzara chiqmasin.
COMMENTS = [
    ("osh", "Sardor", "Choyxona oshidan qolishmaydi. Sabzisi ham xuddi kerakligicha.", 5),
    ("osh", "Nigora", "Tushlikda keldik, issiq va yangi edi. Rahmat.", 5),
    ("osh", "Bekzod", "Mazasi joyida, lekin biroz kutdik.", 4),
    ("kapuchino", "Jasur", "Sut ko'pigi zo'r. Ertalabki qahva shu yerdan endi.", 5),
    ("kapuchino", "Zilola", "Yaxshi, lekin men uchun sal shirinroq edi.", 4),
    ("somsa", "Malika", "08:00 da keling — tandirdan endi chiqqanini berishadi.", 5),
    ("lagmon", "Otabek", "Ugra qo'lda cho'zilgani sezilib turadi.", 4),
    ("mastava", "Kamola", "Sovuq kunda ayni muddao.", 3),
]


VIEW_DAYS = 90


def _seed_views(db, restaurant_id: int, item_ids: list[int]) -> int:
    """Ishonarli ko'rinadigan ochilish tarixi.

    Tasodifiy son emas, naqshli: dam olish kunlari ko'proq, kunlar orasida
    tebranish bor va ommabop taomlar ko'proq ochiladi. Shunday bo'lmasa
    statistika sahifasi tekis chiziq ko'rsatib, hech narsani tushuntirmasdi.
    """
    rng = random.Random(2026)
    last = date.today()
    total = 0

    for offset in range(VIEW_DAYS):
        day = last - timedelta(days=offset)
        # Dam olish kunlari jonliroq, hafta o'rtasi tinchroq
        base = 46 if day.weekday() >= 4 else 28
        # Yaqin kunlar ko'proq — kafe asta-sekin tanilib borgandek
        growth = 1 + (VIEW_DAYS - offset) / VIEW_DAYS * 0.6
        menu_opens = max(3, int(rng.gauss(base * growth, base * 0.22)))

        db.add(MenuView(restaurant_id=restaurant_id, item_id=None, day=day, count=menu_opens))
        total += menu_opens

        # Menyuni ochgan har bir mijoz o'rtacha bir-ikkita taomni bosadi.
        # Ro'yxat boshidagi taomlar ko'proq ko'ziga tashlanadi.
        for index, item_id in enumerate(item_ids):
            share = 0.42 / (1 + index * 0.55)
            clicks = int(menu_opens * share * rng.uniform(0.6, 1.4))
            if clicks:
                db.add(MenuView(restaurant_id=restaurant_id, item_id=item_id, day=day, count=clicks))
    db.commit()
    return total


def _save(image, restaurant_id: int) -> str:
    """Rasmni media papkasiga WebP qilib yozadi va nisbiy yo'lini qaytaradi."""
    directory = settings.media_path / str(restaurant_id)
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.webp"
    image.save(directory / filename, "WEBP", quality=84, method=4)
    return f"{restaurant_id}/{filename}"


def main() -> int:
    password = demo_password()
    accent_rgb = tuple(int(ACCENT[i:i + 2], 16) for i in (1, 3, 5))

    with SessionLocal() as db:
        existing = db.scalar(select(Restaurant).where(Restaurant.slug == DEMO_SLUG))
        if existing:
            print(f"Eski namuna o'chirilmoqda (id={existing.id})")
            # Bazadagi qatorlar cascade bilan ketadi, lekin fayllar diskda
            # qolib ketardi — har qayta yugurtirishda media papkasi shishardi.
            old_media = settings.media_path / str(existing.id)
            if old_media.is_dir():
                for path in old_media.iterdir():
                    if path.is_file():
                        path.unlink()
                old_media.rmdir()
            db.delete(existing)          # cascade: kategoriya, taom, izoh, foydalanuvchi
            db.commit()

        clash = db.scalar(select(User).where(User.username == DEMO_USERNAME))
        if clash:
            print(f"'{DEMO_USERNAME}' logini band — namuna yaratilmadi", file=sys.stderr)
            return 1

        restaurant = Restaurant(
            slug=DEMO_SLUG,
            plan=Plan.full,
            subscription_status=SubscriptionStatus.active,
            **RESTAURANT,
        )
        db.add(restaurant)
        db.flush()

        restaurant.cover_image = _save(demo_art.cover(accent_rgb), restaurant.id)
        restaurant.logo = _save(demo_art.logo(accent_rgb), restaurant.id)

        db.add(User(
            username=DEMO_USERNAME,
            password_hash=hash_password(password),
            role=Role.restaurant_admin,
            restaurant_id=restaurant.id,
        ))

        by_art: dict[str, MenuItem] = {}
        for order, (category_name, dishes) in enumerate(MENU):
            category = Category(
                restaurant_id=restaurant.id, name=category_name, sort_order=order
            )
            db.add(category)
            db.flush()

            for index, dish in enumerate(dishes):
                item = MenuItem(
                    restaurant_id=restaurant.id,
                    category_id=category.id,
                    name=dish["name"],
                    description=dish["description"],
                    ingredients=dish["ingredients"],
                    price=Decimal(dish["price"]),
                    prep_minutes=dish["prep"],
                    image=_save(demo_art.DISHES[dish["art"]](), restaurant.id),
                    is_popular=dish.get("popular", False),
                    is_special=dish.get("special", False),
                    is_spicy=dish.get("spicy", False),
                    is_vegetarian=dish.get("vegetarian", False),
                    is_halal=dish.get("halal", False),
                    sort_order=index,
                )
                db.add(item)
                by_art[dish["art"]] = item
        db.flush()

        for art, author, body, stars in COMMENTS:
            db.add(ItemComment(
                restaurant_id=restaurant.id,
                item_id=by_art[art].id,
                author_name=author,
                body=body,
                rating=stars,
                ip="seed",
                is_approved=True,
            ))

        db.commit()

        opens = _seed_views(db, restaurant.id, [item.id for item in by_art.values()])

        items = sum(len(dishes) for _, dishes in MENU)
        print(f"Tayyor: /r/{DEMO_SLUG} — {len(MENU)} kategoriya, {items} taom, {len(COMMENTS)} izoh")
        print(f"Statistika: {VIEW_DAYS} kunlik tarix, {opens} ta menyu ochilishi")
        print(f"Admin:  {DEMO_USERNAME} / {password}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
