from fastapi import APIRouter, Depends, Request

from app.core.deps import CurrentUser, DbSession
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(request: Request, body: LoginRequest, db: DbSession):
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    token, _ = AuthService(db).login(
        body.username,
        body.password,
        ip_address=ip,
        user_agent=ua,
    )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser):
    return UserResponse.model_validate(user)
