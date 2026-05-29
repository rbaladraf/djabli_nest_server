import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class BatchStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    UPLOADED = "UPLOADED"
    RECEIVED = "RECEIVED"
    QUARANTINE = "QUARANTINE"
    REWEIGHING = "REWEIGHING"
    REGRADING = "REGRADING"
    FINALIZED = "FINALIZED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class DealType(str, enum.Enum):
    KLASIFIKASI = "KLASIFIKASI"
    CONG = "CONG"


class PaymentMethod(str, enum.Enum):
    CASH = "CASH"
    TRANSFER = "TRANSFER"


class ItemType(str, enum.Enum):
    MANGKUK = "MANGKUK"
    SUDUT = "SUDUT"
    PATAHAN = "PATAHAN"
    CONG = "CONG"


class SourceType(str, enum.Enum):
    MOBILE_ESTIMATE = "MOBILE_ESTIMATE"
    ADMIN_FINAL = "ADMIN_FINAL"


class CostType(str, enum.Enum):
    TRANSPORT = "TRANSPORT"
    MAKAN = "MAKAN"
    PENGINAPAN = "PENGINAPAN"
    PENGIRIMAN = "PENGIRIMAN"
    LAIN_LAIN = "LAIN_LAIN"


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_uuid: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    batch_code: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    device_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    farmer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    farmer_location: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deal_type: Mapped[DealType] = mapped_column(Enum(DealType, name="deal_type"), nullable=False)
    mobile_estimated_total_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3), nullable=True)
    mobile_estimated_total_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    payment_method: Mapped[Optional[PaymentMethod]] = mapped_column(
        Enum(PaymentMethod, name="payment_method"), nullable=True
    )
    payment_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    operational_cost_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    status: Mapped[BatchStatus] = mapped_column(
        Enum(BatchStatus, name="batch_status"),
        default=BatchStatus.DRAFT,
        nullable=False,
    )
    server_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    server_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    quarantined_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finalized_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_version: Mapped[int] = mapped_column(default=1, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    purchase_details = relationship("BatchPurchaseDetail", back_populates="batch", lazy="selectin")
    costs = relationship("BatchCost", back_populates="batch", lazy="selectin")
    payments = relationship("BatchPayment", back_populates="batch", lazy="selectin")
    files = relationship("BatchFile", back_populates="batch", lazy="selectin")
    reweighing_records = relationship("ReweighingRecord", back_populates="batch", lazy="selectin")
    regrading_records = relationship("RegradingRecord", back_populates="batch", lazy="selectin")
    inventory_lots = relationship("InventoryLot", back_populates="batch", lazy="selectin")
    status_history = relationship("StatusHistory", back_populates="batch", lazy="selectin")
    verification = relationship(
        "BatchVerification",
        back_populates="batch",
        uselist=False,
        lazy="selectin",
    )


class BatchPurchaseDetail(Base):
    __tablename__ = "batch_purchase_details"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("batches.batch_uuid"), index=True, nullable=False
    )
    item_type: Mapped[ItemType] = mapped_column(Enum(ItemType, name="item_type"), nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    price_per_kg: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="source_type"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    batch = relationship("Batch", back_populates="purchase_details")


class BatchCost(Base):
    __tablename__ = "batch_costs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("batches.batch_uuid"), index=True, nullable=False
    )
    cost_type: Mapped[CostType] = mapped_column(Enum(CostType, name="cost_type"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    batch = relationship("Batch", back_populates="costs")


class BatchPayment(Base):
    __tablename__ = "batch_payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("batches.batch_uuid"), index=True, nullable=False
    )
    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="batch_payment_method"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    receipt_file_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("batch_files.id"), nullable=True
    )
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    batch = relationship("Batch", back_populates="payments")
