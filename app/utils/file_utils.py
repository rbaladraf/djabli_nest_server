import mimetypes
import os
from pathlib import Path

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "application/pdf",
}


def validate_mime_type(mime_type: str) -> bool:
    normalized = mime_type.lower().strip()
    if normalized == "image/jpg":
        normalized = "image/jpeg"
    return normalized in ALLOWED_MIME_TYPES


def guess_mime_type(filename: str) -> str:
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


def build_upload_relative_path(year: int, month: int, batch_uuid: str, filename: str) -> str:
    return f"{year}/{month:02d}/{batch_uuid}/{filename}"


def ensure_upload_dir(base_dir: str, relative_path: str) -> Path:
    full = Path(base_dir) / relative_path
    full.parent.mkdir(parents=True, exist_ok=True)
    return full
