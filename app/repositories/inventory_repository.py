from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory import InventoryLot


class InventoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_batch(self, batch_uuid: str) -> List[InventoryLot]:
        stmt = select(InventoryLot).where(InventoryLot.batch_uuid == batch_uuid)
        return list(self.db.scalars(stmt).all())
