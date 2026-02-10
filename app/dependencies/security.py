# app/dependencies/security.py

from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config.settings import settings
from app.utils.rbac import RBACManager, Permission


# Extract Authorization: Bearer <token>
security = HTTPBearer(auto_error=False)


def get_rbac_manager() -> RBACManager:
    """
    Create RBACManager instance using settings and psycopg2.
    """
    db_params = {
        "host": settings.DATABASE_HOST,
        "port": settings.DATABASE_PORT,
        "dbname": settings.DATABASE_NAME,
        "user": settings.DATABASE_USER,
        "password": settings.DATABASE_PASSWORD,
    }

    return RBACManager(
        db_connection_params=db_params,
        jwt_secret=settings.SECRET_KEY,
    )


# =========================
# AUTH DEPENDENCIES
# =========================

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    rbac: RBACManager = Depends(get_rbac_manager),
):
    """
    Validate JWT token and return current user payload.
    Replacement for Flask @token_required
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token missing",
        )

    token = credentials.credentials
    payload = rbac.verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return payload


def require_permission(permission: Permission):
    """
    Require a specific permission.
    Replacement for Flask @require_permission
    """

    def dependency(current_user=Depends(get_current_user)):
        rbac = get_rbac_manager()
        user_role = current_user.get("role")

        if not rbac.has_permission(user_role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return True

    return dependency


def require_client_access(client_id_param: str = "client_id"):
    """
    Require access to a specific client.
    Replacement for Flask @require_client_access
    """

    def dependency(
        request: Request,
        current_user=Depends(get_current_user),
    ):
        client_id = None

        # Path params
        if client_id_param in request.path_params:
            client_id = request.path_params[client_id_param]

        # Query params
        elif client_id_param in request.query_params:
            client_id = int(request.query_params[client_id_param])

        # JSON body (optional)
        elif request.headers.get("content-type", "").startswith("application/json"):
            body = request.json()
            if client_id_param in body:
                client_id = body[client_id_param]

        if client_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Client ID is required",
            )

        rbac = get_rbac_manager()
        if not rbac.has_client_access(
            current_user.get("client_access", []),
            client_id,
            current_user.get("role"),
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied for this client",
            )

        return True

    return dependency
