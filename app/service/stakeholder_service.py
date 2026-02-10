
import psycopg2
import json
from typing import List, Optional, Dict, Any
from app.config.settings import settings
from app.dto.core import StakeholderCreate, StakeholderUpdate, StakeholderResponse

class StakeholderService:
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
    def create_stakeholder(payload: StakeholderCreate) -> Optional[StakeholderResponse]:
        conn = StakeholderService.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO stakeholders (
                    client_id, name, role, email, tone, metadata, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING stakeholder_id, client_id, name, role, email, tone, tone_analysis, last_interaction, metadata, created_at, updated_at
            """, (
                payload.clientId,
                payload.name,
                payload.role,
                payload.email,
                payload.tone,
                json.dumps(payload.metadata or {})
            ))
            row = cur.fetchone()
            conn.commit()
            
            if row:
                return StakeholderResponse(
                    stakeholder_id=row[0],
                    client_id=row[1],
                    name=row[2],
                    role=row[3],
                    email=row[4],
                    tone=row[5],
                    tone_analysis=row[6] or {},
                    last_interaction=row[7],
                    metadata=row[8] or {},
                    created_at=row[9],
                    updated_at=row[10]
                )
            return None
        except Exception as e:
            conn.rollback()
            print(f"Error creating stakeholder: {e}")
            raise e
        finally:
            conn.close()

    @staticmethod
    def get_stakeholders(client_id: Optional[int] = None) -> List[StakeholderResponse]:
        conn = StakeholderService.get_connection()
        try:
            cur = conn.cursor()
            query = """
                SELECT stakeholder_id, client_id, name, role, email, tone, tone_analysis, last_interaction, metadata, created_at, updated_at
                FROM stakeholders
            """
            params = []
            if client_id:
                query += " WHERE client_id = %s"
                params.append(client_id)
            
            query += " ORDER BY name ASC"
            
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            
            return [
                StakeholderResponse(
                    stakeholder_id=row[0],
                    client_id=row[1],
                    name=row[2],
                    role=row[3],
                    email=row[4],
                    tone=row[5],
                    tone_analysis=row[6] or {},
                    last_interaction=row[7],
                    metadata=row[8] or {},
                    created_at=row[9],
                    updated_at=row[10]
                ) for row in rows
            ]
        finally:
            conn.close()

    @staticmethod
    def get_stakeholder_by_id(stakeholder_id: int) -> Optional[StakeholderResponse]:
        conn = StakeholderService.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT stakeholder_id, client_id, name, role, email, tone, tone_analysis, last_interaction, metadata, created_at, updated_at
                FROM stakeholders
                WHERE stakeholder_id = %s
            """, (stakeholder_id,))
            row = cur.fetchone()
            
            if row:
                return StakeholderResponse(
                    stakeholder_id=row[0],
                    client_id=row[1],
                    name=row[2],
                    role=row[3],
                    email=row[4],
                    tone=row[5],
                    tone_analysis=row[6] or {},
                    last_interaction=row[7],
                    metadata=row[8] or {},
                    created_at=row[9],
                    updated_at=row[10]
                )
            return None
        finally:
            conn.close()

    @staticmethod
    def update_stakeholder(stakeholder_id: int, payload: StakeholderUpdate) -> Optional[StakeholderResponse]:
        conn = StakeholderService.get_connection()
        try:
            cur = conn.cursor()
            
            # Build dynamic update query
            fields = []
            params = []
            
            if payload.name is not None:
                fields.append("name = %s")
                params.append(payload.name)
            if payload.role is not None:
                fields.append("role = %s")
                params.append(payload.role)
            if payload.email is not None:
                fields.append("email = %s")
                params.append(payload.email)
            if payload.tone is not None:
                fields.append("tone = %s")
                params.append(payload.tone)
            if payload.metadata is not None:
                fields.append("metadata = %s")
                params.append(json.dumps(payload.metadata))
                
            if not fields:
                return StakeholderService.get_stakeholder_by_id(stakeholder_id)
                
            query = f"""
                UPDATE stakeholders
                SET {', '.join(fields)}, updated_at = NOW()
                WHERE stakeholder_id = %s
                RETURNING stakeholder_id, client_id, name, role, email, tone, tone_analysis, last_interaction, metadata, created_at, updated_at
            """
            params.append(stakeholder_id)
            
            cur.execute(query, tuple(params))
            row = cur.fetchone()
            conn.commit()
            
            if row:
                return StakeholderResponse(
                    stakeholder_id=row[0],
                    client_id=row[1],
                    name=row[2],
                    role=row[3],
                    email=row[4],
                    tone=row[5],
                    tone_analysis=row[6] or {},
                    last_interaction=row[7],
                    metadata=row[8] or {},
                    created_at=row[9],
                    updated_at=row[10]
                )
            return None
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def delete_stakeholder(stakeholder_id: int) -> bool:
        conn = StakeholderService.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM stakeholders WHERE stakeholder_id = %s", (stakeholder_id,))
            rows_deleted = cur.rowcount
            conn.commit()
            return rows_deleted > 0
        finally:
            conn.close()
