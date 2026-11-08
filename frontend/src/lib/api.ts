import {
  User,
  Project,
  ProjectMember,
  DocumentItem,
  DocumentChunk,
  ExtractedFinding,
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

  async uploadDocuments(projectId: string, files: File[]): Promise<DocumentItem[]> {
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    return request<DocumentItem[]>(`/documents/${projectId}/upload`, {
      method: "POST",
      body: formData,
    });
  },

  async getDocumentChunks(projectId: string, documentId: string): Promise<DocumentChunk[]> {
    return request<DocumentChunk[]>(`/documents/${projectId}/${documentId}/chunks`);
  },

  async deleteDocument(projectId: string, documentId: string): Promise<void> {
    await request(`/documents/${projectId}/${documentId}`, {
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
