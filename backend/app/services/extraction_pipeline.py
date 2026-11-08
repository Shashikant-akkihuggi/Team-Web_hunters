import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from backend.app.models import (
    Project, Document, DocumentChunk, ExtractedFinding,
    ExtractionJob, ExtractionJobStatus, VerificationStatus,
    KnowledgeConflict
)
from backend.app.services.ai_service import default_ai_service, AIService
from backend.app.services.verification_service import run_project_verification, normalize_text

logger = logging.getLogger(__name__)

def run_extraction_pipeline(
    project_id: str,
    user_id: Optional[str],
    db: Session,
    force_reprocess: bool = False,
    existing_job_id: Optional[str] = None
) -> ExtractionJob:
    """
    Executes end-to-end knowledge extraction pipeline:
    1. Manages ExtractionJob record.
    2. Batches document chunks through AIService (Gemini or deterministic engine).
    3. Performs deduplication across chunk boundaries.
    4. Persists ExtractedFinding records with chunk_id, task_status, priority, etc.
    5. Runs verification engine: validates quotes against text, marks VERIFIED vs UNSUPPORTED.
    6. Runs contradiction engine: detects status, deadline, and ownership conflicts and logs KnowledgeConflict.
    7. Updates ExtractionJob metrics and completes.
    """
    if existing_job_id:
        job = db.query(ExtractionJob).filter(ExtractionJob.id == existing_job_id).first()
        if not job:
            job = ExtractionJob(
                id=existing_job_id,
                project_id=project_id,
                status=ExtractionJobStatus.PROCESSING,
                created_by=user_id
            )
            db.add(job)
    else:
        job = ExtractionJob(
            project_id=project_id,
            status=ExtractionJobStatus.PROCESSING,
            created_by=user_id
        )
        db.add(job)

    job.status = ExtractionJobStatus.PROCESSING
    db.commit()
    db.refresh(job)

    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        chunks: List[DocumentChunk] = db.query(DocumentChunk).filter(
            DocumentChunk.project_id == project_id
        ).order_by(DocumentChunk.document_id, DocumentChunk.chunk_index).all()

        docs_count = db.query(Document).filter(Document.project_id == project_id).count()
        job.processed_documents_count = docs_count
        job.processed_chunks_count = len(chunks)

        if not chunks:
            job.status = ExtractionJobStatus.COMPLETED
            job.extracted_findings_count = 0
            job.conflicts_count = 0
            job.unsupported_count = 0
            job.completed_at = datetime.utcnow()
            db.commit()
            return job

        # Clean prior draft findings to prevent endless accumulation
        db.query(ExtractedFinding).filter(
            ExtractedFinding.project_id == project_id,
            ExtractedFinding.status == "DRAFT"
        ).delete()
        db.commit()

        # Deduplication tracker: (entity_type, normalized_quote_prefix)
        seen_findings = set()
        created_count = 0

        for chunk in chunks:
            filename = chunk.document.filename if chunk.document else "Document"
            extracted_items = default_ai_service.extract_from_chunk(
                chunk_text=chunk.text_content,
                page_number=chunk.page_number,
                filename=filename,
                chunk_index=chunk.chunk_index
            )

            for item in extracted_items:
                norm_quote = normalize_text(item.supporting_quotation)[:60]
                dedup_key = (item.entity_type, norm_quote)

                # Deduplicate across adjacent overlapping chunks
                if dedup_key in seen_findings and len(norm_quote) > 15:
                    continue
                seen_findings.add(dedup_key)

                finding = ExtractedFinding(
                    project_id=project_id,
                    document_id=chunk.document_id,
                    chunk_id=chunk.id,
                    entity_type=item.entity_type,
                    title=item.title,
                    description=item.description,
                    owner=item.owner,
                    deadline=item.deadline,
                    task_status=item.task_status,
                    priority=item.priority,
                    decided_by=item.decided_by,
                    decision_date=item.decision_date,
                    impact=item.impact,
                    likelihood=item.likelihood,
                    mitigation=item.mitigation,
                    related_entity=item.related_entity,
                    status="DRAFT",
                    page_number=item.page_number or chunk.page_number,
                    supporting_quotation=item.supporting_quotation,
                    confidence_score=item.confidence_score,
                    is_recommendation=item.is_recommendation,
                    flags={}
                )
                db.add(finding)
                created_count += 1

        db.commit()

        # Run verification and conflict detection
        summary = run_project_verification(project_id, db)

        # Finalize job metrics
        job.extracted_findings_count = summary["total_findings"]
        job.conflicts_count = summary["conflicts_count"]
        job.unsupported_count = summary["unsupported_count"]
        job.status = ExtractionJobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(job)

        return job

    except Exception as err:
        logger.error(f"Extraction pipeline failed for project {project_id}: {err}", exc_info=True)
        job.status = ExtractionJobStatus.FAILED
        job.error_message = str(err)
        job.completed_at = datetime.utcnow()
        db.commit()
        raise err
