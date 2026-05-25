from pydantic import BaseModel, Field

from app.models.user import UserRole
from app.schemas.common import ORMBase


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(ORMBase):
    id: int
    username: str
    full_name: str
    role: UserRole
    is_active: bool
