from pydantic import BaseModel, HttpUrl, EmailStr
from typing import Optional, List
from datetime import datetime, date

# Shared properties
class ClientBase(BaseModel):
    name: str
    industry: Optional[str] = None
    relationshipStartDate: Optional[date] = None
    status: Optional[str] = "enabled"  # enabled, disabled
    metadata: Optional[dict] = {}

class ClientCreate(ClientBase):
    pass

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    relationshipStartDate: Optional[date] = None
    status: Optional[str] = None
    metadata: Optional[dict] = None

class ClientResponse(ClientBase):
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ClientListResponse(BaseModel):
    data: List[ClientResponse]
    total: int
    page: int
    limit: int
    totalPages: int

class ClientDropdownItem(BaseModel):
    id: str
    name: str

