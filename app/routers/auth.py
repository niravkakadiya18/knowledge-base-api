
from fastapi import APIRouter, HTTPException, Depends, status, Request
from typing import Dict
from app.dto.auth import (
    LoginRequest, LoginResponse, 
    ForgotPasswordRequest, ResetPasswordRequest, 
    SuccessResponse
)
from app.dto.api_response import APIResponse
from app.service.auth_service import (
    login_user, forgot_password, reset_password, 
    verify_reset_token as verify_token_service,
    get_current_user_profile, logout_user
)
from app.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=APIResponse[LoginResponse])
def login(payload: LoginRequest):
    try:
        result = login_user(payload.email, payload.password)
        if not result:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return APIResponse(
            status="success",
            success=True,
            data=result,
            message="Login successful"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/me", response_model=APIResponse[dict])
def get_me(current_user: Dict = Depends(get_current_user)):
    try:
        user_id = current_user.get("user_id")
        profile = get_current_user_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="User not found")
        return APIResponse(
            status="success",
            success=True,
            data=profile,
            message="User profile retrieved"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/forgot-password", response_model=APIResponse[SuccessResponse])
def forgot_password_route(payload: ForgotPasswordRequest):
    try:
        # Logic: If email not found, we can either return true to prevent enumerating, 
        # The new service returns False if not found.
        success = forgot_password(payload.email)
        if not success:
             raise HTTPException(status_code=404, detail="Please enter a valid registered email")
        
        return APIResponse(
            status="success",
            success=True,
            data=SuccessResponse(success=True, message="Password reset link has been sent to your email."),
            message="Password reset link sent"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset-password", response_model=APIResponse[SuccessResponse])
def reset_password_route(payload: ResetPasswordRequest):
    try:
        if payload.password != payload.confirmPassword:
            raise HTTPException(status_code=400, detail="Passwords do not match")
            
        if len(payload.password) < 8:
             raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

        success = reset_password(payload.token, payload.password)
        if not success:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")
            
        return APIResponse(
            status="success",
            success=True,
            data=SuccessResponse(success=True, message="Password has been reset successfully. You can now log in."),
            message="Password reset successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/verify-reset-token", response_model=APIResponse[dict])
def verify_reset_token_route(token: str):
    try:
        is_valid = verify_token_service(token)
        if is_valid:
            return APIResponse(
                status="success",
                success=True,
                data={"valid": True, "message": "Token is valid"},
                message="Token is valid"
            )
        else:
            raise HTTPException(status_code=400, detail="Token is invalid or expired")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/logout", response_model=APIResponse[SuccessResponse])
def logout(current_user: Dict = Depends(get_current_user)):
    try:
        user_id = current_user.get("user_id")
        logout_user(user_id)
        return APIResponse(
            status="success",
            success=True,
            data=SuccessResponse(success=True, message="Logged out successfully"),
            message="Logged out successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))