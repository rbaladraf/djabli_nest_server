from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreateRequest, UserOut, UserUpdateRequest
from app.utils.datetime_utils import utc_now

ROLE_RANK = {
    UserRole.MOBILE_USER: 1,
    UserRole.ADMIN: 2,
    UserRole.SUPERADMIN: 3,
}


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def _ensure_manager(self, actor: User) -> None:
        if actor.role not in (UserRole.ADMIN, UserRole.SUPERADMIN):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    def _can_assign_role(self, actor: User, target_role: UserRole) -> bool:
        if actor.role == UserRole.SUPERADMIN:
            return True
        if actor.role == UserRole.ADMIN:
            return target_role == UserRole.MOBILE_USER
        return False

    def _can_modify_user(self, actor: User, target: User) -> bool:
        if actor.role == UserRole.SUPERADMIN:
            return True
        if actor.role == UserRole.ADMIN:
            return target.role == UserRole.MOBILE_USER
        return False

    def _validate_role_assignment(self, actor: User, target_role: UserRole, target: Optional[User] = None) -> None:
        if not self._can_assign_role(actor, target_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to assign this role",
            )
        if target and actor.id == target.id:
            current_rank = ROLE_RANK[target.role]
            new_rank = ROLE_RANK[target_role]
            if new_rank > current_rank:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You cannot elevate your own role",
                )

    def list_users(
        self,
        actor: User,
        *,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> List[UserOut]:
        self._ensure_manager(actor)
        users = self.users.list_users(role=role, is_active=is_active, search=search)
        return [UserOut.model_validate(u) for u in users]

    def get_user(self, actor: User, user_id: int) -> UserOut:
        self._ensure_manager(actor)
        user = self.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return UserOut.model_validate(user)

    def create_user(self, actor: User, data: UserCreateRequest) -> UserOut:
        self._ensure_manager(actor)
        self._validate_role_assignment(actor, data.role)

        if self.users.get_by_username(data.username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists",
            )

        try:
            user = self.users.create(
                username=data.username,
                password_hash=get_password_hash(data.password),
                full_name=data.full_name,
                role=data.role,
                is_active=data.is_active,
            )
            self.db.commit()
            self.db.refresh(user)
            return UserOut.model_validate(user)
        except Exception:
            self.db.rollback()
            raise

    def update_user(self, actor: User, user_id: int, data: UserUpdateRequest) -> UserOut:
        self._ensure_manager(actor)
        user = self.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if not self._can_modify_user(actor, user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

        updates = data.model_dump(exclude_unset=True)
        if "role" in updates and updates["role"] is not None:
            self._validate_role_assignment(actor, updates["role"], target=user)

        if not updates:
            return UserOut.model_validate(user)

        self.users.update(user, **updates)
        self.db.commit()
        self.db.refresh(user)
        return UserOut.model_validate(user)

    def reset_password(self, actor: User, user_id: int, new_password: str) -> UserOut:
        self._ensure_manager(actor)
        user = self.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if not self._can_modify_user(actor, user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

        try:
            self.users.set_password(user, get_password_hash(new_password))
            self.db.commit()
            self.db.refresh(user)
            return UserOut.model_validate(user)
        except Exception:
            self.db.rollback()
            raise

    def set_active(self, actor: User, user_id: int, *, active: bool) -> UserOut:
        self._ensure_manager(actor)
        user = self.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if not self._can_modify_user(actor, user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        if actor.id == user.id and not active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot deactivate your own account",
            )

        self.users.set_active(user, active)
        self.db.commit()
        self.db.refresh(user)
        return UserOut.model_validate(user)
