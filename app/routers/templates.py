from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from typing import List, Optional
from app.dto.template import TemplateCreate, TemplateResponse, TemplateVersionResponse
from app.dto.api_response import APIResponse
from app.service.template_service import TemplateService
from app.dependencies import get_current_user, PermissionChecker
from app.utils.rbac import Permission
import shutil
import tempfile
import os

router = APIRouter(prefix="/templates", tags=["Templates"])

@router.post("", response_model=APIResponse[TemplateResponse], status_code=status.HTTP_201_CREATED)
def create_template(
    name: str = Form(..., description="Name of the template"),
    description: str = Form(..., description="Description of the template"),
    template_type: str = Form(..., description="Type of template (e.g., report, proposal)"),
    file: UploadFile = File(...),
    current_user: dict = Depends(PermissionChecker(Permission.WRITE_TEMPLATE))
):
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        
        payload = TemplateCreate(name=name, description=description, templateType=template_type, isActive=True)
        user_id = current_user['user_id']
        
        result = TemplateService.create_template(payload, tmp_path, user_id)
        
        # Cleanup temp file
        os.unlink(tmp_path)
        
        return APIResponse(
            status="success",
            success=True,
            data=result,
            message="Template created successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=APIResponse[List[TemplateResponse]])
def list_templates(
    current_user: dict = Depends(PermissionChecker(Permission.READ_TEMPLATE))
):
    try:
        # TODO: Add client_id filter logic based on user role
        result = TemplateService.list_templates()
        return APIResponse(
            status="success",
            success=True,
            data=result,
            message="Templates retrieved successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{template_id}", response_model=APIResponse[TemplateResponse])
def get_template(
    template_id: int,
    current_user: dict = Depends(PermissionChecker(Permission.READ_TEMPLATE))
):
    try:
        result = TemplateService.get_template(template_id)
        if not result:
            raise HTTPException(status_code=404, detail="Template not found")
        return APIResponse(
            status="success",
            success=True,
            data=result,
            message="Template retrieved successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{template_id}/versions", response_model=APIResponse[TemplateVersionResponse])
def add_version(
    template_id: int,
    file: UploadFile = File(...),
    changelog: str = Form(None, description="Notes about changes in this version"),
    current_user: dict = Depends(PermissionChecker(Permission.WRITE_TEMPLATE))
):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
            
        user_id = current_user['user_id']
        result = TemplateService.add_template_version(template_id, tmp_path, user_id, changelog)
        
        os.unlink(tmp_path)
        
        return APIResponse(
            status="success",
            success=True,
            data=result,
            message="Version added successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
