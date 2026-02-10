
import logging
from typing import List, Optional, Dict
import psycopg2
import secrets
from datetime import datetime
import json

from app.config.settings import settings
from app.utils.rbac import RBACManager, Role
from app.dto.user import UserResponse, CreateUserRequest, UpdateUserRequest, UserListResponse
from app.service.audit_service import audit_service

logger = logging.getLogger(__name__)

# Initialize RBAC (Shared instance logic could be refactored, but instantiated here for now)
rbac_manager = RBACManager(
    db_connection_params={"dsn": settings.DATABASE_URL},
    jwt_secret=settings.SECRET_KEY
)

def _get_db_connection():
    return psycopg2.connect(settings.DATABASE_URL)

def list_users(
    page: int, limit: int, search: str, role_filter: str, status_filter: str, 
    organisation_filter: int, current_user_id: int
) -> UserListResponse:
    conn = None
    try:
        conn = _get_db_connection()
        cur = conn.cursor()
        
        # Base query excluding current user and deleted users
        where_clauses = [
            "u.id != %s",
            "COALESCE((u.metadata->>'is_deleted')::boolean, false) = false"
        ]
        params = [current_user_id]
        
        # Filters
        if search:
            where_clauses.append("(u.full_name ILIKE %s OR u.email ILIKE %s OR u.username ILIKE %s)")
            params.extend([f'%{search}%'] * 3)
            
        if role_filter:
            where_clauses.append("u.role = %s")
            params.append(role_filter.lower())
            
        if status_filter:
            is_active = status_filter.lower() in ['enabled', 'active', 'true']
            where_clauses.append("u.is_active = %s")
            params.append(is_active)
            
        if organisation_filter:
            where_clauses.append("%s = ANY(u.client_access)")
            params.append(organisation_filter)
            
        where_stmt = " AND ".join(where_clauses)
        
        # Count total
        cur.execute(f"SELECT COUNT(*) FROM users u WHERE {where_stmt}", tuple(params))
        total = cur.fetchone()[0]
        
        # Fetch data
        query = f"""
            SELECT u.id, u.username, u.email, u.role, u.client_access, 
                   u.full_name, u.is_active, u.last_login, u.created_at
            FROM users u
            WHERE {where_stmt}
            ORDER BY u.created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, (page - 1) * limit])
        
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        
        # Get client names
        cur.execute("SELECT client_id, name FROM clients")
        client_map = {row[0]: row[1] for row in cur.fetchall()}
        
        users = []
        for row in rows:
            uid, uname, email, role, client_access, fname, is_active, last_login, created_at = row
            
            # Get client names
            org_names = [{'id': str(cid), 'name': client_map.get(cid, f'Client {cid}')} 
                         for cid in (client_access or [])]
            
            users.append(UserResponse(
                id=str(uid),
                fullName=fname or uname,
                username=uname,
                email=email,
                role=role.upper() if role else 'VIEWER',
                organisations=org_names,
                status='Enabled' if is_active else 'Disabled',
                lastLoginDate=last_login,
                createdAt=created_at
            ))
            
        return UserListResponse(
            data=users,
            total=total,
            page=page,
            limit=limit,
            totalPages=(total + limit - 1) // limit
        )
        
    except Exception as e:
        logger.error(f"List users error: {e}")
        raise e
    finally:
        if conn:
            conn.close()

def get_user(user_id: int) -> Optional[UserResponse]:
    conn = None
    try:
        conn = _get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, username, email, role, client_access, 
                   full_name, is_active, last_login, created_at
            FROM users 
            WHERE id = %s 
              AND COALESCE((metadata->>'is_deleted')::boolean, false) = false
        """, (user_id,))
        
        row = cur.fetchone()
        if not row:
            return None
            
        uid, uname, email, role, client_access, fname, is_active, last_login, created_at = row
        
        # Get orgs
        # Get orgs
        org_names = []
        if client_access:
            cur.execute("SELECT client_id, name FROM clients WHERE client_id = ANY(%s)", (client_access,))
            org_names = [{'id': str(r[0]), 'name': r[1]} for r in cur.fetchall()]
        
        return UserResponse(
            id=str(uid),
            fullName=fname or uname,
            username=uname,
            email=email,
            role=role.upper() if role else 'VIEWER',
            organisations=org_names,
            status='Enabled' if is_active else 'Disabled',
            lastLoginDate=last_login,
            createdAt=created_at
        )
    except Exception as e:
        logger.error(f"Get user error: {e}")
        return None
    finally:
        if conn:
            conn.close()

def create_user(request: CreateUserRequest, created_by: int) -> UserResponse:
    try:
        # Use provided password and username
        # If username is not provided, fallback to email prefix is handled by caller, but here we expect it in request
        
        # Create using RBAC
        user_id = rbac_manager.create_user(
            username=request.username,
            email=request.email,
            password=request.password,
            role=Role(request.role.lower()),
            client_ids=request.organisationIds
        )
        
        # Update extra fields
        conn = _get_db_connection()
        cur = conn.cursor()
        
        is_active = request.status.lower() in ['enabled', 'active', 'true']
        cur.execute("""
            UPDATE users SET full_name = %s, is_active = %s WHERE id = %s
        """, (request.fullName, is_active, user_id))
        conn.commit()
        conn.close()
        
        # Audit
        audit_service.log_action(
            user_id=created_by,
            action='CREATE_USER',
            resource_type='user',
            resource_id=user_id,
            details={'email': request.email}
        )
        
        logger.info(f"Created user {request.username}")
        
        return get_user(user_id)
        
    except Exception as e:
        logger.error(f"Create user error: {e}")
        raise e

def update_user(user_id: int, request: UpdateUserRequest, updated_by: int) -> Optional[UserResponse]:
    conn = None
    try:
        conn = _get_db_connection()
        cur = conn.cursor()
        
        # Check exists
        cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cur.fetchone():
            return None
            
        updates = []
        params = []
        
        if request.fullName is not None:
            updates.append("full_name = %s")
            params.append(request.fullName)
            
        if request.role is not None:
            updates.append("role = %s")
            params.append(request.role.lower())
            
        if request.organisationIds is not None:
            updates.append("client_access = %s")
            params.append(request.organisationIds)
            
        if request.status is not None:
            is_active = request.status.lower() in ['enabled', 'active', 'true']
            updates.append("is_active = %s")
            params.append(is_active)
            
        if updates:
            updates.append("updated_at = NOW()")
            params.append(user_id)
            
            cur.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = %s", tuple(params))
            conn.commit()
            
            audit_service.log_action(
                user_id=updated_by,
                action='UPDATE_USER',
                resource_type='user',
                resource_id=user_id
            )
            
        return get_user(user_id)
    except Exception as e:
        logger.error(f"Update user error: {e}")
        raise e
    finally:
        if conn:
            conn.close()

def delete_user(user_id: int, deleted_by: int, current_role: str) -> bool:
    conn = None
    try:
        conn = _get_db_connection()
        cur = conn.cursor()
        
        # Self delete check
        if user_id == deleted_by:
            raise ValueError("Cannot delete your own account")
            
        # Check target user
        cur.execute("SELECT role FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        if not row:
            return False
            
        target_role = row[0]
        
        if target_role == 'super_admin' and current_role == 'super_admin':
            raise ValueError("Cannot delete another super admin")
            
        # Hard delete dependencies
        cur.execute("DELETE FROM user_sessions WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM audit_log WHERE user_id = %s", (user_id,))
        
        # Hard delete user
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        
        conn.commit()
        
        # We can't log the action using the deleted user ID if we were self-deleting (blocked above), 
        # but here the deleted_by user still exists.
        audit_service.log_action(
            user_id=deleted_by,
            action='DELETE_USER',
            details={'deleted_user_id': user_id}
        )
        
        return True
    except psycopg2.IntegrityError as e:
        logger.error(f"Delete user constraint error: {e}")
        conn.rollback()
        raise ValueError("Cannot delete user because they have associated data (e.g. created entities).")
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()
