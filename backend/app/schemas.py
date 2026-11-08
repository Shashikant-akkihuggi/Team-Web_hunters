from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- Auth & User Schemas ---
class UserBase(BaseModel):
    email: str
    full_name: str
    role: str = "INCOMING_MEMBER"

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserRegister(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6)
    role: Optional[str] = "INCOMING_MEMBER"

    @model_validator(mode='after')
    def verify_passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self

class UserLogin(BaseModel):
    email: str
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)

class UserChangePassword(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6)

    @model_validator(mode='after')
    def verify_passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirm password do not match")
        return self

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

# --- Project & Team Schemas ---
class ProjectMemberBase(BaseModel):
    user_id: str
    role: str

class ProjectMemberAdd(BaseModel):
    email: str
    role: str = "INCOMING_MEMBER"

class ProjectMemberUpdate(BaseModel):
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
    category: Optional[str] = "Engineering"
    domain: Optional[str] = "Engineering"
    status: Optional[str] = "ACTIVE"
    start_date: Optional[datetime] = None
    expected_completion_date: Optional[datetime] = None
    target_handover_date: Optional[datetime] = None
    handover_role: Optional[str] = "Lead Full-Stack Engineer"

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    domain: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    expected_completion_date: Optional[datetime] = None
    target_handover_date: Optional[datetime] = None
    handover_role: Optional[str] = None

class ProjectResponse(ProjectBase):
    id: str
    status: str
    category: Optional[str] = "Engineering"
    created_by: str
    created_at: datetime
    updated_at: datetime
    members_count: Optional[int] = 0
    documents_count: Optional[int] = 0
    findings_count: Optional[int] = 0
    readiness_score: Optional[int] = 0
    current_user_role: Optional[str] = None

    class Config:
        from_attributes = True

# --- Document Schemas ---
class DocumentPageResponse(BaseModel):
    id: str
    document_id: str
    page_number: int
    extracted_text: str
    char_count: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DocumentChunkResponse(BaseModel):
    id: str
    document_id: str
    project_id: Optional[str] = None
    page_number: int
    page_start: Optional[int] = 1
    page_end: Optional[int] = 1
    chunk_index: int
    text_content: str
    content: Optional[str] = None
    char_start: int
    char_end: int
    character_start: Optional[int] = 0
    character_end: Optional[int] = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DocumentResponse(BaseModel):
    id: str
    project_id: str
    filename: str
    original_filename: Optional[str] = None
    storage_key: Optional[str] = None
    file_size: int
    file_type: str
    mime_type: Optional[str] = None
    file_extension: Optional[str] = None
    file_hash: str
    checksum: Optional[str] = None
    page_count: int
    status: str
    processing_status: Optional[str] = "PROCESSED"
    extracted_character_count: Optional[int] = 0
    chunk_count: Optional[int] = 0
    chunks_count: Optional[int] = 0
    error_message: Optional[str] = None
    processing_error: Optional[str] = None
    uploaded_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DocumentContentResponse(BaseModel):
    id: str
    filename: str
    page_count: int
    extracted_character_count: int
    full_text: str
    pages: List[DocumentPageResponse] = []

    class Config:
        from_attributes = True

class DocumentStatusResponse(BaseModel):
    id: str
    filename: str
    status: str
    processing_status: str
    page_count: int
    chunk_count: int
    extracted_character_count: int
    error_message: Optional[str] = None
    processing_error: Optional[str] = None
    processed_at: Optional[datetime] = None

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
    task_status: Optional[str] = None
    priority: Optional[str] = None
    decided_by: Optional[str] = None
    decision_date: Optional[str] = None
    impact: Optional[str] = None
    likelihood: Optional[str] = None
    mitigation: Optional[str] = None
    related_entity: Optional[str] = None
    status: Optional[str] = "DRAFT"
    page_number: Optional[int] = None
    supporting_quotation: Optional[str] = None
    confidence_score: Optional[float] = 1.0
    is_recommendation: Optional[bool] = False
    flags: Optional[Dict[str, Any]] = None

class FindingCreate(FindingBase):
    project_id: str
    document_id: Optional[str] = None
    chunk_id: Optional[str] = None

class FindingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    owner: Optional[str] = None
    deadline: Optional[str] = None
    task_status: Optional[str] = None
    priority: Optional[str] = None
    decided_by: Optional[str] = None
    decision_date: Optional[str] = None
    impact: Optional[str] = None
    likelihood: Optional[str] = None
    mitigation: Optional[str] = None
    related_entity: Optional[str] = None
    status: Optional[str] = None
    verification_status: Optional[str] = None
    is_recommendation: Optional[bool] = None
    flags: Optional[Dict[str, Any]] = None

class FindingResponse(FindingBase):
    id: str
    project_id: str
    document_id: Optional[str] = None
    chunk_id: Optional[str] = None
    verification_status: str
    document_filename: Optional[str] = None
    evidence_refs: List[EvidenceReferenceResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Phase 4 AI Extraction & Intelligence Schemas ---
class ExtractedEntityItem(BaseModel):
    entity_type: str = Field(..., description="DECISION, TASK, RISK, BLOCKER, DEPENDENCY, QUESTION, MILESTONE, RESPONSIBILITY, CONTACT")
    title: str = Field(..., max_length=255)
    description: str
    owner: Optional[str] = None
    deadline: Optional[str] = None
    task_status: Optional[str] = None  # NOT_STARTED, IN_PROGRESS, BLOCKED, COMPLETED, UNKNOWN
    priority: Optional[str] = None      # CRITICAL, HIGH, MEDIUM, LOW
    decided_by: Optional[str] = None
    decision_date: Optional[str] = None
    impact: Optional[str] = None
    likelihood: Optional[str] = None
    mitigation: Optional[str] = None
    related_entity: Optional[str] = None
    supporting_quotation: str = Field(..., description="Verbatim quote from the chunk text")
    confidence_score: float = 0.9
    is_recommendation: bool = False
    page_number: int = 1

class ExtractedEntitiesPayload(BaseModel):
    findings: List[ExtractedEntityItem] = []

class ExtractionJobCreate(BaseModel):
    force_reprocess: Optional[bool] = False

class ExtractionJobResponse(BaseModel):
    id: str
    project_id: str
    status: str
    processed_documents_count: int
    processed_chunks_count: int
    extracted_findings_count: int
    conflicts_count: int
    unsupported_count: int
    error_message: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class KnowledgeConflictResponse(BaseModel):
    id: str
    project_id: str
    finding_id_1: Optional[str] = None
    finding_id_2: Optional[str] = None
    conflict_type: str
    description: str
    source_1_quote: Optional[str] = None
    source_1_page: Optional[int] = None
    source_1_doc_id: Optional[str] = None
    source_1_doc_filename: Optional[str] = None
    source_2_quote: Optional[str] = None
    source_2_page: Optional[int] = None
    source_2_doc_id: Optional[str] = None
    source_2_doc_filename: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class FindingEvidenceDetailResponse(BaseModel):
    finding_id: str
    finding_title: str
    entity_type: str
    verification_status: str
    document_id: Optional[str] = None
    document_filename: Optional[str] = None
    page_number: Optional[int] = None
    chunk_id: Optional[str] = None
    chunk_text: Optional[str] = None
    supporting_quotation: Optional[str] = None
    match_score: float = 1.0
    is_verified: bool = True
    verified_at: Optional[datetime] = None
    flags: Dict[str, Any] = {}

class ProjectKnowledgeSummary(BaseModel):
    total_findings: int
    decisions_count: int
    tasks_count: int
    risks_count: int
    blockers_count: int
    dependencies_count: int
    questions_count: int
    conflicts_count: int
    unsupported_count: int
    verified_percentage: float

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
class DashboardProjectItem(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = "Engineering"
    status: str
    start_date: Optional[datetime] = None
    expected_completion_date: Optional[datetime] = None
    created_at: datetime
    members_count: int = 0
    documents_count: int = 0
    findings_count: int = 0
    readiness_score: int = 0
    current_user_role: Optional[str] = None

    class Config:
        from_attributes = True

class DashboardSummary(BaseModel):
    total_projects: int
    active_projects: int
    completed_projects: int
    on_hold_projects: int
    planning_projects: int
    archived_projects: int
    total_documents: int
    total_findings: int
    pending_reviews: int
    approved_findings: int
    recent_projects: List[DashboardProjectItem] = []

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

# --- Phase 5 Project Knowledge Reconstruction Schemas ---

class ProjectOverviewState(BaseModel):
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    blocked_tasks: int
    not_started_tasks: int
    unknown_status_tasks: int
    completion_rate: float
    total_decisions: int
    open_risks: int
    unresolved_questions: int
    total_dependencies: int

class ProjectOwnershipState(BaseModel):
    assigned_tasks_count: int
    unassigned_tasks_count: int
    distinct_owners_count: int
    ambiguous_owners_count: int
    ownership_conflicts_count: int

class ProjectUncertaintyState(BaseModel):
    missing_deadlines_count: int
    unknown_ownership_count: int
    conflicting_statuses_count: int
    unsupported_claims_count: int

class ProjectStateResponse(BaseModel):
    project_id: str
    project_name: str
    project_description: Optional[str] = None
    project_status: str
    last_reconstructed_at: Optional[datetime] = None
    version: int
    freshness_status: str
    overview: ProjectOverviewState
    ownership_state: ProjectOwnershipState
    uncertainty_state: ProjectUncertaintyState
    active_blockers_summary: List[Dict[str, Any]] = []
    recent_decisions_summary: List[Dict[str, Any]] = []

class DecisionTimelineEvent(BaseModel):
    id: str
    project_id: str
    title: str
    description: str
    decision_date: Optional[str] = None
    normalized_date: Optional[str] = None
    has_date: bool = False
    decided_by: Optional[str] = None
    source_document: Optional[str] = None
    document_id: Optional[str] = None
    supporting_quotation: Optional[str] = None
    page_number: Optional[int] = 1
    verification_status: str = "VERIFIED"
    confidence_score: float = 1.0
    flags: Dict[str, Any] = {}
    created_at: Optional[datetime] = None

class DecisionTimelineResponse(BaseModel):
    dated_events: List[DecisionTimelineEvent] = []
    undated_events: List[DecisionTimelineEvent] = []
    total_decisions: int = 0

class TaskTimelineItem(BaseModel):
    id: str
    title: str
    description: str
    owner: Optional[str] = None
    has_owner: bool = False
    deadline: Optional[str] = None
    normalized_deadline: Optional[str] = None
    has_deadline: bool = False
    start_date: Optional[str] = None
    task_status: str = "UNKNOWN"
    priority: Optional[str] = "MEDIUM"
    is_overdue: bool = False
    dependencies: List[str] = []
    supporting_quotation: Optional[str] = None
    page_number: Optional[int] = 1
    document_filename: Optional[str] = None
    verification_status: str = "VERIFIED"

class TaskTimelineResponse(BaseModel):
    tasks: List[TaskTimelineItem] = []
    total_tasks: int = 0
    completed_count: int = 0
    in_progress_count: int = 0
    blocked_count: int = 0
    overdue_count: int = 0
    unassigned_count: int = 0

class DependencyGraphNode(BaseModel):
    id: str
    label: str
    entity_type: str
    status: Optional[str] = None
    owner: Optional[str] = None
    supporting_quotation: Optional[str] = None
    page_number: Optional[int] = 1
    document_filename: Optional[str] = None

class DependencyGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship_type: str  # DEPENDS_ON, BLOCKS, PREREQUISITE_FOR
    source_evidence: Optional[str] = None
    page_number: Optional[int] = 1
    document_filename: Optional[str] = None

class DependencyGraphResponse(BaseModel):
    nodes: List[DependencyGraphNode] = []
    edges: List[DependencyGraphEdge] = []
    has_cycle: bool = False
    cycles: List[List[str]] = []
    missing_prerequisites: List[str] = []

class OwnerResponsibilityItem(BaseModel):
    owner_name: str
    is_registered_member: bool = False
    role: Optional[str] = None
    total_assigned: int = 0
    completed_count: int = 0
    in_progress_count: int = 0
    blocked_count: int = 0
    pending_count: int = 0
    tasks: List[Dict[str, Any]] = []

class ResponsibilitiesResponse(BaseModel):
    owners: List[OwnerResponsibilityItem] = []
    unassigned_tasks: List[Dict[str, Any]] = []
    unassigned_count: int = 0
    total_tasks: int = 0

class RiskRegisterItem(BaseModel):
    id: str
    title: str
    description: str
    category: str  # SOURCE_IDENTIFIED, AI_RECOMMENDATION, HUMAN_ADDED
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN
    likelihood: str  # HIGH, MEDIUM, LOW, UNKNOWN
    mitigation: Optional[str] = None
    related_tasks: List[str] = []
    supporting_quotation: Optional[str] = None
    page_number: Optional[int] = 1
    document_filename: Optional[str] = None
    verification_status: str = "VERIFIED"

class RiskRegisterResponse(BaseModel):
    source_risks: List[RiskRegisterItem] = []
    blockers: List[RiskRegisterItem] = []
    ai_recommendations: List[RiskRegisterItem] = []
    total_risks: int = 0
    critical_count: int = 0

class KnowledgeSearchItem(BaseModel):
    id: str
    title: str
    description: str
    entity_type: str
    owner: Optional[str] = None
    status: Optional[str] = None
    source_document: Optional[str] = None
    page_number: Optional[int] = 1
    supporting_quotation: Optional[str] = None
    verification_status: str = "VERIFIED"
    confidence_score: float = 1.0
    match_snippet: Optional[str] = None

class KnowledgeSearchResponse(BaseModel):
    query: str
    total_results: int = 0
    results: List[KnowledgeSearchItem] = []

class ReconstructProjectRequest(BaseModel):
    force: Optional[bool] = False
