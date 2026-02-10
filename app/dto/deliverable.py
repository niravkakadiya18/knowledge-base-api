from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class DeliverableCreate(BaseModel):
    clientId: int = Field(alias='client_id')
    deliverableType: str = Field(alias='deliverable_type')
    templateId: Optional[int] = Field(default=None, alias='template_id')
    reviewNotes: Optional[str] = Field(default=None, alias='review_notes')
    metadata: Optional[Dict[str, Any]] = {}

    class Config:
        populate_by_name = True

class ReviewSubmit(BaseModel):
    action: str  # approve, reject, request_changes
    comments: Optional[str] = None
    qualityScore: Optional[float] = Field(default=None, alias='quality_score')
    suggestedChanges: Optional[List[Dict[str, Any]]] = Field(default=None, alias='suggested_changes')

    class Config:
        populate_by_name = True

class DeliverableResponse(BaseModel):
    workflowId: int = Field(alias='workflow_id')
    clientId: int = Field(alias='client_id')
    deliverableType: str = Field(alias='deliverable_type')
    status: str
    submittedBy: Optional[int] = Field(alias='submitted_by')
    submittedAt: Optional[datetime] = Field(alias='submitted_at')
    reviewIteration: int = Field(default=1, alias='review_iteration')
    generationMetadata: Optional[Dict[str, Any]] = Field(default={}, alias='generation_metadata')
    updatedAt: datetime = Field(alias='updated_at')

    class Config:
        populate_by_name = True
