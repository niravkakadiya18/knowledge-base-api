
from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Optional
from app.dto.user import (
    UserResponse, CreateUserRequest, UpdateUserRequest, UserListResponse
)
from app.dto.api_response import APIResponse
from app.service.user_service import (
    list_users, get_user, create_user, update_user, delete_user
)
from app.dependencies import get_current_user, PermissionChecker
from app.utils.rbac import Permission

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("", response_model=APIResponse[UserListResponse])
def list_users_route(
    page: int = 1,
    limit: int = 10,
    search: str = "",
    role: str = "",
    status: str = "",
    organisation: Optional[int] = None,
    current_user: dict = Depends(PermissionChecker(Permission.MANAGE_USERS))
):
    current_user_id = current_user["user_id"]
    try:
        result = list_users(page, limit, search, role, status, organisation, current_user_id)
        return APIResponse(
            status="success",
            success=True,
            data=result,
            message="Users retrieved successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("", response_model=APIResponse[UserResponse], status_code=status.HTTP_201_CREATED)
def create_user_route(
    payload: CreateUserRequest,
    current_user: dict = Depends(PermissionChecker(Permission.MANAGE_USERS))
):
    try:
        result = create_user(payload, current_user["user_id"])
        return APIResponse(
            status="success",
            success=True,
            data=result,
            message="User created successfully"
        )
    except Exception as e:
        if 'duplicate key' in str(e).lower():
            raise HTTPException(status_code=409, detail="User with this email already exists")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_id}", response_model=APIResponse[UserResponse])
def get_user_route(
    user_id: int,
    current_user: dict = Depends(PermissionChecker(Permission.MANAGE_USERS))
):
    try:
        user = get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return APIResponse(
            status="success",
            success=True,
            data=user,
            message="User details retrieved successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{user_id}", response_model=APIResponse[UserResponse])
def update_user_route(
    user_id: int,
    payload: UpdateUserRequest,
    current_user: dict = Depends(PermissionChecker(Permission.MANAGE_USERS))
):
    try:
        updated_user = update_user(user_id, payload, current_user["user_id"])
        if not updated_user:
             raise HTTPException(status_code=404, detail="User not found")
        return APIResponse(
            status="success",
            success=True,
            data=updated_user,
            message="User updated successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{user_id}")
def delete_user_route(
    user_id: int,
    current_user: dict = Depends(PermissionChecker(Permission.MANAGE_USERS))
):
    try:
        success = delete_user(user_id, current_user["user_id"], current_user.get("role"))
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        return APIResponse(
            status="success",
            success=True,
            data={"success": True, "message": "User deleted successfully", "id": str(user_id)},
            message="User deleted successfully"
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
