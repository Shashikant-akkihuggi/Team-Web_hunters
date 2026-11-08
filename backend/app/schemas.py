from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- Auth Schemas ---
class UserBase(BaseModel):
    email: str
    full_name: str
    role: str = "INCOMING_MEMBER"

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(UserBase):
    id: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None

# --- Project Schemas ---
class ProjectMemberBase(BaseModel):
    user_id: str
    role: str

class ProjectMemberAdd(BaseModel):
    email: str
    role: str

class ProjectMemberResponse(BaseModel):
    id: str
    project_id: str
    user_id: str
    role: str
    joined_at: datetime
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True

class ProjectBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    domain: Optional[str] = "Engineering"
    target_handover_date: Optional[datetime] = None
    handover_role: Optional[str] = "Lead Full-Stack Engineer"

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    domain: Optional[str] = None
    status: Optional[str] = None
    target_handover_date: Optional[datetime] = None
    handover_role: Optional[str] = None

class ProjectResponse(ProjectBase):
    id: str
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    members_count: Optional[int] = 0
    documents_count: Optional[int] = 0
    findings_count: Optional[int] = 0
    readiness_score: Optional[int] = 0

    class Config:
        from_attributes = True

# --- Document Schemas ---
class DocumentChunkResponse(BaseModel):
    id: str
    document_id: str
    page_number: int
    chunk_index: int
    text_content: str
    char_start: int
    char_end: int

    class Config:
        from_attributes = True

class DocumentResponse(BaseModel):
    id: str
    project_id: str
    filename: str
    file_size: int
    file_type: str
    file_hash: str
    page_count: int
    status: str
    error_message: Optional[str] = None
    uploaded_by: str
    created_at: datetime
    chunks_count: Optional[int] = 0

    class Config:
        from_attributes = True

# --- Finding & Evidence Schemas ---
class EvidenceReferenceResponse(BaseModel):
    id: str
    finding_id: str
    document_id: str
    page_number: int
    quotation: str
    match_score: float
    is_verified: bool
    verified_at: datetime
    document_filename: Optional[str] = None

    class Config:
        from_attributes = True

class FindingBase(BaseModel):
    entity_type: str
    title: str
    description: str
    owner: Optional[str] = None
    deadline: Optional[str] = None
    status: Optional[str] = "DRAFT"
    page_number: Optional[int] = None
    supporting_quotation: Optional[str] = None
    confidence_score: Optional[float] = 1.0
    is_recommendation: Optional[bool] = False
    flags: Optional[Dict[str, Any]] = None

class FindingCreate(FindingBase):
    project_id: str
    document_id: Optional[str] = None

class FindingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    owner: Optional[str] = None
    deadline: Optional[str] = None
    status: Optional[str] = None
    verification_status: Optional[str] = None
    is_recommendation: Optional[bool] = None
    flags: Optional[Dict[str, Any]] = None

class FindingResponse(FindingBase):
    id: str
    project_id: str
    document_id: Optional[str] = None
    verification_status: str
    document_filename: Optional[str] = None
    evidence_refs: List[EvidenceReferenceResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Review Schemas ---
class ReviewCreate(BaseModel):
    action: str  # APPROVE, REJECT, EDIT, FLAG_INVESTIGATION
    comment: Optional[str] = None
    updated_title: Optional[str] = None
    updated_description: Optional[str] = None
    updated_owner: Optional[str] = None
    updated_deadline: Optional[str] = None

class ReviewResponse(BaseModel):
    id: str
    finding_id: str
    reviewer_id: str
    reviewer_name: Optional[str] = None
    action: str
    comment: Optional[str] = None
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

# --- Handover Schemas ---
class HandoverSection(BaseModel):
    section_id: str
    title: str
    content: str
    items: List[Dict[str, Any]] = []
    evidence_citations: List[Dict[str, Any]] = []

class HandoverContent(BaseModel):
    project_overview: str
    current_status: str
    completed_work: List[Dict[str, Any]] = []
    pending_tasks: List[Dict[str, Any]] = []
    task_ownership: List[Dict[str, Any]] = []
    important_decisions: List[Dict[str, Any]] = []
    dependencies: List[Dict[str, Any]] = []
    blockers: List[Dict[str, Any]] = []
    risks: List[Dict[str, Any]] = []
    unresolved_questions: List[Dict[str, Any]] = []
    recommended_next_actions: List[Dict[str, Any]] = []
    evidence_references: List[Dict[str, Any]] = []
    review_and_approval_info: Dict[str, Any] = {}

class HandoverCreate(BaseModel):
    project_id: str
    target_role: Optional[str] = "Incoming Team Member"
    custom_notes: Optional[str] = None

class HandoverResponse(BaseModel):
    id: str
    project_id: str
    title: str
    target_role: str
    status: str
    summary: Optional[str] = None
    content_json: Dict[str, Any]
    generated_by: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Analytics & Dashboard Schemas ---
class DashboardStats(BaseModel):
    total_projects: int
    total_documents: int
    total_findings: int
    pending_reviews: int
    approved_findings: int
    flagged_issues: int
    completed_handovers: int
    findings_by_type: Dict[str, int]
    verification_breakdown: Dict[str, int]
    recent_activity: List[Dict[str, Any]] = []

# --- Audit Schema ---
class AuditLogResponse(BaseModel):
    id: str
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
