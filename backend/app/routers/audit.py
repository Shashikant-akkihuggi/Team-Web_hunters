from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import AuditLog, User, UserRole
from backend.app.schemas import AuditLogResponse
from backend.app.auth import get_current_user, check_project_access

router = APIRouter(tags=["Audit Logs"])

def _fetch_audit_logs(project_id: str, db: Session, current_user: User) -> List[AuditLogResponse]:
    check_project_access(project_id, current_user, db)
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.project_id == project_id)
        .order_by(AuditLog.created_at.desc())
        .limit(200)
        .all()
    )

    results = []
    for log in logs:
        user = db.query(User).filter(User.id == log.user_id).first() if log.user_id else None
        results.append(AuditLogResponse(
            id=log.id,
            project_id=log.project_id,
            user_id=log.user_id,
            user_name=user.full_name if user else "System",
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            details=log.details or {},
            ip_address=log.ip_address,
            created_at=log.created_at
        ))
    return results

@router.get("/audit/{project_id}", response_model=List[AuditLogResponse])
def get_project_audit_logs_legacy(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return _fetch_audit_logs(project_id, db, current_user)

@router.get("/projects/{project_id}/audit-logs", response_model=List[AuditLogResponse])
def get_project_audit_logs(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return _fetch_audit_logs(project_id, db, current_user)
