# app/utils/rbac.py

from enum import Enum
from typing import Dict, Tuple, List, Optional, Set
from datetime import datetime, timedelta

import jwt
import hashlib
import secrets
import psycopg2



from app.config.settings import settings
from app.config.logger import logger




# =========================
# Permissions & Roles
# =========================

class Permission(Enum):
    READ_KNOWLEDGE = "read_knowledge"
    WRITE_KNOWLEDGE = "write_knowledge"
    DELETE_KNOWLEDGE = "delete_knowledge"

    READ_CLIENT = "read_client"
    WRITE_CLIENT = "write_client"
    DELETE_CLIENT = "delete_client"

    READ_STAKEHOLDER = "read_stakeholder"
    WRITE_STAKEHOLDER = "write_stakeholder"
    DELETE_STAKEHOLDER = "delete_stakeholder"

    READ_DELIVERABLE = "read_deliverable"
    WRITE_DELIVERABLE = "write_deliverable"
    DELETE_DELIVERABLE = "delete_deliverable"
    APPROVE_DELIVERABLE = "approve_deliverable"

    READ_TEMPLATE = "read_template"
    WRITE_TEMPLATE = "write_template"
    DELETE_TEMPLATE = "delete_template"
    VERSION_TEMPLATE = "version_template"

    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"
    SYSTEM_ADMIN = "system_admin"
    READ_AUDIT_LOG = "read_audit_log"

    MANAGE_FIREFLIES = "manage_fireflies"


class Role(Enum):
    SUPER_ADMIN = "super_admin"
    CLIENT_ADMIN = "client_admin"
    PROJECT_MANAGER = "project_manager"
    ANALYST = "analyst"
    VIEWER = "viewer"
    GUEST = "guest"


ROLE_PERMISSIONS = {
    Role.SUPER_ADMIN: list(Permission),

    Role.CLIENT_ADMIN: [
        Permission.READ_KNOWLEDGE, Permission.WRITE_KNOWLEDGE, Permission.DELETE_KNOWLEDGE,
        Permission.READ_CLIENT, Permission.WRITE_CLIENT,
        Permission.READ_STAKEHOLDER, Permission.WRITE_STAKEHOLDER, Permission.DELETE_STAKEHOLDER,
        Permission.READ_DELIVERABLE, Permission.WRITE_DELIVERABLE, Permission.DELETE_DELIVERABLE,
        Permission.APPROVE_DELIVERABLE,
        Permission.READ_TEMPLATE, Permission.WRITE_TEMPLATE, Permission.VERSION_TEMPLATE,
        Permission.MANAGE_FIREFLIES,
        Permission.READ_AUDIT_LOG,
    ],

    Role.PROJECT_MANAGER: [
        Permission.READ_KNOWLEDGE, Permission.WRITE_KNOWLEDGE,
        Permission.READ_CLIENT,
        Permission.READ_STAKEHOLDER, Permission.WRITE_STAKEHOLDER,
        Permission.READ_DELIVERABLE, Permission.WRITE_DELIVERABLE, Permission.APPROVE_DELIVERABLE,
        Permission.READ_TEMPLATE, Permission.WRITE_TEMPLATE,
    ],

    Role.ANALYST: [
        Permission.READ_KNOWLEDGE, Permission.WRITE_KNOWLEDGE,
        Permission.READ_CLIENT,
        Permission.READ_STAKEHOLDER,
        Permission.READ_DELIVERABLE, Permission.WRITE_DELIVERABLE,
        Permission.READ_TEMPLATE,
    ],

    Role.VIEWER: [
        Permission.READ_KNOWLEDGE,
        Permission.READ_CLIENT,
        Permission.READ_STAKEHOLDER,
        Permission.READ_DELIVERABLE,
        Permission.READ_TEMPLATE,
    ],

    Role.GUEST: [
        Permission.READ_KNOWLEDGE,
        Permission.READ_DELIVERABLE,
    ],
}


# =========================
# RBAC Manager
# =========================

class RBACManager:
    """
    Handles authentication, authorization, and permission checks.
    Uses PostgreSQL (psycopg2) and JWT.
    """

    def __init__(self, db_connection_params: Dict = None, jwt_secret: str = None):
        self.db_params = db_connection_params or {
            "host": settings.DATABASE_HOST,
            "port": settings.DATABASE_PORT,
            "database": settings.DATABASE_NAME,
            "user": settings.DATABASE_USER,
            "password": settings.DATABASE_PASSWORD,
        }
        self.jwt_secret = jwt_secret or settings.SECRET_KEY
        self.token_expiry_hours = 24

    def _get_db_connection(self):
        return psycopg2.connect(**self.db_params)

    # -------- Password Handling --------

    def _hash_password(self, password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        if salt is None:
            salt = secrets.token_hex(32)

        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100_000,
        ).hex()

        return password_hash, salt

    # -------- User Management --------
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        conn = cur = None
        try:
            conn = self._get_db_connection()
            cur = conn.cursor()

            cur.execute(
                """
                SELECT
                    id,
                    username,
                    email,
                    password_hash,
                    salt,
                    role,
                    client_access,
                    is_active,
                    full_name,
                    metadata
                FROM users
                WHERE email = %s
                    AND is_active = true
                    AND COALESCE((metadata->>'is_deleted')::boolean, false) = false
                """,
                (email.lower(),),
            )

            row = cur.fetchone()
            if not row:
                return None

            user_id, uname, email, stored_hash, salt, role, client_access, is_active, full_name, metadata = row
            computed_hash, _ = self._hash_password(password, salt)

            if computed_hash != stored_hash:
                return None

            return {
                "id": user_id,
                "username": uname,
                "email": email,
                "role": role,
                "client_access": client_access or [],
                "is_active": is_active,
                "full_name": full_name,
                "metadata": metadata or {}
            }

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return None
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    def create_user(self, username: str, email: str, password: str, role: Role, client_ids: List[int] = None) -> int:
        """
        Create a new user and return permissions.
        """
        conn = cur = None
        try:
            conn = self._get_db_connection()
            cur = conn.cursor()

            password_hash, salt = self._hash_password(password)

            cur.execute(
                """
                INSERT INTO users (
                    username, email, password_hash, salt, role, client_access, is_active, is_superuser, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, true, false, NOW(), NOW())
                RETURNING id
                """,
                (username, email.lower(), password_hash, salt, role.value, client_ids or []),
            )
            
            user_id = cur.fetchone()[0]
            conn.commit()
            return user_id

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to create user: {e}")
            raise e
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    # -------- JWT --------

    def generate_token(self, user_data: Dict) -> str:
        payload = {
            "user_id": user_data["id"],
            "username": user_data["username"],
            "role": user_data["role"],
            "client_access": user_data["client_access"],
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=self.token_expiry_hours),
        }

        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")

    def verify_token(self, token: str) -> Optional[Dict]:
        try:
            return jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            logger.warning("JWT expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid JWT")
            return None

    # -------- Permissions --------

    def get_user_permissions(self, role: str) -> Set[Permission]:
        try:
            return set(ROLE_PERMISSIONS.get(Role(role), []))
        except ValueError:
            return set()

    def has_permission(self, user_role: str, permission: Permission) -> bool:
        return permission in self.get_user_permissions(user_role)

    def has_client_access(self, user_client_access: List[int], client_id: int, user_role: str) -> bool:
        if user_role == Role.SUPER_ADMIN.value:
            return True
        return client_id in (user_client_access or [])
