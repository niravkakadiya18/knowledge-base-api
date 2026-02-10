
from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Optional

from app.dto.api_response import APIResponse
from app.dto.client import (
    ClientCreate, ClientUpdate, ClientResponse, ClientListResponse, ClientDropdownItem
)
from app.service.client_service import ClientService
from app.dependencies import get_current_user, PermissionChecker
from app.utils.rbac import Permission

router = APIRouter(prefix="/organisations", tags=["Organisations (Clients)"])

@router.get("/", response_model=APIResponse[ClientListResponse])
def list_organisations(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    industry: Optional[str] = None,
    # current_user: dict = Depends(PermissionChecker(Permission.READ_ORGANISATION)) # Assuming permission enum exists, else use get_current_user
    current_user: dict = Depends(get_current_user)
):
    try:
        result = ClientService.list_organisations(page, limit, search, status, industry)
        return APIResponse(
            status="success",
            success=True,
            data=result,
            message="Organisations retrieved successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dropdown", response_model=APIResponse[List[ClientDropdownItem]])
def get_organisation_dropdown(
    current_user: dict = Depends(get_current_user)
):
    try:
        result = ClientService.get_dropdown()
        return APIResponse(
            status="success",
            success=True,
            data=result,
            message="Organisation dropdown retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{client_id}", response_model=APIResponse[ClientResponse])
def get_organisation(
    client_id: int,
    current_user: dict = Depends(get_current_user)
):
    try:
        client = ClientService.get_organisation(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Organisation not found")
            
        return APIResponse(
            status="success",
            success=True,
            data=client,
            message="Organisation retrieved successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=APIResponse[ClientResponse], status_code=status.HTTP_201_CREATED)
def create_organisation(
    payload: ClientCreate,
    current_user: dict = Depends(get_current_user)
):
    # TODO: Add specific permission check if needed, e.g. ADMIN only
    try:
        client = ClientService.create_organisation(payload, int(current_user['user_id']))
        return APIResponse(
            status="success",
            success=True,
            data=client,
            message="Organisation created successfully"
        )
    except Exception as e:
        if "already exists" in str(e):
             raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{client_id}", response_model=APIResponse[ClientResponse])
def update_organisation(
    client_id: int,
    payload: ClientUpdate,
    current_user: dict = Depends(get_current_user)
):
    try:
        client = ClientService.update_organisation(client_id, payload, int(current_user['user_id']))
        if not client:
             raise HTTPException(status_code=404, detail="Organisation not found")
             
        return APIResponse(
            status="success",
            success=True,
            data=client,
            message="Organisation updated successfully"
        )
    except ValueError as ve:
        raise HTTPException(status_code=409, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{client_id}")
def delete_organisation(
    client_id: int,
    current_user: dict = Depends(get_current_user)
):
    try:
        success = ClientService.delete_organisation(client_id, int(current_user['user_id']))
        if not success:
            raise HTTPException(status_code=404, detail="Organisation not found")
            
        return APIResponse(
            status="success",
            success=True,
            data=None,
            message="Organisation deleted successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
