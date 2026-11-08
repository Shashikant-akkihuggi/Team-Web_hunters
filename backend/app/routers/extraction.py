from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import DocumentChunk, ExtractedFinding, User, UserRole, Project
from backend.app.auth import get_current_user, check_project_access
from backend.app.config import settings
from backend.app.services.extraction_service import extract_project_knowledge
from backend.app.services.verification_service import run_project_verification

router = APIRouter(prefix="/extraction", tags=["Extraction"])

class ExtractionTestRequest(BaseModel):
    text: str
    page_number: Optional[int] = 1
    filename: Optional[str] = "test_document.txt"

class ExtractionStatusResponse(BaseModel):
    gemini_configured: bool
    gemini_model: str
    fallback_engine: str
    supported_entity_types: List[str]

@router.get("/status", response_model=ExtractionStatusResponse)
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

@router.post("/preview", response_model=List[Dict[str, Any]])
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

@router.post("/project/{project_id}/re-extract")
def re_extract_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_project_access(project_id, current_user, db, allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER])
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    chunks = db.query(DocumentChunk).filter(DocumentChunk.project_id == project_id).all()
    if not chunks:
        return {"message": "No document chunks to extract from.", "findings_count": 0}

    # Delete existing draft findings to avoid duplicates
    db.query(ExtractedFinding).filter(
        ExtractedFinding.project_id == project_id,
        ExtractedFinding.status == "DRAFT"
    ).delete()

    created_count = 0
    for c in chunks:
        fname = c.document.filename if c.document else "Document"
        extracted = extract_project_knowledge(
            chunk_text=c.text_content,
            page_number=c.page_number,
            filename=fname
        )
        for ent in extracted:
            finding = ExtractedFinding(
                project_id=project_id,
                document_id=c.document_id,
                entity_type=ent["entity_type"],
                title=ent["title"],
                description=ent["description"],
                owner=ent["owner"],
                deadline=ent["deadline"],
                status="DRAFT",
                page_number=ent["page_number"],
                supporting_quotation=ent["supporting_quotation"],
                confidence_score=ent["confidence_score"],
                is_recommendation=ent["is_recommendation"]
            )
            db.add(finding)
            created_count += 1

    db.commit()
    run_project_verification(project_id, db)

    return {
        "message": f"Successfully re-extracted {created_count} findings across {len(chunks)} chunks.",
        "findings_count": created_count
    }
