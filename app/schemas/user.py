from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.user import UserRole
from app.schemas.common import ORMBase


class UserOut(ORMBase):
    id: int
    username: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=4, max_length=64)
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=255)
    role: UserRole = UserRole.MOBILE_USER
    is_active: bool = True


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8)
