from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.inventory import GradeType
from app.schemas.batch import BatchDetailOut


class AdminSyncResponse(BaseModel):
    server_time: datetime
    items: List[BatchDetailOut]


class ReweighRequest(BaseModel):
    gross_weight_kg: Decimal = Field(gt=0)
    tare_weight_kg: Decimal = Field(ge=0)
    net_weight_kg: Decimal = Field(gt=0)
    shrinkage_kg: Optional[Decimal] = None
    moisture_note: Optional[str] = None


class RegradeItemRequest(BaseModel):
    grade_type: GradeType
    weight_kg: Decimal = Field(gt=0)
    quality_note: Optional[str] = None
    defect_note: Optional[str] = None


class RegradeRequest(BaseModel):
    items: List[RegradeItemRequest] = Field(min_length=1)


class FinalizeRequest(BaseModel):
    note: Optional[str] = None


class StatusChangeRequest(BaseModel):
    note: Optional[str] = None


class RejectRequest(BaseModel):
    note: str = Field(min_length=1)


class BatchActionResponse(BaseModel):
    batch_uuid: str
    status: str
    sync_version: int
    message: str
