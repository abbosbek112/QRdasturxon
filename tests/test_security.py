import html

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from pydantic import ValidationError

from app.config import INSECURE_SECRET, Settings
from app.database import Base, SessionLocal, engine
from app.models import LoginAttempt, Restaurant
from app.security import MAX_ATTEMPTS

from tests.conftest import csrf, login


def test_models_and_migrations_stay_in_sync():
    """Modelni o'zgartirib migratsiya yozishni unutish — eng oson yo'l qoladigan xato."""
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        differences = compare_metadata(context, Base.metadata)
    assert differences == [], f"Migratsiya yozilmagan o'zgarishlar bor: {differences}"


def test_production_rejects_the_default_secret():
    with pytest.raises(ValidationError) as error:
        Settings(debug=False, secret_key=INSECURE_SECRET, _env_file=None)
    assert "SECRET_KEY" in str(error.value)


def test_production_rejects_a_short_secret():
    with pytest.raises(ValidationError) as error:
        Settings(debug=False, secret_key="qisqa", _env_file=None)
    assert "qisqa" in str(error.value) or "belgi" in str(error.value)


def test_debug_mode_allows_the_default_secret():
    """Lokal ishlashga xalaqit bermasin — tekshiruv faqat prod rejimida."""
    assert Settings(debug=True, secret_key=INSECURE_SECRET, _env_file=None).debug


def test_security_headers_are_sent(client, tenant_a):
    restaurant, _ = tenant_a
    headers = client.get(f"/r/{restaurant.slug}").headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert "strict-origin" in headers["referrer-policy"]
    # Barcha JS tashqi faylda — shuning uchun inline skriptga ruxsat bermaymiz
    assert "script-src 'self'" in headers["content-security-policy"]


def test_repeated_failures_lock_the_login(client, tenant_a):
    token = csrf(client)
    for _ in range(MAX_ATTEMPTS):
        client.post(
            "/login",
            data={"csrf_token": token, "username": "osh", "password": "notogri"},
        )

    blocked = client.post(
        "/login",
        data={"csrf_token": token, "username": "osh", "password": "adminpass123"},
    )
    assert "Juda ko'p urinish" in html.unescape(blocked.text)


def test_login_lock_survives_a_restart(client, tenant_a):
    """Cheklov bazada — server o'chib yonsa ham kuchida qolishi kerak."""
    token = csrf(client)
    for _ in range(MAX_ATTEMPTS):
        client.post(
            "/login",
            data={"csrf_token": token, "username": "osh", "password": "notogri"},
        )

    with SessionLocal() as session:
        assert session.query(LoginAttempt).count() == MAX_ATTEMPTS

    # Yangi klient = yangi sessiya, xuddi qayta ishga tushgandek
    blocked = client.post(
        "/login",
        data={"csrf_token": csrf(client), "username": "osh", "password": "adminpass123"},
    )
    assert "Juda ko'p urinish" in html.unescape(blocked.text)


def test_successful_login_clears_the_counter(client, tenant_a):
    token = csrf(client)
    client.post(
        "/login", data={"csrf_token": token, "username": "osh", "password": "notogri"}
    )
    client.post(
        "/login",
        data={"csrf_token": csrf(client), "username": "osh", "password": "adminpass123"},
    )
    with SessionLocal() as session:
        assert session.query(LoginAttempt).count() == 0


# --- ro'yxatdan o'tish cheklovi ---

def _signup(client, n: int):
    return client.post(
        "/signup",
        data={
            "csrf_token": csrf(client, "/signup"),
            "name": f"Kafe {n}",
            "slug": f"kafe-{n}",
            "username": f"kafe{n}",
            "password": "parol12345",
            "phone": "",
            "email": "",
        },
    )


def test_signup_stops_after_the_limit(client, db):
    """Bitta IP cheksiz restoran ocholmasin — yaxshi slug'lar band bo'lib ketmasin."""
    from app.security import MAX_SIGNUPS

    for n in range(MAX_SIGNUPS):
        assert _signup(client, n).status_code == 200

    blocked = _signup(client, 99)
    assert blocked.status_code == 429
    assert db.query(Restaurant).filter_by(slug="kafe-99").first() is None


def test_a_failed_signup_still_counts(client, db):
    """Aks holda ataylab xato yuborib hisoblagichni chetlab o'tish mumkin edi."""
    from app.security import MAX_SIGNUPS

    for _ in range(MAX_SIGNUPS):
        # slug band — signup yiqiladi, lekin urinish baribir sanaladi
        client.post(
            "/signup",
            data={
                "csrf_token": csrf(client, "/signup"),
                "name": "X", "slug": "admin", "username": "x",
                "password": "parol12345", "phone": "", "email": "",
            },
        )

    assert _signup(client, 1).status_code == 429


def test_logging_in_does_not_reset_the_signup_limit(client, db, tenant_a):
    """Eng muhim tarmoq: ikki hisoblagich ALOHIDA bo'lishi kerak.

    Urinishlar bitta jadvalda yotadi va muvaffaqiyatli login o'z IP'sining
    yozuvlarini tozalaydi. Agar signup ham o'sha hisobga qo'shilsa, chegaraga
    yetgan odam bitta login qilib hisoblagichni nolga tushirib olardi —
    ya'ni cheklovni cheksiz aylanib o'tish mumkin bo'lardi.
    """
    from app.security import MAX_SIGNUPS

    for n in range(MAX_SIGNUPS):
        _signup(client, n)
    assert _signup(client, 50).status_code == 429

    # Haqiqiy hisob bilan muvaffaqiyatli kirish (yordamchi o'zi tekshiradi)
    login(client, "osh", "adminpass123")

    # Signup hamon yopiq bo'lishi kerak
    assert _signup(client, 51).status_code == 429


def test_signup_attempts_do_not_lock_out_login(client, db, tenant_a):
    """Teskari tomoni ham: signup urinishlari login'ni bloklab qo'ymasin."""
    from app.security import MAX_SIGNUPS

    for n in range(MAX_SIGNUPS):
        _signup(client, n)

    login(client, "osh", "adminpass123")
    assert client.get("/admin").status_code == 200


# --- chiqishdan keyin "orqaga" -------------------------------------------
#
# Foydalanuvchi topgan xato: chiqib, brauzerning "orqaga" tugmasini bosganda
# oldingi odamning paneli qaytib ko'rinardi. Yangi so'rov baribir kirish
# sahifasiga yuboriladi, lekin ekrandagi ma'lumot allaqachon ko'rilgan
# bo'lardi. Umumiy planshetda bu haqiqiy muammo.


def test_the_panel_is_never_cached(client, tenant_a):
    login(client, "osh", "adminpass123")

    kesh = client.get("/admin").headers.get("cache-control", "")

    assert "no-store" in kesh, "panel keshlansa 'orqaga' bilan qaytib ko'rinadi"


def test_the_waiter_board_is_never_cached(client, tenant_a):
    login(client, "osh", "adminpass123")

    assert "no-store" in client.get("/zal").headers.get("cache-control", "")


def test_the_public_menu_may_still_be_cached(client, tenant_a):
    """Mijoz menyusi keshlansa bo'ladi — u yerda shaxsiy narsa yo'q.

    Hammasini `no-store` qilish menyuni har safar qaytadan yuklashga majbur
    qilardi va sekinlashtirardi.
    """
    restaurant, _ = tenant_a

    kesh = client.get(f"/r/{restaurant.slug}").headers.get("cache-control", "")

    assert "no-store" not in kesh
