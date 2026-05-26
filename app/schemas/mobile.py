from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.batch import BatchStatus, DealType
from app.schemas.batch import CostSchema, FarmerSchema, PaymentSchema, PurchaseDetailSchema


class MobileLoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)
    device_id: Optional[str] = Field(None, min_length=1, max_length=128)
    platform: Optional[str] = Field(None, max_length=64)
    device_name: Optional[str] = Field(None, max_length=255)


class MobileCreateBatchRequest(BaseModel):
    batch_uuid: str = Field(min_length=1)
    batch_code: str
    device_id: str
    farmer: FarmerSchema
    deal_type: DealType
    purchase_details: List[PurchaseDetailSchema]
    payment: PaymentSchema
    costs: List[CostSchema] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MobileBatchResponse(BaseModel):
    batch_uuid: str
    batch_code: str
    status: str
    sync_version: int
    message: str = "ok"


class MobileBatchStatusResponse(BaseModel):
    batch_uuid: str
    status: str
    sync_version: int
    submitted_at: Optional[datetime] = None


class MobileSyncConfigResponse(BaseModel):
    min_sop_photos: int = 4
    required_photo_types: List[str] = [
        "UTUH",
        "CLOSE_UP_SERAT",
        "AREA_KOTORAN",
        "SAMPING",
    ]
    max_upload_mb: int
    allowed_mime_types: List[str] = ["image/jpeg", "image/png", "application/pdf"]
