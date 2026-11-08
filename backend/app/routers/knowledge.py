from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.database import get_db
from backend.app.models import ExtractedFinding, EvidenceReference, Document, User, UserRole, AuditLog
from backend.app.schemas import FindingCreate, FindingUpdate, FindingResponse, EvidenceReferenceResponse
from backend.app.auth import get_current_user, check_project_access
from backend.app.services.verification_service import run_project_verification

router = APIRouter(prefix="/knowledge", tags=["Knowledge & Findings"])

@router.get("/{project_id}/findings", response_model=List[FindingResponse])
def list_findings(
    project_id: str,
    entity_type: Optional[str] = Query(None),
    verification_status: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_project_access(project_id, current_user, db)
    query = db.query(ExtractedFinding).filter(ExtractedFinding.project_id == project_id)

    # Incoming member role restriction: only approved or verified findings
    membership = check_project_access(project_id, current_user, db)
    if membership and membership.role == UserRole.INCOMING_MEMBER:
        query = query.filter(ExtractedFinding.status == "APPROVED")

    if entity_type:
        query = query.filter(ExtractedFinding.entity_type == entity_type.upper())
    if verification_status:
        query = query.filter(ExtractedFinding.verification_status == verification_status.upper())
    if status:
        query = query.filter(ExtractedFinding.status == status.upper())
    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            or_(
                ExtractedFinding.title.ilike(search_fmt),
                ExtractedFinding.description.ilike(search_fmt),
                ExtractedFinding.owner.ilike(search_fmt)
            )
        )

    findings = query.order_by(ExtractedFinding.created_at.desc()).all()

    # Format output with evidence references and document filenames
    results = []
    for f in findings:
        doc = db.query(Document).filter(Document.id == f.document_id).first() if f.document_id else None
        refs = db.query(EvidenceReference).filter(EvidenceReference.finding_id == f.id).all()
        ref_responses = [
            EvidenceReferenceResponse(
                id=r.id,
                finding_id=r.finding_id,
                document_id=r.document_id,
                page_number=r.page_number,
                quotation=r.quotation,
                match_score=r.match_score,
                is_verified=r.is_verified,
                verified_at=r.verified_at,
                document_filename=doc.filename if doc else None
            ) for r in refs
        ]
        results.append(FindingResponse(
            id=f.id,
            project_id=f.project_id,
            document_id=f.document_id,
            entity_type=f.entity_type,
            title=f.title,
            description=f.description,
            owner=f.owner,
            deadline=f.deadline,
            status=f.status,
            page_number=f.page_number,
            supporting_quotation=f.supporting_quotation,
            confidence_score=f.confidence_score,
            is_recommendation=f.is_recommendation,
            flags=f.flags or {},
            verification_status=f.verification_status,
            document_filename=doc.filename if doc else None,
            evidence_refs=ref_responses,
            created_at=f.created_at,
            updated_at=f.updated_at
        ))
    return results

@router.post("/{project_id}/findings", response_model=FindingResponse)
def create_finding(
    project_id: str,
    finding_in: FindingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_project_access(project_id, current_user, db, allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.OUTGOING_MEMBER])

    finding = ExtractedFinding(
        project_id=project_id,
        document_id=finding_in.document_id,
        entity_type=finding_in.entity_type.upper(),
        title=finding_in.title,
        description=finding_in.description,
        owner=finding_in.owner,
        deadline=finding_in.deadline,
        status="DRAFT",
        page_number=finding_in.page_number or 1,
        supporting_quotation=finding_in.supporting_quotation,
        confidence_score=finding_in.confidence_score or 1.0,
        is_recommendation=finding_in.is_recommendation or False,
        flags=finding_in.flags or {}
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)

    # Trigger verification
    run_project_verification(project_id, db)
    db.refresh(finding)

    doc = db.query(Document).filter(Document.id == finding.document_id).first() if finding.document_id else None
    return FindingResponse(
        id=finding.id,
        project_id=finding.project_id,
        document_id=finding.document_id,
        entity_type=finding.entity_type,
        title=finding.title,
        description=finding.description,
        owner=finding.owner,
        deadline=finding.deadline,
        status=finding.status,
        page_number=finding.page_number,
        supporting_quotation=finding.supporting_quotation,
        confidence_score=finding.confidence_score,
        is_recommendation=finding.is_recommendation,
        flags=finding.flags or {},
        verification_status=finding.verification_status,
        document_filename=doc.filename if doc else None,
        evidence_refs=[],
        created_at=finding.created_at,
        updated_at=finding.updated_at
    )

@router.put("/{project_id}/findings/{finding_id}", response_model=FindingResponse)
def update_finding(
    project_id: str,
    finding_id: str,
    finding_in: FindingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_project_access(project_id, current_user, db, allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER])
    finding = db.query(ExtractedFinding).filter(
        ExtractedFinding.id == finding_id,
        ExtractedFinding.project_id == project_id
    ).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    if finding_in.title is not None:
        finding.title = finding_in.title
    if finding_in.description is not None:
        finding.description = finding_in.description
    if finding_in.owner is not None:
        finding.owner = finding_in.owner
    if finding_in.deadline is not None:
        finding.deadline = finding_in.deadline
    if finding_in.status is not None:
        finding.status = finding_in.status
    if finding_in.verification_status is not None:
        finding.verification_status = finding_in.verification_status
    if finding_in.is_recommendation is not None:
        finding.is_recommendation = finding_in.is_recommendation
    if finding_in.flags is not None:
        finding.flags = finding_in.flags

    db.commit()
    db.refresh(finding)

    doc = db.query(Document).filter(Document.id == finding.document_id).first() if finding.document_id else None
    return FindingResponse(
        id=finding.id,
        project_id=finding.project_id,
        document_id=finding.document_id,
        entity_type=finding.entity_type,
        title=finding.title,
        description=finding.description,
        owner=finding.owner,
        deadline=finding.deadline,
        status=finding.status,
        page_number=finding.page_number,
        supporting_quotation=finding.supporting_quotation,
        confidence_score=finding.confidence_score,
        is_recommendation=finding.is_recommendation,
        flags=finding.flags or {},
        verification_status=finding.verification_status,
        document_filename=doc.filename if doc else None,
        evidence_refs=[],
        created_at=finding.created_at,
        updated_at=finding.updated_at
    )

@router.post("/{project_id}/verify")
def re_verify_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_project_access(project_id, current_user, db, allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER])
    run_project_verification(project_id, db)
    return {"message": "Evidence verification and conflict detection completed successfully"}

@router.get("/{project_id}/timeline")
def get_timeline(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_project_access(project_id, current_user, db)
    items = db.query(ExtractedFinding).filter(
        ExtractedFinding.project_id == project_id,
        ExtractedFinding.entity_type.in_(["DECISION", "MILESTONE", "DEADLINE", "TASK"])
    ).order_by(ExtractedFinding.created_at.asc()).all()

    timeline_items = []
    for item in items:
        timeline_items.append({
            "id": item.id,
            "entity_type": item.entity_type,
            "title": item.title,
            "description": item.description,
            "owner": item.owner,
            "deadline": item.deadline,
            "status": item.status,
            "verification_status": item.verification_status,
            "page_number": item.page_number,
            "created_at": item.created_at
        })
    return timeline_items

@router.get("/{project_id}/risks-dependencies")
def get_risks_and_dependencies(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_project_access(project_id, current_user, db)
    findings = db.query(ExtractedFinding).filter(
        ExtractedFinding.project_id == project_id,
        ExtractedFinding.entity_type.in_(["RISK", "BLOCKER", "DEPENDENCY", "QUESTION"])
    ).all()

    return {
        "risks": [
            {
                "id": f.id,
                "title": f.title,
                "description": f.description,
                "severity": "CRITICAL" if "loss" in f.description.lower() or "critical" in f.description.lower() else "MEDIUM",
                "status": f.status,
                "page": f.page_number,
                "quotation": f.supporting_quotation
            } for f in findings if f.entity_type == "RISK"
        ],
        "blockers": [
            {
                "id": f.id,
                "title": f.title,
                "description": f.description,
                "owner": f.owner or "Requires Escalation",
                "status": f.status,
                "page": f.page_number,
                "flags": f.flags or {}
            } for f in findings if f.entity_type == "BLOCKER"
        ],
        "dependencies": [
            {
                "id": f.id,
                "title": f.title,
                "description": f.description,
                "status": f.status,
                "page": f.page_number
            } for f in findings if f.entity_type == "DEPENDENCY"
        ],
        "questions": [
            {
                "id": f.id,
                "title": f.title,
                "description": f.description,
                "status": f.status,
                "page": f.page_number
            } for f in findings if f.entity_type == "QUESTION"
        ]
    }
