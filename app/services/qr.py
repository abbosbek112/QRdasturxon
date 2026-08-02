import re
from functools import lru_cache
from io import BytesIO

import qrcode
from qrcode.image.svg import SvgPathImage

from app.config import settings


def menu_url(slug: str) -> str:
    return f"{settings.base_url.rstrip('/')}/r/{slug}"


def _make(slug: str, box_size: int, image_factory=None) -> qrcode.QRCode:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=2,
        image_factory=image_factory,
    )
    qr.add_data(menu_url(slug))
    qr.make(fit=True)
    return qr


def png_bytes(slug: str, box_size: int = 12) -> bytes:
    image = _make(slug, box_size).make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def svg_bytes(slug: str, box_size: int = 12) -> bytes:
    image = _make(slug, box_size, image_factory=SvgPathImage).make_image()
    buffer = BytesIO()
    image.save(buffer)
    return buffer.getvalue()


_XML_PROLOG = re.compile(r"^\s*<\?xml[^>]*\?>\s*")
_FIXED_SIZE = re.compile(r'\s(?:width|height)="[\d.]+mm"')


@lru_cache(maxsize=8)
def svg_markup(slug: str, box_size: int = 6) -> str:
    """Sahifa ichiga to'g'ridan-to'g'ri qo'yiladigan SVG.

    Kutubxona to'liq fayl yasaydi: boshida XML e'loni, ildizida esa qat'iy
    `mm` o'lchami. HTML ichida XML e'loni matn bo'lib qoladi, `mm` esa
    rasmni CSS bilan boshqarib bo'lmaydigan qilib qotiradi — shuning uchun
    ikkalasi ham olib tashlanadi. `viewBox` joyida qoladi, ya'ni o'lcham
    endi butunlay CSS ixtiyorida.

    Natija keshlanadi: manzil `BASE_URL` va slug'dan yig'iladi, ikkalasi
    ham ishlash paytida o'zgarmaydi.
    """
    markup = svg_bytes(slug, box_size).decode("utf-8")
    markup = _XML_PROLOG.sub("", markup)
    return _FIXED_SIZE.sub("", markup, count=2)
