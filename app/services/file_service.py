import secrets
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.batch import BatchStatus
from app.models.file import BatchFile, FileType, PhotoType
from app.repositories.batch_repository import BatchRepository
from app.repositories.file_repository import FileRepository
from app.utils.datetime_utils import utc_now
from app.utils.file_utils import (
    build_upload_relative_path,
    ensure_upload_dir,
    guess_mime_type,
    validate_mime_type,
)
from app.utils.hash_utils import sha256_hex
from app.utils.id_utils import new_uuid

settings = get_settings()


class FileService:
    def __init__(self, db: Session):
        self.db = db
        self.files = FileRepository(db)
        self.batches = BatchRepository(db)

    async def upload_batch_file(
        self,
        batch_uuid: str,
        upload: UploadFile,
        file_type: FileType,
        photo_type: Optional[PhotoType],
        client_sha256: Optional[str],
        user_id: int,
    ) -> BatchFile:
        batch = self.batches.get_by_uuid(batch_uuid)
        if not batch:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
        if batch.status == BatchStatus.FINALIZED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot upload to finalized batch",
            )

        content = await upload.read()
        if len(content) > settings.max_upload_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds {settings.MAX_UPLOAD_MB}MB limit",
            )

        mime_type = upload.content_type or guess_mime_type(upload.filename or "file.bin")
        if not validate_mime_type(mime_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid mime type. Allowed: jpg, png, pdf",
            )

        server_sha = sha256_hex(content)
        if client_sha256 and client_sha256.lower() != server_sha:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SHA256 mismatch",
            )

        now = utc_now()
        ext = Path(upload.filename or "file").suffix or ".bin"
        stored_filename = f"{secrets.token_hex(8)}{ext}"
        relative_path = build_upload_relative_path(
            now.year, now.month, batch_uuid, stored_filename
        )
        full_path = ensure_upload_dir(settings.UPLOAD_DIR, relative_path)
        full_path.write_bytes(content)

        record = BatchFile(
            file_uuid=new_uuid(),
            batch_uuid=batch_uuid,
            file_type=file_type,
            photo_type=photo_type,
            original_filename=upload.filename or stored_filename,
            stored_filename=stored_filename,
            relative_path=relative_path,
            mime_type=mime_type,
            size_bytes=len(content),
            sha256=server_sha,
            uploaded_by_user_id=user_id,
        )
        self.files.create(record)
        self.batches.increment_sync_version(batch)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_file_for_download(self, file_uuid: str) -> tuple[BatchFile, Path]:
        record = self.files.get_by_uuid(file_uuid)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        path = Path(settings.UPLOAD_DIR) / record.relative_path
        if not path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File missing on disk")
        return record, path
