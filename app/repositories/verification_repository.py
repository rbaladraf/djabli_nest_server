from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.verification import BatchVerification


class VerificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_batch_id(self, batch_id: int) -> Optional[BatchVerification]:
        return self.db.scalar(
            select(BatchVerification).where(BatchVerification.batch_id == batch_id)
        )

    def create(self, verification: BatchVerification) -> BatchVerification:
        self.db.add(verification)
        self.db.flush()
        return verification

    def list_for_report(
        self,
        *,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        collector_id: Optional[int] = None,
        supplier_id: Optional[int] = None,
    ) -> List[BatchVerification]:
        stmt = select(BatchVerification).join(Batch, Batch.id == BatchVerification.batch_id)
        if start_date:
            stmt = stmt.where(BatchVerification.created_at >= start_date)
        if end_date:
            stmt = stmt.where(BatchVerification.created_at <= end_date)
        if collector_id is not None:
            stmt = stmt.where(BatchVerification.collector_id == collector_id)
        if supplier_id is not None:
            stmt = stmt.where(BatchVerification.supplier_id == supplier_id)
        return list(self.db.scalars(stmt).all())

    def yield_summary(
        self,
        *,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        collector_id: Optional[int] = None,
        supplier_id: Optional[int] = None,
    ) -> dict:
        stmt = select(
            func.count(BatchVerification.id),
            func.avg(BatchVerification.yield_pct),
            func.avg(BatchVerification.susut_lapangan_to_final_pct),
            func.avg(BatchVerification.susut_received_to_quarantine_pct),
            func.sum(case((BatchVerification.risk_level == "HIGH", 1), else_=0)),
        ).select_from(BatchVerification)
        if start_date:
            stmt = stmt.where(BatchVerification.created_at >= start_date)
        if end_date:
            stmt = stmt.where(BatchVerification.created_at <= end_date)
        if collector_id is not None:
            stmt = stmt.where(BatchVerification.collector_id == collector_id)
        if supplier_id is not None:
            stmt = stmt.where(BatchVerification.supplier_id == supplier_id)
        row = self.db.execute(stmt).one()
        return {
            "total_batch_count": int(row[0] or 0),
            "avg_yield_pct": row[1],
            "avg_total_shrink_pct": row[2],
            "avg_quarantine_shrink_pct": row[3],
            "high_risk_batch_count": int(row[4] or 0),
        }

    def collector_risk_rows(
        self,
        *,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[dict]:
        from app.models.user import User

        high_case = case((BatchVerification.risk_level == "HIGH", 1), else_=0)
        stmt = (
            select(
                BatchVerification.collector_id,
                User.full_name,
                func.count(BatchVerification.id),
                func.avg(BatchVerification.yield_pct),
                func.avg(BatchVerification.susut_lapangan_to_final_pct),
                func.sum(high_case),
            )
            .join(User, User.id == BatchVerification.collector_id, isouter=True)
            .where(BatchVerification.collector_id.isnot(None))
            .group_by(BatchVerification.collector_id, User.full_name)
        )
        if start_date:
            stmt = stmt.where(BatchVerification.created_at >= start_date)
        if end_date:
            stmt = stmt.where(BatchVerification.created_at <= end_date)
        rows = self.db.execute(stmt).all()
        result = []
        for r in rows:
            total = int(r[2] or 0)
            high = int(r[5] or 0)
            risk_score = (high / total * 100) if total > 0 else 0.0
            result.append(
                {
                    "collector_id": r[0],
                    "collector_name": r[1] or "",
                    "total_batches": total,
                    "avg_yield_pct": r[3],
                    "avg_total_shrink_pct": r[4],
                    "high_risk_count": high,
                    "risk_score": round(risk_score, 2),
                }
            )
        return result

    def supplier_risk_rows(
        self,
        *,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[dict]:
        high_case = case((BatchVerification.risk_level == "HIGH", 1), else_=0)
        stmt = (
            select(
                BatchVerification.supplier_id,
                func.count(BatchVerification.id),
                func.avg(BatchVerification.yield_pct),
                func.avg(BatchVerification.susut_lapangan_to_final_pct),
                func.sum(high_case),
            )
            .where(BatchVerification.supplier_id.isnot(None))
            .group_by(BatchVerification.supplier_id)
        )
        if start_date:
            stmt = stmt.where(BatchVerification.created_at >= start_date)
        if end_date:
            stmt = stmt.where(BatchVerification.created_at <= end_date)
        rows = self.db.execute(stmt).all()
        result = []
        for r in rows:
            total = int(r[1] or 0)
            high = int(r[4] or 0)
            risk_score = (high / total * 100) if total > 0 else 0.0
            result.append(
                {
                    "supplier_id": r[0],
                    "supplier_name": f"Supplier #{r[0]}",
                    "total_batches": total,
                    "avg_yield_pct": r[2],
                    "avg_total_shrink_pct": r[3],
                    "high_risk_count": high,
                    "risk_score": round(risk_score, 2),
                }
            )
        return result
