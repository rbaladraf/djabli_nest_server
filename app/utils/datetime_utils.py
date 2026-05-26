from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def parse_optional_since(value: Optional[str]) -> Optional[datetime]:
    """Treat missing or blank `since` as full sync (no filter)."""
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    normalized = stripped.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid since datetime: {stripped}",
        ) from exc
