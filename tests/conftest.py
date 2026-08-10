import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="qrdasturxon-test-")
# Prod Postgres'da ishlaydi, shuning uchun testlarni ham o'sha yerda yugurtirish mumkin:
#   TEST_DATABASE_URL=postgresql+psycopg://user:pass@localhost/qrdasturxon_test pytest
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", f"sqlite:///{_tmp}/test.db"
)
os.environ["MEDIA_DIR"] = f"{_tmp}/media"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["BASE_URL"] = "http://testserver"
os.environ["DEBUG"] = "true"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from argon2 import PasswordHasher  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import BASE_DIR  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import LoginAttempt, Restaurant, Role, User  # noqa: E402
from app.plans import start_trial  # noqa: E402
from app import security  # noqa: E402
from app.security import hash_password  # noqa: E402


# Argon2 ATAYLAB sekin — parol sindirishni qimmat qilish uning butun vazifasi.
# Lekin testlarda yuzlab marta login qilinadi va o'sha sekinlik to'plamning
# uchdan ikki qismini yeb qo'yadi. Bu yerda kuchini eng pastga tushiramiz:
# tekshirilayotgan narsa xesh kuchi emas, uning ATROFIDAGI mantiq.
#
# Prod parametrlariga tegilmaydi — `app/security.py` o'z holicha qoladi.
security._hasher = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1)


@pytest.fixture(scope="session", autouse=True)
def _schema():
    """Jadvallarni migratsiyalar orqali quradi.

    `Base.metadata.create_all` emas — shunda har test yugurishida migratsiyalar
    ham tekshiriladi va "modelda bor, migratsiyada yo'q" holati darrov bilinadi.
    """
    config = Config(BASE_DIR / "alembic.ini")
    config.set_main_option("script_location", str(BASE_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])

    Base.metadata.drop_all(engine)  # oldingi yugurishdan qolgani bo'lsa
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")

    command.upgrade(config, "head")
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture(autouse=True)
def _clean_db(_schema):
    with SessionLocal() as session:
        # Restaurant o'chirilganda menu_views/categories/items kaskad bilan ketadi;
        # login_attempts esa hech kimga bog'lanmagan, uni alohida tozalaymiz
        for model in (LoginAttempt, User, Restaurant):
            session.query(model).delete()
        session.commit()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def superadmin(db):
    user = User(
        username="root", password_hash=hash_password("rootpass123"), role=Role.superadmin
    )
    db.add(user)
    db.commit()
    return user


def make_restaurant(db, *, slug: str, username: str) -> tuple[Restaurant, User]:
    restaurant = Restaurant(name=slug.title(), slug=slug)
    # Haqiqiy ro'yxatdan o'tish doim start_trial() ni chaqiradi. Busiz
    # trial_ends_at bo'sh qolardi va menyu "muddati tugagan" deb yopilardi —
    # ya'ni testlar hech qachon uchramaydigan holatni tekshirardi.
    start_trial(restaurant)
    db.add(restaurant)
    db.flush()
    user = User(
        username=username,
        password_hash=hash_password("adminpass123"),
        role=Role.restaurant_admin,
        restaurant_id=restaurant.id,
    )
    db.add(user)
    db.commit()
    return restaurant, user


@pytest.fixture
def tenant_a(db):
    return make_restaurant(db, slug="osh-markazi", username="osh")


@pytest.fixture
def tenant_b(db):
    return make_restaurant(db, slug="choyxona", username="choy")


def csrf(client: TestClient, path: str = "/login") -> str:
    import re

    html = client.get(path).text
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, f"csrf_token topilmadi: {path}"
    return match.group(1)


def login(client: TestClient, username: str, password: str) -> None:
    token = csrf(client, "/login")
    response = client.post(
        "/login", data={"username": username, "password": password, "csrf_token": token}
    )
    assert response.status_code == 200, response.text
