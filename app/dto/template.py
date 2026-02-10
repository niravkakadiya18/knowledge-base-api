from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class TemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    templateType: str = Field(alias='template_type')
    clientId: Optional[int] = Field(default=None, alias='client_id')
    isActive: bool = Field(default=True, alias='is_active')

    class Config:
        populate_by_name = True

class TemplateCreate(TemplateBase):
    pass

class TemplateVersionResponse(BaseModel):
    versionId: int = Field(alias='version_id')
    versionNumber: str = Field(alias='version_number')
    filePath: str = Field(alias='file_path')
    createdAt: datetime = Field(alias='created_at')
    createdBy: Optional[int] = Field(alias='created_by')
    changelog: Optional[str] = None
    isActive: bool = Field(default=True, alias='is_active')

    class Config:
        populate_by_name = True

class TemplateResponse(TemplateBase):
    id: int = Field(alias='template_id')
    createdBy: Optional[int] = Field(alias='created_by')
    createdAt: datetime = Field(alias='created_at')
    versions: List[TemplateVersionResponse] = []

    class Config:
        populate_by_name = True

class TemplateVersionCreate(BaseModel):
    changelog: Optional[str] = None
