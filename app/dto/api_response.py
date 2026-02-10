from typing import Optional, Generic, TypeVar, Any
from pydantic import BaseModel, Field

T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    status: str = Field(..., description="Response status: 'success' or 'error'")
    success: bool = Field(..., description="Boolean indicating success or failure")
    message: Optional[str] = Field(None, description="Human-readable message")
    data: Optional[T] = Field(None, description="Payload data")
    error: Optional[Any] = Field(None, description="Error details if any")

    class Config:
        arbitrary_types_allowed = True
