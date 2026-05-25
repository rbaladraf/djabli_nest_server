from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.file import BatchFile, FileType, PhotoType


class FileRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_uuid(self, file_uuid: str) -> Optional[BatchFile]:
        return self.db.scalar(select(BatchFile).where(BatchFile.file_uuid == file_uuid))

    def list_by_batch(self, batch_uuid: str) -> List[BatchFile]:
        stmt = select(BatchFile).where(BatchFile.batch_uuid == batch_uuid)
        return list(self.db.scalars(stmt).all())

    def create(self, file_record: BatchFile) -> BatchFile:
        self.db.add(file_record)
        self.db.flush()
        return file_record

    def has_sop_photo_types(self, batch_uuid: str, required: set[PhotoType]) -> bool:
        stmt = select(BatchFile).where(
            BatchFile.batch_uuid == batch_uuid,
            BatchFile.file_type == FileType.SOP_PHOTO,
        )
        files = list(self.db.scalars(stmt).all())
        present = {f.photo_type for f in files if f.photo_type}
        return required.issubset(present)
