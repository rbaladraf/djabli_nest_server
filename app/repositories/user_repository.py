from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.device import Device
from app.models.user import User, UserRole


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.get(User, user_id)

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.scalar(select(User).where(User.username == username))

    def create(
        self,
        username: str,
        password_hash: str,
        full_name: str,
        role: UserRole,
    ) -> User:
        user = User(
            username=username,
            password_hash=password_hash,
            full_name=full_name,
            role=role,
            is_active=True,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def get_device_by_device_id(self, device_id: str) -> Optional[Device]:
        return self.db.scalar(select(Device).where(Device.device_id == device_id))

    def create_device(
        self,
        device_id: str,
        user_id: int,
        device_name: Optional[str] = None,
        platform: Optional[str] = None,
    ) -> Device:
        device = Device(
            device_id=device_id,
            user_id=user_id,
            device_name=device_name,
            platform=platform,
        )
        self.db.add(device)
        self.db.flush()
        return device

    def touch_device(self, device: Device) -> None:
        from app.utils.datetime_utils import utc_now

        device.last_seen_at = utc_now()
        self.db.flush()
