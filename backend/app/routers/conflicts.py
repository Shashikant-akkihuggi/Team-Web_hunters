from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import (
    KnowledgeConflict, ExtractedFinding, EvidenceReference, Document,
    User, UserRole, ConflictStatus, ConflictSeverity, AuditLog
)
from backend.app.schemas import (
    KnowledgeConflictResponse, ConflictDetailResponse, ConflictReviewRequest,
    ConflictResolveRequest, ConflictDismissRequest, ConflictHistoryResponse,
    ConflictHistoryItem
)
from backend.app.auth import get_current_user, check_project_access
from backend.app.services.verification_service import review_conflict, resolve_conflict, dismiss_conflict

router = APIRouter(tags=["Knowledge Conflicts"])

def _format_conflict_response(c: KnowledgeConflict, db: Session) -> KnowledgeConflictResponse:
    doc1 = db.query(Document).filter(Document.id == (c.source_1_doc_id)).first() if c.source_1_doc_id else None
    doc2 = db.query(Document).filter(Document.id == (c.source_2_doc_id)).first() if c.source_2_doc_id else None
    resolver = db.query(User).filter(User.id == c.resolved_by).first() if c.resolved_by else None

    return KnowledgeConflictResponse(
        id=c.id,
        project_id=c.project_id,
        title=c.title or f"{c.conflict_type.capitalize()} conflict",
        related_entity_type=c.related_entity_type,
        related_entity_id=c.related_entity_id,
        finding_id_1=c.finding_id_1 or c.finding_a_id,
        finding_id_2=c.finding_id_2 or c.finding_b_id,
        finding_a_id=c.finding_a_id or c.finding_id_1,
        finding_b_id=c.finding_b_id or c.finding_id_2,
        evidence_a_id=c.evidence_a_id,
        evidence_b_id=c.evidence_b_id,
        conflict_type=c.conflict_type,
        severity=c.severity or "MEDIUM",
        description=c.description,
        source_1_quote=c.source_1_quote,
        source_1_page=c.source_1_page,
        source_1_doc_id=c.source_1_doc_id,
        source_1_doc_filename=doc1.filename if doc1 else None,
        source_2_quote=c.source_2_quote,
        source_2_page=c.source_2_page,
        source_2_doc_id=c.source_2_doc_id,
        source_2_doc_filename=doc2.filename if doc2 else None,
        source_a_quote=c.source_1_quote,
        source_a_page=c.source_1_page,
        source_a_doc_id=c.source_1_doc_id,
        source_a_doc_filename=doc1.filename if doc1 else None,
        source_b_quote=c.source_2_quote,
        source_b_page=c.source_2_page,
        source_b_doc_id=c.source_2_doc_id,
        source_b_doc_filename=doc2.filename if doc2 else None,
        conflict_status=c.conflict_status or c.status or ConflictStatus.OPEN,
        status=c.conflict_status or c.status or ConflictStatus.OPEN,
        resolution_choice=c.resolution_choice,
        resolution_notes=c.resolution_notes,
        resolved_by=c.resolved_by,
        resolver_name=resolver.full_name if resolver else None,
        detected_at=c.detected_at or c.created_at,
        resolved_at=c.resolved_at,
        created_at=c.created_at,
        updated_at=c.updated_at
    )

@router.get("/projects/{project_id}/conflicts", response_model=List[KnowledgeConflictResponse])
def get_project_conflicts(
    project_id: str,
    conflict_status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    conflict_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns all contradictory findings and conflicting claims detected across project documents.
    """
    check_project_access(project_id, current_user, db)
    query = db.query(KnowledgeConflict).filter(KnowledgeConflict.project_id == project_id)

    if conflict_status:
        query = query.filter((KnowledgeConflict.conflict_status == conflict_status.upper()) | (KnowledgeConflict.status == conflict_status.upper()))
    if severity:
        query = query.filter(KnowledgeConflict.severity == severity.upper())
    if conflict_type:
        query = query.filter(KnowledgeConflict.conflict_type == conflict_type.upper())

    conflicts = query.order_by(KnowledgeConflict.created_at.desc()).offset(offset).limit(limit).all()
    return [_format_conflict_response(c, db) for c in conflicts]

@router.get("/conflicts/{conflict_id}", response_model=ConflictDetailResponse)
def get_conflict_detail(
    conflict_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns deep side-by-side inspection data for a contradiction,
    including both findings, their original citations, document metadata, and resolution state.
    """
    conflict = db.query(KnowledgeConflict).filter(KnowledgeConflict.id == conflict_id).first()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")

    check_project_access(conflict.project_id, current_user, db)

    base = _format_conflict_response(conflict, db)

    f_a = db.query(ExtractedFinding).filter(ExtractedFinding.id == (conflict.finding_a_id or conflict.finding_id_1)).first()
    f_b = db.query(ExtractedFinding).filter(ExtractedFinding.id == (conflict.finding_b_id or conflict.finding_id_2)).first()

    ref_a = db.query(EvidenceReference).filter(EvidenceReference.finding_id == f_a.id).first() if f_a else None
    ref_b = db.query(EvidenceReference).filter(EvidenceReference.finding_id == f_b.id).first() if f_b else None

    doc_a = db.query(Document).filter(Document.id == f_a.document_id).first() if (f_a and f_a.document_id) else None
    doc_b = db.query(Document).filter(Document.id == f_b.document_id).first() if (f_b and f_b.document_id) else None

    finding_a_dict = None
    if f_a:
        finding_a_dict = {
            "id": f_a.id,
            "title": f_a.title,
            "description": f_a.description,
            "entity_type": f_a.entity_type,
            "task_status": f_a.task_status,
            "owner": f_a.owner,
            "deadline": f_a.deadline,
            "page_number": f_a.page_number,
            "document_filename": doc_a.filename if doc_a else None,
            "supporting_quotation": f_a.supporting_quotation,
            "verification_status": f_a.verification_status
        }

    finding_b_dict = None
    if f_b:
        finding_b_dict = {
            "id": f_b.id,
            "title": f_b.title,
            "description": f_b.description,
            "entity_type": f_b.entity_type,
            "task_status": f_b.task_status,
            "owner": f_b.owner,
            "deadline": f_b.deadline,
            "page_number": f_b.page_number,
            "document_filename": doc_b.filename if doc_b else None,
            "supporting_quotation": f_b.supporting_quotation,
            "verification_status": f_b.verification_status
        }

    evidence_a_dict = None
    if ref_a:
        evidence_a_dict = {
            "id": ref_a.id,
            "document_id": ref_a.document_id,
            "document_filename": ref_a.document_filename or (doc_a.filename if doc_a else None),
            "page_number": ref_a.page_number,
            "quotation": ref_a.quotation,
            "character_start": ref_a.character_start,
            "character_end": ref_a.character_end,
            "match_score": ref_a.match_score,
            "verification_status": ref_a.verification_status
        }

    evidence_b_dict = None
    if ref_b:
        evidence_b_dict = {
            "id": ref_b.id,
            "document_id": ref_b.document_id,
            "document_filename": ref_b.document_filename or (doc_b.filename if doc_b else None),
            "page_number": ref_b.page_number,
            "quotation": ref_b.quotation,
            "character_start": ref_b.character_start,
            "character_end": ref_b.character_end,
            "match_score": ref_b.match_score,
            "verification_status": ref_b.verification_status
        }

    return ConflictDetailResponse(
        **base.dict(),
        finding_a=finding_a_dict,
        finding_b=finding_b_dict,
        evidence_a=evidence_a_dict,
        evidence_b=evidence_b_dict
    )

@router.post("/conflicts/{conflict_id}/review", response_model=KnowledgeConflictResponse)
def review_conflict_endpoint(
    conflict_id: str,
    payload: Optional[ConflictReviewRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Marks a conflict as UNDER_REVIEW and logs the investigation activity in audit logs.
    """
    conflict = db.query(KnowledgeConflict).filter(KnowledgeConflict.id == conflict_id).first()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")

    check_project_access(
        conflict.project_id,
        current_user,
        db,
        allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER]
    )

    notes = payload.notes if payload else None
    updated = review_conflict(conflict_id, db, current_user, notes=notes)
    return _format_conflict_response(updated, db)

@router.post("/conflicts/{conflict_id}/resolve", response_model=KnowledgeConflictResponse)
def resolve_conflict_endpoint(
    conflict_id: str,
    payload: ConflictResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Resolves a contradiction between claims.
    Requires explanation and choice.
    Non-destructive: original findings and historical evidence remain preserved.
    """
    conflict = db.query(KnowledgeConflict).filter(KnowledgeConflict.id == conflict_id).first()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")

    check_project_access(
        conflict.project_id,
        current_user,
        db,
        allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER]
    )

    try:
        updated = resolve_conflict(
            conflict_id=conflict_id,
            resolution_choice=payload.resolution_choice,
            resolution_notes=payload.resolution_notes,
            db=db,
            user=current_user
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _format_conflict_response(updated, db)

@router.post("/conflicts/{conflict_id}/dismiss", response_model=KnowledgeConflictResponse)
def dismiss_conflict_endpoint(
    conflict_id: str,
    payload: ConflictDismissRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Dismisses a flagged contradiction with an explanation.
    Restores findings from CONFLICTED status.
    """
    conflict = db.query(KnowledgeConflict).filter(KnowledgeConflict.id == conflict_id).first()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")

    check_project_access(
        conflict.project_id,
        current_user,
        db,
        allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER]
    )

    try:
        updated = dismiss_conflict(
            conflict_id=conflict_id,
            resolution_notes=payload.resolution_notes,
            db=db,
            user=current_user
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _format_conflict_response(updated, db)

@router.get("/conflicts/{conflict_id}/history", response_model=ConflictHistoryResponse)
def get_conflict_history(
    conflict_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns audit trail and human review history for this specific conflict.
    """
    conflict = db.query(KnowledgeConflict).filter(KnowledgeConflict.id == conflict_id).first()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")

    check_project_access(conflict.project_id, current_user, db)

    logs = (
        db.query(AuditLog)
        .filter(AuditLog.entity_id == conflict_id)
        .order_by(AuditLog.created_at.desc())
        .all()
    )

    history_items = []
    for l in logs:
        user = db.query(User).filter(User.id == l.user_id).first() if l.user_id else None
        history_items.append(ConflictHistoryItem(
            id=l.id,
            conflict_id=conflict_id,
            action=l.action,
            user_id=l.user_id,
            user_name=user.full_name if user else "System",
            details=l.details or {},
            created_at=l.created_at
        ))

    return ConflictHistoryResponse(
        conflict_id=conflict_id,
        history=history_items
    )
