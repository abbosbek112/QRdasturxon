from tests.conftest import csrf, login


def test_login_page_renders(client):
    assert client.get("/login").status_code == 200


def test_wrong_password_rejected(client, superadmin):
    token = csrf(client)
    response = client.post(
        "/login", data={"username": "root", "password": "wrong", "csrf_token": token}
    )
    assert response.status_code == 401
    assert "Login yoki parol" in response.text


def test_login_requires_csrf(client, superadmin):
    response = client.post("/login", data={"username": "root", "password": "rootpass123"})
    assert response.status_code == 403


def test_superadmin_lands_on_superadmin_panel(client, superadmin):
    login(client, "root", "rootpass123")
    assert "Restoranlar" in client.get("/superadmin").text


def test_restaurant_admin_cannot_open_superadmin(client, tenant_a):
    login(client, "osh", "adminpass123")
    assert client.get("/superadmin").status_code == 403


def test_anonymous_is_redirected_to_login(client):
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_inactive_user_cannot_log_in(client, db, tenant_a):
    _, user = tenant_a
    user.is_active = False
    db.commit()

    token = csrf(client)
    response = client.post(
        "/login", data={"username": "osh", "password": "adminpass123", "csrf_token": token}
    )
    assert response.status_code == 401
