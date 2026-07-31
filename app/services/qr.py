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
