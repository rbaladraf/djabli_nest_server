import io
import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.main import app
from app.models.device import Device
from app.models.user import User, UserRole
from app.utils.hash_utils import sha256_hex
from app.utils.id_utils import new_uuid

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://djabli:djabli_secret@localhost:5432/djablinest_test",
)


def _use_sqlite() -> bool:
    return os.getenv("USE_SQLITE_TESTS", "1") == "1"


@pytest.fixture(scope="session")
def engine():
    if _use_sqlite():
        eng = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        eng = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    Base.metadata.drop_all(bind=eng)
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture
def db(engine) -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    TestingSession = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    session = TestingSession()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db: Session, tmp_path) -> Generator[TestClient, None, None]:
    os.environ["UPLOAD_DIR"] = str(tmp_path / "uploads")

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def seed_users(db: Session):
    admin = User(
        username="admin_test",
        password_hash=get_password_hash("admin123"),
        full_name="Admin Test",
        role=UserRole.ADMIN,
        is_active=True,
    )
    mobile = User(
        username="mobile_test",
        password_hash=get_password_hash("mobile123"),
        full_name="Mobile Test",
        role=UserRole.MOBILE_USER,
        is_active=True,
    )
    db.add_all([admin, mobile])
    db.flush()
    device = Device(
        device_id="device-test-001",
        user_id=mobile.id,
        device_name="Test Phone",
        platform="android",
    )
    db.add(device)
    db.commit()
    return {"admin": admin, "mobile": mobile, "device_id": device.device_id}


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_token(client: TestClient, seed_users):
    r = client.post("/api/auth/login", json={"username": "admin_test", "password": "admin123"})
    assert r.status_code == 200
    return r.json()["access_token"]


@pytest.fixture
def mobile_token(client: TestClient, seed_users):
    r = client.post("/api/mobile/auth/login", json={"username": "mobile_test", "password": "mobile123"})
    assert r.status_code == 200
    return r.json()["access_token"]


def make_dummy_jpeg() -> bytes:
    return (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xd9"
    )


@pytest.fixture
def dummy_jpeg():
    return make_dummy_jpeg()
