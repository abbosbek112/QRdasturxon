"""Tarjima kaliti sahifaga chiqib qolmasin.

`t()` noma'lum kalit uchun kalitning O'ZINI qaytaradi. Ya'ni shablonda
xato yozilgan kalit sahifani buzmaydi — u shunchaki `dl_protect_title`
degan yozuvni ko'rsatadi va buni faqat odam payqaydi.

Bu haqiqatan sodir bo'lgan: `/ilova` sahifasida ikkita kalit tarjima
o'rniga o'z nomi bilan chiqib turgan edi.

Tekshiruv oddiy: ko'rinadigan matnda `pastki_chiziqli` so'z bo'lmasligi
kerak. Hech bir tilda odam o'qiydigan matn bunday yozilmaydi, kalitlar esa
aynan shunday. Shu sababdan mavjud kalitlar ro'yxati bilan solishtirilmaydi
— xato yozilgan kalit ro'yxatda BO'LMAYDI, ya'ni solishtirish aynan kerakli
holatni o'tkazib yuborardi.
"""

import re

import pytest

from app.models import Category, MenuItem, Table

from tests.conftest import login


KALITGA_OXSHASH = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")

# Matnda uchrashi mumkin bo'lgan, kalit bo'lmagan so'zlar. Har biri sababi
# bilan yoziladi — aks holda ro'yxat asta-sekin tekshiruvni bo'shatib
# yuboradi.
RUXSAT: set[str] = {
    "odam_dev",  # bosh sahifadagi Telegram manzili (@odam_dev)
}


def korinadigan_matn(body: str) -> str:
    """HTML dan faqat odam ko'radigan matnni ajratadi.

    `<script>` va `<style>` butunlay tashlanadi: ular ichida pastki
    chiziqli o'zgaruvchi nomlari bo'lishi tabiiy va ular sahifada
    ko'rinmaydi. Teg ichidagi atributlar ham (sinf nomi, manzil) tashqarida
    qoladi, chunki teglar olib tashlanadi.
    """
    body = re.sub(r"<script\b.*?</script>", " ", body, flags=re.S | re.I)
    body = re.sub(r"<style\b.*?</style>", " ", body, flags=re.S | re.I)
    return re.sub(r"<[^>]+>", " ", body)


def sizib_chiqqan(body: str) -> set[str]:
    matn = korinadigan_matn(body)
    return set(KALITGA_OXSHASH.findall(matn)) - RUXSAT


@pytest.fixture
def toliq_restoran(db, tenant_a):
    """Bo'sh sahifada tarjima kamchiligi ko'rinmaydi — mazmun kerak."""
    restaurant, _ = tenant_a
    restaurant.orders_enabled = True

    category = Category(restaurant_id=restaurant.id, name={"uz": "Taomlar"})
    db.add(category)
    db.flush()
    db.add(
        MenuItem(
            restaurant_id=restaurant.id,
            category_id=category.id,
            name={"uz": "Osh"},
            price=38000,
            is_spicy=True,
            is_vegetarian=True,
        )
    )
    db.add(Table(restaurant_id=restaurant.id, label="1", code="sinovkod"))
    db.commit()
    return restaurant


@pytest.mark.parametrize("lang", ["uz", "ru", "en"])
@pytest.mark.parametrize(
    "path",
    [
        "/admin",
        "/admin/categories",
        "/admin/items",
        "/admin/items/new",
        "/admin/tables",
        "/admin/staff",
        "/admin/orders",
        "/admin/stats",
        "/admin/comments",
        "/admin/qr",
        "/admin/settings",
    ],
)
def test_admin_pages_have_no_raw_keys(client, toliq_restoran, path, lang):
    login(client, "osh", "adminpass123")
    body = client.get(f"{path}?lang={lang}").text

    qolgan = sizib_chiqqan(body)
    assert not qolgan, f"{path} [{lang}] — tarjimasiz kalit: {sorted(qolgan)}"


@pytest.mark.parametrize("lang", ["uz", "ru", "en"])
@pytest.mark.parametrize("path", ["/", "/ilova", "/r/osh", "/login", "/signup"])
def test_public_pages_have_no_raw_keys(client, toliq_restoran, path, lang):
    body = client.get(f"{path}?lang={lang}").text

    qolgan = sizib_chiqqan(body)
    assert not qolgan, f"{path} [{lang}] — tarjimasiz kalit: {sorted(qolgan)}"


def test_the_check_catches_a_missing_key(client, toliq_restoran):
    """Tekshiruvning o'zi ishlashiga ishonch.

    Birinchi variantda bu tekshiruv faqat MAVJUD kalitlarni qidirardi va
    shu sababdan hech qachon yiqilmasdi: xato yozilgan kalit ro'yxatda
    bo'lmaydi. Mutatsiya sinovi shuni ko'rsatdi.
    """
    # Aynan shunday ko'rinadi: shablonda `t('nav_stats_yoq', ...)` yozilsa
    assert sizib_chiqqan("<p>nav_stats_yoq</p>") == {"nav_stats_yoq"}

    # Teg ichidagi sinf nomi va manzil xato deb hisoblanmasin
    assert sizib_chiqqan('<div class="hall_card"><a href="/a_b">Salom</a></div>') == set()
    # Skript ichidagi o'zgaruvchi ham
    assert sizib_chiqqan('<script>var raw_key = 1;</script>') == set()
    # Oddiy matn tinch qolsin
    assert sizib_chiqqan("<p>Buyurtmangiz yuborildi</p>") == set()
