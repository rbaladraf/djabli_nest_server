from typing import List, Optional

from fastapi import APIRouter, Query

from app.core.deps import AdminUser, DbSession
from app.models.batch import BatchStatus
from app.schemas.batch import BatchDetailOut, BatchSummaryOut
from app.schemas.verification import (
    BatchActionWithVerificationResponse,
    BatchVerificationOut,
    FinalizeVerificationRequest,
    QuarantineVerificationRequest,
    ReceiveVerificationRequest,
    RegradeVerificationRequest,
    RejectVerificationRequest,
    ReweighVerificationRequest,
)
from app.services.batch_service import BatchService
from app.services.batch_verification_service import BatchVerificationService
from app.services.sync_service import SyncService
from app.utils.datetime_utils import parse_optional_since

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/sync/batches")
def sync_batches(
    user: AdminUser,
    db: DbSession,
    since: Optional[str] = Query(
        None,
        description="ISO datetime; kosong = sync semua batch",
    ),
):
    return SyncService(db).admin_sync_batches(parse_optional_since(since))


@router.get("/batches", response_model=List[BatchSummaryOut])
def list_batches(
    user: AdminUser,
    db: DbSession,
    status: Optional[BatchStatus] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    batches = BatchService(db).batches.list_batches(status=status, limit=limit, offset=offset)
    return [BatchSummaryOut.model_validate(b) for b in batches]


@router.get("/batches/{batch_uuid}", response_model=BatchDetailOut)
def get_batch(batch_uuid: str, user: AdminUser, db: DbSession):
    return BatchService(db).get_batch_detail(batch_uuid)


@router.get("/batches/{batch_uuid}/verification", response_model=BatchVerificationOut)
def get_verification(batch_uuid: str, user: AdminUser, db: DbSession):
    return BatchVerificationService(db).get_verification(batch_uuid)


@router.get("/batches/{batch_uuid}/photos")
def list_photos(batch_uuid: str, user: AdminUser, db: DbSession):
    from app.repositories.file_repository import FileRepository

    files = FileRepository(db).list_by_batch(batch_uuid)
    return [
        {
            "file_uuid": f.file_uuid,
            "file_type": f.file_type.value,
            "photo_type": f.photo_type.value if f.photo_type else None,
            "original_filename": f.original_filename,
            "mime_type": f.mime_type,
            "size_bytes": f.size_bytes,
            "created_at": f.created_at.isoformat(),
        }
        for f in files
    ]


@router.post("/batches/{batch_uuid}/receive", response_model=BatchActionWithVerificationResponse)
def receive(batch_uuid: str, user: AdminUser, db: DbSession, body: ReceiveVerificationRequest):
    return BatchVerificationService(db).receive(batch_uuid, user, body)


@router.post(
    "/batches/{batch_uuid}/move-to-quarantine",
    response_model=BatchActionWithVerificationResponse,
)
def quarantine(batch_uuid: str, user: AdminUser, db: DbSession, body: QuarantineVerificationRequest):
    return BatchVerificationService(db).move_to_quarantine(batch_uuid, user, body)


@router.post("/batches/{batch_uuid}/reweigh", response_model=BatchActionWithVerificationResponse)
def reweigh(batch_uuid: str, user: AdminUser, db: DbSession, body: ReweighVerificationRequest):
    return BatchVerificationService(db).reweigh(batch_uuid, user, body)


@router.post("/batches/{batch_uuid}/regrade", response_model=BatchActionWithVerificationResponse)
def regrade(batch_uuid: str, user: AdminUser, db: DbSession, body: RegradeVerificationRequest):
    return BatchVerificationService(db).regrade(batch_uuid, user, body)


@router.post("/batches/{batch_uuid}/finalize", response_model=BatchActionWithVerificationResponse)
def finalize(
    batch_uuid: str,
    user: AdminUser,
    db: DbSession,
    body: FinalizeVerificationRequest = FinalizeVerificationRequest(),
):
    return BatchVerificationService(db).finalize(batch_uuid, user, body)


@router.post("/batches/{batch_uuid}/reject", response_model=BatchActionWithVerificationResponse)
def reject(batch_uuid: str, user: AdminUser, db: DbSession, body: RejectVerificationRequest):
    return BatchVerificationService(db).reject(batch_uuid, user, body)
