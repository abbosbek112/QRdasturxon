"""Rasm yuklash.

Bu yerdagi ikki tekshiruv HAQIQIY foydalanuvchi to'sig'idan chiqqan:
kategoriyaga rasm qo'ymoqchi bo'lgan egasi "400 — Fayl rasm emas" degan
yalang'och sahifaga tushib qolgan, yozganlarining hammasi yo'qolgan.

Sabab ikkita edi. Fayl iPhone formatida (HEIC) bo'lgan va Pillow uni
o'zi ocha olmaydi. Ikkinchidan, xato forma sahifasiga qaytmasdan to'liq
xato sahifasini ochib yuborgan.
"""

import html
import io

import pytest
from PIL import Image

from app.models import Category
from app.services import images

from tests.conftest import csrf, login


def rasm_bayt(fmt="PNG", size=(60, 40), mode="RGB") -> bytes:
    buf = io.BytesIO()
    Image.new(mode, size, (200, 120, 40)).save(buf, fmt)
    return buf.getvalue()


@pytest.fixture
def kirgan(client, tenant_a):
    login(client, "osh", "adminpass123")
    return tenant_a[0]


def yubor(client, data, files=None):
    """Kategoriya formasi. Nom uchala tilda ham majburiy, shuning uchun
    chaqiruvchi faqat o'zbekchasini bersa qolgani shu yerda to'ldiriladi —
    har testda uch qatordan yozib chiqish tekshirilayotgan narsani
    ko'rinmas qilib qo'yardi."""
    token = csrf(client, "/admin/menu")
    uz = data.get("name_uz", "")
    toliq = {"name_ru": uz, "name_en": uz, **data}
    return client.post(
        "/admin/categories", data={"csrf_token": token, **toliq}, files=files,
        follow_redirects=False,
    )


# ------------------------------------------------------------------ formatlar


def test_an_iphone_photo_is_accepted(client, db, kirgan):
    """HEIC — iPhone'dan chiqadigan format.

    Pillow uni o'zi ocha olmaydi va shu sababdan haqiqiy foydalanuvchi
    to'silgan edi. `pillow_heif` ro'yxatdan o'tkazilgach ochiladi.
    """
    pillow_heif = pytest.importorskip("pillow_heif")

    buf = io.BytesIO()
    heif = pillow_heif.from_pillow(Image.new("RGB", (60, 40), "red"))
    heif.save(buf, format="HEIF")

    response = yubor(client, {"name_uz": "Issiq"},
                     files={"image": ("photo.heic", buf.getvalue(), "image/heic")})

    assert response.status_code == 303, response.text
    category = db.query(Category).filter(Category.name["uz"].as_string() == "Issiq").one()
    assert category.image and category.image.endswith(".webp")


@pytest.mark.parametrize("fmt, nom", [("PNG", "a.png"), ("JPEG", "a.jpg"),
                                      ("WEBP", "a.webp"), ("BMP", "a.bmp"),
                                      ("TIFF", "a.tif")])
def test_common_formats_are_accepted(client, kirgan, fmt, nom):
    """Ro'yxat keng: egasi formatni bilmaydi va bilishi ham shart emas."""
    response = yubor(client, {"name_uz": f"K{fmt}"},
                     files={"image": (nom, rasm_bayt(fmt), "image/*")})
    assert response.status_code == 303, f"{fmt}: {response.text[:200]}"


def test_a_transparent_png_does_not_turn_black(kirgan):
    """Shaffof fon oq bo'lsin.

    WebP ga RGB bo'lib o'tganda shaffoflik QORA dog' bo'lib chiqardi va
    shaffof logotip menyuda qora to'rtburchak bo'lib turardi.
    """
    import asyncio

    from app.config import settings

    buf = io.BytesIO()
    Image.new("RGBA", (20, 20), (0, 0, 0, 0)).save(buf, "PNG")

    class Soxta:
        filename = "a.png"

        async def read(self, n):
            return buf.getvalue()

    yol = asyncio.run(images.save_image(Soxta(), kirgan.id))
    fayl = settings.media_path / yol
    try:
        with Image.open(fayl) as chiqdi:
            assert chiqdi.convert("RGB").getpixel((5, 5)) == (255, 255, 255)
    finally:
        fayl.unlink(missing_ok=True)


# --------------------------------------------------------------------- xato


def test_a_bad_file_returns_to_the_form_not_a_dead_end(client, kirgan):
    """Xato forma sahifasiga qaytsin, yalang'och 400 sahifasiga emas.

    Egasi kategoriya nomini uch tilda yozib, rasm tanlab yuboradi. Rasm
    rad etilsa u "400" degan bo'sh sahifaga tushar va yozganlarining
    hammasi yo'qolardi.
    """
    response = yubor(client, {"name_uz": "Salatlar"},
                     files={"image": ("hujjat.pdf", b"%PDF-1.4 bu rasm emas", "application/pdf")})

    assert response.status_code == 303
    assert "/admin" in response.headers["location"]


def test_the_reason_is_explained(client, kirgan):
    """Xabar nima qilish kerakligini aytsin."""
    yubor(client, {"name_uz": "Salatlar"},
          files={"image": ("hujjat.pdf", b"not an image", "application/pdf")})

    body = html.unescape(client.get("/admin/menu").text)
    assert "rasm emas" in body
    # Qaysi formatlar mumkinligi ham aytilsin
    assert "HEIC" in body


def test_a_huge_file_is_refused_with_advice(client, kirgan):
    katta = b"\xff\xd8\xff" + b"\x00" * (images.MAX_BYTES + 10)
    response = yubor(client, {"name_uz": "Katta"},
                     files={"image": ("big.jpg", katta, "image/jpeg")})

    assert response.status_code == 303
    assert "5 MB" in client.get("/admin/menu").text


def test_csrf_failures_still_show_the_error_page(client, kirgan):
    """403 yumshoq xabarga aylanmasin — u haqiqiy muammo belgisi."""
    response = client.post("/admin/categories", data={"name_uz": "X"},
                           follow_redirects=False)
    assert response.status_code == 403


def test_an_openable_but_unlisted_format_is_refused(client, db, kirgan):
    """Ruxsat ro'yxati chindan ish bajarsin.

    Pillow o'nlab formatni ochadi — ilmiy FITS, ko'p qatlamli PSD va
    shunga o'xshashlar. Ular rasm bo'lsa ham menyuga tushmasligi kerak:
    ularni ochish qimmat va natijasi oldindan noma'lum.

    Tekshiruv XBM bilan qilinadi: Pillow uni bemalol ochadi, ya'ni
    "rasm emas" yo'liga tushmaydi va FAQAT ro'yxat uni to'sadi. Ro'yxat
    olib tashlansa bu test yiqiladi — mutatsiya bilan tasdiqlangan.
    """
    buf = io.BytesIO()
    Image.new("1", (16, 16)).save(buf, "XBM")

    response = yubor(client, {"name_uz": "Ajabtovur"},
                     files={"image": ("a.xbm", buf.getvalue(), "image/x-xbitmap")})

    assert response.status_code == 303
    # `html.unescape` SHART: apostrof sahifada `&#39;` bo'lib chiqadi va
    # oddiy qidiruv uni topmaydi — test jimgina yiqilardi
    body = html.unescape(client.get("/admin/menu").text)
    assert "XBM" in body and "qo'llab-quvvatlanmaydi" in body
    # Kategoriya rasmsiz ham yaratilmasin — forma butunlay rad etildi
    assert db.query(Category).filter(Category.name["uz"].as_string() == "Ajabtovur").count() == 0
