import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FileType(str, enum.Enum):
    SOP_PHOTO = "SOP_PHOTO"
    TRANSFER_RECEIPT = "TRANSFER_RECEIPT"
    OTHER = "OTHER"


class PhotoType(str, enum.Enum):
    UTUH = "UTUH"
    CLOSE_UP_SERAT = "CLOSE_UP_SERAT"
    AREA_KOTORAN = "AREA_KOTORAN"
    SAMPING = "SAMPING"


class BatchFile(Base):
    __tablename__ = "batch_files"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    file_uuid: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    batch_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("batches.batch_uuid"), index=True, nullable=False
    )
    file_type: Mapped[FileType] = mapped_column(Enum(FileType, name="file_type"), nullable=False)
    photo_type: Mapped[Optional[PhotoType]] = mapped_column(
        Enum(PhotoType, name="photo_type"), nullable=True
    )
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    relative_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    batch = relationship("Batch", back_populates="files")
