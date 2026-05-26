from typing import List, Optional

from fastapi import APIRouter, Query

from app.core.deps import AdminUser, DbSession
from app.models.user import UserRole
from app.schemas.user import ResetPasswordRequest, UserCreateRequest, UserOut, UserUpdateRequest
from app.services.user_service import UserService

router = APIRouter(prefix="/api/admin/users", tags=["Admin Users"])


@router.get("", response_model=List[UserOut])
def list_users(
    actor: AdminUser,
    db: DbSession,
    role: Optional[UserRole] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    return UserService(db).list_users(actor, role=role, is_active=is_active, search=search)


@router.post("", response_model=UserOut, status_code=201)
def create_user(actor: AdminUser, db: DbSession, body: UserCreateRequest):
    return UserService(db).create_user(actor, body)


@router.get("/{user_id}", response_model=UserOut)
def get_user(actor: AdminUser, db: DbSession, user_id: int):
    return UserService(db).get_user(actor, user_id)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(actor: AdminUser, db: DbSession, user_id: int, body: UserUpdateRequest):
    return UserService(db).update_user(actor, user_id, body)


@router.post("/{user_id}/reset-password", response_model=UserOut)
def reset_password(actor: AdminUser, db: DbSession, user_id: int, body: ResetPasswordRequest):
    return UserService(db).reset_password(actor, user_id, body.new_password)


@router.post("/{user_id}/activate", response_model=UserOut)
def activate_user(actor: AdminUser, db: DbSession, user_id: int):
    return UserService(db).set_active(actor, user_id, active=True)


@router.post("/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(actor: AdminUser, db: DbSession, user_id: int):
    return UserService(db).set_active(actor, user_id, active=False)
