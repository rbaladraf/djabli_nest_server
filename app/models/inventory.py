import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class GradeType(str, enum.Enum):
    MANGKUK = "MANGKUK"
    SUDUT = "SUDUT"
    PATAHAN = "PATAHAN"
    CONG = "CONG"
    REJECT = "REJECT"


class LotStatus(str, enum.Enum):
    VERIFIED = "VERIFIED"
    SOLD = "SOLD"
    ADJUSTED = "ADJUSTED"
    CANCELLED = "CANCELLED"


class ReweighingRecord(Base):
    __tablename__ = "reweighing_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("batches.batch_uuid"), index=True, nullable=False
    )
    gross_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    tare_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    net_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    shrinkage_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3), nullable=True)
    moisture_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    operator_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    batch = relationship("Batch", back_populates="reweighing_records")


class RegradingRecord(Base):
    __tablename__ = "regrading_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("batches.batch_uuid"), index=True, nullable=False
    )
    grade_type: Mapped[GradeType] = mapped_column(Enum(GradeType, name="grade_type"), nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    quality_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    defect_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    operator_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    batch = relationship("Batch", back_populates="regrading_records")


class InventoryLot(Base):
    __tablename__ = "inventory_lots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("batches.batch_uuid"), index=True, nullable=False
    )
    lot_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    grade_type: Mapped[GradeType] = mapped_column(Enum(GradeType, name="lot_grade_type"), nullable=False)
    final_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    cost_basis: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[LotStatus] = mapped_column(
        Enum(LotStatus, name="lot_status"), default=LotStatus.VERIFIED, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    batch = relationship("Batch", back_populates="inventory_lots")
