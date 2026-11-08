from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import Handover, Project, User, UserRole, HandoverStatus, AuditLog
from backend.app.schemas import HandoverCreate, HandoverResponse
from backend.app.auth import get_current_user, check_project_access
from backend.app.services.handover_service import generate_handover_report
from backend.app.services.pdf_generator import generate_handover_pdf

router = APIRouter(prefix="/handovers", tags=["Handover Generation"])

@router.post("/{project_id}/generate", response_model=HandoverResponse)
def generate_handover(
    project_id: str,
    handover_in: HandoverCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_project_access(project_id, current_user, db, allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER])
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    target_role = handover_in.target_role or project.handover_role or "Incoming Team Member"

    # Generate the 13 sections with verified evidence
    content_json = generate_handover_report(
        project_id=project_id,
        target_role=target_role,
        user_id=current_user.id,
        db=db,
        custom_notes=handover_in.custom_notes
    )

    title = f"{project.name} - Handover for {target_role}"
    summary = content_json.get("project_overview", "")[:300]

    handover = Handover(
        project_id=project_id,
        title=title,
        target_role=target_role,
        status=HandoverStatus.DRAFT,
        summary=summary,
        content_json=content_json,
        generated_by=current_user.id
    )
    db.add(handover)

    # Audit log
    audit = AuditLog(
        project_id=project_id,
        user_id=current_user.id,
        action="HANDOVER_GENERATED",
        entity_type="HANDOVER",
        entity_id=handover.id,
        details={"title": title, "target_role": target_role}
    )
    db.add(audit)
    db.commit()
    db.refresh(handover)

    return handover

@router.get("/{project_id}", response_model=List[HandoverResponse])
def list_handovers(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = check_project_access(project_id, current_user, db)
    query = db.query(Handover).filter(Handover.project_id == project_id)

    # Enforce role restriction: INCOMING_MEMBER can only see approved/finalized handovers
    if membership and membership.role == UserRole.INCOMING_MEMBER:
        query = query.filter(Handover.status.in_([HandoverStatus.APPROVED, HandoverStatus.FINALIZED, HandoverStatus.SHARED]))

    handovers = query.order_by(Handover.created_at.desc()).all()
    return handovers

@router.get("/{project_id}/{handover_id}", response_model=HandoverResponse)
def get_handover(
    project_id: str,
    handover_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = check_project_access(project_id, current_user, db)
    handover = db.query(Handover).filter(Handover.id == handover_id, Handover.project_id == project_id).first()
    if not handover:
        raise HTTPException(status_code=404, detail="Handover not found")

    if membership and membership.role == UserRole.INCOMING_MEMBER:
        if handover.status not in [HandoverStatus.APPROVED, HandoverStatus.FINALIZED, HandoverStatus.SHARED]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This handover is currently pending managerial review and has not yet been approved for incoming member viewing."
            )

    return handover

@router.post("/{project_id}/{handover_id}/approve", response_model=HandoverResponse)
def approve_handover(
    project_id: str,
    handover_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_project_access(project_id, current_user, db, allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER])
    handover = db.query(Handover).filter(Handover.id == handover_id, Handover.project_id == project_id).first()
    if not handover:
        raise HTTPException(status_code=404, detail="Handover not found")

    handover.status = HandoverStatus.APPROVED
    handover.approved_by = current_user.id
    handover.approved_at = datetime.utcnow()

    content = dict(handover.content_json)
    if "review_and_approval_info" in content:
        content["review_and_approval_info"]["approval_state"] = "APPROVED_BY_PROJECT_MANAGER"
        content["review_and_approval_info"]["approved_by_name"] = current_user.full_name
        content["review_and_approval_info"]["approved_at"] = handover.approved_at.isoformat()
    handover.content_json = content

    # Audit log
    audit = AuditLog(
        project_id=project_id,
        user_id=current_user.id,
        action="HANDOVER_APPROVED",
        entity_type="HANDOVER",
        entity_id=handover.id,
        details={"approved_by": current_user.email}
    )
    db.add(audit)
    db.commit()
    db.refresh(handover)

    return handover

@router.get("/{project_id}/{handover_id}/export-pdf")
def export_pdf(
    project_id: str,
    handover_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = check_project_access(project_id, current_user, db)
    handover = db.query(Handover).filter(Handover.id == handover_id, Handover.project_id == project_id).first()
    if not handover:
        raise HTTPException(status_code=404, detail="Handover not found")

    if membership and membership.role == UserRole.INCOMING_MEMBER:
        if handover.status not in [HandoverStatus.APPROVED, HandoverStatus.FINALIZED, HandoverStatus.SHARED]:
            raise HTTPException(status_code=403, detail="Unapproved handovers cannot be exported.")

    pdf_stream = generate_handover_pdf(handover.title, handover.content_json)

    # Audit log
    audit = AuditLog(
        project_id=project_id,
        user_id=current_user.id,
        action="HANDOVER_EXPORTED_PDF",
        entity_type="HANDOVER",
        entity_id=handover.id,
        details={"title": handover.title}
    )
    db.add(audit)
    db.commit()

    filename = f"Knowledge_Handover_{project_id[:8]}.pdf"
    return Response(
        content=pdf_stream.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
