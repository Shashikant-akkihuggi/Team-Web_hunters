from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import EvidenceReference, ExtractedFinding, Document, DocumentChunk, User, UserRole
from backend.app.schemas import EvidenceReferenceResponse
from backend.app.auth import get_current_user, check_project_access
from backend.app.services.verification_service import verify_single_finding

router = APIRouter(prefix="/evidence", tags=["Evidence"])

@router.get("/finding/{finding_id}", response_model=List[EvidenceReferenceResponse])
def get_finding_evidence(
    finding_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    finding = db.query(ExtractedFinding).filter(ExtractedFinding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    check_project_access(finding.project_id, current_user, db)

    refs = db.query(EvidenceReference).filter(EvidenceReference.finding_id == finding_id).all()
    results = []
    for r in refs:
        doc = db.query(Document).filter(Document.id == r.document_id).first() if r.document_id else None
        results.append(EvidenceReferenceResponse(
            id=r.id,
            finding_id=r.finding_id,
            document_id=r.document_id,
            page_number=r.page_number,
            quotation=r.quotation,
            match_score=r.match_score,
            is_verified=r.is_verified,
            verified_at=r.verified_at,
            document_filename=doc.filename if doc else None
        ))
    return results

@router.post("/verify-finding/{finding_id}")
def verify_finding_endpoint(
    finding_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    finding = db.query(ExtractedFinding).filter(ExtractedFinding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    check_project_access(finding.project_id, current_user, db, allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER])

    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == finding.document_id).all()
    is_verified, score, verified_page = verify_single_finding(finding, chunks)

    finding.verification_status = "VERIFIED" if is_verified else "UNSUPPORTED"
    flags = finding.flags or {}
    flags["missing_evidence"] = not is_verified
    flags["evidence_strength"] = "STRONG" if is_verified else "NONE"
    finding.flags = flags

    db.commit()

    return {
        "finding_id": finding.id,
        "is_verified": is_verified,
        "score": score,
        "verified_page": verified_page,
        "verification_status": finding.verification_status
    }
