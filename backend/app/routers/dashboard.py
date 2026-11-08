from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.database import get_db
from backend.app.models import (
    Project, ProjectMember, Document, ExtractedFinding,
    AuditLog, User, UserRole, ProjectStatus
)
from backend.app.schemas import DashboardSummary, DashboardProjectItem, AuditLogResponse
from backend.app.auth import get_current_user
from backend.app.routers.projects import calculate_readiness_score, get_user_role_in_project

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Computes real summary statistics and recent projects from the database
    strictly isolated to projects accessible to the current user.
    """
    # 1. Query projects accessible to current user
    if current_user.role == UserRole.ADMIN:
        accessible_projects = db.query(Project).all()
        project_ids = [p.id for p in accessible_projects]
    else:
        accessible_projects = (
            db.query(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id, isouter=True)
            .filter((Project.created_by == current_user.id) | (ProjectMember.user_id == current_user.id))
            .distinct()
            .all()
        )
        project_ids = [p.id for p in accessible_projects]

    total_projects = len(accessible_projects)
    active_projects = sum(1 for p in accessible_projects if p.status == ProjectStatus.ACTIVE)
    completed_projects = sum(1 for p in accessible_projects if p.status == ProjectStatus.COMPLETED)
    on_hold_projects = sum(1 for p in accessible_projects if p.status == ProjectStatus.ON_HOLD)
    planning_projects = sum(1 for p in accessible_projects if p.status == ProjectStatus.PLANNING)
    archived_projects = sum(1 for p in accessible_projects if p.status == ProjectStatus.ARCHIVED)

    # 2. Ingested documents count across accessible projects
    if project_ids:
        total_documents = db.query(Document).filter(Document.project_id.in_(project_ids)).count()
        findings_query = db.query(ExtractedFinding).filter(ExtractedFinding.project_id.in_(project_ids))
        total_findings = findings_query.count()
        pending_reviews = findings_query.filter(
            or_(
                ExtractedFinding.status == "DRAFT",
                ExtractedFinding.verification_status == "UNVERIFIED"
            )
        ).count()
        approved_findings = findings_query.filter(ExtractedFinding.status == "APPROVED").count()
    else:
        total_documents = 0
        total_findings = 0
        pending_reviews = 0
        approved_findings = 0

    # 3. Recent projects (ordered by created_at desc, top 5)
    sorted_projects = sorted(accessible_projects, key=lambda p: p.created_at, reverse=True)[:5]
    recent_items: List[DashboardProjectItem] = []
    for p in sorted_projects:
        m_count = db.query(ProjectMember).filter(ProjectMember.project_id == p.id).count()
        d_count = db.query(Document).filter(Document.project_id == p.id).count()
        f_count = db.query(ExtractedFinding).filter(ExtractedFinding.project_id == p.id).count()
        score = calculate_readiness_score(p, db)
        role = get_user_role_in_project(p.id, current_user, db)

        recent_items.append(
            DashboardProjectItem(
                id=p.id,
                name=p.name,
                description=p.description,
                category=p.category or p.domain or "Engineering",
                status=p.status,
                start_date=p.start_date,
                expected_completion_date=p.expected_completion_date,
                created_at=p.created_at,
                members_count=m_count,
                documents_count=d_count,
                findings_count=f_count,
                readiness_score=score,
                current_user_role=role
            )
        )

    return DashboardSummary(
        total_projects=total_projects,
        active_projects=active_projects,
        completed_projects=completed_projects,
        on_hold_projects=on_hold_projects,
        planning_projects=planning_projects,
        archived_projects=archived_projects,
        total_documents=total_documents,
        total_findings=total_findings,
        pending_reviews=pending_reviews,
        approved_findings=approved_findings,
        recent_projects=recent_items
    )

@router.get("/recent-activity", response_model=List[AuditLogResponse])
def get_recent_activity(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns real project activity derived from the audit log table,
    isolated to actions relevant to the current user or their projects.
    """
    if current_user.role == UserRole.ADMIN:
        logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(20).all()
    else:
        # User's project IDs
        project_ids = [
            m.project_id for m in db.query(ProjectMember.project_id)
            .filter(ProjectMember.user_id == current_user.id).all()
        ]
        created_pids = [
            p.id for p in db.query(Project.id)
            .filter(Project.created_by == current_user.id).all()
        ]
        all_pids = list(set(project_ids + created_pids))

        logs = (
            db.query(AuditLog)
            .filter(
                or_(
                    AuditLog.user_id == current_user.id,
                    AuditLog.project_id.in_(all_pids)
                )
            )
            .order_by(AuditLog.created_at.desc())
            .limit(20)
            .all()
        )

    result = []
    for log in logs:
        u_name = None
        if log.user:
            u_name = log.user.full_name
        result.append(
            AuditLogResponse(
                id=log.id,
                project_id=log.project_id,
                user_id=log.user_id,
                user_name=u_name,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                details=log.details or {},
                ip_address=log.ip_address,
                created_at=log.created_at
            )
        )
    return result
