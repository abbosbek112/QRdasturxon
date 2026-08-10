import re
from functools import lru_cache
from io import BytesIO

import qrcode
from qrcode.image.svg import SvgPathImage

from app.config import settings


def _base() -> str:
    return settings.base_url.rstrip("/")


def menu_url(slug: str) -> str:
    return f"{_base()}/r/{slug}"


def table_url(slug: str, code: str) -> str:
    """Stoldagi QR ortidagi manzil.

    Kod stol raqami emas, tasodifiy kalit — aks holda restoran tashqarisidagi
    odam raqamni terib buyurtma bera olardi.
    """
    return f"{_base()}/r/{slug}/t/{code}"


def _make(url: str, box_size: int, image_factory=None) -> qrcode.QRCode:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=2,
        image_factory=image_factory,
    )
    qr.add_data(url)
    qr.make(fit=True)
    return qr


def png_bytes(url: str, box_size: int = 12) -> bytes:
    image = _make(url, box_size).make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def svg_bytes(url: str, box_size: int = 12) -> bytes:
    image = _make(url, box_size, image_factory=SvgPathImage).make_image()
    buffer = BytesIO()
    image.save(buffer)
    return buffer.getvalue()


_XML_PROLOG = re.compile(r"^\s*<\?xml[^>]*\?>\s*")
_FIXED_SIZE = re.compile(r'\s(?:width|height)="[\d.]+mm"')


def inline_svg(url: str, box_size: int = 6) -> str:
    """Sahifa ichiga to'g'ridan-to'g'ri qo'yiladigan SVG.

    Kutubxona to'liq fayl yasaydi: boshida XML e'loni, ildizida esa qat'iy
    `mm` o'lchami. HTML ichida XML e'loni matn bo'lib qoladi, `mm` esa
    rasmni CSS bilan boshqarib bo'lmaydigan qilib qotiradi — shuning uchun
    ikkalasi ham olib tashlanadi. `viewBox` joyida qoladi, ya'ni o'lcham
    endi butunlay CSS ixtiyorida.

    Bu funksiya ATAYLAB keshlanmagan: stollarni chop etish varaqi bir yugurishda
    30 tagacha turli QR yasaydi va ular keshni to'ldirib, undan foyda o'rniga
    zarar chiqardi. Keshlanadigan variant uchun `cached_inline_svg()`.
    """
    markup = svg_bytes(url, box_size).decode("utf-8")
    markup = _XML_PROLOG.sub("", markup)
    return _FIXED_SIZE.sub("", markup, count=2)


@lru_cache(maxsize=8)
def cached_inline_svg(url: str, box_size: int = 6) -> str:
    """Har so'rovda bir xil chiqadigan QR uchun (bosh sahifadagi namuna)."""
    return inline_svg(url, box_size)


def svg_markup(slug: str, box_size: int = 6) -> str:
    """Menyu QR'ining sahifaga qo'yiladigan ko'rinishi."""
    return cached_inline_svg(menu_url(slug), box_size)
