
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from app.dto.core import StakeholderCreate, StakeholderUpdate, StakeholderResponse
from app.dto.api_response import APIResponse
from app.service.stakeholder_service import StakeholderService
from app.dependencies import get_current_user

router = APIRouter(prefix="/stakeholders", tags=["Stakeholders"])

@router.post("/", response_model=APIResponse[StakeholderResponse], status_code=status.HTTP_201_CREATED)
def create_stakeholder(payload: StakeholderCreate, current_user: dict = Depends(get_current_user)):
    # TODO: Check if user has access to payload.clientId (RLS check in app level)
    try:
        stakeholder = StakeholderService.create_stakeholder(payload)
        if not stakeholder:
             raise HTTPException(status_code=400, detail="Could not create stakeholder")
        return APIResponse(
            status="success",
            success=True,
            data=stakeholder,
            message="Stakeholder created successfully"
        )
    except Exception as e:
        if "unique_stakeholder" in str(e):
             raise HTTPException(status_code=409, detail="Stakeholder with this email/name already exists for this client")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=APIResponse[List[StakeholderResponse]])
def get_stakeholders(clientId: Optional[int] = None, current_user: dict = Depends(get_current_user)):
    try:
        # TODO: Enforce that if clientId is None, only SuperAdmin can see all, otherwise filter by user's access
        result = StakeholderService.get_stakeholders(client_id=clientId)
        return APIResponse(
            status="success",
            success=True,
            data=result,
            message="Stakeholders retrieved successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{stakeholder_id}", response_model=APIResponse[StakeholderResponse])
def get_stakeholder(stakeholder_id: int, current_user: dict = Depends(get_current_user)):
    try:
        stakeholder = StakeholderService.get_stakeholder_by_id(stakeholder_id)
        if not stakeholder:
            raise HTTPException(status_code=404, detail="Stakeholder not found")
        return APIResponse(
            status="success",
            success=True,
            data=stakeholder,
            message="Stakeholder retrieved successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{stakeholder_id}", response_model=APIResponse[StakeholderResponse])
def update_stakeholder(stakeholder_id: int, payload: StakeholderUpdate, current_user: dict = Depends(get_current_user)):
    try:
        stakeholder = StakeholderService.update_stakeholder(stakeholder_id, payload)
        if not stakeholder:
            raise HTTPException(status_code=404, detail="Stakeholder not found or update failed")
        return APIResponse(
            status="success",
            success=True,
            data=stakeholder,
            message="Stakeholder updated successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{stakeholder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stakeholder(stakeholder_id: int, current_user: dict = Depends(get_current_user)):
    try:
        success = StakeholderService.delete_stakeholder(stakeholder_id)
        if not success:
            raise HTTPException(status_code=404, detail="Stakeholder not found")
        return APIResponse(
            status="success",
            success=True,
            data=None,
            message="Stakeholder deleted successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
