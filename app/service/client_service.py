
import logging
import json
import psycopg2
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.config.settings import settings
from app.dto.client import (
    ClientCreate, ClientUpdate, ClientResponse, ClientListResponse, ClientDropdownItem
)
from app.service.audit_service import audit_service

logger = logging.getLogger(__name__)

class ClientService:
    @staticmethod
    def _get_connection():
        return psycopg2.connect(settings.DATABASE_URL)

    @staticmethod
    def _parse_json_field(value):
        if not value:
            return {}
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except Exception:
            return {}

    @staticmethod
    def list_organisations(
        page: int, limit: int, search: str, status: str, industry: str
    ) -> ClientListResponse:
        conn = None
        try:
            conn = ClientService._get_connection()
            cur = conn.cursor()
            
            # Base query
            base_query = """
                SELECT c.client_id, c.name, c.industry, c.relationship_start_date, c.is_active, 
                       c.metadata, c.created_at, c.updated_at
                FROM clients c
                WHERE 1=1
            """
            count_query = "SELECT COUNT(*) FROM clients c WHERE 1=1"
            params = []
            count_params = []
            
            # Search
            if search:
                search_clause = " AND (c.name ILIKE %s OR c.industry ILIKE %s)"
                base_query += search_clause
                count_query += search_clause
                search_param = f'%{search}%'
                params.extend([search_param, search_param])
                count_params.extend([search_param, search_param])
                
            # Status
            if status:
                is_active = status.lower() in ['enabled', 'active', 'true']
                status_clause = " AND c.is_active = %s"
                base_query += status_clause
                count_query += status_clause
                params.append(is_active)
                count_params.append(is_active)
                
            # Industry
            if industry:
                ind_clause = " AND c.industry = %s"
                base_query += ind_clause
                count_query += ind_clause
                params.append(industry)
                count_params.append(industry)
                
            # Count
            cur.execute(count_query, tuple(count_params))
            total = cur.fetchone()[0]
            
            # Pagination
            base_query += " ORDER BY c.created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, (page - 1) * limit])
            
            cur.execute(base_query, tuple(params))
            rows = cur.fetchall()
            
            data = []
            for row in rows:
                cid, name, ind, rel_start, active, meta_json, created, updated = row
                meta = ClientService._parse_json_field(meta_json)
                
                data.append(ClientResponse(
                    id=str(cid),
                    name=name,
                    industry=ind,
                    relationshipStartDate=rel_start,
                    status='Enabled' if active else 'Disabled',
                    metadata=meta,
                    created_at=created,
                    updated_at=updated
                ))
                
            return ClientListResponse(
                data=data,
                total=total,
                page=page,
                limit=limit,
                totalPages=(total + limit - 1) // limit
            )
        except Exception as e:
            logger.error(f"List organisations error: {e}")
            raise e
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_organisation(client_id: int) -> Optional[ClientResponse]:
        conn = None
        try:
            conn = ClientService._get_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT client_id, name, industry, relationship_start_date, is_active, metadata, 
                       created_at, updated_at
                FROM clients 
                WHERE client_id = %s
            """, (client_id,))
            
            row = cur.fetchone()
            if not row:
                return None
                
            cid, name, ind, rel_start, active, meta_json, created, updated = row
            meta = ClientService._parse_json_field(meta_json)
            
            return ClientResponse(
                id=str(cid),
                name=name,
                industry=ind,
                relationshipStartDate=rel_start,
                status='Enabled' if active else 'Disabled',
                metadata=meta,
                created_at=created,
                updated_at=updated
            )
        except Exception as e:
            logger.error(f"Get organisation error: {e}")
            return None
        finally:
            if conn:
                conn.close()

    @staticmethod
    def create_organisation(payload: ClientCreate, user_id: int) -> ClientResponse:
        conn = None
        try:
            conn = ClientService._get_connection()
            cur = conn.cursor()
            
            is_active = payload.status.lower() in ['enabled', 'active', 'true']
            
            is_active = payload.status.lower() in ['enabled', 'active', 'true']
            
            metadata = payload.metadata or {}
            
            cur.execute("""
                INSERT INTO clients (name, industry, relationship_start_date, is_active, metadata, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING client_id, created_at, updated_at
            """, (payload.name, payload.industry, payload.relationshipStartDate, is_active, json.dumps(metadata)))
            
            res = cur.fetchone()
            client_id, created_at, updated_at = res
            conn.commit()
            
            audit_service.log_action(
                user_id=user_id,
                action='CREATE_ORGANISATION',
                resource_type='client',
                resource_id=client_id,
                details={'name': payload.name}
            )
            
            return ClientResponse(
                id=str(client_id),
                name=payload.name,
                industry=payload.industry,
                relationshipStartDate=payload.relationshipStartDate,
                status='Enabled' if is_active else 'Disabled',
                metadata=metadata,
                created_at=created_at,
                updated_at=updated_at
            )
        except Exception as e:
            logger.error(f"Create organisation error: {e}")
            raise e
        finally:
            if conn:
                conn.close()

    @staticmethod
    def update_organisation(client_id: int, payload: ClientUpdate, user_id: int) -> Optional[ClientResponse]:
        conn = None
        try:
            conn = ClientService._get_connection()
            cur = conn.cursor()
            
            # Check exists
            cur.execute("SELECT client_id, metadata FROM clients WHERE client_id = %s", (client_id,))
            row = cur.fetchone()
            if not row:
                return None
            
            existing_meta = ClientService._parse_json_field(row[1])
            
            updates = []
            params = []
            
            if payload.name is not None:
                # Check duplicate name
                cur.execute("""
                    SELECT client_id FROM clients 
                    WHERE LOWER(name) = LOWER(%s) AND client_id != %s
                """, (payload.name.strip(), client_id))
                if cur.fetchone():
                    raise ValueError(f'An organisation with the name "{payload.name}" already exists.')
                    
                updates.append("name = %s")
                params.append(payload.name)
                
            if payload.industry is not None:
                updates.append("industry = %s")
                params.append(payload.industry)

            if payload.relationshipStartDate is not None:
                updates.append("relationship_start_date = %s")
                params.append(payload.relationshipStartDate)
                
            if payload.status is not None:
                is_active = payload.status.lower() in ['enabled', 'active', 'true']
                updates.append("is_active = %s")
                params.append(is_active)
            
            if payload.metadata is not None:
                updates.append("metadata = %s")
                params.append(json.dumps(payload.metadata))
                
            if updates:
                updates.append("updated_at = NOW()")
                params.append(client_id)
                
                cur.execute(f"UPDATE clients SET {', '.join(updates)} WHERE client_id = %s", tuple(params))
                conn.commit()
                
                audit_service.log_action(
                    user_id=user_id,
                    action='UPDATE_ORGANISATION',
                    resource_type='client',
                    resource_id=client_id
                )
                
            return ClientService.get_organisation(client_id)
            
        except Exception as e:
            logger.error(f"Update organisation error: {e}")
            raise e
        finally:
            if conn:
                conn.close()

    @staticmethod
    def delete_organisation(client_id: int, user_id: int) -> bool:
        conn = None
        try:
            conn = ClientService._get_connection()
            cur = conn.cursor()
            
            # 1. Delete Dependencies first to avoid constraint violations
            
            # Delete Stakeholders
            cur.execute("DELETE FROM stakeholders WHERE client_id = %s", (client_id,))
            
            # Delete Knowledge Entries
            cur.execute("DELETE FROM knowledge_entries WHERE client_id = %s", (client_id,))
            
            # Delete Deliverables (Workflows) 
            # Note: This might cascade to deliverable_reviews if FK exists (it should), verify if error occurs
            cur.execute("DELETE FROM deliverable_reviews WHERE workflow_id IN (SELECT workflow_id FROM deliverable_workflows WHERE client_id = %s)", (client_id,))
            cur.execute("DELETE FROM deliverable_workflows WHERE client_id = %s", (client_id,))
            
            # Delete Client
            cur.execute("DELETE FROM clients WHERE client_id = %s RETURNING client_id", (client_id,))
            
            if not cur.fetchone():
                return False
                
            conn.commit()
            
            audit_service.log_action(
                user_id=user_id,
                action='DELETE_ORGANISATION',
                details={'deleted_client_id': client_id}
            )
            return True
        except Exception as e:
            logger.error(f"Delete organisation error: {e}")
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_dropdown() -> List[ClientDropdownItem]:
        conn = None
        try:
            conn = ClientService._get_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT client_id, name FROM clients 
                WHERE is_active = true 
                ORDER BY name
            """)
            
            return [ClientDropdownItem(id=str(r[0]), name=r[1]) for r in cur.fetchall()]
        except Exception as e:
            logger.error(f"Get dropdown error: {e}")
            raise e
        finally:
            if conn:
                conn.close()
