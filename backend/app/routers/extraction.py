from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import (
    DocumentChunk, ExtractedFinding, User, UserRole, Project,
    ExtractionJob, ExtractionJobStatus
)
from backend.app.schemas import (
    ExtractionJobCreate, ExtractionJobResponse
)
from backend.app.auth import get_current_user, check_project_access
from backend.app.config import settings
from backend.app.services.extraction_service import extract_project_knowledge
from backend.app.services.extraction_pipeline import run_extraction_pipeline

router = APIRouter(tags=["Extraction"])

class ExtractionTestRequest(BaseModel):
    text: str
    page_number: Optional[int] = 1
    filename: Optional[str] = "test_document.txt"

class ExtractionStatusResponse(BaseModel):
    gemini_configured: bool
    gemini_model: str
    fallback_engine: str
    supported_entity_types: List[str]

# --- General Status & Preview Endpoints ---

@router.get("/extraction/status", response_model=ExtractionStatusResponse)
def get_extraction_status(current_user: User = Depends(get_current_user)):
    return ExtractionStatusResponse(
        gemini_configured=bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip()),
        gemini_model=settings.GEMINI_MODEL,
        fallback_engine="Deterministic Regex & Heuristic NLP (Zero-Hallucination)",
        supported_entity_types=[
            "DECISION", "TASK", "RESPONSIBILITY", "DEADLINE",
            "MILESTONE", "RISK", "BLOCKER", "DEPENDENCY",
            "QUESTION", "CONTACT"
        ]
    )

@router.post("/extraction/preview", response_model=List[Dict[str, Any]])
def preview_extraction(
    req: ExtractionTestRequest,
    current_user: User = Depends(get_current_user)
):
    findings = extract_project_knowledge(
        chunk_text=req.text,
        page_number=req.page_number or 1,
        filename=req.filename or "preview.txt"
    )
    return findings

# --- Phase 4 Extraction Job Endpoints ---

@router.post("/projects/{project_id}/extractions", response_model=ExtractionJobResponse)
def trigger_extraction(
    project_id: str,
    payload: Optional[ExtractionJobCreate] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Triggers an AI knowledge extraction pipeline job for all documents in the project.
    """
    check_project_access(project_id, current_user, db, allowed_roles=[
        UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.OUTGOING_MEMBER
    ])
    force = payload.force_reprocess if payload else False
    job = run_extraction_pipeline(
        project_id=project_id,
        user_id=current_user.id,
        db=db,
        force_reprocess=force
    )
    return job

@router.get("/projects/{project_id}/extractions", response_model=List[ExtractionJobResponse])
def list_project_extractions(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lists all extraction jobs executed for the project, sorted by most recent.
    """
    check_project_access(project_id, current_user, db)
    jobs = db.query(ExtractionJob).filter(
        ExtractionJob.project_id == project_id
    ).order_by(ExtractionJob.created_at.desc()).all()
    return jobs

@router.get("/extractions/{extraction_id}", response_model=ExtractionJobResponse)
def get_extraction_job(
    extraction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves full details of a specific extraction job.
    """
    job = db.query(ExtractionJob).filter(ExtractionJob.id == extraction_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Extraction job not found")
    check_project_access(job.project_id, current_user, db)
    return job

@router.get("/extractions/{extraction_id}/status", response_model=ExtractionJobResponse)
def get_extraction_job_status(
    extraction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Pollable status endpoint for tracking progress of an ongoing extraction job.
    """
    job = db.query(ExtractionJob).filter(ExtractionJob.id == extraction_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Extraction job not found")
    check_project_access(job.project_id, current_user, db)
    return job

@router.post("/extractions/{extraction_id}/retry", response_model=ExtractionJobResponse)
def retry_extraction_job(
    extraction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retries an extraction job.
    """
    job = db.query(ExtractionJob).filter(ExtractionJob.id == extraction_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Extraction job not found")
    check_project_access(job.project_id, current_user, db, allowed_roles=[
        UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.OUTGOING_MEMBER
    ])
    retried_job = run_extraction_pipeline(
        project_id=job.project_id,
        user_id=current_user.id,
        db=db,
        force_reprocess=True,
        existing_job_id=job.id
    )
    return retried_job

# --- Backward compatibility alias for re-extract ---
@router.post("/extraction/project/{project_id}/re-extract")
def re_extract_project_legacy(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_project_access(project_id, current_user, db, allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER])
    job = run_extraction_pipeline(
        project_id=project_id,
        user_id=current_user.id,
        db=db,
        force_reprocess=True
    )
    return {
        "message": "Extraction pipeline executed successfully",
        "job_id": job.id,
        "findings_count": job.extracted_findings_count,
        "conflicts_count": job.conflicts_count,
        "unsupported_count": job.unsupported_count,
        "status": job.status
    }
