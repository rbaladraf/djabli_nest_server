from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.device import Device
from app.models.user import User, UserRole
from app.utils.datetime_utils import utc_now


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.get(User, user_id)

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.scalar(select(User).where(User.username == username))

    def list_users(
        self,
        *,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> List[User]:
        stmt = select(User).order_by(User.id.asc())
        if role is not None:
            stmt = stmt.where(User.role == role)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        if search:
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(User.username.ilike(term), User.full_name.ilike(term)),
            )
        return list(self.db.scalars(stmt).all())

    def create(
        self,
        username: str,
        password_hash: str,
        full_name: str,
        role: UserRole,
        is_active: bool = True,
    ) -> User:
        user = User(
            username=username,
            password_hash=password_hash,
            full_name=full_name,
            role=role,
            is_active=is_active,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def update(self, user: User, **fields) -> User:
        for key, value in fields.items():
            setattr(user, key, value)
        user.updated_at = utc_now()
        self.db.flush()
        return user

    def set_password(self, user: User, password_hash: str) -> User:
        user.password_hash = password_hash
        user.updated_at = utc_now()
        self.db.flush()
        return user

    def set_active(self, user: User, is_active: bool) -> User:
        user.is_active = is_active
        user.updated_at = utc_now()
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
