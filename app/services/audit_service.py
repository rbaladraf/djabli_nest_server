from typing import Optional

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        action: str,
        user_id: Optional[int] = None,
        entity_type: Optional[str] = None,
        entity_uuid: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        self.db.add(
            AuditLog(
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_uuid=entity_uuid,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )
