"""Bir martalik xabar: formadan qaytgan xatoni sahifada ko'rsatish uchun.

Nega kerak: forma xatosi (masalan "'3' stoli allaqachon bor") to'liq xato
sahifasiga otvorib yuborardi. Restoran egasi shu payt stollarni ketma-ket
kiritib o'tirgan bo'ladi — bitta takror raqam uni ishidan uzib, boshqa
sahifaga tashlab yuborishi kerak emas. Xabar o'sha sahifaning o'zida
chiqadi va ish davom etadi.

Xabar sessiyada saqlanadi va BIRINCHI ko'rsatilgandan keyin o'chadi, aks
holda u sahifadan sahifaga ergashib yurardi.
"""

from starlette.requests import Request

FLASH_KEY = "flash"


def set_flash(request: Request, text: str, kind: str = "warn") -> None:
    request.session[FLASH_KEY] = {"text": text, "kind": kind}


def pop_flash(request: Request) -> dict | None:
    return request.session.pop(FLASH_KEY, None)
