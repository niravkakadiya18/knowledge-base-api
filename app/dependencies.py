
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Optional, List
import jwt
from app.config.settings import settings
from app.utils.rbac import RBACManager, Permission

security = HTTPBearer()

rbac_manager = RBACManager(
    db_connection_params={
        "host": settings.DATABASE_HOST,
        "port": settings.DATABASE_PORT,
        "database": settings.DATABASE_NAME,
        "user": settings.DATABASE_USER,
        "password": settings.DATABASE_PASSWORD,
    },
    jwt_secret=settings.SECRET_KEY
)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = rbac_manager.verify_token(token)
    if payload is None:
        raise credentials_exception
        
    return payload

def get_current_active_user(current_user: Dict = Depends(get_current_user)) -> Dict:
    # In verify_token we trust the token, but we could also check DB here if needed.
    # For now, just return the payload from token.
    return current_user

class PermissionChecker:
    def __init__(self, required_permission: Permission):
        self.required_permission = required_permission

    def __call__(self, current_user: Dict = Depends(get_current_active_user)):
        user_role = current_user.get("role")
        if not rbac_manager.has_permission(user_role, self.required_permission):
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
