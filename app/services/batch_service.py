import json
from decimal import Decimal
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.batch import (
    Batch,
    BatchCost,
    BatchPayment,
    BatchPurchaseDetail,
    BatchStatus,
    PaymentMethod,
    SourceType,
)
from app.models.file import PhotoType
from app.models.inventory import GradeType, RegradingRecord, ReweighingRecord
from app.models.user import User
from app.repositories.batch_repository import BatchRepository
from app.repositories.file_repository import FileRepository
from app.repositories.user_repository import UserRepository
from app.schemas.admin import (
    FinalizeRequest,
    RegradeRequest,
    RejectRequest,
    ReweighRequest,
    StatusChangeRequest,
)
from app.schemas.batch import BatchDetailOut
from app.schemas.mobile import MobileCreateBatchRequest
from app.services.inventory_service import InventoryService
from app.utils.datetime_utils import utc_now

REQUIRED_SOP_PHOTOS = {
    PhotoType.UTUH,
    PhotoType.CLOSE_UP_SERAT,
    PhotoType.AREA_KOTORAN,
    PhotoType.SAMPING,
}

class BatchService:
    def __init__(self, db: Session):
        self.db = db
        self.batches = BatchRepository(db)
        self.files = FileRepository(db)
        self.users = UserRepository(db)
        self.inventory = InventoryService()

    def _payload_fingerprint(self, data: MobileCreateBatchRequest) -> str:
        payload = data.model_dump(mode="json")
        return json.dumps(payload, sort_keys=True, default=str)

    def _validate_mobile_create(self, data: MobileCreateBatchRequest, user: User) -> None:
        if not data.batch_uuid.strip():
            raise HTTPException(status_code=400, detail="batch_uuid is required")
        if not data.farmer.name.strip():
            raise HTTPException(status_code=400, detail="farmer.name is required")
        if not data.purchase_details:
            raise HTTPException(status_code=400, detail="purchase_details cannot be empty")
        for item in data.purchase_details:
            if item.weight_kg <= 0:
                raise HTTPException(status_code=400, detail="weight_kg must be > 0")
            if item.price_per_kg <= 0:
                raise HTTPException(status_code=400, detail="price_per_kg must be > 0")
        if data.payment.amount <= 0:
            raise HTTPException(status_code=400, detail="payment.amount must be > 0")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="User inactive")
        device = self.users.get_device_by_device_id(data.device_id)
        if not device or device.user_id != user.id:
            raise HTTPException(status_code=400, detail="device_id is invalid")

    def _compute_totals(self, data: MobileCreateBatchRequest) -> tuple[Decimal, Decimal]:
        total_kg = sum((d.weight_kg for d in data.purchase_details), Decimal("0"))
        total_amount = sum((d.subtotal for d in data.purchase_details), Decimal("0"))
        return total_kg, total_amount

    def create_mobile_batch(self, data: MobileCreateBatchRequest, user: User) -> Batch:
        self._validate_mobile_create(data, user)
        existing = self.batches.get_by_uuid(data.batch_uuid)
        fingerprint = self._payload_fingerprint(data)

        if existing:
            if not self._existing_matches_request(existing, data):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="batch_uuid already exists with different payload",
                )
            return existing

        total_kg, total_amount = self._compute_totals(data)
        op_cost = sum((c.amount for c in data.costs), Decimal("0"))

        batch = self.batches.create_batch(
            batch_uuid=data.batch_uuid,
            batch_code=data.batch_code,
            device_id=data.device_id,
            created_by_user_id=user.id,
            farmer_name=data.farmer.name,
            farmer_location=data.farmer.location,
            latitude=data.farmer.latitude,
            longitude=data.farmer.longitude,
            note=data.farmer.note,
            deal_type=data.deal_type,
            mobile_estimated_total_kg=total_kg,
            mobile_estimated_total_amount=total_amount,
            payment_method=data.payment.method,
            payment_amount=data.payment.amount,
            operational_cost_total=op_cost,
            status=BatchStatus.DRAFT,
        )
        details = [
            BatchPurchaseDetail(
                batch_uuid=batch.batch_uuid,
                item_type=d.item_type,
                weight_kg=d.weight_kg,
                price_per_kg=d.price_per_kg,
                subtotal=d.subtotal,
                source_type=SourceType.MOBILE_ESTIMATE,
            )
            for d in data.purchase_details
        ]
        costs = [
            BatchCost(
                batch_uuid=batch.batch_uuid,
                cost_type=c.cost_type,
                amount=c.amount,
                note=c.note,
            )
            for c in data.costs
        ]
        payment = BatchPayment(
            batch_uuid=batch.batch_uuid,
            method=data.payment.method,
            amount=data.payment.amount,
            note=data.payment.note,
        )
        self.batches.add_purchase_details(details)
        self.batches.add_costs(costs)
        self.batches.add_payment(payment)

        device = self.users.get_device_by_device_id(data.device_id)
        if device:
            self.users.touch_device(device)

        self.batches.add_sync_event("batch", batch.batch_uuid, "BATCH_CREATED", batch.sync_version)
        self.db.commit()
        self.db.refresh(batch)
        return batch

    def _existing_matches_request(self, batch: Batch, data: MobileCreateBatchRequest) -> bool:
        full = self.batches.get_by_uuid(batch.batch_uuid, with_relations=True)
        if not full:
            return False
        if (
            full.batch_code != data.batch_code
            or full.device_id != data.device_id
            or full.farmer_name != data.farmer.name
            or full.deal_type != data.deal_type
            or full.payment_method != data.payment.method
            or full.payment_amount != data.payment.amount
        ):
            return False
        if len(full.purchase_details) != len(data.purchase_details):
            return False
        for stored, incoming in zip(
            sorted(full.purchase_details, key=lambda x: x.item_type.value),
            sorted(data.purchase_details, key=lambda x: x.item_type.value),
        ):
            if (
                stored.item_type != incoming.item_type
                or stored.weight_kg != incoming.weight_kg
                or stored.price_per_kg != incoming.price_per_kg
                or stored.subtotal != incoming.subtotal
            ):
                return False
        return True

    def submit_batch(self, batch_uuid: str, user: User) -> Batch:
        batch = self.batches.get_by_uuid(batch_uuid, with_relations=True)
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        if batch.submitted_at:
            return batch
        if not batch.payments:
            raise HTTPException(status_code=400, detail="Payment required")
        if not batch.purchase_details:
            raise HTTPException(status_code=400, detail="Purchase details required")
        for d in batch.purchase_details:
            if d.weight_kg <= 0 or d.price_per_kg <= 0:
                raise HTTPException(status_code=400, detail="Invalid purchase details")
        if not self.files.has_sop_photo_types(batch_uuid, REQUIRED_SOP_PHOTOS):
            raise HTTPException(
                status_code=400,
                detail="Missing required SOP photos: UTUH, CLOSE_UP_SERAT, AREA_KOTORAN, SAMPING",
            )

        now = utc_now()
        self.batches.update_status(
            batch,
            BatchStatus.UPLOADED,
            user.id,
            note="Mobile submit",
            submitted_at=now,
        )
        self.batches.add_sync_event(
            "batch",
            batch.batch_uuid,
            "BATCH_SUBMITTED",
            batch.sync_version,
            {"status": BatchStatus.UPLOADED.value},
        )
        self.db.commit()
        self.db.refresh(batch)
        return batch

    def get_batch_status_display(self, batch: Batch) -> str:
        if batch.status == BatchStatus.DRAFT:
            return "DRAFT"
        return batch.status.value

    def get_batch_detail(self, batch_uuid: str) -> BatchDetailOut:
        batch = self.batches.get_by_uuid(batch_uuid, with_relations=True)
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        return BatchDetailOut.model_validate(batch)

    def _get_batch_or_404(self, batch_uuid: str) -> Batch:
        batch = self.batches.get_by_uuid(batch_uuid, with_relations=True)
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        if batch.status == BatchStatus.FINALIZED:
            raise HTTPException(
                status_code=400,
                detail="adjustment not implemented",
            )
        return batch

    def receive(self, batch_uuid: str, user: User, body: StatusChangeRequest) -> Batch:
        batch = self._get_batch_or_404(batch_uuid)
        if batch.status != BatchStatus.UPLOADED:
            raise HTTPException(status_code=400, detail="receive only allowed from UPLOADED")
        self.batches.update_status(
            batch,
            BatchStatus.RECEIVED,
            user.id,
            note=body.note,
            received_at=utc_now(),
        )
        self.batches.add_sync_event("batch", batch.batch_uuid, "BATCH_RECEIVED", batch.sync_version)
        self.db.commit()
        self.db.refresh(batch)
        return batch

    def move_to_quarantine(self, batch_uuid: str, user: User, body: StatusChangeRequest) -> Batch:
        batch = self._get_batch_or_404(batch_uuid)
        if batch.status != BatchStatus.RECEIVED:
            raise HTTPException(status_code=400, detail="quarantine only allowed from RECEIVED")
        self.batches.update_status(
            batch,
            BatchStatus.QUARANTINE,
            user.id,
            note=body.note,
            quarantined_at=utc_now(),
        )
        self.batches.add_sync_event("batch", batch.batch_uuid, "BATCH_QUARANTINE", batch.sync_version)
        self.db.commit()
        self.db.refresh(batch)
        return batch

    def reweigh(self, batch_uuid: str, user: User, body: ReweighRequest) -> Batch:
        batch = self._get_batch_or_404(batch_uuid)
        if batch.status not in (BatchStatus.QUARANTINE, BatchStatus.REWEIGHING):
            raise HTTPException(
                status_code=400,
                detail="reweigh only allowed from QUARANTINE or REWEIGHING",
            )
        record = ReweighingRecord(
            batch_uuid=batch_uuid,
            gross_weight_kg=body.gross_weight_kg,
            tare_weight_kg=body.tare_weight_kg,
            net_weight_kg=body.net_weight_kg,
            shrinkage_kg=body.shrinkage_kg,
            moisture_note=body.moisture_note,
            operator_user_id=user.id,
        )
        self.batches.add_reweighing(record)
        if batch.status != BatchStatus.REWEIGHING:
            self.batches.update_status(batch, BatchStatus.REWEIGHING, user.id, note="Reweighing")
        else:
            self.batches.increment_sync_version(batch)
        self.batches.add_sync_event("batch", batch.batch_uuid, "BATCH_REWEIGH", batch.sync_version)
        self.db.commit()
        self.db.refresh(batch)
        return batch

    def regrade(self, batch_uuid: str, user: User, body: RegradeRequest) -> Batch:
        batch = self._get_batch_or_404(batch_uuid)
        if self.batches.count_reweighing(batch_uuid) < 1:
            raise HTTPException(status_code=400, detail="At least one reweighing record required")
        records = [
            RegradingRecord(
                batch_uuid=batch_uuid,
                grade_type=item.grade_type,
                weight_kg=item.weight_kg,
                quality_note=item.quality_note,
                defect_note=item.defect_note,
                operator_user_id=user.id,
            )
            for item in body.items
        ]
        self.batches.add_regrading_records(records)
        if batch.status != BatchStatus.REGRADING:
            self.batches.update_status(batch, BatchStatus.REGRADING, user.id, note="Regrading")
        else:
            self.batches.increment_sync_version(batch)
        self.batches.add_sync_event("batch", batch.batch_uuid, "BATCH_REGRADE", batch.sync_version)
        self.db.commit()
        self.db.refresh(batch)
        return batch

    def finalize(self, batch_uuid: str, user: User, body: FinalizeRequest) -> Batch:
        batch = self.batches.get_by_uuid(batch_uuid, with_relations=True)
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        if batch.status == BatchStatus.FINALIZED:
            return batch

        if self.batches.count_reweighing(batch_uuid) < 1:
            raise HTTPException(status_code=400, detail="Reweighing records required")
        if self.batches.count_regrading(batch_uuid) < 1:
            raise HTTPException(status_code=400, detail="Regrading records required")

        regrading = list(batch.regrading_records)
        if not regrading:
            stmt_records = self.db.query(RegradingRecord).filter(
                RegradingRecord.batch_uuid == batch_uuid
            ).all()
            regrading = stmt_records

        total_final_weight = sum(
            (r.weight_kg for r in regrading if r.grade_type != GradeType.REJECT),
            Decimal("0"),
        )
        if total_final_weight <= 0:
            raise HTTPException(status_code=400, detail="Total final grade weight invalid")

        total_payment = batch.payment_amount or Decimal("0")
        lots = self.inventory.build_lots_from_regrading(
            batch, regrading, total_payment, total_final_weight
        )
        if not lots:
            raise HTTPException(status_code=400, detail="No inventory lots to create")

        try:
            self.batches.add_inventory_lots(lots)
            self.batches.update_status(
                batch,
                BatchStatus.FINALIZED,
                user.id,
                note=body.note,
                finalized_at=utc_now(),
            )
            self.batches.add_sync_event(
                "batch",
                batch.batch_uuid,
                "BATCH_FINALIZED",
                batch.sync_version,
                {"lots": len(lots)},
            )
            self.db.commit()
            self.db.refresh(batch)
            return batch
        except Exception:
            self.db.rollback()
            raise

    def reject(self, batch_uuid: str, user: User, body: RejectRequest) -> Batch:
        batch = self._get_batch_or_404(batch_uuid)
        if batch.status in (BatchStatus.FINALIZED, BatchStatus.REJECTED):
            raise HTTPException(status_code=400, detail=f"Cannot reject from {batch.status.value}")
        self.batches.update_status(
            batch,
            BatchStatus.REJECTED,
            user.id,
            note=body.note,
            rejected_at=utc_now(),
        )
        self.batches.add_sync_event("batch", batch.batch_uuid, "BATCH_REJECTED", batch.sync_version)
        self.db.commit()
        self.db.refresh(batch)
        return batch
