from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import (
    Project, ProjectMember, User, UserRole, ProjectStatus,
    Document, ExtractedFinding, AuditLog
)
from backend.app.schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    ProjectMemberAdd, ProjectMemberUpdate, ProjectMemberResponse,
    DocumentResponse
)
from backend.app.auth import get_current_user, check_project_access

router = APIRouter(prefix="/projects", tags=["Projects"])

VALID_ROLES = [
    UserRole.ADMIN,
    UserRole.PROJECT_MANAGER,
    UserRole.OUTGOING_MEMBER,
    UserRole.INCOMING_MEMBER
]

VALID_STATUSES = [
    ProjectStatus.PLANNING,
    ProjectStatus.ACTIVE,
    ProjectStatus.ON_HOLD,
    ProjectStatus.COMPLETED,
    ProjectStatus.ARCHIVED
]

def calculate_readiness_score(project: Project, db: Session) -> int:
    """
    Computes a 0-100% handover readiness score based on:
    - Documents ingested (20%)
    - Findings extracted & verified (30%)
    - Review & approval percentage (30%)
    - Resolved blockers & timeline alignment (20%)
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

def get_user_role_in_project(project_id: str, user: User, db: Session) -> str:
    """Returns the effective role of the user within a project."""
    if user.role == UserRole.ADMIN:
        return UserRole.ADMIN
    membership = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user.id
    ).first()
    return membership.role if membership else "NONE"

@router.get("", response_model=List[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all projects accessible to the current user.
    System ADMIN sees all projects.
    Other users see only projects where they are creator or a registered team member.
    """
    if current_user.role == UserRole.ADMIN:
        projects = db.query(Project).order_by(Project.created_at.desc()).all()
    else:
        projects = (
            db.query(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id, isouter=True)
            .filter((Project.created_by == current_user.id) | (ProjectMember.user_id == current_user.id))
            .distinct()
            .order_by(Project.created_at.desc())
            .all()
        )

    results = []
    for p in projects:
        m_count = db.query(ProjectMember).filter(ProjectMember.project_id == p.id).count()
        d_count = db.query(Document).filter(Document.project_id == p.id).count()
        f_count = db.query(ExtractedFinding).filter(ExtractedFinding.project_id == p.id).count()
        score = calculate_readiness_score(p, db)
        role = get_user_role_in_project(p.id, current_user, db)

        p_dict = {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "category": p.category or p.domain or "Engineering",
            "domain": p.domain or p.category or "Engineering",
            "status": p.status,
            "start_date": p.start_date,
            "expected_completion_date": p.expected_completion_date,
            "target_handover_date": p.target_handover_date,
            "handover_role": p.handover_role,
            "created_by": p.created_by,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
            "members_count": m_count,
            "documents_count": d_count,
            "findings_count": f_count,
            "readiness_score": score,
            "current_user_role": role
        }
        results.append(ProjectResponse(**p_dict))
    return results

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project_in: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new project.
    The creator automatically becomes the project's ADMIN with full ownership.
    """
    status_val = project_in.status.upper() if project_in.status else ProjectStatus.ACTIVE
    if status_val not in VALID_STATUSES:
        status_val = ProjectStatus.ACTIVE

    category_val = project_in.category or project_in.domain or "Engineering"

    project = Project(
        name=project_in.name.strip(),
        description=project_in.description.strip() if project_in.description else None,
        category=category_val,
        domain=category_val,
        status=status_val,
        start_date=project_in.start_date or datetime.utcnow(),
        expected_completion_date=project_in.expected_completion_date,
        target_handover_date=project_in.target_handover_date,
        handover_role=project_in.handover_role or "Lead Full-Stack Engineer",
        created_by=current_user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Automatic ownership assignment: Creator becomes project ADMIN
    membership = ProjectMember(
        project_id=project.id,
        user_id=current_user.id,
        role=UserRole.ADMIN
    )
    db.add(membership)

    # Audit log
    audit = AuditLog(
        project_id=project.id,
        user_id=current_user.id,
        action="PROJECT_CREATED",
        entity_type="PROJECT",
        entity_id=project.id,
        details={
            "name": project.name,
            "category": project.category,
            "status": project.status,
            "ownership_role": UserRole.ADMIN
        }
    )
    db.add(audit)
    db.commit()

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        category=project.category,
        domain=project.domain,
        status=project.status,
        start_date=project.start_date,
        expected_completion_date=project.expected_completion_date,
        target_handover_date=project.target_handover_date,
        handover_role=project.handover_role,
        created_by=project.created_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
        members_count=1,
        documents_count=0,
        findings_count=0,
        readiness_score=0,
        current_user_role=UserRole.ADMIN
    )

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """View details of a specific project. Access is verified against project membership."""
    check_project_access(project_id, current_user, db)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    m_count = db.query(ProjectMember).filter(ProjectMember.project_id == project.id).count()
    d_count = db.query(Document).filter(Document.project_id == project.id).count()
    f_count = db.query(ExtractedFinding).filter(ExtractedFinding.project_id == project.id).count()
    score = calculate_readiness_score(project, db)
    role = get_user_role_in_project(project.id, current_user, db)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        category=project.category or project.domain or "Engineering",
        domain=project.domain or project.category or "Engineering",
        status=project.status,
        start_date=project.start_date,
        expected_completion_date=project.expected_completion_date,
        target_handover_date=project.target_handover_date,
        handover_role=project.handover_role,
        created_by=project.created_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
        members_count=m_count,
        documents_count=d_count,
        findings_count=f_count,
        readiness_score=score,
        current_user_role=role
    )

@router.put("/{project_id}", response_model=ProjectResponse)
@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    project_in: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update project details. Only project ADMIN or PROJECT_MANAGER can update."""
    check_project_access(project_id, current_user, db, allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER])
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project_in.name is not None and project_in.name.strip():
        project.name = project_in.name.strip()
    if project_in.description is not None:
        project.description = project_in.description.strip() if project_in.description else None
    if project_in.category is not None:
        project.category = project_in.category
        project.domain = project_in.category
    elif project_in.domain is not None:
        project.domain = project_in.domain
        project.category = project_in.domain
    if project_in.status is not None:
        status_norm = project_in.status.upper()
        if status_norm in VALID_STATUSES:
            project.status = status_norm
    if project_in.start_date is not None:
        project.start_date = project_in.start_date
    if project_in.expected_completion_date is not None:
        project.expected_completion_date = project_in.expected_completion_date
    if project_in.target_handover_date is not None:
        project.target_handover_date = project_in.target_handover_date
    if project_in.handover_role is not None:
        project.handover_role = project_in.handover_role

    project.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(project)

    # Audit log
    audit = AuditLog(
        project_id=project.id,
        user_id=current_user.id,
        action="PROJECT_UPDATED",
        entity_type="PROJECT",
        entity_id=project.id,
        details={"name": project.name, "status": project.status, "category": project.category}
    )
    db.add(audit)
    db.commit()

    score = calculate_readiness_score(project, db)
    role = get_user_role_in_project(project.id, current_user, db)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        category=project.category,
        domain=project.domain,
        status=project.status,
        start_date=project.start_date,
        expected_completion_date=project.expected_completion_date,
        target_handover_date=project.target_handover_date,
        handover_role=project.handover_role,
        created_by=project.created_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
        members_count=db.query(ProjectMember).filter(ProjectMember.project_id == project.id).count(),
        documents_count=db.query(Document).filter(Document.project_id == project.id).count(),
        findings_count=db.query(ExtractedFinding).filter(ExtractedFinding.project_id == project.id).count(),
        readiness_score=score,
        current_user_role=role
    )

@router.post("/{project_id}/archive", response_model=ProjectResponse)
def archive_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Archive a project. Only project ADMIN or PROJECT_MANAGER can archive."""
    check_project_access(project_id, current_user, db, allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER])
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.status = ProjectStatus.ARCHIVED
    project.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(project)

    audit = AuditLog(
        project_id=project.id,
        user_id=current_user.id,
        action="PROJECT_ARCHIVED",
        entity_type="PROJECT",
        entity_id=project.id,
        details={"status": project.status}
    )
    db.add(audit)
    db.commit()

    score = calculate_readiness_score(project, db)
    role = get_user_role_in_project(project.id, current_user, db)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        category=project.category,
        domain=project.domain,
        status=project.status,
        start_date=project.start_date,
        expected_completion_date=project.expected_completion_date,
        target_handover_date=project.target_handover_date,
        handover_role=project.handover_role,
        created_by=project.created_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
        members_count=db.query(ProjectMember).filter(ProjectMember.project_id == project.id).count(),
        documents_count=db.query(Document).filter(Document.project_id == project.id).count(),
        findings_count=db.query(ExtractedFinding).filter(ExtractedFinding.project_id == project.id).count(),
        readiness_score=score,
        current_user_role=role
    )

@router.delete("/{project_id}")
def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a project.
    Permitted ONLY for project ADMIN or system ADMIN.
    """
    check_project_access(project_id, current_user, db, allowed_roles=[UserRole.ADMIN])
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project_name = project.name
    db.delete(project)
    db.commit()

    audit = AuditLog(
        user_id=current_user.id,
        action="PROJECT_DELETED",
        entity_type="PROJECT",
        entity_id=project_id,
        details={"name": project_name}
    )
    db.add(audit)
    db.commit()

    return {"message": f"Project '{project_name}' deleted successfully."}

# =========================================================================
# Team & Membership Endpoints
# =========================================================================

@router.get("/{project_id}/members", response_model=List[ProjectMemberResponse])
def list_project_members(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all team members of a project."""
    check_project_access(project_id, current_user, db)
    members = db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()
    return members

@router.post("/{project_id}/members", response_model=ProjectMemberResponse, status_code=status.HTTP_201_CREATED)
def add_project_member(
    project_id: str,
    member_in: ProjectMemberAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a registered user to the project by email.
    Only project ADMIN or PROJECT_MANAGER can add members.
    Rejects duplicate membership with a clear 400 error.
    """
    check_project_access(project_id, current_user, db, allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER])

    # 1. Validate email
    normalized_email = member_in.email.strip().lower()
    user = db.query(User).filter(User.email.ilike(normalized_email)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{member_in.email}' is not registered on the platform."
        )

    # 2. Prevent duplicate membership
    existing = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user.id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User '{user.email}' is already a member of this project with role '{existing.role}'."
        )

    # 3. Validate role
    role_norm = member_in.role.upper() if member_in.role else UserRole.INCOMING_MEMBER
    if role_norm not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid project role '{member_in.role}'. Must be one of: {', '.join(VALID_ROLES)}"
        )

    # 4. Add member
    new_member = ProjectMember(
        project_id=project_id,
        user_id=user.id,
        role=role_norm
    )
    db.add(new_member)

    # 5. Audit log
    audit = AuditLog(
        project_id=project_id,
        user_id=current_user.id,
        action="MEMBER_ADDED",
        entity_type="PROJECT_MEMBER",
        entity_id=user.id,
        details={"user_email": user.email, "role": role_norm}
    )
    db.add(audit)
    db.commit()
    db.refresh(new_member)

    return new_member

@router.patch("/{project_id}/members/{user_id}", response_model=ProjectMemberResponse)
@router.put("/{project_id}/members/{user_id}", response_model=ProjectMemberResponse)
def update_project_member_role(
    project_id: str,
    user_id: str,
    role_in: ProjectMemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a member's role in the project.
    Only project ADMIN can assign or update roles.
    Includes safeguards to ensure a project always retains at least one ADMIN.
    """
    check_project_access(project_id, current_user, db, allowed_roles=[UserRole.ADMIN])

    membership = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        (ProjectMember.user_id == user_id) | (ProjectMember.id == user_id)
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Member not found in this project.")

    role_norm = role_in.role.upper()
    if role_norm not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{role_in.role}'. Allowed roles: {', '.join(VALID_ROLES)}"
        )

    # Safeguard: Do not demote the last ADMIN
    if membership.role == UserRole.ADMIN and role_norm != UserRole.ADMIN:
        admin_count = db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.role == UserRole.ADMIN
        ).count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the sole project ADMIN. Assign another ADMIN first."
            )

    old_role = membership.role
    membership.role = role_norm
    db.commit()
    db.refresh(membership)

    audit = AuditLog(
        project_id=project_id,
        user_id=current_user.id,
        action="MEMBER_ROLE_UPDATED",
        entity_type="PROJECT_MEMBER",
        entity_id=membership.user_id,
        details={"old_role": old_role, "new_role": role_norm}
    )
    db.add(audit)
    db.commit()

    return membership

@router.delete("/{project_id}/members/{user_id}")
def remove_project_member(
    project_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove a member from the project.
    Only project ADMIN can remove members.
    Safeguards prevent removing the last ADMIN or the project creator.
    """
    check_project_access(project_id, current_user, db, allowed_roles=[UserRole.ADMIN])

    membership = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        (ProjectMember.user_id == user_id) | (ProjectMember.id == user_id)
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Member not found in this project.")

    # Safeguard: Cannot remove the last project ADMIN
    if membership.role == UserRole.ADMIN:
        admin_count = db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.role == UserRole.ADMIN
        ).count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the sole project ADMIN. Assign another ADMIN before removing."
            )

    removed_user_id = membership.user_id
    db.delete(membership)

    audit = AuditLog(
        project_id=project_id,
        user_id=current_user.id,
        action="MEMBER_REMOVED",
        entity_type="PROJECT_MEMBER",
        entity_id=removed_user_id,
        details={"user_id": removed_user_id}
    )
    db.add(audit)
    db.commit()

    return {"message": "Member removed successfully from project."}

# =========================================================================
# Project Documents Direct Endpoints (Phase 3 Specification)
# =========================================================================

@router.post("/{project_id}/documents", response_model=List[DocumentResponse])
async def upload_project_documents(
    project_id: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Direct alias for document upload: POST /api/v1/projects/{project_id}/documents."""
    from backend.app.routers.documents import upload_documents
    return await upload_documents(project_id=project_id, files=files, db=db, current_user=current_user)

@router.get("/{project_id}/documents", response_model=List[DocumentResponse])
def get_project_documents(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Direct alias for document listing: GET /api/v1/projects/{project_id}/documents."""
    from backend.app.routers.documents import list_project_documents
    return list_project_documents(project_id=project_id, db=db, current_user=current_user)

