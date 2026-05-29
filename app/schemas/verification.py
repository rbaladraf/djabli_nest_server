from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.inventory import GradeType
from app.schemas.common import ORMBase


class VerificationSummaryOut(BaseModel):
    risk_level: str
    flags: List[str] = []
    yield_pct: Optional[Decimal] = None
    susut_received_to_quarantine_pct: Optional[Decimal] = None
    susut_lapangan_to_final_pct: Optional[Decimal] = None
    kadar_air_pct: Optional[Decimal] = None


class BatchVerificationOut(ORMBase):
    id: int
    batch_id: int
    batch_uuid: str
    collector_id: Optional[int] = None
    supplier_id: Optional[int] = None
    berat_lapangan_kg: Decimal
    berat_received_kg: Optional[Decimal] = None
    berat_karantina_kg: Optional[Decimal] = None
    berat_reweighing_kg: Optional[Decimal] = None
    berat_final_kg: Optional[Decimal] = None
    kadar_air_pct: Optional[Decimal] = None
    kelembapan_pct: Optional[Decimal] = None
    susut_received_to_quarantine_pct: Optional[Decimal] = None
    susut_lapangan_to_final_pct: Optional[Decimal] = None
    yield_pct: Optional[Decimal] = None
    risk_level: str
    flags_json: List[str] = []
    notes: Optional[str] = None
    rejected_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    received_at: Optional[datetime] = None
    quarantine_at: Optional[datetime] = None
    reweighing_at: Optional[datetime] = None
    regrading_at: Optional[datetime] = None
    finalized_at: Optional[datetime] = None
    verified_by: Optional[int] = None
    batch_status: str


class ReceiveVerificationRequest(BaseModel):
    berat_received_kg: Decimal = Field(gt=0)
    kadar_air_pct: Optional[Decimal] = Field(None, ge=0, le=100)
    kelembapan_pct: Optional[Decimal] = Field(None, ge=0, le=100)
    notes: Optional[str] = None


class QuarantineVerificationRequest(BaseModel):
    berat_karantina_kg: Decimal = Field(gt=0)
    notes: Optional[str] = None


class ReweighVerificationRequest(BaseModel):
    berat_reweighing_kg: Decimal = Field(gt=0)
    notes: Optional[str] = None
    gross_weight_kg: Optional[Decimal] = Field(None, gt=0)
    tare_weight_kg: Optional[Decimal] = Field(None, ge=0)
    shrinkage_kg: Optional[Decimal] = None
    moisture_note: Optional[str] = None


class RegradeVerificationRequest(BaseModel):
    berat_final_kg: Decimal = Field(gt=0)
    notes: Optional[str] = None
    items: Optional[List["RegradeItemInline"]] = None


class RegradeItemInline(BaseModel):
    grade_type: GradeType
    weight_kg: Decimal = Field(gt=0)
    quality_note: Optional[str] = None
    defect_note: Optional[str] = None


class RejectVerificationRequest(BaseModel):
    reason: str = Field(min_length=1)


class FinalizeVerificationRequest(BaseModel):
    note: Optional[str] = None


class BatchActionWithVerificationResponse(BaseModel):
    batch_uuid: str
    status: str
    sync_version: int
    message: str = "ok"
    verification: VerificationSummaryOut
    warnings: List[str] = []


class YieldSummaryReport(BaseModel):
    total_batch_count: int
    avg_yield_pct: Optional[float] = None
    avg_total_shrink_pct: Optional[float] = None
    avg_quarantine_shrink_pct: Optional[float] = None
    high_risk_batch_count: int


class CollectorRiskRow(BaseModel):
    collector_id: int
    collector_name: str
    total_batches: int
    avg_yield_pct: Optional[float] = None
    avg_total_shrink_pct: Optional[float] = None
    high_risk_count: int
    risk_score: float


class SupplierRiskRow(BaseModel):
    supplier_id: int
    supplier_name: str
    total_batches: int
    avg_yield_pct: Optional[float] = None
    avg_total_shrink_pct: Optional[float] = None
    high_risk_count: int
    risk_score: float
