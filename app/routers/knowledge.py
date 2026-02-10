
from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Optional
from app.dto.core import KnowledgeCreate, KnowledgeResponse, KnowledgeSearchRequest
from app.dto.api_response import APIResponse
from app.service.knowledge_service import KnowledgeService
from app.dependencies import get_current_user

router = APIRouter(prefix="/knowledge", tags=["Knowledge"])

@router.post("/", response_model=APIResponse[KnowledgeResponse], status_code=status.HTTP_201_CREATED)
def create_entry(payload: KnowledgeCreate, current_user: dict = Depends(get_current_user)):
    try:
        user_id = int(current_user['user_id'])
        entry = KnowledgeService.create_entry(payload, user_id)
        if not entry:
            raise HTTPException(status_code=400, detail="Could not create knowledge entry")
        return APIResponse(
            status="success",
            success=True,
            data=entry,
            message="Knowledge entry created successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=APIResponse[dict])
def search_entries(
    clientId: int = Query(..., description="Client ID to filter by"),
    query: Optional[str] = None,
    tags: Optional[List[str]] = Query(None),
    entryType: Optional[str] = None,
    daaegPhase: Optional[str] = None,
    stakeholderId: Optional[int] = None,
    page: int = 1,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    offset = (page - 1) * limit
    filters = KnowledgeSearchRequest(
        clientId=clientId,
        query=query,
        tags=tags,
        entryType=entryType,
        daaegPhase=daaegPhase,
        stakeholderId=stakeholderId,
        limit=limit,
        offset=offset
    )
    # Pass current_user to service for security check
    try:
        result = KnowledgeService.search_entries(filters, current_user)
        return APIResponse(
            status="success",
            success=True,
            data=result,
            message="Knowledge entries retrieved successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        if "Access denied" in str(e):
             raise HTTPException(status_code=403, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{entry_id}", response_model=APIResponse[KnowledgeResponse])
def get_entry(entry_id: int, current_user: dict = Depends(get_current_user)):
    try:
        entry = KnowledgeService.get_entry_by_id(entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        return APIResponse(
            status="success",
            success=True,
            data=entry,
            message="Knowledge entry retrieved successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(entry_id: int, current_user: dict = Depends(get_current_user)):
    try:
        success = KnowledgeService.delete_entry(entry_id)
        if not success:
             raise HTTPException(status_code=404, detail="Entry not found")
        return APIResponse(
            status="success",
            success=True,
            data=None,
            message="Knowledge entry deleted successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
