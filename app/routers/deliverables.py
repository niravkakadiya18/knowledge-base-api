from fastapi import APIRouter, HTTPException, Depends, status
from app.dto.deliverable import DeliverableCreate, DeliverableResponse, ReviewSubmit
from app.dto.api_response import APIResponse
from app.service.deliverable_service import DeliverableService
from app.dependencies import get_current_user, PermissionChecker
from app.utils.rbac import Permission, RBACManager

router = APIRouter(prefix="/deliverables", tags=["Deliverables"])

@router.post("/submit", response_model=APIResponse[DeliverableResponse], status_code=status.HTTP_201_CREATED)
def submit_deliverable(
    payload: DeliverableCreate,
    current_user: dict = Depends(PermissionChecker(Permission.WRITE_DELIVERABLE))
):
    try:
        # Check client access
        rbac = RBACManager()
        if not rbac.has_client_access(current_user['client_access'], payload.clientId, current_user['role']):
             raise HTTPException(status_code=403, detail="Access denied for this client")

        user_id = current_user['user_id']
        result = DeliverableService.submit_deliverable(payload, user_id)
        
        return APIResponse(
            status="success",
            success=True,
            data=result,
            message="Deliverable submitted successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{workflow_id}/review", response_model=APIResponse[dict])
def submit_review(
    workflow_id: int,
    payload: ReviewSubmit,
    current_user: dict = Depends(PermissionChecker(Permission.APPROVE_DELIVERABLE))
):
    try:
        user_id = current_user['user_id']
        # Note: Additional verification if user is assigned reviewer should be here or in service
        success = DeliverableService.submit_review(workflow_id, user_id, payload)
        
        return APIResponse(
            status="success",
            success=True,
            data={"submitted": success},
            message="Review submitted successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{workflow_id}", response_model=APIResponse[DeliverableResponse])
def get_deliverable_status(
    workflow_id: int,
    current_user: dict = Depends(PermissionChecker(Permission.READ_DELIVERABLE))
):
    try:
        result = DeliverableService.get_deliverable(workflow_id)
        if not result:
            raise HTTPException(status_code=404, detail="Deliverable not found")
        
        return APIResponse(
            status="success",
            success=True,
            data=result,
            message="Deliverable status retrieved"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
