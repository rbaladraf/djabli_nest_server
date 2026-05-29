from decimal import Decimal
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.batch import Batch, BatchStatus
from app.models.inventory import GradeType, RegradingRecord, ReweighingRecord
from app.models.user import User
from app.models.verification import BatchVerification, RiskLevel
from app.repositories.batch_repository import BatchRepository
from app.repositories.verification_repository import VerificationRepository
from app.schemas.verification import (
    BatchActionWithVerificationResponse,
    BatchVerificationOut,
    FinalizeVerificationRequest,
    QuarantineVerificationRequest,
    ReceiveVerificationRequest,
    RegradeVerificationRequest,
    RegradeItemInline,
    RejectVerificationRequest,
    ReweighVerificationRequest,
    VerificationSummaryOut,
)
from app.services.audit_service import AuditService
from app.services.inventory_service import InventoryService
from app.utils.datetime_utils import utc_now
from app.utils.yield_metrics import calculate_yield_metrics


class BatchVerificationService:
    def __init__(self, db: Session):
        self.db = db
        self.batches = BatchRepository(db)
        self.verifications = VerificationRepository(db)
        self.audit = AuditService(db)
        self.inventory = InventoryService()

    def _field_weight(self, batch: Batch) -> Decimal:
        if batch.mobile_estimated_total_kg and batch.mobile_estimated_total_kg > 0:
            return batch.mobile_estimated_total_kg
        if batch.purchase_details:
            total = sum((d.weight_kg for d in batch.purchase_details), Decimal("0"))
            if total > 0:
                return total
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot determine berat_lapangan_kg from batch",
        )

    def _get_batch(self, batch_uuid: str) -> Batch:
        batch = self.batches.get_by_uuid(batch_uuid, with_relations=True)
        if not batch:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
        return batch

    def _ensure_not_finalized_locked(self, batch: Batch) -> None:
        if batch.status == BatchStatus.FINALIZED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="adjustment not implemented",
            )

    def get_or_create_verification(self, batch: Batch) -> BatchVerification:
        existing = self.verifications.get_by_batch_id(batch.id)
        if existing:
            return existing
        berat_lapangan = self._field_weight(batch)
        v = BatchVerification(
            batch_id=batch.id,
            collector_id=batch.created_by_user_id,
            supplier_id=None,
            berat_lapangan_kg=berat_lapangan,
            flags_json=[],
            risk_level=RiskLevel.LOW.value,
        )
        return self.verifications.create(v)

    def _apply_metrics(self, verification: BatchVerification) -> None:
        metrics = calculate_yield_metrics(
            berat_lapangan_kg=verification.berat_lapangan_kg,
            berat_received_kg=verification.berat_received_kg,
            berat_karantina_kg=verification.berat_karantina_kg,
            berat_reweighing_kg=verification.berat_reweighing_kg,
            berat_final_kg=verification.berat_final_kg,
            kadar_air_pct=verification.kadar_air_pct,
        )
        verification.susut_received_to_quarantine_pct = metrics["susut_received_to_quarantine_pct"]
        verification.susut_lapangan_to_final_pct = metrics["susut_lapangan_to_final_pct"]
        verification.yield_pct = metrics["yield_pct"]
        verification.risk_level = metrics["risk_level"]
        verification.flags_json = metrics["flags_json"]
        verification.updated_at = utc_now()

    def _to_out(self, batch: Batch, verification: BatchVerification) -> BatchVerificationOut:
        return BatchVerificationOut(
            id=verification.id,
            batch_id=verification.batch_id,
            batch_uuid=batch.batch_uuid,
            collector_id=verification.collector_id,
            supplier_id=verification.supplier_id,
            berat_lapangan_kg=verification.berat_lapangan_kg,
            berat_received_kg=verification.berat_received_kg,
            berat_karantina_kg=verification.berat_karantina_kg,
            berat_reweighing_kg=verification.berat_reweighing_kg,
            berat_final_kg=verification.berat_final_kg,
            kadar_air_pct=verification.kadar_air_pct,
            kelembapan_pct=verification.kelembapan_pct,
            susut_received_to_quarantine_pct=verification.susut_received_to_quarantine_pct,
            susut_lapangan_to_final_pct=verification.susut_lapangan_to_final_pct,
            yield_pct=verification.yield_pct,
            risk_level=verification.risk_level,
            flags_json=verification.flags_json or [],
            notes=verification.notes,
            rejected_reason=verification.rejected_reason,
            created_at=verification.created_at,
            updated_at=verification.updated_at,
            received_at=verification.received_at,
            quarantine_at=verification.quarantine_at,
            reweighing_at=verification.reweighing_at,
            regrading_at=verification.regrading_at,
            finalized_at=verification.finalized_at,
            verified_by=verification.verified_by,
            batch_status=batch.status.value,
        )

    def _summary(self, verification: BatchVerification) -> VerificationSummaryOut:
        return VerificationSummaryOut(
            risk_level=verification.risk_level,
            flags=verification.flags_json or [],
            yield_pct=verification.yield_pct,
            susut_received_to_quarantine_pct=verification.susut_received_to_quarantine_pct,
            susut_lapangan_to_final_pct=verification.susut_lapangan_to_final_pct,
            kadar_air_pct=verification.kadar_air_pct,
        )

    def _action_response(
        self, batch: Batch, verification: BatchVerification, warnings: Optional[List[str]] = None
    ) -> BatchActionWithVerificationResponse:
        return BatchActionWithVerificationResponse(
            batch_uuid=batch.batch_uuid,
            status=batch.status.value,
            sync_version=batch.sync_version,
            verification=self._summary(verification),
            warnings=warnings or [],
        )

    def get_verification(self, batch_uuid: str) -> BatchVerificationOut:
        batch = self._get_batch(batch_uuid)
        verification = self.get_or_create_verification(batch)
        self._apply_metrics(verification)
        self.db.commit()
        self.db.refresh(verification)
        return self._to_out(batch, verification)

    def receive(
        self, batch_uuid: str, user: User, body: ReceiveVerificationRequest
    ) -> BatchActionWithVerificationResponse:
        batch = self._get_batch(batch_uuid)
        self._ensure_not_finalized_locked(batch)
        if batch.status not in (BatchStatus.UPLOADED, BatchStatus.RECEIVED):
            raise HTTPException(
                status_code=400,
                detail="receive only allowed from UPLOADED or RECEIVED",
            )

        verification = self.get_or_create_verification(batch)
        verification.berat_received_kg = body.berat_received_kg
        if body.kadar_air_pct is not None:
            verification.kadar_air_pct = body.kadar_air_pct
        if body.kelembapan_pct is not None:
            verification.kelembapan_pct = body.kelembapan_pct
        if body.notes:
            verification.notes = body.notes
        verification.received_at = utc_now()
        verification.verified_by = user.id

        if batch.status != BatchStatus.RECEIVED:
            self.batches.update_status(
                batch,
                BatchStatus.RECEIVED,
                user.id,
                note=body.notes,
                received_at=verification.received_at,
            )
        else:
            self.batches.increment_sync_version(batch)

        self._apply_metrics(verification)
        self.audit.log(
            "BATCH_RECEIVED_WEIGHT_RECORDED",
            user.id,
            "batch",
            batch.batch_uuid,
        )
        self.audit.log("VERIFICATION_RISK_RECALCULATED", user.id, "batch", batch.batch_uuid)
        self.db.commit()
        self.db.refresh(batch)
        self.db.refresh(verification)
        return self._action_response(batch, verification)

    def move_to_quarantine(
        self, batch_uuid: str, user: User, body: QuarantineVerificationRequest
    ) -> BatchActionWithVerificationResponse:
        batch = self._get_batch(batch_uuid)
        self._ensure_not_finalized_locked(batch)
        if batch.status not in (BatchStatus.RECEIVED, BatchStatus.QUARANTINE):
            raise HTTPException(
                status_code=400,
                detail="quarantine only allowed from RECEIVED or QUARANTINE",
            )

        verification = self.get_or_create_verification(batch)
        verification.berat_karantina_kg = body.berat_karantina_kg
        if body.notes:
            verification.notes = body.notes
        verification.quarantine_at = utc_now()
        verification.verified_by = user.id

        if batch.status != BatchStatus.QUARANTINE:
            self.batches.update_status(
                batch,
                BatchStatus.QUARANTINE,
                user.id,
                note=body.notes,
                quarantined_at=verification.quarantine_at,
            )
        else:
            self.batches.increment_sync_version(batch)

        self._apply_metrics(verification)
        self.audit.log("BATCH_MOVED_TO_QUARANTINE", user.id, "batch", batch.batch_uuid)
        self.audit.log("VERIFICATION_RISK_RECALCULATED", user.id, "batch", batch.batch_uuid)
        self.db.commit()
        self.db.refresh(batch)
        self.db.refresh(verification)
        return self._action_response(batch, verification)

    def _ensure_reweighing_record(
        self, batch_uuid: str, user: User, net_kg: Decimal, body: ReweighVerificationRequest
    ) -> None:
        gross = body.gross_weight_kg or net_kg
        tare = body.tare_weight_kg or Decimal("0")
        record = ReweighingRecord(
            batch_uuid=batch_uuid,
            gross_weight_kg=gross,
            tare_weight_kg=tare,
            net_weight_kg=net_kg,
            shrinkage_kg=body.shrinkage_kg,
            moisture_note=body.moisture_note or body.notes,
            operator_user_id=user.id,
        )
        self.batches.add_reweighing(record)

    def reweigh(
        self, batch_uuid: str, user: User, body: ReweighVerificationRequest
    ) -> BatchActionWithVerificationResponse:
        batch = self._get_batch(batch_uuid)
        self._ensure_not_finalized_locked(batch)
        if batch.status not in (BatchStatus.QUARANTINE, BatchStatus.REWEIGHING):
            raise HTTPException(
                status_code=400,
                detail="reweigh only allowed from QUARANTINE or REWEIGHING",
            )

        verification = self.get_or_create_verification(batch)
        verification.berat_reweighing_kg = body.berat_reweighing_kg
        if body.notes:
            verification.notes = body.notes
        verification.reweighing_at = utc_now()
        verification.verified_by = user.id

        self._ensure_reweighing_record(batch_uuid, user, body.berat_reweighing_kg, body)

        if batch.status != BatchStatus.REWEIGHING:
            self.batches.update_status(batch, BatchStatus.REWEIGHING, user.id, note=body.notes)
        else:
            self.batches.increment_sync_version(batch)

        self._apply_metrics(verification)
        self.audit.log("BATCH_REWEIGHING_RECORDED", user.id, "batch", batch.batch_uuid)
        self.audit.log("VERIFICATION_RISK_RECALCULATED", user.id, "batch", batch.batch_uuid)
        self.db.commit()
        self.db.refresh(batch)
        self.db.refresh(verification)
        return self._action_response(batch, verification)

    def _ensure_regrading_records(
        self,
        batch_uuid: str,
        user: User,
        berat_final_kg: Decimal,
        items: Optional[List[RegradeItemInline]],
    ) -> None:
        if items:
            records = [
                RegradingRecord(
                    batch_uuid=batch_uuid,
                    grade_type=item.grade_type,
                    weight_kg=item.weight_kg,
                    quality_note=item.quality_note,
                    defect_note=item.defect_note,
                    operator_user_id=user.id,
                )
                for item in items
            ]
        else:
            records = [
                RegradingRecord(
                    batch_uuid=batch_uuid,
                    grade_type=GradeType.MANGKUK,
                    weight_kg=berat_final_kg,
                    operator_user_id=user.id,
                )
            ]
        self.batches.add_regrading_records(records)

    def regrade(
        self, batch_uuid: str, user: User, body: RegradeVerificationRequest
    ) -> BatchActionWithVerificationResponse:
        batch = self._get_batch(batch_uuid)
        self._ensure_not_finalized_locked(batch)
        if batch.status not in (BatchStatus.REWEIGHING, BatchStatus.REGRADING):
            raise HTTPException(
                status_code=400,
                detail="regrade only allowed from REWEIGHING or REGRADING",
            )
        verification = self.get_or_create_verification(batch)
        if self.batches.count_reweighing(batch_uuid) < 1:
            if verification.berat_reweighing_kg:
                self._ensure_reweighing_record(
                    batch_uuid,
                    user,
                    verification.berat_reweighing_kg,
                    ReweighVerificationRequest(berat_reweighing_kg=verification.berat_reweighing_kg),
                )
            else:
                raise HTTPException(status_code=400, detail="At least one reweighing record required")

        verification.berat_final_kg = body.berat_final_kg
        if body.notes:
            verification.notes = body.notes
        verification.regrading_at = utc_now()
        verification.verified_by = user.id

        self._ensure_regrading_records(batch_uuid, user, body.berat_final_kg, body.items)

        if batch.status != BatchStatus.REGRADING:
            self.batches.update_status(batch, BatchStatus.REGRADING, user.id, note=body.notes)
        else:
            self.batches.increment_sync_version(batch)

        self._apply_metrics(verification)
        self.audit.log("BATCH_REGRADING_RECORDED", user.id, "batch", batch.batch_uuid)
        self.audit.log("VERIFICATION_RISK_RECALCULATED", user.id, "batch", batch.batch_uuid)
        self.db.commit()
        self.db.refresh(batch)
        self.db.refresh(verification)
        return self._action_response(batch, verification)

    def finalize(
        self, batch_uuid: str, user: User, body: FinalizeVerificationRequest
    ) -> BatchActionWithVerificationResponse:
        batch = self._get_batch(batch_uuid)
        if batch.status == BatchStatus.FINALIZED:
            verification = self.get_or_create_verification(batch)
            return self._action_response(batch, verification)

        if batch.status != BatchStatus.REGRADING:
            raise HTTPException(status_code=400, detail="finalize only allowed from REGRADING")

        verification = self.get_or_create_verification(batch)
        if verification.berat_final_kg is None:
            raise HTTPException(status_code=400, detail="berat_final_kg required before finalize")

        if self.batches.count_reweighing(batch_uuid) < 1:
            raise HTTPException(status_code=400, detail="Reweighing records required")
        if self.batches.count_regrading(batch_uuid) < 1:
            raise HTTPException(status_code=400, detail="Regrading records required")

        regrading = list(batch.regrading_records)
        total_final_weight = sum(
            (r.weight_kg for r in regrading if r.grade_type != GradeType.REJECT),
            Decimal("0"),
        )
        if total_final_weight <= 0:
            raise HTTPException(status_code=400, detail="Total final grade weight invalid")

        self._apply_metrics(verification)
        warnings: List[str] = []
        if verification.risk_level == RiskLevel.HIGH.value:
            warnings.append("HIGH risk detected; finalize allowed with warning")

        total_payment = batch.payment_amount or Decimal("0")
        lots = self.inventory.build_lots_from_regrading(
            batch, regrading, total_payment, total_final_weight
        )
        if not lots:
            raise HTTPException(status_code=400, detail="No inventory lots to create")

        try:
            self.batches.add_inventory_lots(lots)
            now = utc_now()
            verification.finalized_at = now
            verification.verified_by = user.id
            self.batches.update_status(
                batch,
                BatchStatus.FINALIZED,
                user.id,
                note=body.note,
                finalized_at=now,
            )
            self.batches.add_sync_event(
                "batch",
                batch.batch_uuid,
                "BATCH_FINALIZED",
                batch.sync_version,
                {"lots": len(lots), "risk_level": verification.risk_level},
            )
            self.audit.log("BATCH_FINALIZED_WITH_YIELD", user.id, "batch", batch.batch_uuid)
            self.audit.log("VERIFICATION_RISK_RECALCULATED", user.id, "batch", batch.batch_uuid)
            self.db.commit()
            self.db.refresh(batch)
            self.db.refresh(verification)
            return self._action_response(batch, verification, warnings=warnings)
        except Exception:
            self.db.rollback()
            raise

    def reject(
        self, batch_uuid: str, user: User, body: RejectVerificationRequest
    ) -> BatchActionWithVerificationResponse:
        batch = self._get_batch(batch_uuid)
        if batch.status in (BatchStatus.FINALIZED, BatchStatus.REJECTED):
            raise HTTPException(status_code=400, detail=f"Cannot reject from {batch.status.value}")

        verification = self.get_or_create_verification(batch)
        verification.rejected_reason = body.reason
        verification.notes = body.reason
        verification.verified_by = user.id
        self._apply_metrics(verification)

        self.batches.update_status(
            batch,
            BatchStatus.REJECTED,
            user.id,
            note=body.reason,
            rejected_at=utc_now(),
        )
        self.audit.log("BATCH_REJECTED", user.id, "batch", batch.batch_uuid)
        self.db.commit()
        self.db.refresh(batch)
        self.db.refresh(verification)
        return self._action_response(batch, verification)
