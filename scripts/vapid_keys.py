"""Bildirishnoma uchun VAPID kalit juftini yasaydi.

Serverda BIR MARTA yugurtiriladi va natija `.env` ga ko'chiriladi:

    python -m scripts.vapid_keys

Maxfiy kalit hech qachon repoga tushmasligi kerak — `SECRET_KEY` bilan bir
xil tartib. Kalit almashtirilsa mavjud obunalar kuchini yo'qotadi va
afitsantlar bildirishnomani qaytadan yoqishi kerak bo'ladi.
"""

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def _b64(raw: bytes) -> str:
    """URL uchun xavfsiz base64, oxiridagi '=' siz — VAPID shuni kutadi."""
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def generate() -> tuple[str, str]:
    """(ochiq kalit, maxfiy kalit) — ikkalasi ham base64url matn."""
    key = ec.generate_private_key(ec.SECP256R1())

    # Ochiq kalit siqilmagan nuqta ko'rinishida (0x04 + X + Y) = 65 bayt.
    # Brauzer `applicationServerKey` uchun aynan shuni kutadi.
    public = key.public_key().public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )
    private = key.private_numbers().private_value.to_bytes(32, "big")
    return _b64(public), _b64(private)


if __name__ == "__main__":
    public, private = generate()
    print("# .env fayliga qo'shing:")
    print(f"VAPID_PUBLIC_KEY={public}")
    print(f"VAPID_PRIVATE_KEY={private}")
