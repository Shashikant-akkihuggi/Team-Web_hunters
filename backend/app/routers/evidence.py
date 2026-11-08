from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import (
    EvidenceReference, ExtractedFinding, Document, DocumentChunk, User, UserRole, VerificationStatus
)
from backend.app.schemas import (
    EvidenceReferenceResponse, EvidenceDetailItemResponse,
    EvidenceSummaryResponse, EvidenceVerifyResponse
)
from backend.app.auth import get_current_user, check_project_access
from backend.app.services.verification_service import (
    verify_single_finding, verify_finding_integrity,
    get_evidence_coverage_metrics, run_8_point_integrity_check
)

router = APIRouter(tags=["Evidence Verification"])

@router.get("/projects/{project_id}/evidence/summary", response_model=EvidenceSummaryResponse)
def get_project_evidence_summary(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns high-level evidence metrics, coverage ratio (Findings with valid evidence / Total findings * 100),
    and per-document/entity breakdown.
    """
    check_project_access(project_id, current_user, db)
    metrics = get_evidence_coverage_metrics(project_id, db)
    return EvidenceSummaryResponse(**metrics)

@router.get("/projects/{project_id}/evidence", response_model=List[EvidenceReferenceResponse])
def list_project_evidence(
    project_id: str,
    verification_status: Optional[str] = Query(None),
    document_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lists all evidence references belonging to a project with optional filtering.
    """
    check_project_access(project_id, current_user, db)
    query = (
        db.query(EvidenceReference)
        .join(ExtractedFinding, ExtractedFinding.id == EvidenceReference.finding_id)
        .filter(ExtractedFinding.project_id == project_id)
    )

    if verification_status:
        query = query.filter(EvidenceReference.verification_status == verification_status.upper())
    if document_id:
        query = query.filter(EvidenceReference.document_id == document_id)

    refs = query.order_by(EvidenceReference.verified_at.desc()).offset(offset).limit(limit).all()

    results = []
    for r in refs:
        doc = db.query(Document).filter(Document.id == r.document_id).first() if r.document_id else None
        results.append(EvidenceReferenceResponse(
            id=r.id,
            finding_id=r.finding_id,
            document_id=r.document_id,
            document_filename=r.document_filename or (doc.filename if doc else None),
            chunk_id=r.chunk_id,
            page_number=r.page_number,
            page_end=r.page_end or r.page_number,
            quotation=r.quotation,
            character_start=r.character_start or 0,
            character_end=r.character_end or len(r.quotation),
            match_score=r.match_score,
            is_verified=r.is_verified,
            verification_status=r.verification_status or "VERIFIED",
            verification_method=r.verification_method or "EXACT_SUBSTRING",
            verified_at=r.verified_at,
            verification_timestamp=r.verification_timestamp or r.verified_at
        ))
    return results

@router.get("/evidence/{evidence_id}", response_model=EvidenceDetailItemResponse)
def get_evidence_detail(
    evidence_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns complete granular evidence detail for an evidence citation,
    including surrounding text chunk, character offsets, match score, and integrity check results.
    """
    ref = db.query(EvidenceReference).filter(EvidenceReference.id == evidence_id).first()
    if not ref:
        raise HTTPException(status_code=404, detail="Evidence reference not found")

    finding = db.query(ExtractedFinding).filter(ExtractedFinding.id == ref.finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding associated with evidence not found")

    check_project_access(finding.project_id, current_user, db)

    doc = db.query(Document).filter(Document.id == ref.document_id).first() if ref.document_id else None
    chunk = db.query(DocumentChunk).filter(DocumentChunk.id == ref.chunk_id).first() if ref.chunk_id else None

    # Run fresh 8-point check
    integrity_result = run_8_point_integrity_check(
        db=db,
        finding=finding,
        doc=doc,
        chunk=chunk,
        quotation=ref.quotation,
        page_number=ref.page_number
    )

    return EvidenceDetailItemResponse(
        id=ref.id,
        finding_id=ref.finding_id,
        finding_title=finding.title,
        entity_type=finding.entity_type,
        document_id=ref.document_id,
        document_filename=ref.document_filename or (doc.filename if doc else None),
        chunk_id=ref.chunk_id,
        chunk_text=chunk.text_content if chunk else None,
        page_number=ref.page_number,
        page_end=ref.page_end or ref.page_number,
        quotation=ref.quotation,
        character_start=ref.character_start or 0,
        character_end=ref.character_end or len(ref.quotation),
        match_score=ref.match_score,
        is_verified=ref.is_verified,
        verification_status=ref.verification_status or "VERIFIED",
        verification_method=ref.verification_method or "EXACT_SUBSTRING",
        verified_at=ref.verified_at,
        integrity_checks=integrity_result["checks"],
        surrounding_context=integrity_result["surrounding_context"]
    )

@router.post("/evidence/{evidence_id}/verify", response_model=EvidenceVerifyResponse)
def verify_evidence_endpoint(
    evidence_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Executes the 8-point evidence integrity check on this specific evidence reference.
    """
    ref = db.query(EvidenceReference).filter(EvidenceReference.id == evidence_id).first()
    if not ref:
        raise HTTPException(status_code=404, detail="Evidence reference not found")

    finding = db.query(ExtractedFinding).filter(ExtractedFinding.id == ref.finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding associated with evidence not found")

    check_project_access(finding.project_id, current_user, db, allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER])

    integrity_res = verify_finding_integrity(finding.id, db)
    db.refresh(ref)

    return EvidenceVerifyResponse(
        evidence_id=ref.id,
        finding_id=finding.id,
        is_verified=ref.is_verified,
        verification_status=ref.verification_status,
        verification_method=ref.verification_method,
        match_score=ref.match_score,
        verified_page=ref.page_number,
        integrity_checks=integrity_res["checks"],
        error_message=None if ref.is_verified else "Quotation could not be verified with strong match against document text"
    )

@router.get("/evidence/finding/{finding_id}", response_model=List[EvidenceReferenceResponse])
def get_finding_evidence(
    finding_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns all evidence references associated with a finding (legacy compatibility).
    """
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
            document_filename=r.document_filename or (doc.filename if doc else None),
            chunk_id=r.chunk_id,
            page_number=r.page_number,
            page_end=r.page_end or r.page_number,
            quotation=r.quotation,
            character_start=r.character_start or 0,
            character_end=r.character_end or len(r.quotation),
            match_score=r.match_score,
            is_verified=r.is_verified,
            verification_status=r.verification_status or "VERIFIED",
            verification_method=r.verification_method or "EXACT_SUBSTRING",
            verified_at=r.verified_at,
            verification_timestamp=r.verification_timestamp or r.verified_at
        ))
    return results

@router.post("/evidence/verify-finding/{finding_id}")
def verify_finding_endpoint(
    finding_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Legacy verify-finding endpoint: runs 8-point check on finding.
    """
    finding = db.query(ExtractedFinding).filter(ExtractedFinding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    check_project_access(finding.project_id, current_user, db, allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER])

    result = verify_finding_integrity(finding_id, db)

    return {
        "finding_id": finding.id,
        "is_verified": (result["status"] == VerificationStatus.VERIFIED),
        "score": result["match_score"],
        "verified_page": result["verified_page"],
        "verification_status": finding.verification_status,
        "integrity_checks": result["checks"]
    }
