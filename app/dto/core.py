
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

# --- Stakeholders ---

class StakeholderBase(BaseModel):
    name: str
    role: Optional[str] = None
    email: Optional[EmailStr] = None
    tone: Optional[str] = 'neutral'
    metadata: Optional[Dict[str, Any]] = {}

    class Config:
        populate_by_name = True


class StakeholderCreate(StakeholderBase):
    clientId: int

    class Config:
        populate_by_name = True

class StakeholderUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    email: Optional[EmailStr] = None
    tone: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class StakeholderResponse(StakeholderBase):
    id: int = Field(alias='stakeholder_id')
    clientId: int = Field(alias='client_id')
    toneAnalysis: Optional[Dict[str, Any]] = Field(default={}, alias='tone_analysis')
    lastInteraction: Optional[datetime] = Field(default=None, alias='last_interaction')
    createdAt: datetime = Field(alias='created_at')
    updatedAt: datetime = Field(alias='updated_at')

    class Config:
        populate_by_name = True

# --- Knowledge Entries ---

class KnowledgeBase(BaseModel):
    content: str
    entryType: str = Field(alias='entry_type') # meeting, email, document, note
    source: Optional[str] = None
    daaegPhase: Optional[str] = Field(default=None, alias='daaeg_phase')
    tags: Optional[List[str]] = []
    metadata: Optional[Dict[str, Any]] = {}

    class Config:
        populate_by_name = True


class KnowledgeCreate(KnowledgeBase):
    clientId: int
    stakeholderIds: Optional[List[int]] = Field(default=[], alias='stakeholder_ids')
    # embedding: Optional[List[float]] = None # Optional for manual entry

    class Config:
        populate_by_name = True

class KnowledgeResponse(KnowledgeBase):
    id: int = Field(alias='entry_id')
    clientId: int = Field(alias='client_id')
    stakeholderIds: List[int] = Field(alias='stakeholder_ids')
    createdBy: Optional[int] = Field(alias='created_by')
    createdAt: datetime = Field(alias='created_at')
    updatedAt: datetime = Field(alias='updated_at')

    class Config:
        populate_by_name = True

class KnowledgeSearchRequest(BaseModel):
    clientId: int
    query: Optional[str] = None
    tags: Optional[List[str]] = None
    entryType: Optional[str] = None
    daaegPhase: Optional[str] = None
    stakeholderId: Optional[int] = None
    limit: int = 20
    offset: int = 0
