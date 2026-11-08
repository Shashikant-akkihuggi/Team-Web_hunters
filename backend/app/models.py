import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class UserRole:
    ADMIN = "ADMIN"
    PROJECT_MANAGER = "PROJECT_MANAGER"
    OUTGOING_MEMBER = "OUTGOING_MEMBER"
    INCOMING_MEMBER = "INCOMING_MEMBER"

class EntityType:
    DECISION = "DECISION"
    TASK = "TASK"
    RESPONSIBILITY = "RESPONSIBILITY"
    DEADLINE = "DEADLINE"
    MILESTONE = "MILESTONE"
    RISK = "RISK"
    BLOCKER = "BLOCKER"
    DEPENDENCY = "DEPENDENCY"
    QUESTION = "QUESTION"
    CONTACT = "CONTACT"

class FindingStatus:
    DRAFT = "DRAFT"
    VERIFIED = "VERIFIED"
    FLAGGED = "FLAGGED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"

class VerificationStatus:
    VERIFIED = "VERIFIED"
    UNSUPPORTED = "UNSUPPORTED"
    CONFLICTING = "CONFLICTING"
    AMBIGUOUS = "AMBIGUOUS"

class ProjectStatus:
    PLANNING = "PLANNING"
    ACTIVE = "ACTIVE"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"

class HandoverStatus:
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    APPROVED = "APPROVED"
    FINALIZED = "FINALIZED"
    SHARED = "SHARED"

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default=UserRole.INCOMING_MEMBER, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project_memberships = relationship("ProjectMember", back_populates="user", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="reviewer")
    audit_logs = relationship("AuditLog", back_populates="user")

class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), default="Engineering")
    domain = Column(String(100), default="Engineering")
    status = Column(String(50), default=ProjectStatus.ACTIVE)  # PLANNING, ACTIVE, ON_HOLD, COMPLETED, ARCHIVED
    start_date = Column(DateTime, default=datetime.utcnow)
    expected_completion_date = Column(DateTime, nullable=True)
    target_handover_date = Column(DateTime, nullable=True)
    handover_role = Column(String(100), default="Lead Full-Stack Engineer")
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    document_chunks = relationship("DocumentChunk", back_populates="project", cascade="all, delete-orphan")
    findings = relationship("ExtractedFinding", back_populates="project", cascade="all, delete-orphan")
    handovers = relationship("Handover", back_populates="project", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="project", cascade="all, delete-orphan")

class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint('project_id', 'user_id', name='uq_project_user'),)

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(50), default=UserRole.INCOMING_MEMBER, nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="project_memberships")

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, default=0)
    file_type = Column(String(50), nullable=False)  # pdf, docx, txt
    file_hash = Column(String(64), nullable=False, index=True)
    page_count = Column(Integer, default=1)
    status = Column(String(50), default="PENDING")  # PENDING, PROCESSING, COMPLETED, FAILED
    error_message = Column(Text, nullable=True)
    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    findings = relationship("ExtractedFinding", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False, default=1)
    chunk_index = Column(Integer, nullable=False, default=0)
    text_content = Column(Text, nullable=False)
    char_start = Column(Integer, default=0)
    char_end = Column(Integer, default=0)
    embedding = Column(JSON, nullable=True)  # Store embedding array or vector
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="chunks")
    project = relationship("Project", back_populates="document_chunks")

class ExtractedFinding(Base):
    __tablename__ = "extracted_findings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=True, index=True)
    entity_type = Column(String(50), nullable=False, index=True)  # DECISION, TASK, RISK, etc.
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    owner = Column(String(255), nullable=True)  # Null if not explicitly found
    deadline = Column(String(100), nullable=True)  # Null if not explicitly found
    status = Column(String(50), default=FindingStatus.DRAFT, index=True)
    verification_status = Column(String(50), default=VerificationStatus.UNSUPPORTED, index=True)
    page_number = Column(Integer, nullable=True)
    supporting_quotation = Column(Text, nullable=True)
    confidence_score = Column(Float, default=1.0)
    is_recommendation = Column(Boolean, default=False)
    flags = Column(JSON, default=dict)  # {"has_conflict": bool, "missing_evidence": bool, "ambiguous_ownership": bool, "notes": str}
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="findings")
    document = relationship("Document", back_populates="findings")
    evidence_refs = relationship("EvidenceReference", back_populates="finding", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="finding", cascade="all, delete-orphan")

class EvidenceReference(Base):
    __tablename__ = "evidence_references"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    finding_id = Column(String(36), ForeignKey("extracted_findings.id"), nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False, default=1)
    quotation = Column(Text, nullable=False)
    match_score = Column(Float, default=1.0)
    is_verified = Column(Boolean, default=True)
    verified_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    finding = relationship("ExtractedFinding", back_populates="evidence_refs")

class Review(Base):
    __tablename__ = "reviews"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    finding_id = Column(String(36), ForeignKey("extracted_findings.id"), nullable=False, index=True)
    reviewer_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    action = Column(String(50), nullable=False)  # APPROVE, REJECT, EDIT, FLAG_INVESTIGATION
    comment = Column(Text, nullable=True)
    previous_state = Column(JSON, nullable=True)
    new_state = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    finding = relationship("ExtractedFinding", back_populates="reviews")
    reviewer = relationship("User", back_populates="reviews")

class Handover(Base):
    __tablename__ = "handovers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    target_role = Column(String(100), default="Incoming Team Member")
    status = Column(String(50), default=HandoverStatus.DRAFT, index=True)
    summary = Column(Text, nullable=True)
    content_json = Column(JSON, nullable=False)  # Holds all 13 sections and evidence
    generated_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    approved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="handovers")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(String(36), nullable=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")
