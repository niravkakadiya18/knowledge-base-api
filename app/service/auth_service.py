
import logging
from typing import Optional, Dict, List
import psycopg2
import json
from datetime import datetime, timedelta
import secrets

from app.config.settings import settings
from app.utils.rbac import RBACManager
from app.dto.auth import LoginResponse, UserDTO, OrganisationDTO
from app.service.audit_service import audit_service
from app.service.email_service import email_service

logger = logging.getLogger(__name__)

# Initialize RBAC Manager
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

def _get_db_connection():
    return psycopg2.connect(
        host=settings.DATABASE_HOST,
        port=settings.DATABASE_PORT,
        database=settings.DATABASE_NAME,
        user=settings.DATABASE_USER,
        password=settings.DATABASE_PASSWORD,
    )

def login_user(email: str, password: str) -> Optional[LoginResponse]:
    """
    Authenticates user and returns login response with token and user details.
    """
    user_data = rbac_manager.authenticate_user(email, password)
    
    if not user_data:
        return None

    token = rbac_manager.generate_token(user_data)
    
    # Get organisations
    organisations = []
    last_selected_org_id = None
    
    conn = None
    try:
        conn = _get_db_connection()
        cur = conn.cursor()
        
        # Logic to fetch organisations based on role (Super Admin vs others)
        if user_data.get('role') == 'super_admin':
            cur.execute("""
                SELECT client_id, name FROM clients 
                WHERE is_active = true 
                  AND (metadata->>'is_deleted' IS NULL OR metadata->>'is_deleted' != 'true')
                ORDER BY name
            """)
            organisations_data = cur.fetchall()
        elif user_data.get('client_access'):
            cur.execute("""
                SELECT client_id, name FROM clients 
                WHERE client_id = ANY(%s)
                  AND is_active = true
                  AND (metadata->>'is_deleted' IS NULL OR metadata->>'is_deleted' != 'true')
            """, (user_data['client_access'],))
            organisations_data = cur.fetchall()
        else:
            organisations_data = []

        organisations = [OrganisationDTO(id=str(row[0]), name=row[1]) for row in organisations_data]
        
        # Get last selected org from metadata
        user_meta = user_data.get('metadata', {})
        last_selected_org_id = user_meta.get('last_selected_org_id')
        
        # Default to first org if no last selected
        if not last_selected_org_id and organisations:
            last_selected_org_id = organisations[0].id
            
        cur.close()
    except Exception as e:
        logger.error(f"Error fetching organisations: {e}")
    finally:
        if conn:
            conn.close()

    # Audit Log
    audit_service.log_action(
        user_id=user_data['id'],
        action='USER_LOGIN',
        details={'email': email}
    )

    return LoginResponse(
        token=token,
        user=UserDTO(
            id=str(user_data['id']),
            name=user_data.get('full_name') or user_data['username'],
            email=user_data['email'],
            role=user_data['role'],
            organisation=organisations[0].name if organisations else None,
            organisations=organisations,
            lastSelectedOrgId=str(last_selected_org_id) if last_selected_org_id else None
        )
    )

def forgot_password(email: str) -> bool:
    """
    Initiates password reset flow.
    """
    conn = None
    try:
        conn = _get_db_connection()
        cur = conn.cursor()
        
        # Check user existence
        cur.execute("""
            SELECT id, full_name FROM users 
            WHERE email = %s AND is_active = true
            AND COALESCE((metadata->>'is_deleted')::boolean, false) = false
        """, (email.lower(),))
        row = cur.fetchone()
        
        if not row:
            return False
            
        user_id, full_name = row
        
        # Generate and store token
        reset_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        cur.execute("""
            INSERT INTO user_sessions (user_id, token_hash, expires_at, created_at)
            VALUES (%s, %s, %s, NOW())
        """, (user_id, f"reset_{reset_token}", expires_at))
        
        conn.commit()
        
        # Send Email
        email_service.send_password_reset_email(email, reset_token, full_name or "User")
        
        # Audit Log
        audit_service.log_action(
            user_id=user_id,
            action='PASSWORD_RESET_REQUESTED',
            details={'email': email}
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Forgot password error: {e}")
        return False
    finally:
        if conn:
            conn.close()

def verify_reset_token(token: str) -> bool:
    conn = None
    try:
        conn = _get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT user_id FROM user_sessions 
            WHERE token_hash = %s AND expires_at > NOW()
        """, (f"reset_{token}",))
        
        return cur.fetchone() is not None
    except Exception as e:
        logger.error(f"Verify token error: {e}")
        return False
    finally:
        if conn:
            conn.close()

def reset_password(token: str, password: str) -> bool:
    conn = None
    try:
        conn = _get_db_connection()
        cur = conn.cursor()
        
        # Validate token
        cur.execute("""
            SELECT user_id FROM user_sessions 
            WHERE token_hash = %s AND expires_at > NOW()
        """, (f"reset_{token}",))
        
        row = cur.fetchone()
        if not row:
            return False
            
        user_id = row[0]
        
        # Hash new password
        password_hash, salt = rbac_manager._hash_password(password)
        
        # Update user
        cur.execute("""
            UPDATE users 
            SET password_hash = %s, salt = %s, updated_at = NOW()
            WHERE id = %s
        """, (password_hash, salt, user_id))
        
        # Invalidate tokens
        cur.execute("DELETE FROM user_sessions WHERE user_id = %s", (user_id,))
        
        conn.commit()
        
        audit_service.log_action(
            user_id=user_id,
            action='PASSWORD_RESET_COMPLETED'
        )
        
        return True
    except Exception as e:
        logger.error(f"Reset password error: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_current_user_profile(user_id: int) -> Optional[Dict]:
    conn = None
    try:
        conn = _get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, username, email, role, client_access, full_name, last_login
            FROM users WHERE id = %s
        """, (user_id,))
        
        row = cur.fetchone()
        if not row:
            return None
            
        uid, uname, email, role, client_access, full_name, last_login = row
        
        # Get organisations
        organisations = []
        if client_access:
            cur.execute("SELECT client_id, name FROM clients WHERE client_id = ANY(%s)", (client_access,))
            organisations = [{'id': str(r[0]), 'name': r[1]} for r in cur.fetchall()]
            
        return {
            'id': str(uid),
            'username': uname,
            'email': email,
            'role': role,
            'organisations': organisations,
            'profilePicture': None,
            'lastLoginDate': last_login.isoformat() if last_login else None
        }
    except Exception as e:
        logger.error(f"Get profile error: {e}")
        return None
    finally:
        if conn:
            conn.close()

def logout_user(user_id: int):
    conn = None
    try:
        conn = _get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM user_sessions WHERE user_id = %s", (user_id,))
        conn.commit()
        
        audit_service.log_action(
            user_id=user_id,
            action='USER_LOGOUT',
            details={'method': 'explicit_logout'}
        )
    except Exception as e:
        logger.error(f"Logout error: {e}")
    finally:
        if conn:
            conn.close()
