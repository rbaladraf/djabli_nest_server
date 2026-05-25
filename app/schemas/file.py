from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    file_uuid: str
    batch_uuid: str
    relative_path: str
    sha256: str
    message: str = "uploaded"
