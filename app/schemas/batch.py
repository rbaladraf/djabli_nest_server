from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.batch import (
    BatchStatus,
    CostType,
    DealType,
    ItemType,
    PaymentMethod,
    SourceType,
)
from app.models.file import FileType, PhotoType
from app.models.inventory import GradeType, LotStatus
from app.schemas.common import ORMBase


class PurchaseDetailSchema(BaseModel):
    item_type: ItemType
    weight_kg: Decimal
    price_per_kg: Decimal
    subtotal: Decimal


class CostSchema(BaseModel):
    cost_type: CostType
    amount: Decimal
    note: Optional[str] = None


class PaymentSchema(BaseModel):
    method: PaymentMethod
    amount: Decimal
    note: Optional[str] = None


class FarmerSchema(BaseModel):
    name: str = Field(min_length=1)
    location: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    note: Optional[str] = None


class BatchFileOut(ORMBase):
    file_uuid: str
    file_type: FileType
    photo_type: Optional[PhotoType] = None
    original_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    created_at: datetime


class PurchaseDetailOut(ORMBase):
    id: int
    item_type: ItemType
    weight_kg: Decimal
    price_per_kg: Decimal
    subtotal: Decimal
    source_type: SourceType
    created_at: datetime


class CostOut(ORMBase):
    id: int
    cost_type: CostType
    amount: Decimal
    note: Optional[str] = None
    created_at: datetime


class PaymentOut(ORMBase):
    id: int
    method: PaymentMethod
    amount: Decimal
    note: Optional[str] = None
    created_at: datetime


class ReweighingOut(ORMBase):
    id: int
    gross_weight_kg: Decimal
    tare_weight_kg: Decimal
    net_weight_kg: Decimal
    shrinkage_kg: Optional[Decimal] = None
    moisture_note: Optional[str] = None
    created_at: datetime


class RegradingOut(ORMBase):
    id: int
    grade_type: GradeType
    weight_kg: Decimal
    quality_note: Optional[str] = None
    defect_note: Optional[str] = None
    created_at: datetime


class InventoryLotOut(ORMBase):
    id: int
    lot_code: str
    grade_type: GradeType
    final_weight_kg: Decimal
    cost_basis: Decimal
    status: LotStatus
    created_at: datetime


class StatusHistoryOut(ORMBase):
    id: int
    old_status: Optional[BatchStatus] = None
    new_status: BatchStatus
    note: Optional[str] = None
    created_at: datetime


class BatchSummaryOut(ORMBase):
    batch_uuid: str
    batch_code: str
    status: BatchStatus
    sync_version: int
    server_updated_at: datetime
    farmer_name: str
    farmer_location: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    deal_type: DealType
    mobile_estimated_total_kg: Optional[Decimal] = None
    mobile_estimated_total_amount: Optional[Decimal] = None
    payment_method: Optional[PaymentMethod] = None
    payment_amount: Optional[Decimal] = None
    operational_cost_total: Optional[Decimal] = None
    submitted_at: Optional[datetime] = None


class BatchDetailOut(BatchSummaryOut):
    purchase_details: List[PurchaseDetailOut] = []
    costs: List[CostOut] = []
    payments: List[PaymentOut] = []
    files: List[BatchFileOut] = []
    reweighing_records: List[ReweighingOut] = []
    regrading_records: List[RegradingOut] = []
    inventory_lots: List[InventoryLotOut] = []
    status_history: List[StatusHistoryOut] = []
