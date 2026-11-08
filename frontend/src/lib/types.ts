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

export type VerificationStatus = "VERIFIED" | "UNSUPPORTED" | "CONFLICTING" | "CONFLICTED" | "NEEDS_REVIEW" | "AMBIGUOUS";

export type TaskStatus = "NOT_STARTED" | "IN_PROGRESS" | "BLOCKED" | "COMPLETED" | "UNKNOWN";

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
  chunk_id?: string | null;
  entity_type: EntityType;
  title: string;
  description: string;
  owner: string | null;
  deadline: string | null;
  task_status?: TaskStatus | null;
  priority?: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | null;
  decided_by?: string | null;
  decision_date?: string | null;
  impact?: string | null;
  likelihood?: string | null;
  mitigation?: string | null;
  related_entity?: string | null;
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

export interface ExtractionJob {
  id: string;
  project_id: string;
  status: "QUEUED" | "PROCESSING" | "COMPLETED" | "PARTIALLY_COMPLETED" | "FAILED";
  processed_documents_count: number;
  processed_chunks_count: number;
  extracted_findings_count: number;
  conflicts_count: number;
  unsupported_count: number;
  error_message?: string | null;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
}

export interface KnowledgeConflict {
  id: string;
  project_id: string;
  finding_id_1?: string | null;
  finding_id_2?: string | null;
  conflict_type: "STATUS" | "DEADLINE" | "OWNERSHIP" | "CONTRADICTION";
  description: string;
  source_1_quote?: string | null;
  source_1_page?: number | null;
  source_1_doc_id?: string | null;
  source_1_doc_filename?: string | null;
  source_2_quote?: string | null;
  source_2_page?: number | null;
  source_2_doc_id?: string | null;
  source_2_doc_filename?: string | null;
  status: "OPEN" | "RESOLVED" | "IGNORED";
  created_at: string;
}

export interface FindingEvidenceDetail {
  finding_id: string;
  finding_title: string;
  entity_type: EntityType;
  verification_status: VerificationStatus;
  document_id?: string | null;
  document_filename?: string | null;
  page_number?: number | null;
  chunk_id?: string | null;
  chunk_text?: string | null;
  supporting_quotation?: string | null;
  match_score: number;
  is_verified: boolean;
  verified_at?: string | null;
  flags: FindingFlags;
}

export interface ProjectKnowledgeSummary {
  total_findings: number;
  decisions_count: number;
  tasks_count: number;
  risks_count: number;
  blockers_count: number;
  dependencies_count: number;
  questions_count: number;
  conflicts_count: number;
  unsupported_count: number;
  verified_percentage: number;
}

// --- Phase 5 Project Knowledge Reconstruction Types ---

export interface ProjectOverviewState {
  total_tasks: number;
  completed_tasks: number;
  in_progress_tasks: number;
  blocked_tasks: number;
  not_started_tasks: number;
  unknown_status_tasks: number;
  completion_rate: number;
  total_decisions: number;
  open_risks: number;
  unresolved_questions: number;
  total_dependencies: number;
}

export interface ProjectOwnershipState {
  assigned_tasks_count: number;
  unassigned_tasks_count: number;
  distinct_owners_count: number;
  ambiguous_owners_count: number;
  ownership_conflicts_count: number;
}

export interface ProjectUncertaintyState {
  missing_deadlines_count: number;
  unknown_ownership_count: number;
  conflicting_statuses_count: number;
  unsupported_claims_count: number;
}

export interface ProjectStateResponse {
  project_id: string;
  project_name: string;
  project_description?: string | null;
  project_status: string;
  last_reconstructed_at?: string | null;
  version: number;
  freshness_status: string;
  overview: ProjectOverviewState;
  ownership_state: ProjectOwnershipState;
  uncertainty_state: ProjectUncertaintyState;
  active_blockers_summary: Array<{
    id: string;
    title: string;
    description: string;
    supporting_quotation?: string | null;
    page_number?: number | null;
  }>;
  recent_decisions_summary: Array<{
    id: string;
    title: string;
    description: string;
    decision_date?: string | null;
    decided_by?: string | null;
    page_number?: number | null;
  }>;
}

export interface DecisionTimelineEvent {
  id: string;
  project_id: string;
  title: string;
  description: string;
  decision_date?: string | null;
  normalized_date?: string | null;
  has_date: boolean;
  decided_by?: string | null;
  source_document?: string | null;
  document_id?: string | null;
  supporting_quotation?: string | null;
  page_number?: number | null;
  verification_status: VerificationStatus;
  confidence_score: number;
  flags: FindingFlags;
  created_at?: string | null;
}

export interface DecisionTimelineResponse {
  dated_events: DecisionTimelineEvent[];
  undated_events: DecisionTimelineEvent[];
  total_decisions: number;
}

export interface TaskTimelineItem {
  id: string;
  title: string;
  description: string;
  owner?: string | null;
  has_owner: boolean;
  deadline?: string | null;
  normalized_deadline?: string | null;
  has_deadline: boolean;
  start_date?: string | null;
  task_status: string;
  priority?: string | null;
  is_overdue: boolean;
  dependencies: string[];
  supporting_quotation?: string | null;
  page_number?: number | null;
  document_filename?: string | null;
  verification_status: VerificationStatus;
}

export interface TaskTimelineResponse {
  tasks: TaskTimelineItem[];
  total_tasks: number;
  completed_count: number;
  in_progress_count: number;
  blocked_count: number;
  overdue_count: number;
  unassigned_count: number;
}

export interface DependencyGraphNode {
  id: string;
  label: string;
  entity_type: string;
  status?: string | null;
  owner?: string | null;
  supporting_quotation?: string | null;
  page_number?: number | null;
  document_filename?: string | null;
}

export interface DependencyGraphEdge {
  id: string;
  source: string;
  target: string;
  relationship_type: string;
  source_evidence?: string | null;
  page_number?: number | null;
  document_filename?: string | null;
}

export interface DependencyGraphResponse {
  nodes: DependencyGraphNode[];
  edges: DependencyGraphEdge[];
  has_cycle: boolean;
  cycles: string[][];
  missing_prerequisites: string[];
}

export interface OwnerResponsibilityItem {
  owner_name: string;
  is_registered_member: boolean;
  role?: string | null;
  total_assigned: number;
  completed_count: number;
  in_progress_count: number;
  blocked_count: number;
  pending_count: number;
  tasks: Array<{
    id: string;
    title: string;
    description: string;
    task_status: string;
    deadline?: string | null;
    page_number?: number | null;
  }>;
}

export interface ResponsibilitiesResponse {
  owners: OwnerResponsibilityItem[];
  unassigned_tasks: Array<{
    id: string;
    title: string;
    description: string;
    task_status: string;
    deadline?: string | null;
    supporting_quotation?: string | null;
    page_number?: number | null;
  }>;
  unassigned_count: number;
  total_tasks: number;
}

export interface RiskRegisterItem {
  id: string;
  title: string;
  description: string;
  category: string;
  severity: string;
  likelihood: string;
  mitigation?: string | null;
  related_tasks: string[];
  supporting_quotation?: string | null;
  page_number?: number | null;
  document_filename?: string | null;
  verification_status: VerificationStatus;
}

export interface RiskRegisterResponse {
  source_risks: RiskRegisterItem[];
  blockers: RiskRegisterItem[];
  ai_recommendations: RiskRegisterItem[];
  total_risks: number;
  critical_count: number;
}

export interface KnowledgeSearchItem {
  id: string;
  title: string;
  description: string;
  entity_type: EntityType;
  owner?: string | null;
  status?: string | null;
  source_document?: string | null;
  page_number?: number | null;
  supporting_quotation?: string | null;
  verification_status: VerificationStatus;
  confidence_score: number;
  match_snippet?: string | null;
}

export interface KnowledgeSearchResponse {
  query: string;
  total_results: number;
  results: KnowledgeSearchItem[];
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
