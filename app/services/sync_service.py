from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.repositories.batch_repository import BatchRepository
from app.schemas.admin import AdminSyncResponse
from app.schemas.batch import BatchDetailOut
from app.utils.datetime_utils import utc_now


class SyncService:
    def __init__(self, db: Session):
        self.db = db
        self.batches = BatchRepository(db)

    def admin_sync_batches(self, since: Optional[datetime]) -> AdminSyncResponse:
        items = self.batches.list_updated_since(since)
        return AdminSyncResponse(
            server_time=utc_now(),
            items=[BatchDetailOut.model_validate(b) for b in items],
        )
