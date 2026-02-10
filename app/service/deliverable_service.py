import json
from datetime import datetime
from typing import List, Optional, Dict, Any
import psycopg2
from app.config.settings import settings
from app.config.logger import logger
from app.dto.deliverable import DeliverableCreate, DeliverableResponse, ReviewSubmit

class DeliverableService:
    
    @staticmethod
    def _get_connection():
        return psycopg2.connect(settings.DATABASE_URL)

    @staticmethod
    def submit_deliverable(payload: DeliverableCreate, created_by: int, file_path: str = None) -> DeliverableResponse:
        conn = DeliverableService._get_connection()
        try:
            cur = conn.cursor()
            metadata = payload.metadata or {}
            if payload.reviewNotes:
                metadata['review_notes'] = payload.reviewNotes
            
            cur.execute("""
                INSERT INTO deliverable_workflows 
                (client_id, deliverable_type, template_id, file_path, status, generation_metadata, created_by, created_at, updated_at)
                VALUES (%s, %s, %s, %s, 'pending_review', %s, %s, NOW(), NOW())
                RETURNING workflow_id, client_id, deliverable_type, status, created_by, created_at, generation_metadata, updated_at
            """, (
                payload.clientId, payload.deliverableType, payload.templateId, file_path,
                json.dumps(metadata), created_by
            ))
            
            row = cur.fetchone()
            conn.commit()

            # Trigger assignment logic here (omitted for brevity, assume manual or auto-assign later)
            
            return DeliverableResponse(
                workflow_id=row[0], client_id=row[1], deliverable_type=row[2], status=row[3],
                submitted_by=row[4], submitted_at=row[5], generation_metadata=row[6], updated_at=row[7]
            )
        except Exception as e:
            conn.rollback()
            logger.error(f"Error submitting deliverable: {e}")
            raise e
        finally:
            conn.close()

    @staticmethod
    def submit_review(workflow_id: int, reviewer_id: int, payload: ReviewSubmit) -> bool:
        conn = DeliverableService._get_connection()
        try:
            cur = conn.cursor()
            
            # Record review
            feedback = payload.comments or ""
            if payload.qualityScore: feedback += f" Score: {payload.qualityScore}"
            
            cur.execute("""
                INSERT INTO deliverable_reviews (workflow_id, reviewer_id, review_status, feedback, reviewed_at)
                VALUES (%s, %s, %s, %s, NOW())
            """, (workflow_id, reviewer_id, payload.action, feedback))
            
            # Update workflow status based on action
            new_status = 'in_review'
            if payload.action == 'approve':
                new_status = 'approved'
                # Trigger enrichment
                DeliverableService._schedule_enrichment(cur, workflow_id)
            elif payload.action == 'reject':
                new_status = 'rejected'
            elif payload.action == 'request_changes':
                new_status = 'draft'
            
            cur.execute("""
                UPDATE deliverable_workflows SET status = %s, updated_at = NOW() WHERE workflow_id = %s
            """, (new_status, workflow_id))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Error submitting review: {e}")
            raise e
        finally:
            conn.close()

    @staticmethod
    def _schedule_enrichment(cur, workflow_id: int):
        # Insert into queue
        cur.execute("""
            INSERT INTO enrichment_queue (workflow_id, status, created_at) VALUES (%s, 'pending', NOW())
        """, (workflow_id,))

    @staticmethod
    def get_deliverable(workflow_id: int) -> Optional[DeliverableResponse]:
        conn = DeliverableService._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT workflow_id, client_id, deliverable_type, status, created_by, created_at, generation_metadata, updated_at
                FROM deliverable_workflows WHERE workflow_id = %s
            """, (workflow_id,))
            row = cur.fetchone()
            if not row: return None
            return DeliverableResponse(
                workflow_id=row[0], client_id=row[1], deliverable_type=row[2], status=row[3],
                submitted_by=row[4], submitted_at=row[5], generation_metadata=row[6], updated_at=row[7]
            )
        finally:
            conn.close()
