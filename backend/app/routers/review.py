from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import ExtractedFinding, Review, User, UserRole, FindingStatus, AuditLog, Document
from backend.app.schemas import ReviewCreate, ReviewResponse, FindingResponse, EvidenceReferenceResponse
from backend.app.auth import get_current_user, check_project_access

router = APIRouter(prefix="/review", tags=["Review Workspace"])

@router.get("/{project_id}/queue", response_model=List[FindingResponse])
def get_review_queue(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_project_access(project_id, current_user, db, allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER])

    # Pending findings in DRAFT, FLAGGED, or UNDER_INVESTIGATION
    findings = (
        db.query(ExtractedFinding)
        .filter(
            ExtractedFinding.project_id == project_id,
            ExtractedFinding.status.in_([FindingStatus.DRAFT, FindingStatus.FLAGGED, FindingStatus.UNDER_INVESTIGATION])
        )
        .order_by(ExtractedFinding.created_at.asc())
        .all()
    )

    results = []
    for f in findings:
        doc = db.query(Document).filter(Document.id == f.document_id).first() if f.document_id else None
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
            evidence_refs=[],
            created_at=f.created_at,
            updated_at=f.updated_at
        ))
    return results

@router.post("/{project_id}/findings/{finding_id}", response_model=ReviewResponse)
def submit_review(
    project_id: str,
    finding_id: str,
    review_in: ReviewCreate,
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

    prev_state = {
        "title": finding.title,
        "description": finding.description,
        "owner": finding.owner,
        "deadline": finding.deadline,
        "status": finding.status
    }

    # Apply updates if provided
    if review_in.updated_title:
        finding.title = review_in.updated_title
    if review_in.updated_description:
        finding.description = review_in.updated_description
    if review_in.updated_owner is not None:
        finding.owner = review_in.updated_owner
    if review_in.updated_deadline is not None:
        finding.deadline = review_in.updated_deadline

    # Update status according to action
    act = review_in.action.upper()
    if act == "APPROVE":
        finding.status = FindingStatus.APPROVED
    elif act == "REJECT":
        finding.status = FindingStatus.REJECTED
    elif act == "FLAG_INVESTIGATION":
        finding.status = FindingStatus.UNDER_INVESTIGATION
    elif act == "EDIT":
        finding.status = FindingStatus.VERIFIED

    new_state = {
        "title": finding.title,
        "description": finding.description,
        "owner": finding.owner,
        "deadline": finding.deadline,
        "status": finding.status
    }

    # Record review log
    rev = Review(
        finding_id=finding.id,
        reviewer_id=current_user.id,
        action=act,
        comment=review_in.comment,
        previous_state=prev_state,
        new_state=new_state
    )
    db.add(rev)

    # Audit log
    audit = AuditLog(
        project_id=project_id,
        user_id=current_user.id,
        action=f"FINDING_{act}",
        entity_type="FINDING",
        entity_id=finding.id,
        details={"action": act, "comment": review_in.comment}
    )
    db.add(audit)
    db.commit()
    db.refresh(rev)

    return ReviewResponse(
        id=rev.id,
        finding_id=rev.finding_id,
        reviewer_id=rev.reviewer_id,
        reviewer_name=current_user.full_name,
        action=rev.action,
        comment=rev.comment,
        previous_state=rev.previous_state,
        new_state=rev.new_state,
        created_at=rev.created_at
    )

@router.get("/{project_id}/history", response_model=List[ReviewResponse])
def get_review_history(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_project_access(project_id, current_user, db)
    reviews = (
        db.query(Review)
        .join(ExtractedFinding, ExtractedFinding.id == Review.finding_id)
        .filter(ExtractedFinding.project_id == project_id)
        .order_by(Review.created_at.desc())
        .all()
    )

    results = []
    for r in reviews:
        reviewer = db.query(User).filter(User.id == r.reviewer_id).first()
        results.append(ReviewResponse(
            id=r.id,
            finding_id=r.finding_id,
            reviewer_id=r.reviewer_id,
            reviewer_name=reviewer.full_name if reviewer else "Reviewer",
            action=r.action,
            comment=r.comment,
            previous_state=r.previous_state,
            new_state=r.new_state,
            created_at=r.created_at
        ))
    return results
