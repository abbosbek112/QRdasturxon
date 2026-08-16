"""Yuklangan rasmlarni qabul qilish va WebP ga o'tkazish.

Kirish tomoni ATAYLAB keng, chiqish tomoni esa bitta: qanday format
kelmasin, saqlanadigan fayl har doim WebP bo'ladi. Sabab oddiy —
restoran egasi telefonidan rasm tanlaydi va uning formati nima ekanini
bilmaydi ham. Uni "noto'g'ri format" deb qaytarish bizning muammomizni
uning muammosiga aylantirish bo'lardi.
"""

import uuid
from io import BytesIO

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import settings

MAX_BYTES = 5 * 1024 * 1024

# Ochilgandan keyingi eng katta ruxsat etilgan o'lcham, pikselda.
#
# Fayl hajmi 5 MB bilan chegaralangan, lekin bu YETARLI EMAS: siqilgan
# PNG bir necha yuz kilobayt bo'lib, ochilganda gigabaytlab xotira
# talab qilishi mumkin ("rasm bombasi"). Serverda ikkita ishchi jarayon
# bor va bitta so'rov ularni butun sayt bilan birga yiqitardi.
#
# Pillow'ning o'z chegarasi 89 megapiksel — bu RGB'da 256 MB. Menyudagi
# rasm uchun bu bema'ni katta: eng kattasi 1600 px enida saqlanadi.
# 40 megapiksel (taxminan 8000x5000) har qanday telefon va kamera
# uchun ortig'i bilan yetadi.
MAX_PIXELS = 40_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS

# iPhone rasmlari HEIC formatida keladi va Pillow ularni O'ZI ocha
# olmaydi. Bu haqiqiy foydalanuvchini to'sgan: kategoriyaga rasm
# qo'ymoqchi bo'lgan odam "Fayl rasm emas" degan xatoga urilgan,
# holbuki fayl mutlaqo joyida edi — u shunchaki iPhone'dan olingan.
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:  # pragma: no cover - kutubxona bo'lmasa ham ishlayveradi
    pass

# Ro'yxat keng: telefon va kompyuterdan chiqadigan deyarli hamma narsa.
# Bu yerda YO'Q format kelsa ham fayl rad etilmaydi — pastdagi izohga
# qarang.
ALLOWED_FORMATS = {
    "JPEG", "PNG", "WEBP", "GIF",  # eng ko'p uchraydiganlari
    "HEIF", "AVIF",  # zamonaviy telefonlar
    "BMP", "TIFF", "ICO", "PPM", "TGA", "PCX",  # kompyuterdan chiqadiganlar
}

# Xabar ro'yxatdan YASALADI — ro'yxatga format qo'shilib, xabar eskirib
# qolmasin
_ODDIY = "JPEG, PNG, WEBP, HEIC"


async def save_image(upload: UploadFile, restaurant_id: int, max_width: int = 1200) -> str:
    """Yuklangan rasmni WebP ga o'tkazadi va media ichidagi yo'lini qaytaradi."""
    raw = await upload.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "Rasm hajmi 5 MB dan oshmasin. Telefon galereyasidan tanlaganda "
            "\"kichik hajmda\" variantini tanlang yoki rasmni qirqib yuboring.",
        )
    if not raw:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Fayl bo'sh")

    try:
        with Image.open(BytesIO(raw)) as probe:
            image_format = probe.format
            # `verify()` dan OLDIN tekshiriladi: o'lcham sarlavhadan
            # o'qiladi va butun rasmni xotiraga yozmasdan bilinadi
            kengligi, balandligi = probe.size
            if kengligi * balandligi > MAX_PIXELS:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Rasm juda katta: {kengligi}x{balandligi}. "
                    "Kichikroq rasm tanlang yoki uni qirqib yuboring.",
                )
            probe.verify()
    except Image.DecompressionBombError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Rasm juda katta. Kichikroq rasm tanlang yoki uni qirqib yuboring.",
        )
    except (UnidentifiedImageError, OSError):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Bu fayl rasm emas. {_ODDIY} formatlaridan birini tanlang.",
        )

    if image_format not in ALLOWED_FORMATS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"{image_format} formati qo'llab-quvvatlanmaydi. {_ODDIY} tanlang.",
        )

    try:
        with Image.open(BytesIO(raw)) as image:
            # `exif_transpose` telefonda yonboshlab olingan rasmni
            # to'g'rilaydi: usiz u menyuda yotgan holda chiqardi
            image = ImageOps.exif_transpose(image)
            # Shaffof fon oq bo'lib qolsin: WebP ga RGB bo'lib o'tadi va
            # shaffoflik qora dog' bo'lib chiqib qolardi
            if image.mode in ("RGBA", "LA", "P"):
                fon = Image.new("RGB", image.size, "white")
                nusxa = image.convert("RGBA")
                fon.paste(nusxa, mask=nusxa.split()[-1])
                image = fon
            else:
                image = image.convert("RGB")

            if image.width > max_width:
                height = round(image.height * max_width / image.width)
                image = image.resize((max_width, height), Image.LANCZOS)

            directory = settings.media_path / str(restaurant_id)
            directory.mkdir(parents=True, exist_ok=True)
            filename = f"{uuid.uuid4().hex}.webp"
            image.save(directory / filename, "WEBP", quality=82, method=4)
    except OSError:
        # Fayl boshi to'g'ri, ichi buzuq bo'lsa shu yerga tushadi —
        # 500 emas, tushunarli xabar chiqsin
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Rasmni o'qib bo'lmadi — fayl buzuq bo'lishi mumkin"
        )

    return f"{restaurant_id}/{filename}"


def delete_image(relative_path: str | None) -> None:
    if not relative_path:
        return
    target = (settings.media_path / relative_path).resolve()
    if not target.is_relative_to(settings.media_path.resolve()):
        return
    target.unlink(missing_ok=True)
