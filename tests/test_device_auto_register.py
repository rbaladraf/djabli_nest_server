from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from tests.conftest import auth_header
from tests.test_mobile_batch_flow import _batch_payload


def test_batch_auto_registers_unknown_device(client, db):
    user = User(
        username="collector_new",
        password_hash=get_password_hash("mobile123"),
        full_name="Collector New",
        role=UserRole.MOBILE_USER,
        is_active=True,
    )
    db.add(user)
    db.commit()

    login = client.post(
        "/api/mobile/auth/login",
        json={"username": "collector_new", "password": "mobile123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    device_id = "auto-device-xyz-001"
    assert UserRepository(db).get_device_by_device_id(device_id) is None

    payload = _batch_payload(device_id)
    r = client.post(
        "/api/mobile/batches",
        json=payload,
        headers=auth_header(token),
    )
    assert r.status_code == 200, r.text

    device = UserRepository(db).get_device_by_device_id(device_id)
    assert device is not None
    assert device.user_id == user.id


def test_login_auto_registers_device(client, db):
    user = User(
        username="collector_login",
        password_hash=get_password_hash("mobile123"),
        full_name="Collector Login",
        role=UserRole.MOBILE_USER,
        is_active=True,
    )
    db.add(user)
    db.commit()

    device_id = "auto-device-login-001"
    r = client.post(
        "/api/mobile/auth/login",
        json={
            "username": "collector_login",
            "password": "mobile123",
            "device_id": device_id,
            "platform": "android",
        },
    )
    assert r.status_code == 200
    device = UserRepository(db).get_device_by_device_id(device_id)
    assert device is not None
    assert device.user_id == user.id


def test_device_registered_to_other_user_returns_409(client, db, seed_users, mobile_token):
    other = User(
        username="other_mobile",
        password_hash=get_password_hash("mobile123"),
        full_name="Other",
        role=UserRole.MOBILE_USER,
        is_active=True,
    )
    db.add(other)
    db.flush()
    UserRepository(db).create_device("shared-device-001", other.id, platform="android")
    db.commit()

    payload = _batch_payload("shared-device-001")
    r = client.post(
        "/api/mobile/batches",
        json=payload,
        headers=auth_header(mobile_token),
    )
    assert r.status_code == 409
