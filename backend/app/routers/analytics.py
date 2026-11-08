from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.database import get_db
from backend.app.models import Project, Document, ExtractedFinding, Handover, Review, AuditLog, User
from backend.app.schemas import DashboardStats
from backend.app.auth import get_current_user

router = APIRouter(prefix="/analytics", tags=["Analytics & Dashboard"])

@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    total_projects = db.query(Project).count()
    total_documents = db.query(Document).count()
    total_findings = db.query(ExtractedFinding).count()

    pending_reviews = db.query(ExtractedFinding).filter(
        ExtractedFinding.status.in_(["DRAFT", "FLAGGED", "UNDER_INVESTIGATION"])
    ).count()

    approved_findings = db.query(ExtractedFinding).filter(
        ExtractedFinding.status == "APPROVED"
    ).count()

    flagged_issues = db.query(ExtractedFinding).filter(
        ExtractedFinding.verification_status.in_(["CONFLICTING", "UNSUPPORTED"])
    ).count()

    completed_handovers = db.query(Handover).filter(
        Handover.status.in_(["APPROVED", "FINALIZED", "SHARED"])
    ).count()

    # Findings grouped by entity_type
    type_counts = (
        db.query(ExtractedFinding.entity_type, func.count(ExtractedFinding.id))
        .group_by(ExtractedFinding.entity_type)
        .all()
    )
    findings_by_type = {t[0]: t[1] for t in type_counts}

    # Findings grouped by verification_status
    verif_counts = (
        db.query(ExtractedFinding.verification_status, func.count(ExtractedFinding.id))
        .group_by(ExtractedFinding.verification_status)
        .all()
    )
    verification_breakdown = {v[0]: v[1] for v in verif_counts}

    # Recent activity stream
    recent_audits = (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(10)
        .all()
    )

    activity_stream = []
    for a in recent_audits:
        actor = db.query(User).filter(User.id == a.user_id).first() if a.user_id else None
        proj = db.query(Project).filter(Project.id == a.project_id).first() if a.project_id else None
        activity_stream.append({
            "id": a.id,
            "action": a.action,
            "user_name": actor.full_name if actor else "System",
            "project_name": proj.name if proj else "Global",
            "details": a.details or {},
            "timestamp": a.created_at.isoformat()
        })

    return DashboardStats(
        total_projects=total_projects,
        total_documents=total_documents,
        total_findings=total_findings,
        pending_reviews=pending_reviews,
        approved_findings=approved_findings,
        flagged_issues=flagged_issues,
        completed_handovers=completed_handovers,
        findings_by_type=findings_by_type,
        verification_breakdown=verification_breakdown,
        recent_activity=activity_stream
    )
