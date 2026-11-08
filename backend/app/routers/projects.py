from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from backend.app.database import get_db
from backend.app.models import Project, ProjectMember, User, UserRole, Document, ExtractedFinding, Handover, AuditLog
from backend.app.schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectMemberAdd, ProjectMemberResponse
)
from backend.app.auth import get_current_user, check_project_access

router = APIRouter(prefix="/projects", tags=["Projects"])

def calculate_readiness_score(project: Project, db: Session) -> int:
    """
    Computes a 0-100% handover readiness score based on:
    - Documents ingested (20%)
    - Findings extracted & verified (30%)
    - Review & approval percentage (30%)
    - Target handover date alignment & resolved blockers (20%)
    """
    doc_count = db.query(Document).filter(Document.project_id == project.id).count()
    if doc_count == 0:
        return 0

    findings = db.query(ExtractedFinding).filter(ExtractedFinding.project_id == project.id).all()
    if not findings:
        return 20

    doc_score = min(20, doc_count * 10)
    verified_count = len([f for f in findings if f.verification_status == "VERIFIED"])
    verification_score = int((verified_count / len(findings)) * 30) if findings else 0

    approved_count = len([f for f in findings if f.status == "APPROVED"])
    review_score = int((approved_count / len(findings)) * 30) if findings else 0

    blockers = [f for f in findings if f.entity_type == "BLOCKER"]
    blocker_penalty = min(15, len(blockers) * 5)
    quality_score = max(0, 20 - blocker_penalty)

    return min(100, doc_score + verification_score + review_score + quality_score)

@router.get("", response_model=List[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.ADMIN:
        projects = db.query(Project).all()
    else:
        # Projects where user is a member or creator
        projects = (
            db.query(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id, isouter=True)
            .filter((Project.created_by == current_user.id) | (ProjectMember.user_id == current_user.id))
            .distinct()
            .all()
        )

    results = []
    for p in projects:
        m_count = db.query(ProjectMember).filter(ProjectMember.project_id == p.id).count()
        d_count = db.query(Document).filter(Document.project_id == p.id).count()
        f_count = db.query(ExtractedFinding).filter(ExtractedFinding.project_id == p.id).count()
        score = calculate_readiness_score(p, db)

        p_dict = {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "domain": p.domain,
            "status": p.status,
            "target_handover_date": p.target_handover_date,
            "handover_role": p.handover_role,
            "created_by": p.created_by,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
            "members_count": m_count,
            "documents_count": d_count,
            "findings_count": f_count,
            "readiness_score": score
        }
        results.append(ProjectResponse(**p_dict))
    return results

@router.post("", response_model=ProjectResponse)
def create_project(
    project_in: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = Project(
        name=project_in.name,
        description=project_in.description,
        domain=project_in.domain or "Engineering",
        target_handover_date=project_in.target_handover_date,
        handover_role=project_in.handover_role or "Lead Full-Stack Engineer",
        created_by=current_user.id,
        status="ACTIVE"
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Assign creator as PROJECT_MANAGER
    membership = ProjectMember(
        project_id=project.id,
        user_id=current_user.id,
        role=UserRole.PROJECT_MANAGER if current_user.role != UserRole.ADMIN else UserRole.ADMIN
    )
    db.add(membership)

    # Audit log
    audit = AuditLog(
        project_id=project.id,
        user_id=current_user.id,
        action="PROJECT_CREATED",
        entity_type="PROJECT",
        entity_id=project.id,
        details={"name": project.name, "domain": project.domain}
    )
    db.add(audit)
    db.commit()

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        domain=project.domain,
        status=project.status,
        target_handover_date=project.target_handover_date,
        handover_role=project.handover_role,
        created_by=project.created_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
        members_count=1,
        documents_count=0,
        findings_count=0,
        readiness_score=0
    )

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_project_access(project_id, current_user, db)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    m_count = db.query(ProjectMember).filter(ProjectMember.project_id == project.id).count()
    d_count = db.query(Document).filter(Document.project_id == project.id).count()
    f_count = db.query(ExtractedFinding).filter(ExtractedFinding.project_id == project.id).count()
    score = calculate_readiness_score(project, db)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        domain=project.domain,
        status=project.status,
        target_handover_date=project.target_handover_date,
        handover_role=project.handover_role,
        created_by=project.created_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
        members_count=m_count,
        documents_count=d_count,
        findings_count=f_count,
        readiness_score=score
    )

@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    project_in: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_project_access(project_id, current_user, db, allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER])
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project_in.name is not None:
        project.name = project_in.name
    if project_in.description is not None:
        project.description = project_in.description
    if project_in.domain is not None:
        project.domain = project_in.domain
    if project_in.status is not None:
        project.status = project_in.status
    if project_in.target_handover_date is not None:
        project.target_handover_date = project_in.target_handover_date
    if project_in.handover_role is not None:
        project.handover_role = project_in.handover_role

    db.commit()
    db.refresh(project)

    # Audit log
    audit = AuditLog(
        project_id=project.id,
        user_id=current_user.id,
        action="PROJECT_UPDATED",
        entity_type="PROJECT",
        entity_id=project.id,
        details={"status": project.status, "target_role": project.handover_role}
    )
    db.add(audit)
    db.commit()

    score = calculate_readiness_score(project, db)
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        domain=project.domain,
        status=project.status,
        target_handover_date=project.target_handover_date,
        handover_role=project.handover_role,
        created_by=project.created_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
        members_count=db.query(ProjectMember).filter(ProjectMember.project_id == project.id).count(),
        documents_count=db.query(Document).filter(Document.project_id == project.id).count(),
        findings_count=db.query(ExtractedFinding).filter(ExtractedFinding.project_id == project.id).count(),
        readiness_score=score
    )

@router.get("/{project_id}/members", response_model=List[ProjectMemberResponse])
def list_project_members(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_project_access(project_id, current_user, db)
    members = db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()
    return members

@router.post("/{project_id}/members", response_model=ProjectMemberResponse)
def add_project_member(
    project_id: str,
    member_in: ProjectMemberAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_project_access(project_id, current_user, db, allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER])
    user = db.query(User).filter(User.email == member_in.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User with this email not found")

    existing = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user.id
    ).first()

    if existing:
        existing.role = member_in.role
        db.commit()
        db.refresh(existing)
        return existing

    new_member = ProjectMember(
        project_id=project_id,
        user_id=user.id,
        role=member_in.role
    )
    db.add(new_member)

    # Audit log
    audit = AuditLog(
        project_id=project_id,
        user_id=current_user.id,
        action="MEMBER_ADDED",
        entity_type="PROJECT_MEMBER",
        entity_id=user.id,
        details={"email": user.email, "role": member_in.role}
    )
    db.add(audit)
    db.commit()
    db.refresh(new_member)
    return new_member

@router.delete("/{project_id}/members/{user_id}")
def remove_project_member(
    project_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_project_access(project_id, current_user, db, allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER])
    membership = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Member not found in this project")

    db.delete(membership)

    audit = AuditLog(
        project_id=project_id,
        user_id=current_user.id,
        action="MEMBER_REMOVED",
        entity_type="PROJECT_MEMBER",
        entity_id=user_id,
        details={"user_id": user_id}
    )
    db.add(audit)
    db.commit()
    return {"message": "Member removed successfully"}
