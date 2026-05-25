from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.batch import (
    Batch,
    BatchCost,
    BatchPayment,
    BatchPurchaseDetail,
    BatchStatus,
    DealType,
    PaymentMethod,
    SourceType,
)
from app.models.inventory import InventoryLot, RegradingRecord, ReweighingRecord
from app.models.sync import StatusHistory, SyncEvent


class BatchRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_uuid(self, batch_uuid: str, with_relations: bool = False) -> Optional[Batch]:
        stmt = select(Batch).where(
            Batch.batch_uuid == batch_uuid,
            Batch.deleted_at.is_(None),
        )
        if with_relations:
            stmt = stmt.options(
                selectinload(Batch.purchase_details),
                selectinload(Batch.costs),
                selectinload(Batch.payments),
                selectinload(Batch.files),
                selectinload(Batch.reweighing_records),
                selectinload(Batch.regrading_records),
                selectinload(Batch.inventory_lots),
                selectinload(Batch.status_history),
            )
        return self.db.scalar(stmt)

    def list_batches(
        self,
        status: Optional[BatchStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Batch]:
        stmt = (
            select(Batch)
            .where(Batch.deleted_at.is_(None))
            .order_by(Batch.server_updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status:
            stmt = stmt.where(Batch.status == status)
        return list(self.db.scalars(stmt).all())

    def list_updated_since(self, since: Optional[datetime]) -> List[Batch]:
        stmt = (
            select(Batch)
            .where(Batch.deleted_at.is_(None))
            .order_by(Batch.server_updated_at.asc())
        )
        if since:
            stmt = stmt.where(Batch.server_updated_at > since)
        stmt = stmt.options(
            selectinload(Batch.purchase_details),
            selectinload(Batch.costs),
            selectinload(Batch.payments),
            selectinload(Batch.files),
            selectinload(Batch.reweighing_records),
            selectinload(Batch.regrading_records),
            selectinload(Batch.inventory_lots),
            selectinload(Batch.status_history),
        )
        return list(self.db.scalars(stmt).all())

    def create_batch(
        self,
        batch_uuid: str,
        batch_code: str,
        device_id: str,
        created_by_user_id: int,
        farmer_name: str,
        farmer_location: Optional[str],
        latitude: Optional[Decimal],
        longitude: Optional[Decimal],
        note: Optional[str],
        deal_type: DealType,
        mobile_estimated_total_kg: Decimal,
        mobile_estimated_total_amount: Decimal,
        payment_method: PaymentMethod,
        payment_amount: Decimal,
        operational_cost_total: Decimal,
        status: BatchStatus,
    ) -> Batch:
        batch = Batch(
            batch_uuid=batch_uuid,
            batch_code=batch_code,
            device_id=device_id,
            created_by_user_id=created_by_user_id,
            farmer_name=farmer_name,
            farmer_location=farmer_location,
            latitude=latitude,
            longitude=longitude,
            note=note,
            deal_type=deal_type,
            mobile_estimated_total_kg=mobile_estimated_total_kg,
            mobile_estimated_total_amount=mobile_estimated_total_amount,
            payment_method=payment_method,
            payment_amount=payment_amount,
            operational_cost_total=operational_cost_total,
            status=status,
            sync_version=1,
        )
        self.db.add(batch)
        self.db.flush()
        return batch

    def add_purchase_details(self, details: List[BatchPurchaseDetail]) -> None:
        self.db.add_all(details)

    def add_costs(self, costs: List[BatchCost]) -> None:
        self.db.add_all(costs)

    def add_payment(self, payment: BatchPayment) -> None:
        self.db.add(payment)

    def increment_sync_version(self, batch: Batch) -> int:
        batch.sync_version += 1
        from app.utils.datetime_utils import utc_now

        batch.server_updated_at = utc_now()
        self.db.flush()
        return batch.sync_version

    def update_status(
        self,
        batch: Batch,
        new_status: BatchStatus,
        changed_by_user_id: int,
        note: Optional[str] = None,
        *,
        received_at: Optional[datetime] = None,
        quarantined_at: Optional[datetime] = None,
        finalized_at: Optional[datetime] = None,
        rejected_at: Optional[datetime] = None,
        submitted_at: Optional[datetime] = None,
    ) -> None:
        old_status = batch.status
        batch.status = new_status
        if received_at is not None:
            batch.received_at = received_at
        if quarantined_at is not None:
            batch.quarantined_at = quarantined_at
        if finalized_at is not None:
            batch.finalized_at = finalized_at
        if rejected_at is not None:
            batch.rejected_at = rejected_at
        if submitted_at is not None:
            batch.submitted_at = submitted_at
        history = StatusHistory(
            batch_uuid=batch.batch_uuid,
            old_status=old_status,
            new_status=new_status,
            changed_by_user_id=changed_by_user_id,
            note=note,
        )
        self.db.add(history)
        self.increment_sync_version(batch)

    def add_sync_event(
        self,
        entity_type: str,
        entity_uuid: str,
        event_type: str,
        version: int,
        payload_json: Optional[dict] = None,
    ) -> None:
        self.db.add(
            SyncEvent(
                entity_type=entity_type,
                entity_uuid=entity_uuid,
                event_type=event_type,
                version=version,
                payload_json=payload_json,
            )
        )

    def add_reweighing(self, record: ReweighingRecord) -> None:
        self.db.add(record)

    def add_regrading_records(self, records: List[RegradingRecord]) -> None:
        self.db.add_all(records)

    def add_inventory_lots(self, lots: List[InventoryLot]) -> None:
        self.db.add_all(lots)

    def count_reweighing(self, batch_uuid: str) -> int:
        stmt = select(ReweighingRecord).where(ReweighingRecord.batch_uuid == batch_uuid)
        return len(list(self.db.scalars(stmt).all()))

    def count_regrading(self, batch_uuid: str) -> int:
        stmt = select(RegradingRecord).where(RegradingRecord.batch_uuid == batch_uuid)
        return len(list(self.db.scalars(stmt).all()))
