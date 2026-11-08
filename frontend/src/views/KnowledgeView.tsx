"use client";

import React, { useEffect, useState } from "react";
import {
  BrainCircuit,
  Search,
  Filter,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  FileText,
  User,
  Calendar,
  Sparkles,
  RefreshCw,
  CheckSquare,
  Bookmark,
  ShieldAlert,
  GitCompare,
  Layers,
  HelpCircle,
  ArrowRight,
  Clock,
  Play,
  RotateCcw,
  CheckCircle,
} from "lucide-react";
import {
  ExtractedFinding,
  EntityType,
  VerificationStatus,
  ExtractionJob,
  KnowledgeConflict,
  ProjectKnowledgeSummary,
} from "@/lib/types";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { EvidenceModal } from "@/components/EvidenceModal";
import { ReviewModal } from "@/components/ReviewModal";

export function KnowledgeView() {
  const { currentProject, user } = useAuth();
  const [findings, setFindings] = useState<ExtractedFinding[]>([]);
  const [conflicts, setConflicts] = useState<KnowledgeConflict[]>([]);
  const [summary, setSummary] = useState<ProjectKnowledgeSummary | null>(null);
  const [latestJob, setLatestJob] = useState<ExtractionJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [extracting, setExtracting] = useState(false);
  const [search, setSearch] = useState("");
  const [activeTab, setActiveTab] = useState<
    "ALL" | "DECISIONS" | "TASKS" | "RISKS_BLOCKERS" | "DEPENDENCIES" | "QUESTIONS" | "CONFLICTS"
  >("ALL");
  const [taskStatusFilter, setTaskStatusFilter] = useState<string>("ALL");
  const [selectedVerif, setSelectedVerif] = useState<string>("ALL");
  const [isReverifying, setIsReverifying] = useState(false);

  // Inspector & Review Modals
  const [inspectFinding, setInspectFinding] = useState<ExtractedFinding | null>(null);
  const [reviewFinding, setReviewFinding] = useState<ExtractedFinding | null>(null);

  const canEdit = user?.role === "ADMIN" || user?.role === "PROJECT_MANAGER" || user?.role === "OUTGOING_MEMBER";
  const canReview = user?.role === "ADMIN" || user?.role === "PROJECT_MANAGER";

  async function loadData() {
    if (!currentProject) return;
    setLoading(true);
    try {
      // 1. Load Knowledge Hub
      const knowledgeData = await api.getProjectKnowledge(currentProject.id);
      setFindings(knowledgeData.findings || []);
      setConflicts(knowledgeData.conflicts || []);
      setSummary(knowledgeData.summary || null);

      // 2. Load latest extraction job
      const jobs = await api.listExtractions(currentProject.id);
      if (jobs && jobs.length > 0) {
        setLatestJob(jobs[0]);
      }
    } catch (e) {
      console.warn("Failed to load project knowledge hub:", e);
      // Fallback to basic listFindings
      try {
        const fallbackFindings = await api.listFindings(currentProject.id);
        setFindings(fallbackFindings);
      } catch (err) {
        console.error("Fallback findings failed:", err);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, [currentProject]);

  async function handleTriggerExtraction(force: boolean = false) {
    if (!currentProject) return;
    setExtracting(true);
    try {
      const job = await api.triggerExtraction(currentProject.id, force);
      setLatestJob(job);
      await loadData();
    } catch (err) {
      console.error("Extraction job trigger failed:", err);
    } finally {
      setExtracting(false);
    }
  }

  async function handleRetryJob(jobId: string) {
    setExtracting(true);
    try {
      const job = await api.retryExtraction(jobId);
      setLatestJob(job);
      await loadData();
    } catch (err) {
      console.error("Retry extraction failed:", err);
    } finally {
      setExtracting(false);
    }
  }

  async function handleReverify() {
    if (!currentProject) return;
    setIsReverifying(true);
    try {
      await api.reVerifyProject(currentProject.id);
      await loadData();
    } finally {
      setIsReverifying(false);
    }
  }

  async function handleReviewSubmit(findingId: string, reviewData: any) {
    if (!currentProject) return;
    await api.submitReview(currentProject.id, findingId, reviewData);
    await loadData();
  }

  // Filter findings based on active tab and search/verification filters
  const filteredFindings = findings.filter((f) => {
    // 1. Tab filter
    if (activeTab === "DECISIONS" && f.entity_type !== "DECISION") return false;
    if (activeTab === "TASKS" && f.entity_type !== "TASK") return false;
    if (activeTab === "RISKS_BLOCKERS" && f.entity_type !== "RISK" && f.entity_type !== "BLOCKER") return false;
    if (activeTab === "DEPENDENCIES" && f.entity_type !== "DEPENDENCY") return false;
    if (activeTab === "QUESTIONS" && f.entity_type !== "QUESTION") return false;

    // 2. Task status filter (when in TASKS tab)
    if (activeTab === "TASKS" && taskStatusFilter !== "ALL") {
      if ((f.task_status || "").toUpperCase() !== taskStatusFilter.toUpperCase()) return false;
    }

    // 3. Verification filter
    if (selectedVerif !== "ALL") {
      if (selectedVerif === "CONFLICTED") {
        if (f.verification_status !== "CONFLICTED" && f.verification_status !== "CONFLICTING") return false;
      } else if (f.verification_status !== selectedVerif) {
        return false;
      }
    }

    // 4. Search query
    if (search.trim()) {
      const q = search.toLowerCase();
      const matchTitle = f.title.toLowerCase().includes(q);
      const matchDesc = f.description.toLowerCase().includes(q);
      const matchOwner = (f.owner || "").toLowerCase().includes(q);
      const matchQuote = (f.supporting_quotation || "").toLowerCase().includes(q);
      if (!matchTitle && !matchDesc && !matchOwner && !matchQuote) return false;
    }

    return true;
  });

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* 1. Extraction Intelligence Header & Controls */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <BrainCircuit className="w-6 h-6 text-teal-600" />
              <h2 className="text-xl font-bold text-slate-900">AI Knowledge Extraction & Intelligence Engine</h2>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Extracts decisions, tasks, dependencies, risks, and contradictions from project documents with verifiable source quotations.
            </p>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            {canReview && (
              <button
                onClick={handleReverify}
                disabled={isReverifying}
                className="flex items-center gap-1.5 px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isReverifying ? "animate-spin text-teal-600" : ""}`} />
                Re-Verify Evidence
              </button>
            )}

            {canEdit && (
              <button
                onClick={() => handleTriggerExtraction(true)}
                disabled={extracting}
                className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold rounded-lg shadow-xs transition"
              >
                <Sparkles className={`w-4 h-4 ${extracting ? "animate-spin" : ""}`} />
                {extracting ? "Running AI Extraction..." : "Trigger AI Extraction"}
              </button>
            )}
          </div>
        </div>

        {/* Extraction Job Status Bar */}
        {latestJob && (
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200/80 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="font-semibold text-slate-700 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                Latest Extraction:
              </span>
              <span
                className={`px-2 py-0.5 rounded-full font-bold uppercase text-[10px] tracking-wider ${
                  latestJob.status === "COMPLETED"
                    ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                    : latestJob.status === "PROCESSING"
                    ? "bg-blue-100 text-blue-800 border border-blue-300 animate-pulse"
                    : latestJob.status === "FAILED"
                    ? "bg-rose-100 text-rose-800 border border-rose-300"
                    : "bg-slate-200 text-slate-800"
                }`}
              >
                {latestJob.status}
              </span>
              <span className="text-slate-500">
                Docs: <strong>{latestJob.processed_documents_count}</strong> • Chunks:{" "}
                <strong>{latestJob.processed_chunks_count}</strong> • Findings:{" "}
                <strong className="text-teal-700">{latestJob.extracted_findings_count}</strong> • Conflicts:{" "}
                <strong className="text-amber-700">{latestJob.conflicts_count}</strong> • Unsupported:{" "}
                <strong className="text-rose-700">{latestJob.unsupported_count}</strong>
              </span>
            </div>

            {latestJob.status === "FAILED" && canEdit && (
              <button
                onClick={() => handleRetryJob(latestJob.id)}
                className="flex items-center gap-1 text-rose-700 hover:text-rose-800 font-semibold"
              >
                <RotateCcw className="w-3.5 h-3.5" /> Retry Failed Job
              </button>
            )}
          </div>
        )}
      </div>

      {/* 2. Knowledge Metrics KPI Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Total Findings</div>
          <div className="text-2xl font-bold text-slate-900 mt-1">{summary ? summary.total_findings : findings.length}</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Decisions</div>
          <div className="text-2xl font-bold text-teal-700 mt-1">
            {summary ? summary.decisions_count : findings.filter((f) => f.entity_type === "DECISION").length}
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Active Tasks</div>
          <div className="text-2xl font-bold text-blue-700 mt-1">
            {summary ? summary.tasks_count : findings.filter((f) => f.entity_type === "TASK").length}
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Risks & Blockers</div>
          <div className="text-2xl font-bold text-rose-700 mt-1">
            {summary
              ? summary.risks_count + summary.blockers_count
              : findings.filter((f) => f.entity_type === "RISK" || f.entity_type === "BLOCKER").length}
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Contradictions</div>
          <div className="text-2xl font-bold text-amber-700 mt-1">{conflicts.length}</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Verified Evidence</div>
          <div className="text-2xl font-bold text-emerald-700 mt-1">
            {summary ? `${summary.verified_percentage}%` : "100%"}
          </div>
        </div>
      </div>

      {/* 3. Tabbed Navigation & Filter Controls */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-3">
        {/* Main Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs border-b border-slate-100">
          <button
            onClick={() => setActiveTab("ALL")}
            className={`px-3.5 py-2 rounded-lg font-semibold transition whitespace-nowrap flex items-center gap-1.5 ${
              activeTab === "ALL" ? "bg-slate-900 text-white shadow-xs" : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            All Findings ({findings.length})
          </button>

          <button
            onClick={() => setActiveTab("DECISIONS")}
            className={`px-3.5 py-2 rounded-lg font-semibold transition whitespace-nowrap flex items-center gap-1.5 ${
              activeTab === "DECISIONS" ? "bg-slate-900 text-white shadow-xs" : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            Decisions ({findings.filter((f) => f.entity_type === "DECISION").length})
          </button>

          <button
            onClick={() => setActiveTab("TASKS")}
            className={`px-3.5 py-2 rounded-lg font-semibold transition whitespace-nowrap flex items-center gap-1.5 ${
              activeTab === "TASKS" ? "bg-slate-900 text-white shadow-xs" : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            Tasks ({findings.filter((f) => f.entity_type === "TASK").length})
          </button>

          <button
            onClick={() => setActiveTab("RISKS_BLOCKERS")}
            className={`px-3.5 py-2 rounded-lg font-semibold transition whitespace-nowrap flex items-center gap-1.5 ${
              activeTab === "RISKS_BLOCKERS" ? "bg-slate-900 text-white shadow-xs" : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            Risks & Blockers (
            {findings.filter((f) => f.entity_type === "RISK" || f.entity_type === "BLOCKER").length})
          </button>

          <button
            onClick={() => setActiveTab("DEPENDENCIES")}
            className={`px-3.5 py-2 rounded-lg font-semibold transition whitespace-nowrap flex items-center gap-1.5 ${
              activeTab === "DEPENDENCIES" ? "bg-slate-900 text-white shadow-xs" : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            Dependencies ({findings.filter((f) => f.entity_type === "DEPENDENCY").length})
          </button>

          <button
            onClick={() => setActiveTab("QUESTIONS")}
            className={`px-3.5 py-2 rounded-lg font-semibold transition whitespace-nowrap flex items-center gap-1.5 ${
              activeTab === "QUESTIONS" ? "bg-slate-900 text-white shadow-xs" : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            Questions ({findings.filter((f) => f.entity_type === "QUESTION").length})
          </button>

          <button
            onClick={() => setActiveTab("CONFLICTS")}
            className={`px-3.5 py-2 rounded-lg font-semibold transition whitespace-nowrap flex items-center gap-1.5 ${
              activeTab === "CONFLICTS"
                ? "bg-amber-600 text-white shadow-xs"
                : "text-amber-800 bg-amber-50 hover:bg-amber-100"
            }`}
          >
            <GitCompare className="w-3.5 h-3.5" />
            Contradictions ({conflicts.length})
          </button>
        </div>

        {/* Sub-filters & Search Bar */}
        <div className="flex flex-col sm:flex-row gap-3 items-center justify-between pt-1">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search findings, owners, quotations..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full text-xs pl-9 pr-3 py-2 border border-slate-300 rounded-lg focus:outline-teal-600"
            />
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto flex-wrap">
            {activeTab === "TASKS" && (
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-slate-500 font-semibold">Task Status:</span>
                <select
                  value={taskStatusFilter}
                  onChange={(e) => setTaskStatusFilter(e.target.value)}
                  className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white text-slate-700"
                >
                  <option value="ALL">All Statuses</option>
                  <option value="COMPLETED">Completed</option>
                  <option value="IN_PROGRESS">In Progress</option>
                  <option value="BLOCKED">Blocked</option>
                  <option value="NOT_STARTED">Not Started</option>
                </select>
              </div>
            )}

            {activeTab !== "CONFLICTS" && (
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-slate-500 font-semibold">Evidence:</span>
                <select
                  value={selectedVerif}
                  onChange={(e) => setSelectedVerif(e.target.value)}
                  className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white text-slate-700"
                >
                  <option value="ALL">All Evidence</option>
                  <option value="VERIFIED">Verified Only</option>
                  <option value="CONFLICTED">Conflicting Only</option>
                  <option value="UNSUPPORTED">Unsupported Only</option>
                </select>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 4. Main Body: Findings or Conflicts View */}
      {loading ? (
        <div className="p-16 text-center text-xs text-slate-500">Retrieving project knowledge...</div>
      ) : activeTab === "CONFLICTS" ? (
        /* Contradiction Resolver View */
        <div className="space-y-4">
          {conflicts.length === 0 ? (
            <div className="bg-white p-16 rounded-xl border border-slate-200 text-center space-y-2">
              <CheckCircle className="w-10 h-10 text-emerald-500 mx-auto" />
              <h3 className="text-sm font-semibold text-slate-800">No Contradictions Detected</h3>
              <p className="text-xs text-slate-500">
                All statements across project documents agree on task statuses, ownership, and delivery dates.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 flex items-start gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-bold text-amber-950">Detected Cross-Document Inconsistencies</h4>
                  <p className="mt-0.5 text-amber-800">
                    The platform has identified conflicting facts between multiple source documents. Both versions are
                    preserved with original citations for human review.
                  </p>
                </div>
              </div>

              {conflicts.map((c) => (
                <div
                  key={c.id}
                  className="bg-white rounded-xl border border-amber-200 p-6 shadow-2xs space-y-4"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-300">
                      Conflict Type: {c.conflict_type}
                    </span>
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                      Status: {c.status}
                    </span>
                  </div>

                  <h3 className="text-sm font-bold text-slate-900">{c.description}</h3>

                  {/* Side-by-Side Source Comparison */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Source 1 */}
                    <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2">
                      <div className="flex items-center justify-between text-xs text-slate-600 font-semibold pb-1.5 border-b border-slate-200">
                        <span className="flex items-center gap-1">
                          <FileText className="w-3.5 h-3.5 text-teal-600" />
                          {c.source_1_doc_filename || "Document 1"}
                        </span>
                        <span className="bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-700">
                          Page {c.source_1_page || 1}
                        </span>
                      </div>
                      <blockquote className="text-xs italic text-slate-800 bg-white p-3 rounded-lg border border-slate-200">
                        &ldquo;{c.source_1_quote || "Quotation unavailable"}&rdquo;
                      </blockquote>
                    </div>

                    {/* Source 2 */}
                    <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2">
                      <div className="flex items-center justify-between text-xs text-slate-600 font-semibold pb-1.5 border-b border-slate-200">
                        <span className="flex items-center gap-1">
                          <FileText className="w-3.5 h-3.5 text-teal-600" />
                          {c.source_2_doc_filename || "Document 2"}
                        </span>
                        <span className="bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-700">
                          Page {c.source_2_page || 1}
                        </span>
                      </div>
                      <blockquote className="text-xs italic text-slate-800 bg-white p-3 rounded-lg border border-slate-200">
                        &ldquo;{c.source_2_quote || "Quotation unavailable"}&rdquo;
                      </blockquote>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : filteredFindings.length === 0 ? (
        <div className="bg-white p-16 rounded-xl border border-slate-200 text-center space-y-2">
          <BrainCircuit className="w-10 h-10 text-slate-300 mx-auto" />
          <h3 className="text-sm font-semibold text-slate-700">No findings matched criteria</h3>
          <p className="text-xs text-slate-500">Try adjusting your filters or search keywords.</p>
        </div>
      ) : (
        /* Findings Grid */
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredFindings.map((f) => {
            const isVerified = f.verification_status === "VERIFIED";
            const isConflicting =
              f.verification_status === "CONFLICTED" || f.verification_status === "CONFLICTING";
            const flags = f.flags || {};

            return (
              <div
                key={f.id}
                className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs hover:shadow-xs transition space-y-3 flex flex-col justify-between"
              >
                <div className="space-y-2.5">
                  {/* Top tags */}
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-teal-50 text-teal-700 border border-teal-200">
                      {f.entity_type}
                    </span>

                    <div className="flex items-center gap-1.5">
                      {isVerified ? (
                        <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                          <CheckCircle2 className="w-3 h-3" /> Verified
                        </span>
                      ) : isConflicting ? (
                        <span className="flex items-center gap-1 text-[11px] font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                          <AlertTriangle className="w-3 h-3" /> Conflicted
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-[11px] font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                          <XCircle className="w-3 h-3" /> Unsupported
                        </span>
                      )}

                      {f.task_status && (
                        <span
                          className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                            f.task_status === "COMPLETED"
                              ? "bg-emerald-100 text-emerald-800"
                              : f.task_status === "BLOCKED"
                              ? "bg-rose-100 text-rose-800"
                              : f.task_status === "IN_PROGRESS"
                              ? "bg-blue-100 text-blue-800"
                              : "bg-slate-100 text-slate-700"
                          }`}
                        >
                          {f.task_status}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Title & Description */}
                  <div>
                    <h3 className="text-sm font-bold text-slate-900 leading-snug">{f.title}</h3>
                    <p className="text-xs text-slate-600 mt-1 line-clamp-3">{f.description}</p>
                  </div>

                  {/* Conflict Notice if any */}
                  {flags.has_conflict && flags.conflict_reason && (
                    <div className="p-2 bg-amber-50 border border-amber-200 rounded text-[11px] text-amber-800 flex items-start gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
                      <span>{flags.conflict_reason}</span>
                    </div>
                  )}

                  {/* Metadata Row */}
                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-100 text-[11px] text-slate-600">
                    <div className="flex items-center gap-1 truncate">
                      <User className="w-3 h-3 text-slate-400 shrink-0" />
                      <span className="truncate">
                        Owner: <strong className="text-slate-800">{f.owner || "Unassigned"}</strong>
                      </span>
                    </div>
                    <div className="flex items-center gap-1 truncate">
                      <Calendar className="w-3 h-3 text-slate-400 shrink-0" />
                      <span className="truncate">
                        Deadline: <strong className="text-slate-800">{f.deadline || "None"}</strong>
                      </span>
                    </div>
                  </div>

                  {/* Quote preview */}
                  <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100 text-xs italic text-slate-700 line-clamp-2">
                    &ldquo;{f.supporting_quotation}&rdquo;
                  </div>
                </div>

                {/* Footer Actions */}
                <div className="flex items-center justify-between pt-3 border-t border-slate-100 text-xs">
                  <span className="text-[11px] text-slate-500 flex items-center gap-1">
                    <FileText className="w-3 h-3 text-slate-400" />
                    p.{f.page_number || 1} • {f.document_filename || "Source"}
                  </span>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setInspectFinding(f)}
                      className="flex items-center gap-1 px-2.5 py-1 text-teal-700 bg-teal-50 hover:bg-teal-100 font-semibold rounded text-xs transition"
                    >
                      <Bookmark className="w-3 h-3" />
                      Inspect Evidence
                    </button>

                    {canReview && (
                      <button
                        onClick={() => setReviewFinding(f)}
                        className="flex items-center gap-1 px-2 py-1 text-slate-700 hover:bg-slate-100 font-semibold rounded text-xs transition"
                      >
                        <CheckSquare className="w-3 h-3 text-slate-500" />
                        Review
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Evidence Inspector Modal */}
      {inspectFinding && (
        <EvidenceModal
          finding={inspectFinding}
          onClose={() => setInspectFinding(null)}
        />
      )}

      {/* Human Review Modal */}
      {reviewFinding && currentProject && (
        <ReviewModal
          finding={reviewFinding}
          projectId={currentProject.id}
          onClose={() => setReviewFinding(null)}
          onSubmit={handleReviewSubmit}
        />
      )}
    </div>
  );
}
