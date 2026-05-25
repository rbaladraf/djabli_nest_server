from decimal import Decimal
from typing import List

from app.models.batch import Batch
from app.models.inventory import GradeType, InventoryLot, LotStatus, RegradingRecord
from app.utils.id_utils import new_uuid


class InventoryService:
    @staticmethod
    def build_lots_from_regrading(
        batch: Batch,
        regrading_records: List[RegradingRecord],
        total_payment: Decimal,
        total_final_weight: Decimal,
    ) -> List[InventoryLot]:
        lots: List[InventoryLot] = []
        for record in regrading_records:
            if record.grade_type == GradeType.REJECT:
                continue
            weight_ratio = (
                record.weight_kg / total_final_weight if total_final_weight > 0 else Decimal("0")
            )
            cost_basis = (total_payment * weight_ratio).quantize(Decimal("0.01"))
            lot_code = f"{batch.batch_code}-{record.grade_type.value}-{new_uuid()[:8]}"
            lots.append(
                InventoryLot(
                    batch_uuid=batch.batch_uuid,
                    lot_code=lot_code,
                    grade_type=record.grade_type,
                    final_weight_kg=record.weight_kg,
                    cost_basis=cost_basis,
                    status=LotStatus.VERIFIED,
                )
            )
        return lots
