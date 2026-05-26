from fastapi import APIRouter, File, Form, Request, UploadFile

from app.core.config import get_settings
from app.core.deps import DbSession, MobileUser, get_client_meta
from app.models.file import FileType, PhotoType
from app.models.user import UserRole
from app.schemas.auth import TokenResponse
from app.schemas.file import FileUploadResponse
from app.schemas.mobile import (
    MobileBatchResponse,
    MobileBatchStatusResponse,
    MobileCreateBatchRequest,
    MobileLoginRequest,
    MobileSyncConfigResponse,
)
from app.services.auth_service import AuthService
from app.services.batch_service import BatchService
from app.services.device_service import DeviceService
from app.services.file_service import FileService

router = APIRouter(prefix="/api/mobile", tags=["mobile"])
settings = get_settings()


@router.post("/auth/login", response_model=TokenResponse)
def mobile_login(request: Request, body: MobileLoginRequest, db: DbSession):
    meta = get_client_meta(request)
    auth = AuthService(db)
    token, user = auth.login(
        body.username,
        body.password,
        ip_address=meta["ip_address"],
        user_agent=meta["user_agent"],
        allowed_roles={UserRole.MOBILE_USER},
    )
    if body.device_id:
        DeviceService(db).register_or_get_device(
            user,
            body.device_id,
            platform=body.platform,
            device_name=body.device_name,
        )
        db.commit()
    return TokenResponse(access_token=token)


@router.post("/batches", response_model=MobileBatchResponse)
def create_batch(body: MobileCreateBatchRequest, user: MobileUser, db: DbSession):
    batch = BatchService(db).create_mobile_batch(body, user)
    return MobileBatchResponse(
        batch_uuid=batch.batch_uuid,
        batch_code=batch.batch_code,
        status=BatchService(db).get_batch_status_display(batch),
        sync_version=batch.sync_version,
    )


@router.post("/batches/{batch_uuid}/photos", response_model=FileUploadResponse)
async def upload_photo(
    batch_uuid: str,
    user: MobileUser,
    db: DbSession,
    file: UploadFile = File(...),
    file_type: FileType = Form(...),
    photo_type: PhotoType | None = Form(None),
    sha256: str | None = Form(None),
):
    record = await FileService(db).upload_batch_file(
        batch_uuid, file, file_type, photo_type, sha256, user.id
    )
    return FileUploadResponse(
        file_uuid=record.file_uuid,
        batch_uuid=record.batch_uuid,
        relative_path=record.relative_path,
        sha256=record.sha256,
    )


@router.post("/batches/{batch_uuid}/submit", response_model=MobileBatchResponse)
def submit_batch(batch_uuid: str, user: MobileUser, db: DbSession):
    batch = BatchService(db).submit_batch(batch_uuid, user)
    return MobileBatchResponse(
        batch_uuid=batch.batch_uuid,
        batch_code=batch.batch_code,
        status=batch.status.value,
        sync_version=batch.sync_version,
        message="submitted",
    )


@router.get("/batches/{batch_uuid}/status", response_model=MobileBatchStatusResponse)
def batch_status(batch_uuid: str, user: MobileUser, db: DbSession):
    from fastapi import HTTPException

    batch = BatchService(db).batches.get_by_uuid(batch_uuid)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return MobileBatchStatusResponse(
        batch_uuid=batch.batch_uuid,
        status=BatchService(db).get_batch_status_display(batch),
        sync_version=batch.sync_version,
        submitted_at=batch.submitted_at,
    )


@router.get("/sync/config", response_model=MobileSyncConfigResponse)
def sync_config(user: MobileUser):
    return MobileSyncConfigResponse(max_upload_mb=settings.MAX_UPLOAD_MB)
