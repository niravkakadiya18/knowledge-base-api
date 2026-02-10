
import json
import logging
from typing import Dict, Optional, Any
import psycopg2
from app.config.settings import settings

logger = logging.getLogger(__name__)

class AuditService:
    @staticmethod
    def log_action(
        user_id: Optional[int],
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        client_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an action to the audit_log table.
        """
        conn = None
        try:
            conn = psycopg2.connect(settings.DATABASE_URL)
            cur = conn.cursor()
            
            query = """
                INSERT INTO audit_log 
                (user_id, action, resource_type, resource_id, client_id, details, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """
            cur.execute(query, (
                user_id,
                action,
                resource_type,
                resource_id,
                client_id,
                json.dumps(details or {})
            ))
            conn.commit()
            logger.info(f"Audit log: {action} by user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to log audit action: {e}")
        finally:
            if conn:
                conn.close()

audit_service = AuditService()
