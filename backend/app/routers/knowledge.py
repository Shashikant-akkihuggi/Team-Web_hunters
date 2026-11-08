from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.database import get_db
from backend.app.models import (
    ExtractedFinding, EvidenceReference, Document, DocumentChunk,
    User, UserRole, KnowledgeConflict, VerificationStatus
)
from backend.app.schemas import (
    FindingCreate, FindingUpdate, FindingResponse, EvidenceReferenceResponse,
    KnowledgeConflictResponse, FindingEvidenceDetailResponse, ProjectKnowledgeSummary
)
from backend.app.auth import get_current_user, check_project_access
from backend.app.services.verification_service import run_project_verification

router = APIRouter(tags=["Knowledge & Intelligence"])

def _format_finding_response(f: ExtractedFinding, db: Session) -> FindingResponse:
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
    return FindingResponse(
        id=f.id,
        project_id=f.project_id,
        document_id=f.document_id,
        chunk_id=f.chunk_id,
        entity_type=f.entity_type,
        title=f.title,
        description=f.description,
        owner=f.owner,
        deadline=f.deadline,
        task_status=f.task_status,
        priority=f.priority,
        decided_by=f.decided_by,
        decision_date=f.decision_date,
        impact=f.impact,
        likelihood=f.likelihood,
        mitigation=f.mitigation,
        related_entity=f.related_entity,
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
    )

def _format_conflict_response(c: KnowledgeConflict, db: Session) -> KnowledgeConflictResponse:
    doc1 = db.query(Document).filter(Document.id == c.source_1_doc_id).first() if c.source_1_doc_id else None
    doc2 = db.query(Document).filter(Document.id == c.source_2_doc_id).first() if c.source_2_doc_id else None
    return KnowledgeConflictResponse(
        id=c.id,
        project_id=c.project_id,
        finding_id_1=c.finding_id_1,
        finding_id_2=c.finding_id_2,
        conflict_type=c.conflict_type,
        description=c.description,
        source_1_quote=c.source_1_quote,
        source_1_page=c.source_1_page,
        source_1_doc_id=c.source_1_doc_id,
        source_1_doc_filename=doc1.filename if doc1 else None,
        source_2_quote=c.source_2_quote,
        source_2_page=c.source_2_page,
        source_2_doc_id=c.source_2_doc_id,
        source_2_doc_filename=doc2.filename if doc2 else None,
        status=c.status,
        created_at=c.created_at
    )

# --- Phase 4 Knowledge Hub Endpoints ---

@router.get("/projects/{project_id}/knowledge")
def get_project_knowledge_hub(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns full synthesized project knowledge hub, including metrics,
    findings breakdown, and detected conflicts.
    """
    check_project_access(project_id, current_user, db)
    findings = db.query(ExtractedFinding).filter(
        ExtractedFinding.project_id == project_id
    ).order_by(ExtractedFinding.created_at.desc()).all()

    conflicts = db.query(KnowledgeConflict).filter(
        KnowledgeConflict.project_id == project_id
    ).order_by(KnowledgeConflict.created_at.desc()).all()

    total = len(findings)
    verified = sum(1 for f in findings if f.verification_status == VerificationStatus.VERIFIED)
    unsupported = sum(1 for f in findings if f.verification_status == VerificationStatus.UNSUPPORTED)
    pct = round((verified / total * 100), 1) if total > 0 else 100.0

    summary = ProjectKnowledgeSummary(
        total_findings=total,
        decisions_count=sum(1 for f in findings if f.entity_type == "DECISION"),
        tasks_count=sum(1 for f in findings if f.entity_type == "TASK"),
        risks_count=sum(1 for f in findings if f.entity_type == "RISK"),
        blockers_count=sum(1 for f in findings if f.entity_type == "BLOCKER"),
        dependencies_count=sum(1 for f in findings if f.entity_type == "DEPENDENCY"),
        questions_count=sum(1 for f in findings if f.entity_type == "QUESTION"),
        conflicts_count=len(conflicts),
        unsupported_count=unsupported,
        verified_percentage=pct
    )

    formatted_findings = [_format_finding_response(f, db) for f in findings]
    formatted_conflicts = [_format_conflict_response(c, db) for c in conflicts]

    return {
        "summary": summary,
        "findings": formatted_findings,
        "conflicts": formatted_conflicts
    }

@router.get("/projects/{project_id}/decisions", response_model=List[FindingResponse])
def get_project_decisions(
    project_id: str,
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_project_access(project_id, current_user, db)
    query = db.query(ExtractedFinding).filter(
        ExtractedFinding.project_id == project_id,
        ExtractedFinding.entity_type == "DECISION"
    )
    if search:
        query = query.filter(ExtractedFinding.title.ilike(f"%{search}%") | ExtractedFinding.description.ilike(f"%{search}%"))
    findings = query.order_by(ExtractedFinding.created_at.desc()).all()
    return [_format_finding_response(f, db) for f in findings]

@router.get("/projects/{project_id}/tasks", response_model=List[FindingResponse])
def get_project_tasks(
    project_id: str,
    task_status: Optional[str] = Query(None),
    owner: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_project_access(project_id, current_user, db)
    query = db.query(ExtractedFinding).filter(
        ExtractedFinding.project_id == project_id,
        ExtractedFinding.entity_type == "TASK"
    )
    if task_status:
        query = query.filter(ExtractedFinding.task_status == task_status.upper())
    if owner:
        query = query.filter(ExtractedFinding.owner.ilike(f"%{owner}%"))
    if priority:
        query = query.filter(ExtractedFinding.priority == priority.upper())
    if search:
        query = query.filter(
            or_(
                ExtractedFinding.title.ilike(f"%{search}%"),
                ExtractedFinding.description.ilike(f"%{search}%"),
                ExtractedFinding.owner.ilike(f"%{search}%")
            )
        )
    findings = query.order_by(ExtractedFinding.created_at.desc()).all()
    return [_format_finding_response(f, db) for f in findings]

@router.get("/projects/{project_id}/risks", response_model=List[FindingResponse])
def get_project_risks(
    project_id: str,
    priority: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_project_access(project_id, current_user, db)
    query = db.query(ExtractedFinding).filter(
        ExtractedFinding.project_id == project_id,
        ExtractedFinding.entity_type == "RISK"
    )
    if priority:
        query = query.filter(ExtractedFinding.priority == priority.upper())
    findings = query.order_by(ExtractedFinding.created_at.desc()).all()
    return [_format_finding_response(f, db) for f in findings]

@router.get("/projects/{project_id}/blockers", response_model=List[FindingResponse])
def get_project_blockers(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_project_access(project_id, current_user, db)
    findings = db.query(ExtractedFinding).filter(
        ExtractedFinding.project_id == project_id,
        ExtractedFinding.entity_type == "BLOCKER"
    ).order_by(ExtractedFinding.created_at.desc()).all()
    return [_format_finding_response(f, db) for f in findings]

@router.get("/projects/{project_id}/dependencies", response_model=List[FindingResponse])
def get_project_dependencies(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_project_access(project_id, current_user, db)
    findings = db.query(ExtractedFinding).filter(
        ExtractedFinding.project_id == project_id,
        ExtractedFinding.entity_type == "DEPENDENCY"
    ).order_by(ExtractedFinding.created_at.desc()).all()
    return [_format_finding_response(f, db) for f in findings]

@router.get("/projects/{project_id}/questions", response_model=List[FindingResponse])
def get_project_questions(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_project_access(project_id, current_user, db)
    findings = db.query(ExtractedFinding).filter(
        ExtractedFinding.project_id == project_id,
        ExtractedFinding.entity_type == "QUESTION"
    ).order_by(ExtractedFinding.created_at.desc()).all()
    return [_format_finding_response(f, db) for f in findings]

@router.get("/projects/{project_id}/conflicts", response_model=List[KnowledgeConflictResponse])
def get_project_conflicts(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns all contradictory findings and conflicting claims detected across project documents.
    """
    check_project_access(project_id, current_user, db)
    conflicts = db.query(KnowledgeConflict).filter(
        KnowledgeConflict.project_id == project_id
    ).order_by(KnowledgeConflict.created_at.desc()).all()
    return [_format_conflict_response(c, db) for c in conflicts]

@router.get("/knowledge/{finding_id}/evidence", response_model=FindingEvidenceDetailResponse)
def get_finding_evidence_detail(
    finding_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns complete granular evidence detail for a finding, including original chunk text,
    page citation, match score, and verified quotation.
    """
    finding = db.query(ExtractedFinding).filter(ExtractedFinding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    check_project_access(finding.project_id, current_user, db)

    doc = db.query(Document).filter(Document.id == finding.document_id).first() if finding.document_id else None
    chunk = db.query(DocumentChunk).filter(DocumentChunk.id == finding.chunk_id).first() if finding.chunk_id else None
    ref = db.query(EvidenceReference).filter(EvidenceReference.finding_id == finding.id).first()

    return FindingEvidenceDetailResponse(
        finding_id=finding.id,
        finding_title=finding.title,
        entity_type=finding.entity_type,
        verification_status=finding.verification_status,
        document_id=finding.document_id,
        document_filename=doc.filename if doc else None,
        page_number=ref.page_number if ref else (finding.page_number or 1),
        chunk_id=chunk.id if chunk else finding.chunk_id,
        chunk_text=chunk.text_content if chunk else None,
        supporting_quotation=ref.quotation if ref else finding.supporting_quotation,
        match_score=ref.match_score if ref else 1.0,
        is_verified=ref.is_verified if ref else (finding.verification_status == VerificationStatus.VERIFIED),
        verified_at=ref.verified_at if ref else None,
        flags=finding.flags or {}
    )

# --- Backward-compatible endpoints ---

@router.get("/knowledge/{project_id}/findings", response_model=List[FindingResponse])
def list_findings_legacy(
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

    membership = check_project_access(project_id, current_user, db)
    if membership and membership.role == UserRole.INCOMING_MEMBER:
        query = query.filter(ExtractedFinding.status == "APPROVED")

    if isinstance(entity_type, str) and entity_type:
        query = query.filter(ExtractedFinding.entity_type == entity_type.upper())
    if isinstance(verification_status, str) and verification_status:
        query = query.filter(ExtractedFinding.verification_status == verification_status.upper())
    if isinstance(status, str) and status:
        query = query.filter(ExtractedFinding.status == status.upper())
    if isinstance(search, str) and search:
        search_fmt = f"%{search}%"
        query = query.filter(
            or_(
                ExtractedFinding.title.ilike(search_fmt),
                ExtractedFinding.description.ilike(search_fmt),
                ExtractedFinding.owner.ilike(search_fmt)
            )
        )

    findings = query.order_by(ExtractedFinding.created_at.desc()).all()
    return [_format_finding_response(f, db) for f in findings]

list_findings = list_findings_legacy

@router.post("/knowledge/{project_id}/findings", response_model=FindingResponse)
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
        chunk_id=finding_in.chunk_id,
        entity_type=finding_in.entity_type.upper(),
        title=finding_in.title,
        description=finding_in.description,
        owner=finding_in.owner,
        deadline=finding_in.deadline,
        task_status=finding_in.task_status,
        priority=finding_in.priority,
        decided_by=finding_in.decided_by,
        decision_date=finding_in.decision_date,
        impact=finding_in.impact,
        likelihood=finding_in.likelihood,
        mitigation=finding_in.mitigation,
        related_entity=finding_in.related_entity,
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

    run_project_verification(project_id, db)
    db.refresh(finding)
    return _format_finding_response(finding, db)

@router.put("/knowledge/{project_id}/findings/{finding_id}", response_model=FindingResponse)
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

    for field, val in finding_in.model_dump(exclude_unset=True).items():
        setattr(finding, field, val)

    db.commit()
    db.refresh(finding)
    return _format_finding_response(finding, db)

@router.post("/knowledge/{project_id}/verify")
def re_verify_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_project_access(project_id, current_user, db, allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER])
    stats = run_project_verification(project_id, db)
    return {
        "message": "Evidence verification and conflict detection completed successfully",
        "stats": stats
    }

@router.get("/knowledge/{project_id}/timeline")
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

    return [
        {
            "id": item.id,
            "entity_type": item.entity_type,
            "title": item.title,
            "description": item.description,
            "owner": item.owner,
            "deadline": item.deadline,
            "task_status": item.task_status,
            "status": item.status,
            "verification_status": item.verification_status,
            "page_number": item.page_number,
            "created_at": item.created_at
        } for item in items
    ]

@router.get("/knowledge/{project_id}/risks-dependencies")
def get_risks_and_dependencies_legacy(
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
                "severity": f.priority or "MEDIUM",
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
