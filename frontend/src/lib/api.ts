import {
  User,
  Project,
  ProjectMember,
  DocumentItem,
  DocumentChunk,
  DocumentContent,
  DocumentPage,
  ExtractedFinding,
  ExtractionJob,
  KnowledgeConflict,
  ConflictDetail,
  ConflictHistoryItem,
  EvidenceReference,
  EvidenceSummary,
  EvidenceDetailItem,
  FindingEvidenceDetail,
  ProjectKnowledgeSummary,
  ProjectStateResponse,
  DecisionTimelineResponse,
  TaskTimelineResponse,
  DependencyGraphResponse,
  ResponsibilitiesResponse,
  RiskRegisterResponse,
  KnowledgeSearchResponse,
  ReviewLog,
  HandoverDossier,
  DashboardStats,
  DashboardSummary,
  AuditLogItem,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("kc_token");
}

export function setToken(token: string) {
  if (typeof window !== "undefined") {
    localStorage.setItem("kc_token", token);
  }
}

export function removeToken() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("kc_token");
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers || {});
  
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || JSON.stringify(errJson);
    } catch {
      // keep statusText
    }
    throw new Error(errorDetail || `Request failed with status ${response.status}`);
  }

  if (response.headers.get("content-type")?.includes("application/json")) {
    return (await response.json()) as T;
  }
  return {} as T;
}

export const api = {
  // Auth
  async login(email: string, password: string): Promise<{ access_token: string; user: User }> {
    const res = await request<{ access_token: string; user: User }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    if (res.access_token) {
      setToken(res.access_token);
    }
    return res;
  },

  async register(data: {
    email: string;
    full_name: string;
    password: string;
    confirm_password: string;
    role?: string;
  }): Promise<{ access_token: string; user: User }> {
    const res = await request<{ access_token: string; user: User }>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
    if (res.access_token) {
      setToken(res.access_token);
    }
    return res;
  },

  async logout(): Promise<{ message: string }> {
    try {
      const res = await request<{ message: string }>("/auth/logout", {
        method: "POST",
      });
      removeToken();
      return res;
    } catch {
      removeToken();
      return { message: "Logged out" };
    }
  },

  async getMe(): Promise<User> {
    return request<User>("/auth/me");
  },

  // User Management
  async updateProfile(data: { full_name: string }): Promise<User> {
    return request<User>("/users/me", {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  async changePassword(data: {
    current_password: string;
    new_password: string;
    confirm_password: string;
  }): Promise<{ message: string }> {
    return request<{ message: string }>("/users/change-password", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async searchUsers(query: string): Promise<User[]> {
    return request<User[]>(`/users/search?q=${encodeURIComponent(query)}`);
  },

  // Projects
  async listProjects(): Promise<Project[]> {
    return request<Project[]>("/projects");
  },

  async createProject(data: {
    name: string;
    description?: string;
    category?: string;
    domain?: string;
    status?: string;
    start_date?: string;
    expected_completion_date?: string;
    target_handover_date?: string;
    handover_role?: string;
  }): Promise<Project> {
    return request<Project>("/projects", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async getProject(projectId: string): Promise<Project> {
    return request<Project>(`/projects/${projectId}`);
  },

  async updateProject(projectId: string, data: Partial<Project>): Promise<Project> {
    return request<Project>(`/projects/${projectId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  async archiveProject(projectId: string): Promise<Project> {
    return request<Project>(`/projects/${projectId}/archive`, {
      method: "POST",
    });
  },

  async deleteProject(projectId: string): Promise<{ message: string }> {
    return request<{ message: string }>(`/projects/${projectId}`, {
      method: "DELETE",
    });
  },

  // Team Management
  async listMembers(projectId: string): Promise<ProjectMember[]> {
    return request<ProjectMember[]>(`/projects/${projectId}/members`);
  },

  async addMember(projectId: string, email: string, role: string): Promise<ProjectMember> {
    return request<ProjectMember>(`/projects/${projectId}/members`, {
      method: "POST",
      body: JSON.stringify({ email, role }),
    });
  },

  async updateMemberRole(projectId: string, userId: string, role: string): Promise<ProjectMember> {
    return request<ProjectMember>(`/projects/${projectId}/members/${userId}`, {
      method: "PATCH",
      body: JSON.stringify({ role }),
    });
  },

  async removeMember(projectId: string, userId: string): Promise<void> {
    await request(`/projects/${projectId}/members/${userId}`, {
      method: "DELETE",
    });
  },

  // Dashboard
  async getDashboardSummary(): Promise<DashboardSummary> {
    return request<DashboardSummary>("/dashboard/summary");
  },

  async getRecentActivity(): Promise<AuditLogItem[]> {
    return request<AuditLogItem[]>("/dashboard/recent-activity");
  },

  // Documents
  async listDocuments(projectId: string): Promise<DocumentItem[]> {
    return request<DocumentItem[]>(`/documents/${projectId}`);
  },

  async getDocument(documentId: string): Promise<DocumentItem> {
    return request<DocumentItem>(`/documents/detail/${documentId}`);
  },

  async uploadDocuments(projectId: string, files: File[]): Promise<DocumentItem[]> {
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    return request<DocumentItem[]>(`/documents/${projectId}/upload`, {
      method: "POST",
      body: formData,
    });
  },

  async getDocumentContent(documentId: string): Promise<DocumentContent> {
    return request<DocumentContent>(`/documents/${documentId}/content`);
  },

  async getDocumentStatus(documentId: string): Promise<any> {
    return request<any>(`/documents/${documentId}/status`);
  },

  async retryDocument(documentId: string): Promise<DocumentItem> {
    return request<DocumentItem>(`/documents/${documentId}/retry`, {
      method: "POST",
    });
  },

  async getDocumentChunks(projectId: string, documentId: string): Promise<DocumentChunk[]> {
    return request<DocumentChunk[]>(`/documents/${projectId}/${documentId}/chunks`);
  },

  async deleteDocument(projectId: string, documentId: string): Promise<void> {
    await request(`/documents/${documentId}`, {
      method: "DELETE",
    });
  },

  // Knowledge & Findings
  async listFindings(
    projectId: string,
    filters?: { entity_type?: string; verification_status?: string; status?: string; search?: string }
  ): Promise<ExtractedFinding[]> {
    const params = new URLSearchParams();
    if (filters?.entity_type) params.append("entity_type", filters.entity_type);
    if (filters?.verification_status) params.append("verification_status", filters.verification_status);
    if (filters?.status) params.append("status", filters.status);
    if (filters?.search) params.append("search", filters.search);

    const query = params.toString() ? `?${params.toString()}` : "";
    return request<ExtractedFinding[]>(`/knowledge/${projectId}/findings${query}`);
  },

  async createFinding(projectId: string, data: Partial<ExtractedFinding>): Promise<ExtractedFinding> {
    return request<ExtractedFinding>(`/knowledge/${projectId}/findings`, {
      method: "POST",
      body: JSON.stringify({ ...data, project_id: projectId }),
    });
  },

  async updateFinding(projectId: string, findingId: string, data: Partial<ExtractedFinding>): Promise<ExtractedFinding> {
    return request<ExtractedFinding>(`/knowledge/${projectId}/findings/${findingId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  async reVerifyProject(projectId: string): Promise<void> {
    await request(`/knowledge/${projectId}/verify`, { method: "POST" });
  },

  async getTimeline(projectId: string): Promise<any[]> {
    return request<any[]>(`/knowledge/${projectId}/timeline`);
  },

  async getRisksAndDependencies(projectId: string): Promise<{
    risks: any[];
    blockers: any[];
    dependencies: any[];
    questions: any[];
  }> {
    return request(`/knowledge/${projectId}/risks-dependencies`);
  },

  // Phase 4 AI Extraction Pipeline & Knowledge Intelligence Hub
  async triggerExtraction(projectId: string, force_reprocess: boolean = false): Promise<ExtractionJob> {
    return request<ExtractionJob>(`/projects/${projectId}/extractions`, {
      method: "POST",
      body: JSON.stringify({ force_reprocess }),
    });
  },

  async listExtractions(projectId: string): Promise<ExtractionJob[]> {
    return request<ExtractionJob[]>(`/projects/${projectId}/extractions`);
  },

  async getExtraction(extractionId: string): Promise<ExtractionJob> {
    return request<ExtractionJob>(`/extractions/${extractionId}`);
  },

  async getExtractionStatus(extractionId: string): Promise<ExtractionJob> {
    return request<ExtractionJob>(`/extractions/${extractionId}/status`);
  },

  async retryExtraction(extractionId: string): Promise<ExtractionJob> {
    return request<ExtractionJob>(`/extractions/${extractionId}/retry`, {
      method: "POST",
    });
  },

  async getProjectKnowledge(projectId: string): Promise<{
    summary: ProjectKnowledgeSummary;
    findings: ExtractedFinding[];
    conflicts: KnowledgeConflict[];
  }> {
    return request(`/projects/${projectId}/knowledge`);
  },

  async getDecisions(projectId: string, search?: string): Promise<ExtractedFinding[]> {
    const q = search ? `?search=${encodeURIComponent(search)}` : "";
    return request<ExtractedFinding[]>(`/projects/${projectId}/decisions${q}`);
  },

  async getTasks(
    projectId: string,
    filters?: { task_status?: string; owner?: string; priority?: string; search?: string }
  ): Promise<ExtractedFinding[]> {
    const params = new URLSearchParams();
    if (filters?.task_status) params.append("task_status", filters.task_status);
    if (filters?.owner) params.append("owner", filters.owner);
    if (filters?.priority) params.append("priority", filters.priority);
    if (filters?.search) params.append("search", filters.search);
    const q = params.toString() ? `?${params.toString()}` : "";
    return request<ExtractedFinding[]>(`/projects/${projectId}/tasks${q}`);
  },

  async getRisks(projectId: string, priority?: string): Promise<ExtractedFinding[]> {
    const q = priority ? `?priority=${encodeURIComponent(priority)}` : "";
    return request<ExtractedFinding[]>(`/projects/${projectId}/risks${q}`);
  },

  async getBlockers(projectId: string): Promise<ExtractedFinding[]> {
    return request<ExtractedFinding[]>(`/projects/${projectId}/blockers`);
  },

  async getDependencies(projectId: string): Promise<ExtractedFinding[]> {
    return request<ExtractedFinding[]>(`/projects/${projectId}/dependencies`);
  },

  async getQuestions(projectId: string): Promise<ExtractedFinding[]> {
    return request<ExtractedFinding[]>(`/projects/${projectId}/questions`);
  },

  async getConflicts(
    projectId: string,
    filters?: { conflict_status?: string; severity?: string; conflict_type?: string }
  ): Promise<KnowledgeConflict[]> {
    const params = new URLSearchParams();
    if (filters?.conflict_status) params.append("conflict_status", filters.conflict_status);
    if (filters?.severity) params.append("severity", filters.severity);
    if (filters?.conflict_type) params.append("conflict_type", filters.conflict_type);
    const q = params.toString() ? `?${params.toString()}` : "";
    return request<KnowledgeConflict[]>(`/projects/${projectId}/conflicts${q}`);
  },

  async getConflictDetail(conflictId: string): Promise<ConflictDetail> {
    return request<ConflictDetail>(`/conflicts/${conflictId}`);
  },

  async reviewConflict(conflictId: string, notes?: string): Promise<KnowledgeConflict> {
    return request<KnowledgeConflict>(`/conflicts/${conflictId}/review`, {
      method: "POST",
      body: JSON.stringify({ notes }),
    });
  },

  async resolveConflict(
    conflictId: string,
    resolution_choice: string,
    resolution_notes: string
  ): Promise<KnowledgeConflict> {
    return request<KnowledgeConflict>(`/conflicts/${conflictId}/resolve`, {
      method: "POST",
      body: JSON.stringify({ resolution_choice, resolution_notes }),
    });
  },

  async dismissConflict(conflictId: string, resolution_notes: string): Promise<KnowledgeConflict> {
    return request<KnowledgeConflict>(`/conflicts/${conflictId}/dismiss`, {
      method: "POST",
      body: JSON.stringify({ resolution_notes }),
    });
  },

  async getConflictHistory(conflictId: string): Promise<{ conflict_id: string; history: ConflictHistoryItem[] }> {
    return request<{ conflict_id: string; history: ConflictHistoryItem[] }>(`/conflicts/${conflictId}/history`);
  },

  // Phase 6 Evidence Verification & Quality Endpoints
  async getEvidenceSummary(projectId: string): Promise<EvidenceSummary> {
    return request<EvidenceSummary>(`/projects/${projectId}/evidence/summary`);
  },

  async listProjectEvidence(
    projectId: string,
    filters?: { verification_status?: string; document_id?: string; limit?: number; offset?: number }
  ): Promise<EvidenceReference[]> {
    const params = new URLSearchParams();
    if (filters?.verification_status) params.append("verification_status", filters.verification_status);
    if (filters?.document_id) params.append("document_id", filters.document_id);
    if (filters?.limit) params.append("limit", filters.limit.toString());
    if (filters?.offset) params.append("offset", filters.offset.toString());
    const q = params.toString() ? `?${params.toString()}` : "";
    return request<EvidenceReference[]>(`/projects/${projectId}/evidence${q}`);
  },

  async getEvidenceDetail(evidenceId: string): Promise<EvidenceDetailItem> {
    return request<EvidenceDetailItem>(`/evidence/${evidenceId}`);
  },

  async verifyEvidence(evidenceId: string): Promise<any> {
    return request<any>(`/evidence/${evidenceId}/verify`, { method: "POST" });
  },

  async getFindingEvidence(findingId: string): Promise<FindingEvidenceDetail> {
    return request<FindingEvidenceDetail>(`/knowledge/${findingId}/evidence`);
  },

  // Phase 5 Project Knowledge Reconstruction & Intelligence APIs
  async getProjectState(projectId: string): Promise<ProjectStateResponse> {
    return request<ProjectStateResponse>(`/projects/${projectId}/state`);
  },

  async reconstructProject(projectId: string, force: boolean = false): Promise<ProjectStateResponse> {
    return request<ProjectStateResponse>(`/projects/${projectId}/knowledge/reconstruct`, {
      method: "POST",
      body: JSON.stringify({ force }),
    });
  },

  async getDecisionTimeline(projectId: string, search?: string): Promise<DecisionTimelineResponse> {
    const q = search ? `?search=${encodeURIComponent(search)}` : "";
    return request<DecisionTimelineResponse>(`/projects/${projectId}/timeline${q}`);
  },

  async getTaskTimeline(
    projectId: string,
    filters?: { status?: string; owner?: string }
  ): Promise<TaskTimelineResponse> {
    const params = new URLSearchParams();
    if (filters?.status) params.append("status", filters.status);
    if (filters?.owner) params.append("owner", filters.owner);
    const q = params.toString() ? `?${params.toString()}` : "";
    return request<TaskTimelineResponse>(`/projects/${projectId}/tasks/timeline${q}`);
  },

  async getDependencyGraph(projectId: string): Promise<DependencyGraphResponse> {
    return request<DependencyGraphResponse>(`/projects/${projectId}/dependencies/graph`);
  },

  async getResponsibilities(projectId: string): Promise<ResponsibilitiesResponse> {
    return request<ResponsibilitiesResponse>(`/projects/${projectId}/responsibilities`);
  },

  async getRiskRegister(projectId: string): Promise<RiskRegisterResponse> {
    return request<RiskRegisterResponse>(`/projects/${projectId}/risk-register`);
  },

  async searchKnowledge(
    projectId: string,
    query: string,
    entity_type?: string
  ): Promise<KnowledgeSearchResponse> {
    const params = new URLSearchParams({ q: query });
    if (entity_type && entity_type !== "ALL") params.append("entity_type", entity_type);
    return request<KnowledgeSearchResponse>(`/projects/${projectId}/knowledge/search?${params.toString()}`);
  },

  // Review
  async getReviewQueue(projectId: string): Promise<ExtractedFinding[]> {
    return request<ExtractedFinding[]>(`/review/${projectId}/queue`);
  },

  async submitReview(
    projectId: string,
    findingId: string,
    data: {
      action: "APPROVE" | "REJECT" | "EDIT" | "FLAG_INVESTIGATION";
      comment?: string;
      updated_title?: string;
      updated_description?: string;
      updated_owner?: string;
      updated_deadline?: string;
    }
  ): Promise<ReviewLog> {
    return request<ReviewLog>(`/review/${projectId}/findings/${findingId}`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async getReviewHistory(projectId: string): Promise<ReviewLog[]> {
    return request<ReviewLog[]>(`/review/${projectId}/history`);
  },

  // Handover
  async generateHandover(projectId: string, target_role?: string, custom_notes?: string): Promise<HandoverDossier> {
    return request<HandoverDossier>(`/handovers/${projectId}/generate`, {
      method: "POST",
      body: JSON.stringify({ project_id: projectId, target_role, custom_notes }),
    });
  },

  async listHandovers(projectId: string): Promise<HandoverDossier[]> {
    return request<HandoverDossier[]>(`/handovers/${projectId}`);
  },

  async getHandover(projectId: string, handoverId: string): Promise<HandoverDossier> {
    return request<HandoverDossier>(`/handovers/${projectId}/${handoverId}`);
  },

  async approveHandover(projectId: string, handoverId: string): Promise<HandoverDossier> {
    return request<HandoverDossier>(`/handovers/${projectId}/${handoverId}/approve`, {
      method: "POST",
    });
  },

  getPdfDownloadUrl(projectId: string, handoverId: string): string {
    const token = getToken();
    return `${API_BASE}/handovers/${projectId}/${handoverId}/export-pdf?token=${token || ""}`;
  },

  // Legacy Dashboard & Analytics stats
  async getDashboardStats(): Promise<DashboardStats> {
    return request<DashboardStats>("/analytics/dashboard");
  },

  // Audit
  async getProjectAuditLogs(projectId: string): Promise<AuditLogItem[]> {
    return request<AuditLogItem[]>(`/audit/${projectId}`);
  },
};
