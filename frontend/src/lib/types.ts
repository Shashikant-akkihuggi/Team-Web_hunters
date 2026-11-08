export type UserRole = "ADMIN" | "PROJECT_MANAGER" | "OUTGOING_MEMBER" | "INCOMING_MEMBER";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface Project {
  id: string;
  name: string;
  description: string | null;
  category?: string;
  domain?: string;
  status: string;
  start_date?: string | null;
  expected_completion_date?: string | null;
  target_handover_date?: string | null;
  handover_role: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  members_count: number;
  documents_count: number;
  findings_count: number;
  readiness_score: number;
  current_user_role?: UserRole;
}

export interface ProjectMember {
  id: string;
  project_id: string;
  user_id: string;
  role: UserRole;
  joined_at: string;
  user?: User;
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  project_id?: string;
  page_number: number;
  page_start?: number;
  page_end?: number;
  chunk_index: number;
  text_content: string;
  char_start: number;
  char_end: number;
  character_start?: number;
  character_end?: number;
  created_at?: string;
}

export interface DocumentPage {
  id: string;
  document_id: string;
  page_number: number;
  extracted_text: string;
  char_count: number;
  created_at?: string;
}

export interface DocumentContent {
  id: string;
  filename: string;
  page_count: number;
  extracted_character_count: number;
  full_text: string;
  pages: DocumentPage[];
}

export interface DocumentItem {
  id: string;
  project_id: string;
  filename: string;
  original_filename?: string;
  storage_key?: string;
  file_size: number;
  file_type: string;
  mime_type?: string;
  file_extension?: string;
  file_hash: string;
  checksum?: string;
  page_count: number;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "PROCESSED" | "FAILED" | "UPLOADED";
  processing_status?: string;
  extracted_character_count?: number;
  chunk_count?: number;
  chunks_count: number;
  error_message: string | null;
  processing_error?: string | null;
  uploaded_by: string;
  created_at: string;
  updated_at?: string;
  processed_at?: string | null;
}

export type EntityType =
  | "DECISION"
  | "TASK"
  | "RESPONSIBILITY"
  | "DEADLINE"
  | "MILESTONE"
  | "RISK"
  | "BLOCKER"
  | "DEPENDENCY"
  | "QUESTION"
  | "CONTACT";

export type FindingStatus = "DRAFT" | "VERIFIED" | "FLAGGED" | "APPROVED" | "REJECTED" | "UNDER_INVESTIGATION";

export type VerificationStatus = "VERIFIED" | "UNSUPPORTED" | "CONFLICTING" | "AMBIGUOUS";

export interface FindingFlags {
  has_conflict?: boolean;
  missing_evidence?: boolean;
  ambiguous_ownership?: boolean;
  conflict_reason?: string;
  ownership_conflict?: string;
  evidence_strength?: "STRONG" | "WEAK" | "NONE";
  [key: string]: any;
}

export interface EvidenceReference {
  id: string;
  finding_id: string;
  document_id: string;
  page_number: number;
  quotation: string;
  match_score: number;
  is_verified: boolean;
  verified_at: string;
  document_filename?: string;
}

export interface ExtractedFinding {
  id: string;
  project_id: string;
  document_id: string | null;
  entity_type: EntityType;
  title: string;
  description: string;
  owner: string | null;
  deadline: string | null;
  status: FindingStatus;
  page_number: number | null;
  supporting_quotation: string | null;
  confidence_score: number;
  is_recommendation: boolean;
  flags: FindingFlags;
  verification_status: VerificationStatus;
  document_filename?: string | null;
  evidence_refs?: EvidenceReference[];
  created_at: string;
  updated_at: string;
}

export interface ReviewLog {
  id: string;
  finding_id: string;
  reviewer_id: string;
  reviewer_name?: string;
  action: "APPROVE" | "REJECT" | "EDIT" | "FLAG_INVESTIGATION";
  comment?: string;
  previous_state?: any;
  new_state?: any;
  created_at: string;
}

export interface HandoverDossier {
  id: string;
  project_id: string;
  title: string;
  target_role: string;
  status: "DRAFT" | "REVIEWED" | "APPROVED" | "FINALIZED" | "SHARED";
  summary: string | null;
  content_json: {
    project_overview: string;
    current_status: string;
    completed_work: Array<{ id?: string; title: string; description: string; owner?: string; evidence_page?: number }>;
    pending_tasks: Array<{ id?: string; title: string; description: string; owner?: string; deadline?: string; status?: string; evidence_page?: number }>;
    task_ownership: Array<{ task: string; owner: string; has_ambiguity: boolean; deadline: string }>;
    important_decisions: Array<{ id?: string; decision: string; context: string; supporting_quote?: string; page?: number; is_verified?: boolean }>;
    dependencies: Array<{ id?: string; name: string; details: string; quotation?: string; page?: number }>;
    blockers: Array<{ id?: string; blocker: string; impact: string; status: string; owner?: string; page?: number }>;
    risks: Array<{ id?: string; risk: string; severity: string; details: string; mitigation: string; page?: number }>;
    unresolved_questions: Array<{ id?: string; question: string; context: string; evidence_quote?: string; page?: number }>;
    recommended_next_actions: Array<{ timeframe: string; action: string; deliverable?: string; contacts?: string[] }>;
    evidence_references: Array<{ finding_id: string; title: string; entity_type: string; source_doc: string; page_number: number; quotation: string; verification_status: string; flags?: any }>;
    review_and_approval_info: {
      generated_by: string;
      generated_at: string;
      target_role: string;
      project_name: string;
      approval_state: string;
      approved_by_name?: string;
      approved_at?: string;
      notes?: string;
    };
  };
  generated_by: string;
  approved_by: string | null;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DashboardProjectItem {
  id: string;
  name: string;
  description: string | null;
  category?: string;
  status: string;
  start_date?: string | null;
  expected_completion_date?: string | null;
  created_at: string;
  members_count: number;
  documents_count: number;
  findings_count: number;
  readiness_score: number;
  current_user_role?: UserRole;
}

export interface DashboardSummary {
  total_projects: number;
  active_projects: number;
  completed_projects: number;
  on_hold_projects: number;
  planning_projects: number;
  archived_projects: number;
  total_documents: number;
  total_findings: number;
  pending_reviews: number;
  approved_findings: number;
  recent_projects: DashboardProjectItem[];
}

export interface DashboardStats {
  total_projects: number;
  total_documents: number;
  total_findings: number;
  pending_reviews: number;
  approved_findings: number;
  flagged_issues: number;
  completed_handovers: number;
  findings_by_type: Record<string, number>;
  verification_breakdown: Record<string, number>;
  recent_activity: Array<{
    id: string;
    action: string;
    user_name: string;
    project_name: string;
    details: any;
    timestamp: string;
  }>;
}

export interface AuditLogItem {
  id: string;
  project_id?: string;
  user_id?: string;
  user_name?: string;
  action: string;
  entity_type?: string;
  entity_id?: string;
  details: Record<string, any>;
  ip_address?: string;
  created_at: string;
}
