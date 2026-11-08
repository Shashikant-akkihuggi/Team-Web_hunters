from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from backend.app.models import User, UserRole
from backend.app.auth import get_current_user

router = APIRouter(prefix="/permissions", tags=["Permissions & RBAC"])

ROLE_CAPABILITIES: Dict[str, Dict[str, Any]] = {
    UserRole.ADMIN: {
        "title": "System Administrator",
        "can_create_projects": True,
        "can_upload_documents": True,
        "can_delete_documents": True,
        "can_review_findings": True,
        "can_approve_handovers": True,
        "can_view_unapproved_drafts": True,
        "can_manage_members": True,
        "can_view_audit_logs": True,
    },
    UserRole.PROJECT_MANAGER: {
        "title": "Project Manager",
        "can_create_projects": True,
        "can_upload_documents": True,
        "can_delete_documents": True,
        "can_review_findings": True,
        "can_approve_handovers": True,
        "can_view_unapproved_drafts": True,
        "can_manage_members": True,
        "can_view_audit_logs": True,
    },
    UserRole.OUTGOING_MEMBER: {
        "title": "Outgoing Team Member",
        "can_create_projects": False,
        "can_upload_documents": True,
        "can_delete_documents": False,
        "can_review_findings": False,
        "can_approve_handovers": False,
        "can_view_unapproved_drafts": True,
        "can_manage_members": False,
        "can_view_audit_logs": False,
    },
    UserRole.INCOMING_MEMBER: {
        "title": "Incoming Team Member",
        "can_create_projects": False,
        "can_upload_documents": False,
        "can_delete_documents": False,
        "can_review_findings": False,
        "can_approve_handovers": False,
        "can_view_unapproved_drafts": False,
        "can_manage_members": False,
        "can_view_audit_logs": False,
    },
}

@router.get("/matrix")
def get_permissions_matrix():
    return ROLE_CAPABILITIES

@router.get("/my-permissions")
def get_my_permissions(current_user: User = Depends(get_current_user)):
    caps = ROLE_CAPABILITIES.get(current_user.role, ROLE_CAPABILITIES[UserRole.INCOMING_MEMBER])
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "capabilities": caps
    }
