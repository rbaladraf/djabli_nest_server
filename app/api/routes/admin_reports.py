from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Query

from app.core.deps import AdminUser, DbSession
from app.repositories.verification_repository import VerificationRepository
from app.schemas.verification import CollectorRiskRow, SupplierRiskRow, YieldSummaryReport
from app.utils.datetime_utils import parse_optional_since

router = APIRouter(prefix="/api/admin/reports", tags=["Admin Reports"])


@router.get("/yield-summary", response_model=YieldSummaryReport)
def yield_summary(
    user: AdminUser,
    db: DbSession,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    collector_id: Optional[int] = Query(None),
    supplier_id: Optional[int] = Query(None),
):
    repo = VerificationRepository(db)
    start = parse_optional_since(start_date) if start_date else None
    end = parse_optional_since(end_date) if end_date else None
    data = repo.yield_summary(
        start_date=start,
        end_date=end,
        collector_id=collector_id,
        supplier_id=supplier_id,
    )
    return YieldSummaryReport(
        total_batch_count=data["total_batch_count"],
        avg_yield_pct=float(data["avg_yield_pct"]) if data["avg_yield_pct"] is not None else None,
        avg_total_shrink_pct=float(data["avg_total_shrink_pct"])
        if data["avg_total_shrink_pct"] is not None
        else None,
        avg_quarantine_shrink_pct=float(data["avg_quarantine_shrink_pct"])
        if data["avg_quarantine_shrink_pct"] is not None
        else None,
        high_risk_batch_count=data["high_risk_batch_count"],
    )


@router.get("/collector-risk", response_model=List[CollectorRiskRow])
def collector_risk(
    user: AdminUser,
    db: DbSession,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    start = parse_optional_since(start_date) if start_date else None
    end = parse_optional_since(end_date) if end_date else None
    rows = VerificationRepository(db).collector_risk_rows(start_date=start, end_date=end)
    return [CollectorRiskRow(**r) for r in rows]


@router.get("/supplier-risk", response_model=List[SupplierRiskRow])
def supplier_risk(
    user: AdminUser,
    db: DbSession,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    start = parse_optional_since(start_date) if start_date else None
    end = parse_optional_since(end_date) if end_date else None
    rows = VerificationRepository(db).supplier_risk_rows(start_date=start, end_date=end)
    return [SupplierRiskRow(**r) for r in rows]
