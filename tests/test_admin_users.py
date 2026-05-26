import pytest

from app.core.security import get_password_hash
from app.models.user import User, UserRole
from tests.conftest import auth_header


@pytest.fixture
def seed_superadmin(db):
    sa = User(
        username="superadmin_test",
        password_hash=get_password_hash("super12345"),
        full_name="Super Admin Test",
        role=UserRole.SUPERADMIN,
        is_active=True,
    )
    db.add(sa)
    db.commit()
    db.refresh(sa)
    return sa


@pytest.fixture
def superadmin_token(client, seed_users, seed_superadmin):
    r = client.post(
        "/api/auth/login",
        json={"username": "superadmin_test", "password": "super12345"},
    )
    assert r.status_code == 200
    return r.json()["access_token"]


def _create_mobile_payload(username: str) -> dict:
    return {
        "username": username,
        "password": "password123",
        "full_name": f"Collector {username}",
        "role": "MOBILE_USER",
        "is_active": True,
    }


def test_superadmin_create_mobile_user(client, superadmin_token):
    r = client.post(
        "/api/admin/users",
        json=_create_mobile_payload("collector_sa"),
        headers=auth_header(superadmin_token),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["username"] == "collector_sa"
    assert body["role"] == "MOBILE_USER"
    assert "password_hash" not in body
    assert "password" not in body


def test_admin_create_mobile_user(client, admin_token):
    r = client.post(
        "/api/admin/users",
        json=_create_mobile_payload("collector_admin"),
        headers=auth_header(admin_token),
    )
    assert r.status_code == 201
    assert r.json()["role"] == "MOBILE_USER"


def test_admin_cannot_create_admin(client, admin_token):
    r = client.post(
        "/api/admin/users",
        json={
            "username": "newadmin01",
            "password": "password123",
            "full_name": "New Admin",
            "role": "ADMIN",
            "is_active": True,
        },
        headers=auth_header(admin_token),
    )
    assert r.status_code == 403


def test_mobile_user_cannot_access_admin_users(client, mobile_token):
    r = client.get("/api/admin/users", headers=auth_header(mobile_token))
    assert r.status_code == 403


def test_duplicate_username_returns_409(client, admin_token):
    payload = _create_mobile_payload("collector_dup")
    headers = auth_header(admin_token)
    assert client.post("/api/admin/users", json=payload, headers=headers).status_code == 201
    r2 = client.post("/api/admin/users", json=payload, headers=headers)
    assert r2.status_code == 409


def test_deactivate_user_then_login_fails(client, admin_token):
    create = client.post(
        "/api/admin/users",
        json=_create_mobile_payload("collector_off"),
        headers=auth_header(admin_token),
    )
    user_id = create.json()["id"]
    off = client.post(
        f"/api/admin/users/{user_id}/deactivate",
        headers=auth_header(admin_token),
    )
    assert off.status_code == 200
    login = client.post(
        "/api/auth/login",
        json={"username": "collector_off", "password": "password123"},
    )
    assert login.status_code == 403
    assert "inactive" in login.json()["detail"].lower()


def test_reset_password_then_login_with_new_password(client, admin_token):
    create = client.post(
        "/api/admin/users",
        json=_create_mobile_payload("collector_pwd"),
        headers=auth_header(admin_token),
    )
    user_id = create.json()["id"]
    reset = client.post(
        f"/api/admin/users/{user_id}/reset-password",
        json={"new_password": "newpassword99"},
        headers=auth_header(admin_token),
    )
    assert reset.status_code == 200
    old_login = client.post(
        "/api/auth/login",
        json={"username": "collector_pwd", "password": "password123"},
    )
    assert old_login.status_code == 401
    new_login = client.post(
        "/api/auth/login",
        json={"username": "collector_pwd", "password": "newpassword99"},
    )
    assert new_login.status_code == 200
    assert "access_token" in new_login.json()
