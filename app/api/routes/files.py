from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.core.deps import CurrentUser, DbSession
from app.services.file_service import FileService

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/{file_uuid}")
def download_file(file_uuid: str, user: CurrentUser, db: DbSession):
    record, path = FileService(db).get_file_for_download(file_uuid)
    return FileResponse(
        path=str(path),
        media_type=record.mime_type,
        filename=record.original_filename,
    )
