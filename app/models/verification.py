import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class BatchVerification(Base):
    __tablename__ = "batch_verifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("batches.id"), unique=True, index=True, nullable=False
    )
    collector_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    supplier_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    berat_lapangan_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    berat_received_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3), nullable=True)
    berat_karantina_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3), nullable=True)
    berat_reweighing_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3), nullable=True)
    berat_final_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3), nullable=True)
    kadar_air_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    kelembapan_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    susut_received_to_quarantine_pct: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 3), nullable=True
    )
    susut_lapangan_to_final_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 3), nullable=True)
    yield_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 3), nullable=True)
    risk_level: Mapped[str] = mapped_column(String(16), default=RiskLevel.LOW.value, nullable=False)
    flags_json: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rejected_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    quarantine_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reweighing_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    regrading_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finalized_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)

    batch = relationship("Batch", back_populates="verification")
