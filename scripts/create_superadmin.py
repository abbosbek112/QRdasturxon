"""Tizim admini (superadmin) hisobini yaratadi.

Ikki xil ishlatiladi:

  Interaktiv (lokalda):
      .venv/bin/python -m scripts.create_superadmin

  Muhit o'zgaruvchilari bilan (serverda, Docker ichida):
      docker compose exec -T \\
        -e SUPERADMIN_USERNAME=root -e SUPERADMIN_PASSWORD='...' \\
        app python -m scripts.create_superadmin

Ikkinchi yo'l kerak, chunki `docker compose exec -T` da terminal bo'lmaydi va
`input()` darrov xato beradi.
"""

import getpass
import os
import sys

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Role, User
from app.security import hash_password

MIN_USERNAME = 3
MIN_PASSWORD = 8


def _read_username() -> str:
    value = os.environ.get("SUPERADMIN_USERNAME")
    if value is None:
        value = input("Login: ")
    return value.strip().lower()


def _read_password() -> str | None:
    """Parolni oladi. Interaktiv rejimda ikki marta so'raydi."""
    value = os.environ.get("SUPERADMIN_PASSWORD")
    if value is not None:
        return value

    password = getpass.getpass("Parol: ")
    if password != getpass.getpass("Parolni takrorlang: "):
        print("Parollar mos kelmadi.")
        return None
    return password


def main() -> int:
    username = _read_username()
    if len(username) < MIN_USERNAME:
        print(f"Login kamida {MIN_USERNAME} belgidan iborat bo'lsin.")
        return 1

    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.username == username)):
            print(f"'{username}' logini allaqachon band.")
            return 1

        password = _read_password()
        if password is None:
            return 1
        if len(password) < MIN_PASSWORD:
            print(f"Parol kamida {MIN_PASSWORD} belgidan iborat bo'lsin.")
            return 1

        db.add(
            User(
                username=username,
                password_hash=hash_password(password),
                role=Role.superadmin,
            )
        )
        db.commit()

    print(f"Tizim admini yaratildi: {username}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
