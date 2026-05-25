from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.utils.datetime_utils import utc_now

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok", "time": utc_now().isoformat()}


@router.get("/api/health/db")
def health_db(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
