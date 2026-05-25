from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
    extra: Optional[dict[str, Any]] = None


class MessageResponse(BaseModel):
    message: str
