"""Tizim admini (superadmin) hisobini yaratadi.

Ishlatish:  .venv/bin/python -m scripts.create_superadmin
"""

import getpass
import sys

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Role, User
from app.security import hash_password


def main() -> int:
    username = input("Login: ").strip().lower()
    if len(username) < 3:
        print("Login kamida 3 belgidan iborat bo'lsin.")
        return 1

    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.username == username)):
            print(f"'{username}' logini allaqachon band.")
            return 1

        password = getpass.getpass("Parol: ")
        if len(password) < 8:
            print("Parol kamida 8 belgidan iborat bo'lsin.")
            return 1
        if password != getpass.getpass("Parolni takrorlang: "):
            print("Parollar mos kelmadi.")
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
