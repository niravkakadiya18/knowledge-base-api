
import psycopg2
import json
from typing import List, Optional, Dict, Any
from app.config.settings import settings
from app.dto.core import KnowledgeCreate, KnowledgeResponse, KnowledgeSearchRequest

class KnowledgeService:
    @staticmethod
    def get_connection():
        return psycopg2.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            database=settings.DATABASE_NAME,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
        )

    @staticmethod
    def create_entry(payload: KnowledgeCreate, created_by: int) -> Optional[KnowledgeResponse]:
        conn = KnowledgeService.get_connection()
        try:
            cur = conn.cursor()
            
            # Note: We are putting a dummy embedding array [0.0] * 384 just to satisfy the schema if needed
            # or NULL if the schema allows it. The schema has no NOT NULL constraint on embedding.
            # But since type is float8[], we can pass None safely.
            
            cur.execute("""
                INSERT INTO knowledge_entries (
                    client_id, content, entry_type, source, 
                    daaeg_phase, tags, stakeholder_ids, 
                    metadata, created_by, created_at, updated_at, embedding
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), %s)
                RETURNING entry_id, client_id, content, entry_type, source, daaeg_phase, tags, stakeholder_ids, metadata, created_by, created_at, updated_at
            """, (
                payload.clientId,
                payload.content,
                payload.entryType,
                payload.source,
                payload.daaegPhase,
                payload.tags,
                payload.stakeholderIds,
                json.dumps(payload.metadata or {}),
                created_by,
                None # Embedding (None for now)
            ))
            row = cur.fetchone()
            conn.commit()
            
            if row:
                return KnowledgeResponse(
                    entry_id=row[0],
                    client_id=row[1],
                    content=row[2],
                    entry_type=row[3],
                    source=row[4],
                    daaeg_phase=row[5],
                    tags=row[6] or [],
                    stakeholder_ids=row[7] or [],
                    metadata=row[8] or {},
                    created_by=row[9],
                    created_at=row[10],
                    updated_at=row[11]
                )
            return None
        except Exception as e:
            conn.rollback()
            print(f"Error creating knowledge entry: {e}")
            raise e
        finally:
            conn.close()

    @staticmethod
    def search_entries(filters: KnowledgeSearchRequest, current_user: dict) -> Dict[str, Any]:
        
        # Security Check: Ensure user has access to the requested client
        from app.utils.rbac import RBACManager, Role
        rbac = RBACManager()
        if not rbac.has_client_access(current_user.get("client_access", []), filters.clientId, current_user.get("role")):
             # We return empty results instead of 403 to avoid leaking existence, or we could raise exception
             # Raising exception is safer for API clarity
             raise Exception(f"Access denied: User does not have permission for client {filters.clientId}")

        conn = KnowledgeService.get_connection()
        try:
            cur = conn.cursor()
            
            # Base Query
            query = """
                SELECT entry_id, client_id, content, entry_type, source, daaeg_phase, tags, stakeholder_ids, metadata, created_by, created_at, updated_at
                FROM knowledge_entries
                WHERE client_id = %s
            """
            params = [filters.clientId]
            
            # Text Search (Simple ILIKE)
            if filters.query:
                query += " AND content ILIKE %s"
                params.append(f"%{filters.query}%")
                
            # Filters
            if filters.entryType:
                query += " AND entry_type = %s"
                params.append(filters.entryType)
                
            if filters.daaegPhase:
                query += " AND daaeg_phase = %s"
                params.append(filters.daaegPhase)
                
            if filters.stakeholderId:
                query += " AND %s = ANY(stakeholder_ids)"
                params.append(filters.stakeholderId)
                
            if filters.tags and len(filters.tags) > 0:
                # Array intersection: entries where tags && [search_tags] matches
                query += " AND tags && %s"
                params.append(filters.tags)

            # Pagination
            # Get Total Count First
            count_query = f"SELECT COUNT(*) FROM ({query}) AS sub"
            cur.execute(count_query, tuple(params))
            total = cur.fetchone()[0]

            # Add Limit/Offset
            query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            params.append(filters.limit)
            params.append(filters.offset)

            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            
            data = [
                KnowledgeResponse(
                    entry_id=row[0],
                    client_id=row[1],
                    content=row[2],
                    entry_type=row[3],
                    source=row[4],
                    daaeg_phase=row[5],
                    tags=row[6] or [],
                    stakeholder_ids=row[7] or [],
                    metadata=row[8] or {},
                    created_by=row[9],
                    created_at=row[10],
                    updated_at=row[11]
                ) for row in rows
            ]
            
            return {
                "data": data,
                "total": total,
                "page": int(filters.offset / filters.limit) + 1,
                "limit": filters.limit
            }
            
        finally:
            conn.close()

    @staticmethod
    def delete_entry(entry_id: int) -> bool:
        conn = KnowledgeService.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM knowledge_entries WHERE entry_id = %s", (entry_id,))
            rows_deleted = cur.rowcount
            conn.commit()
            return rows_deleted > 0
        finally:
            conn.close()
            
    @staticmethod
    def get_entry_by_id(entry_id: int) -> Optional[KnowledgeResponse]:
        conn = KnowledgeService.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT entry_id, client_id, content, entry_type, source, daaeg_phase, tags, stakeholder_ids, metadata, created_by, created_at, updated_at
                FROM knowledge_entries
                WHERE entry_id = %s
            """, (entry_id,))
            row = cur.fetchone()
            
            if row:
                return KnowledgeResponse(
                    entry_id=row[0],
                    client_id=row[1],
                    content=row[2],
                    entry_type=row[3],
                    source=row[4],
                    daaeg_phase=row[5],
                    tags=row[6] or [],
                    stakeholder_ids=row[7] or [],
                    metadata=row[8] or {},
                    created_by=row[9],
                    created_at=row[10],
                    updated_at=row[11]
                )
            return None
        finally:
            conn.close()
