import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="qrdasturxon-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["MEDIA_DIR"] = f"{_tmp}/media"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["BASE_URL"] = "http://testserver"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Restaurant, Role, User  # noqa: E402
from app.security import hash_password  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture(autouse=True)
def _clean_db(_schema):
    with SessionLocal() as session:
        for model in (User, Restaurant):
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
