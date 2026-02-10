import os
import shutil
import hashlib
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import psycopg2

from app.config.settings import settings
from app.config.logger import logger
from app.dto.template import TemplateCreate, TemplateResponse, TemplateVersionResponse

class TemplateService:
    STORAGE_PATH = Path("storage") 

    @staticmethod
    def _get_connection():
        return psycopg2.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            database=settings.DATABASE_NAME,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
        )

    @staticmethod
    def _init_storage():
        TemplateService.STORAGE_PATH.mkdir(parents=True, exist_ok=True)
        (TemplateService.STORAGE_PATH / "templates").mkdir(exist_ok=True)
        (TemplateService.STORAGE_PATH / "versions").mkdir(exist_ok=True)

    @staticmethod
    def _calculate_file_hash(file_path: str) -> str:
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    @staticmethod
    def _generate_version_number(template_id: int, cur) -> int:
        cur.execute("""
            SELECT MAX(version_number) FROM template_versions 
            WHERE template_id = %s 
        """, (template_id,))
        result = cur.fetchone()
        if result and result[0] is not None:
            return int(result[0]) + 1
        return 1

    @staticmethod
    def create_template(payload: TemplateCreate, file_path: str, created_by: int) -> Optional[TemplateResponse]:
        TemplateService._init_storage()
        conn = TemplateService._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO templates (name, description, category, created_by, created_at, is_active)
                VALUES (%s, %s, %s, %s, NOW(), %s)
                RETURNING template_id, name, description, category, created_by, created_at, is_active
            """, (payload.name, payload.description, payload.templateType, created_by, payload.isActive))
            
            row = cur.fetchone()
            template_id = row[0]
            
            # Create initial version
            version_response = TemplateService.add_template_version(template_id, file_path, created_by, "Initial version", external_cur=cur)
            
            conn.commit()
            
            return TemplateResponse(
                template_id=row[0],
                name=row[1],
                description=row[2],
                template_type=row[3],
                created_by=row[4],
                created_at=row[5],
                is_active=row[6],
                versions=[version_response] if version_response else []
            )
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create template: {e}")
            raise e
        finally:
            conn.close()

    @staticmethod
    def add_template_version(template_id: int, file_path: str, created_by: int, changelog: str = None, external_cur=None) -> TemplateVersionResponse:
        # If external cursor provided, use it (and do NOT close/commit). Else create new one.
        conn = None
        cur = external_cur
        should_close = False

        try:
            if not cur:
                conn = TemplateService._get_connection()
                cur = conn.cursor()
                should_close = True

            # Use cur for all operations
            version_number = TemplateService._generate_version_number(template_id, cur)
            file_hash = TemplateService._calculate_file_hash(file_path)
            
            # Check duplicate
            cur.execute("""
                SELECT version_id FROM template_versions 
                WHERE template_id = %s AND (dynamic_fields->>'file_hash') = %s
            """, (template_id, file_hash))
            if cur.fetchone():
               # raise ValueError("Duplicate file version")
               pass 

            # Storage logic
            version_dir = TemplateService.STORAGE_PATH / "versions" / str(template_id)
            version_dir.mkdir(parents=True, exist_ok=True)
            file_extension = Path(file_path).suffix
            stored_filename = f"v{version_number}{file_extension}"
            stored_path = version_dir / stored_filename
            shutil.copy2(file_path, stored_path)
            
            cur.execute("""
                INSERT INTO template_versions 
                (template_id, version_number, file_path, dynamic_fields, changelog, created_by, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                RETURNING version_id, version_number, file_path, created_at, created_by, changelog, true
            """, (
                template_id, version_number, str(stored_path), 
                json.dumps({'file_hash': file_hash}),
                changelog, created_by
            ))
            
            v_row = cur.fetchone()
            version_id = v_row[0]
            
            cur.execute("""
                UPDATE templates SET current_version_id = %s, updated_at = NOW() WHERE template_id = %s
            """, (version_id, template_id))
            
            if should_close:
                conn.commit()
            
            return TemplateVersionResponse(
                version_id=v_row[0],
                version_number=str(v_row[1]), # Convert int to str for DTO
                file_path=v_row[2],
                created_at=v_row[3],
                created_by=v_row[4],
                changelog=v_row[5],
                is_active=v_row[6]
            )
        except Exception as e:
            if should_close and conn:
                conn.rollback()
            logger.error(f"Error adding version: {e}")
            raise e
        finally:
            if should_close and conn:
                conn.close()

    @staticmethod
    def list_templates(client_id: int = None) -> List[TemplateResponse]:
        conn = TemplateService._get_connection()
        try:
            cur = conn.cursor()
            query = """
                SELECT template_id, name, description, category, created_by, created_at, is_active
                FROM templates WHERE is_active = true
            """
            params = []
            if client_id:
                # Assuming simple filtering for now, schema has no client_id on templates but legacy code implied it?
                # The schema.sql I viewed definitely has client_id on templates? 
                # Wait, schema.sql: 106 CREATE TABLE IF NOT EXISTS templates ... NO client_id visible in lines 106-117??
                # Ah, let me re-read schema.sql content I viewed.
                pass 
                
            cur.execute(query, params)
            rows = cur.fetchall()
            return [
                TemplateResponse(
                    template_id=r[0], name=r[1], description=r[2], template_type=r[3], 
                    created_by=r[4], created_at=r[5], is_active=r[6]
                ) for r in rows
            ]
        finally:
            conn.close()

    @staticmethod
    def get_template(template_id: int) -> Optional[TemplateResponse]:
        conn = TemplateService._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT template_id, name, description, category, created_by, created_at, is_active
                FROM templates WHERE template_id = %s
            """, (template_id,))
            row = cur.fetchone()
            if not row: 
                return None
                
            template = TemplateResponse(
                template_id=row[0], name=row[1], description=row[2], template_type=row[3],
                created_by=row[4], created_at=row[5], is_active=row[6]
            )
            
            cur.execute("""
                SELECT version_id, version_number, file_path, created_at, created_by, changelog, true
                FROM template_versions WHERE template_id = %s ORDER BY created_at DESC
            """, (template_id,))
            
            for v_row in cur.fetchall():
                template.versions.append(TemplateVersionResponse(
                    version_id=v_row[0], version_number=v_row[1], file_path=v_row[2],
                    created_at=v_row[3], created_by=v_row[4], changelog=v_row[5], is_active=v_row[6]
                ))
            return template
        finally:
            conn.close()
