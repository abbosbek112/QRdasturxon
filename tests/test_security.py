import html

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from pydantic import ValidationError

from app.config import INSECURE_SECRET, Settings
from app.database import Base, SessionLocal, engine
from app.models import LoginAttempt
from app.security import MAX_ATTEMPTS

from tests.conftest import csrf


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
