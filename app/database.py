from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

is_sqlite = settings.database_url.startswith("sqlite")

if is_sqlite:
    engine = create_engine(
        settings.database_url, connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        settings.database_url,
        # Baza qayta ishga tushgandan keyin ulanish "o'lik" bo'lib qolishi mumkin —
        # pre_ping har foydalanishdan oldin uni jimgina tekshiradi
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=1800,
    )

if is_sqlite:

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def seconds_between(earlier, later):
    """Ikki vaqt ustuni orasidagi farq — SONIYADA, SQL ichida hisoblanadi.

    Ikki baza ikki xil yo'l tutadi va bu farq bir joyda turishi kerak:
    SQLite'da `julianday` KUN qaytaradi, PostgreSQL'da esa ayirma interval
    bo'lib chiqadi va undan soniyani `extract(epoch)` ajratadi.

    Bu ikkilanish ilgari `staff.py` ichida yozilgan edi. Ikkinchi joyda
    kerak bo'lganda uni ko'chirib yozish tuzoq bo'lardi: birini
    tuzatib, ikkinchisini unutish oson va xato faqat PRODDA ko'rinardi —
    mahalliy SQLite'da hammasi ishlab turaverardi.
    """
    from sqlalchemy import func

    if is_sqlite:
        return (func.julianday(later) - func.julianday(earlier)) * 86400.0
    return func.extract("epoch", later - earlier)
