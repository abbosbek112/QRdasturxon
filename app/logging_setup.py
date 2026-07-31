"""Loglarni sozlash.

Serverda nima bo'layotganini ko'rish uchun. Docker loglarni stdout'dan oladi,
shuning uchun fayl kerak emas: `docker compose logs -f app`.
"""

import logging
import sys

FORMAT = "%(asctime)s %(levelname)-7s %(name)s | %(message)s"


def configure_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(FORMAT, datefmt="%Y-%m-%d %H:%M:%S"))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Har so'rov uchun SQL chiqib ketmasin — kerak bo'lsa qo'lda yoqiladi
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
