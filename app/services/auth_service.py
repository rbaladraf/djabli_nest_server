import time
from collections import defaultdict
from typing import Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, verify_password
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService

settings = get_settings()
_login_attempts: dict[str, list[float]] = defaultdict(list)


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.audit = AuditService(db)

    def _check_rate_limit(self, key: str) -> None:
        now = time.time()
        window = 60.0
        attempts = _login_attempts[key]
        _login_attempts[key] = [t for t in attempts if now - t < window]
        if len(_login_attempts[key]) >= settings.LOGIN_RATE_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Try again later.",
            )
        _login_attempts[key].append(now)

    def login(
        self,
        username: str,
        password: str,
        *,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        allowed_roles: Optional[set[UserRole]] = None,
    ) -> Tuple[str, User]:
        self._check_rate_limit(username)
        user = self.users.get_by_username(username)
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User inactive")
        if allowed_roles and user.role not in allowed_roles and user.role != UserRole.SUPERADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role not allowed")
        token = create_access_token(user.username, user.role.value, user.id)
        self.audit.log("LOGIN", user.id, ip_address=ip_address, user_agent=user_agent)
        self.db.commit()
        return token, user
