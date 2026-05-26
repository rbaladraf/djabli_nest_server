from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.device import Device
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository


class DeviceService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def register_or_get_device(
        self,
        user: User,
        device_id: str,
        *,
        platform: Optional[str] = None,
        device_name: Optional[str] = None,
    ) -> Device:
        normalized = (device_id or "").strip()
        if not normalized:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="device_id is required",
            )

        existing = self.users.get_device_by_device_id(normalized)
        if existing:
            if existing.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="device_id already registered to another user",
                )
            self.users.touch_device(existing)
            return existing

        if user.role not in (UserRole.MOBILE_USER, UserRole.SUPERADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only mobile users can auto-register devices",
            )

        device = self.users.create_device(
            device_id=normalized,
            user_id=user.id,
            device_name=device_name,
            platform=platform or "android",
        )
        self.users.touch_device(device)
        return device
