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
  AlertOctagon,
  UserX,
  CalendarX,
  Share2,
  ListOrdered,
  Users,
  ShieldCheck,
  ChevronRight,
  ExternalLink,
  Info,
  Scale,
  History,
  FileCheck,
  Check,
} from "lucide-react";
import {
  ExtractedFinding,
  EntityType,
  VerificationStatus,
  ExtractionJob,
  KnowledgeConflict,
  EvidenceSummary,
  ConflictStatus,
  ConflictSeverity,
  ResolutionChoice,
  ConflictHistoryItem,
  ProjectStateResponse,
  DecisionTimelineResponse,
  DecisionTimelineEvent,
  TaskTimelineResponse,
  TaskTimelineItem,
  DependencyGraphResponse,
  ResponsibilitiesResponse,
  RiskRegisterResponse,
  KnowledgeSearchResponse,
} from "@/lib/types";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { EvidenceModal } from "@/components/EvidenceModal";
import { ReviewModal } from "@/components/ReviewModal";

export function KnowledgeView() {
  const { currentProject, user } = useAuth();

  // Tab navigation
  const [activeTab, setActiveTab] = useState<
    "STATE_OVERVIEW" | "DECISIONS" | "TASKS" | "DEPENDENCIES" | "RESPONSIBILITIES" | "RISKS" | "CONFLICTS" | "EVIDENCE_QUALITY"
  >("STATE_OVERVIEW");

  // Reconstructed State & Knowledge Data
  const [projectState, setProjectState] = useState<ProjectStateResponse | null>(null);
  const [decisionTimeline, setDecisionTimeline] = useState<DecisionTimelineResponse | null>(null);
  const [taskTimeline, setTaskTimeline] = useState<TaskTimelineResponse | null>(null);
  const [depGraph, setDepGraph] = useState<DependencyGraphResponse | null>(null);
  const [responsibilities, setResponsibilities] = useState<ResponsibilitiesResponse | null>(null);
  const [riskRegister, setRiskRegister] = useState<RiskRegisterResponse | null>(null);
  const [conflicts, setConflicts] = useState<KnowledgeConflict[]>([]);
  const [evidenceSummary, setEvidenceSummary] = useState<EvidenceSummary | null>(null);
  const [latestJob, setLatestJob] = useState<ExtractionJob | null>(null);

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<KnowledgeSearchResponse | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [taskStatusFilter, setTaskStatusFilter] = useState("ALL");
  const [conflictStatusFilter, setConflictStatusFilter] = useState("ALL");
  const [conflictSeverityFilter, setConflictSeverityFilter] = useState("ALL");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Conflict Resolution & Audit States
  const [resolvingConflict, setResolvingConflict] = useState<KnowledgeConflict | null>(null);
  const [resolutionChoice, setResolutionChoice] = useState<ResolutionChoice>("CLAIM_A_SUPPORTED");
  const [resolutionNotes, setResolutionNotes] = useState("");
  const [dismissingConflict, setDismissingConflict] = useState<KnowledgeConflict | null>(null);
  const [dismissalNotes, setDismissalNotes] = useState("");
  const [viewingHistoryConflict, setViewingHistoryConflict] = useState<KnowledgeConflict | null>(null);
  const [conflictHistory, setConflictHistory] = useState<ConflictHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  // Loading & Action states
  const [loading, setLoading] = useState(true);
  const [reconstructing, setReconstructing] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [isReverifying, setIsReverifying] = useState(false);

  // Inspector & Review Modals
  const [inspectFinding, setInspectFinding] = useState<ExtractedFinding | null>(null);
  const [reviewFinding, setReviewFinding] = useState<ExtractedFinding | null>(null);

  const canEdit = user?.role === "ADMIN" || user?.role === "PROJECT_MANAGER" || user?.role === "OUTGOING_MEMBER";
  const canReview = user?.role === "ADMIN" || user?.role === "PROJECT_MANAGER";

  async function loadAllReconstructedData() {
    if (!currentProject) return;
    setLoading(true);
    try {
      // 1. Fetch State Overview
      const state = await api.getProjectState(currentProject.id);
      setProjectState(state);

      // 2. Fetch Decision Timeline
      const decisions = await api.getDecisionTimeline(currentProject.id);
      setDecisionTimeline(decisions);

      // 3. Fetch Task Timeline
      const tasks = await api.getTaskTimeline(currentProject.id);
      setTaskTimeline(tasks);

      // 4. Fetch Dependency Graph
      const graph = await api.getDependencyGraph(currentProject.id);
      setDepGraph(graph);

      // 5. Fetch Responsibilities
      const resps = await api.getResponsibilities(currentProject.id);
      setResponsibilities(resps);

      // 6. Fetch Risk Register
      const risks = await api.getRiskRegister(currentProject.id);
      setRiskRegister(risks);

      // 7. Fetch Conflicts
      const confs = await api.getConflicts(currentProject.id);
      setConflicts(confs);

      // 8. Fetch Evidence Summary
      try {
        const evSum = await api.getEvidenceSummary(currentProject.id);
        setEvidenceSummary(evSum);
      } catch (err) {
        console.warn("Could not load evidence summary:", err);
      }

      // 9. Fetch latest extraction job
      const jobs = await api.listExtractions(currentProject.id);
      if (jobs && jobs.length > 0) {
        setLatestJob(jobs[0]);
      }
    } catch (e) {
      console.warn("Failed loading full project knowledge reconstruction:", e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAllReconstructedData();
  }, [currentProject]);

  async function handleReconstruct() {
    if (!currentProject) return;
    setReconstructing(true);
    try {
      const updated = await api.reconstructProject(currentProject.id, true);
      setProjectState(updated);
      await loadAllReconstructedData();
    } catch (err) {
      console.error("Reconstruction failed:", err);
    } finally {
      setReconstructing(false);
    }
  }

  async function handleTriggerExtraction() {
    if (!currentProject) return;
    setExtracting(true);
    try {
      const job = await api.triggerExtraction(currentProject.id, true);
      setLatestJob(job);
      await handleReconstruct();
    } catch (err) {
      console.error("Extraction trigger failed:", err);
    } finally {
      setExtracting(false);
    }
  }

  async function handleReverify() {
    if (!currentProject) return;
    setIsReverifying(true);
    try {
      await api.reVerifyProject(currentProject.id);
      await handleReconstruct();
    } finally {
      setIsReverifying(false);
    }
  }

  async function handleStartReview(conflictId: string) {
    if (!currentProject) return;
    setActionLoading(true);
    try {
      await api.reviewConflict(conflictId);
      await loadAllReconstructedData();
    } catch (e) {
      console.error("Failed to start review:", e);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleApplyResolution() {
    if (!resolvingConflict || !resolutionNotes.trim()) return;
    setActionLoading(true);
    try {
      await api.resolveConflict(resolvingConflict.id, resolutionChoice, resolutionNotes.trim());
      setResolvingConflict(null);
      setResolutionNotes("");
      await loadAllReconstructedData();
    } catch (e) {
      console.error("Failed to resolve conflict:", e);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleApplyDismissal() {
    if (!dismissingConflict || !dismissalNotes.trim()) return;
    setActionLoading(true);
    try {
      await api.dismissConflict(dismissingConflict.id, dismissalNotes.trim());
      setDismissingConflict(null);
      setDismissalNotes("");
      await loadAllReconstructedData();
    } catch (e) {
      console.error("Failed to dismiss conflict:", e);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleOpenHistory(conflict: KnowledgeConflict) {
    setViewingHistoryConflict(conflict);
    setHistoryLoading(true);
    try {
      const res = await api.getConflictHistory(conflict.id);
      setConflictHistory(res.history || []);
    } catch (e) {
      console.error("Failed loading conflict history:", e);
      setConflictHistory([]);
    } finally {
      setHistoryLoading(false);
    }
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!currentProject || !searchQuery.trim()) {
      setSearchResults(null);
      return;
    }
    setIsSearching(true);
    try {
      const res = await api.searchKnowledge(currentProject.id, searchQuery.trim());
      setSearchResults(res);
    } catch (err) {
      console.error("Search failed:", err);
    } finally {
      setIsSearching(false);
    }
  }

  function clearSearch() {
    setSearchQuery("");
    setSearchResults(null);
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* 1. Header Bar with Actions & Freshness Status */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <BrainCircuit className="w-6 h-6 text-teal-600" />
              <h2 className="text-xl font-bold text-slate-900">Project Knowledge Reconstruction Engine</h2>

              {projectState && (
                <span
                  className={`text-[11px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full border ${
                    projectState.freshness_status === "UP_TO_DATE"
                      ? "bg-emerald-50 text-emerald-800 border-emerald-300"
                      : "bg-amber-50 text-amber-800 border-amber-300"
                  }`}
                >
                  {projectState.freshness_status === "UP_TO_DATE" ? "State: Up-to-date" : "State: Needs Reconstruct"}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Synthesizes real extracted decisions, tasks, dependencies, risks, and contradictions into a coherent, verifiable project representation.
            </p>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
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
                onClick={handleReconstruct}
                disabled={reconstructing}
                className="flex items-center gap-1.5 px-3.5 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg shadow-xs transition"
              >
                <RotateCcw className={`w-3.5 h-3.5 ${reconstructing ? "animate-spin" : ""}`} />
                {reconstructing ? "Reconstructing..." : "Reconstruct State"}
              </button>
            )}

            {canEdit && (
              <button
                onClick={handleTriggerExtraction}
                disabled={extracting}
                className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold rounded-lg shadow-xs transition"
              >
                <Sparkles className={`w-4 h-4 ${extracting ? "animate-spin" : ""}`} />
                {extracting ? "Running AI..." : "Re-Extract All Docs"}
              </button>
            )}
          </div>
        </div>

        {/* Global Project Search Bar */}
        <form onSubmit={handleSearch} className="flex gap-2 items-center pt-1 border-t border-slate-100">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search across all decisions, tasks, blockers, risks, and evidence..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full text-xs pl-9 pr-3 py-2 border border-slate-300 rounded-lg focus:outline-teal-600 bg-slate-50 focus:bg-white transition"
            />
          </div>
          <button
            type="submit"
            disabled={isSearching || !searchQuery.trim()}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold rounded-lg transition disabled:opacity-50"
          >
            {isSearching ? "Searching..." : "Search Knowledge"}
          </button>
          {searchResults && (
            <button
              type="button"
              onClick={clearSearch}
              className="px-3 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 text-xs font-semibold rounded-lg transition"
            >
              Clear
            </button>
          )}
        </form>

        {/* Search Results Drawer if active */}
        {searchResults && (
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-slate-800">
                Found {searchResults.total_results} matching items for &ldquo;{searchResults.query}&rdquo;
              </span>
              <button onClick={clearSearch} className="text-slate-500 hover:text-slate-800">
                Dismiss Search
              </button>
            </div>

            {searchResults.results.length === 0 ? (
              <div className="p-4 bg-white rounded-lg border text-center text-xs text-slate-500">
                No project knowledge entries matched your query.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-72 overflow-y-auto">
                {searchResults.results.map((item) => (
                  <div key={item.id} className="bg-white p-3 rounded-lg border border-slate-200 space-y-1.5 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-teal-50 text-teal-700 border border-teal-200">
                        {item.entity_type}
                      </span>
                      <span className="text-[10px] font-semibold text-slate-500">
                        p.{item.page_number || 1} • {item.source_document || "Source"}
                      </span>
                    </div>
                    <h4 className="font-bold text-slate-900">{item.title}</h4>
                    <p className="text-slate-600 line-clamp-2">{item.description}</p>
                    {item.supporting_quotation && (
                      <div className="bg-slate-50 p-1.5 rounded italic text-slate-700 border text-[11px] line-clamp-2">
                        &ldquo;{item.supporting_quotation}&rdquo;
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* 2. Top-Level Tab Navigation */}
      <div className="bg-white p-2 rounded-xl border border-slate-200 shadow-2xs overflow-x-auto flex items-center gap-1 text-xs">
        <button
          onClick={() => setActiveTab("STATE_OVERVIEW")}
          className={`px-3.5 py-2 rounded-lg font-bold transition whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === "STATE_OVERVIEW" ? "bg-slate-900 text-white shadow-xs" : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          Project State Overview
        </button>

        <button
          onClick={() => setActiveTab("DECISIONS")}
          className={`px-3.5 py-2 rounded-lg font-bold transition whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === "DECISIONS" ? "bg-slate-900 text-white shadow-xs" : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          <Bookmark className="w-3.5 h-3.5 text-teal-500" />
          Decision Timeline ({decisionTimeline ? decisionTimeline.total_decisions : 0})
        </button>

        <button
          onClick={() => setActiveTab("TASKS")}
          className={`px-3.5 py-2 rounded-lg font-bold transition whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === "TASKS" ? "bg-slate-900 text-white shadow-xs" : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          <ListOrdered className="w-3.5 h-3.5 text-blue-500" />
          Task Timeline ({taskTimeline ? taskTimeline.total_tasks : 0})
        </button>

        <button
          onClick={() => setActiveTab("DEPENDENCIES")}
          className={`px-3.5 py-2 rounded-lg font-bold transition whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === "DEPENDENCIES" ? "bg-slate-900 text-white shadow-xs" : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          <Share2 className="w-3.5 h-3.5 text-indigo-500" />
          Dependency Graph ({depGraph ? depGraph.edges.length : 0})
        </button>

        <button
          onClick={() => setActiveTab("RESPONSIBILITIES")}
          className={`px-3.5 py-2 rounded-lg font-bold transition whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === "RESPONSIBILITIES" ? "bg-slate-900 text-white shadow-xs" : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          <Users className="w-3.5 h-3.5 text-purple-500" />
          Ownership & Team ({responsibilities ? responsibilities.owners.length : 0})
        </button>

        <button
          onClick={() => setActiveTab("RISKS")}
          className={`px-3.5 py-2 rounded-lg font-bold transition whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === "RISKS" ? "bg-slate-900 text-white shadow-xs" : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          <ShieldAlert className="w-3.5 h-3.5 text-rose-500" />
          Risk Register ({riskRegister ? riskRegister.total_risks : 0})
        </button>

        <button
          onClick={() => setActiveTab("CONFLICTS")}
          className={`px-3.5 py-2 rounded-lg font-bold transition whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === "CONFLICTS" ? "bg-amber-600 text-white shadow-xs" : "text-amber-800 bg-amber-50 hover:bg-amber-100"
          }`}
        >
          <GitCompare className="w-3.5 h-3.5" />
          Contradictions ({conflicts.length})
        </button>

        <button
          onClick={() => setActiveTab("EVIDENCE_QUALITY")}
          className={`px-3.5 py-2 rounded-lg font-bold transition whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === "EVIDENCE_QUALITY" ? "bg-teal-700 text-white shadow-xs" : "text-teal-800 bg-teal-50 hover:bg-teal-100"
          }`}
        >
          <ShieldCheck className="w-3.5 h-3.5" />
          Evidence Quality ({evidenceSummary ? `${evidenceSummary.coverage_percentage}%` : "100%"})
        </button>
      </div>

      {/* 3. Main View Switching */}
      {loading ? (
        <div className="p-16 text-center text-xs text-slate-500">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto text-teal-600 mb-2" />
          Reconstructing comprehensive project knowledge state...
        </div>
      ) : activeTab === "STATE_OVERVIEW" && projectState ? (
        /* TAB 1: PROJECT STATE OVERVIEW */
        <div className="space-y-6">
          {/* KPI Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Identified Tasks</div>
              <div className="text-2xl font-bold text-slate-900 mt-1">{projectState.overview.total_tasks}</div>
              <div className="text-[10px] text-slate-500 mt-1">From indexed documents</div>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Completed Tasks</div>
              <div className="text-2xl font-bold text-emerald-700 mt-1">{projectState.overview.completed_tasks}</div>
              <div className="text-[10px] text-emerald-600 font-semibold mt-1">Verified finished</div>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">In Progress / WIP</div>
              <div className="text-2xl font-bold text-blue-700 mt-1">{projectState.overview.in_progress_tasks}</div>
              <div className="text-[10px] text-blue-600 font-semibold mt-1">Active development</div>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Blocked Tasks</div>
              <div className="text-2xl font-bold text-rose-700 mt-1">{projectState.overview.blocked_tasks}</div>
              <div className="text-[10px] text-rose-600 font-semibold mt-1">Requires resolution</div>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Supported Completion</div>
              <div className="text-2xl font-bold text-teal-700 mt-1">{projectState.overview.completion_rate}%</div>
              <div className="text-[10px] text-slate-500 mt-1">Definitive task evidence</div>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Contradictions</div>
              <div className="text-2xl font-bold text-amber-700 mt-1">{conflicts.length}</div>
              <div className="text-[10px] text-amber-600 font-semibold mt-1">Conflicting sources</div>
            </div>
          </div>

          {/* Uncertainty & Anomaly Matrix */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-3">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              <h3 className="text-sm font-bold text-slate-900">Project Uncertainty & Knowledge Gaps</h3>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-slate-500 block">Missing Deadlines:</span>
                <strong className="text-base text-slate-800">{projectState.uncertainty_state.missing_deadlines_count} tasks</strong>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-slate-500 block">Unassigned Tasks:</span>
                <strong className="text-base text-slate-800">{projectState.uncertainty_state.unknown_ownership_count} tasks</strong>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-slate-500 block">Conflicting Statuses:</span>
                <strong className="text-base text-amber-700">{projectState.uncertainty_state.conflicting_statuses_count} items</strong>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-slate-500 block">Unsupported Claims:</span>
                <strong className="text-base text-rose-700">{projectState.uncertainty_state.unsupported_claims_count} claims</strong>
              </div>
            </div>
          </div>

          {/* Dual Panel: Outstanding Blockers vs Recent Decisions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Active Blockers */}
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <AlertOctagon className="w-4 h-4 text-rose-600" />
                  Active Blockers & Impediments
                </h3>
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-rose-50 text-rose-700 border border-rose-200">
                  {projectState.active_blockers_summary.length} items
                </span>
              </div>

              {projectState.active_blockers_summary.length === 0 ? (
                <div className="text-xs text-slate-500 py-6 text-center">No active blockers identified.</div>
              ) : (
                <div className="space-y-2.5">
                  {projectState.active_blockers_summary.map((b) => (
                    <div key={b.id} className="p-3 bg-rose-50/50 rounded-lg border border-rose-200 space-y-1 text-xs">
                      <h4 className="font-bold text-rose-950">{b.title}</h4>
                      <p className="text-rose-800 line-clamp-2">{b.description}</p>
                      {b.supporting_quotation && (
                        <div className="text-[11px] italic text-rose-900 pt-1 border-t border-rose-200/50 line-clamp-1">
                          &ldquo;{b.supporting_quotation}&rdquo;
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Key Decisions */}
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Bookmark className="w-4 h-4 text-teal-600" />
                  Key Recorded Decisions
                </h3>
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-teal-50 text-teal-700 border border-teal-200">
                  {projectState.recent_decisions_summary.length} items
                </span>
              </div>

              {projectState.recent_decisions_summary.length === 0 ? (
                <div className="text-xs text-slate-500 py-6 text-center">No decisions recorded yet.</div>
              ) : (
                <div className="space-y-2.5">
                  {projectState.recent_decisions_summary.map((d) => (
                    <div key={d.id} className="p-3 bg-teal-50/40 rounded-lg border border-teal-200 space-y-1 text-xs">
                      <div className="flex items-center justify-between">
                        <h4 className="font-bold text-teal-950">{d.title}</h4>
                        {d.decision_date && (
                          <span className="text-[10px] text-teal-700 bg-white px-1.5 py-0.5 rounded border border-teal-200">
                            {d.decision_date}
                          </span>
                        )}
                      </div>
                      <p className="text-teal-900 line-clamp-2">{d.description}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      ) : activeTab === "DECISIONS" && decisionTimeline ? (
        /* TAB 2: DECISION TIMELINE */
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-4">
            <div>
              <h3 className="text-base font-bold text-slate-900">Chronological Decision Timeline</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Traceable architectural and product decisions extracted strictly from authorized documentation.
              </p>
            </div>

            {/* Dated Events */}
            <div className="space-y-4">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Dated Decisions ({decisionTimeline.dated_events.length})
              </h4>

              {decisionTimeline.dated_events.length === 0 ? (
                <div className="p-6 bg-slate-50 rounded-lg text-xs text-slate-500 text-center">
                  No decisions with explicit calendar dates found in source material.
                </div>
              ) : (
                <div className="relative pl-6 border-l-2 border-teal-400 space-y-6">
                  {decisionTimeline.dated_events.map((ev) => (
                    <div key={ev.id} className="relative group">
                      <div className="absolute -left-[31px] top-1.5 w-3.5 h-3.5 rounded-full bg-teal-600 border-2 border-white ring-2 ring-teal-200" />
                      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-2 text-xs">
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <span className="font-bold text-teal-700 bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
                            {ev.normalized_date || ev.decision_date}
                          </span>
                          <span className="text-slate-500">
                            Source: <strong>{ev.source_document || "Document"}</strong> (p.{ev.page_number || 1})
                          </span>
                        </div>
                        <h4 className="font-bold text-sm text-slate-900">{ev.title}</h4>
                        <p className="text-slate-700">{ev.description}</p>
                        {ev.supporting_quotation && (
                          <blockquote className="bg-slate-50 p-2.5 rounded-lg border border-slate-200 text-slate-800 italic">
                            &ldquo;{ev.supporting_quotation}&rdquo;
                          </blockquote>
                        )}
                        {ev.decided_by && (
                          <div className="text-[11px] text-slate-600">
                            Decided By: <strong className="text-slate-800">{ev.decided_by}</strong>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Undated Decisions Drawer */}
            {decisionTimeline.undated_events.length > 0 && (
              <div className="pt-4 border-t border-slate-100 space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Undated Decisions ({decisionTimeline.undated_events.length})
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {decisionTimeline.undated_events.map((ev) => (
                    <div key={ev.id} className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-semibold text-slate-500 bg-white px-2 py-0.5 rounded border">
                          No explicit date in source
                        </span>
                        <span className="text-slate-500 text-[10px]">p.{ev.page_number || 1} • {ev.source_document || "Source"}</span>
                      </div>
                      <h4 className="font-bold text-slate-900">{ev.title}</h4>
                      <p className="text-slate-700 line-clamp-2">{ev.description}</p>
                      {ev.supporting_quotation && (
                        <div className="text-[11px] italic text-slate-800 bg-white p-2 rounded border line-clamp-2">
                          &ldquo;{ev.supporting_quotation}&rdquo;
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      ) : activeTab === "TASKS" && taskTimeline ? (
        /* TAB 3: TASK TIMELINE & SCHEDULE */
        <div className="space-y-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs flex items-center justify-between flex-wrap gap-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Task Schedule & Deliverables</h3>
              <p className="text-xs text-slate-500">Tasks ordered chronologically by verified deadline.</p>
            </div>

            {/* Task Filter */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500 font-semibold">Filter Status:</span>
              <select
                value={taskStatusFilter}
                onChange={(e) => setTaskStatusFilter(e.target.value)}
                className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white text-slate-700"
              >
                <option value="ALL">All Statuses ({taskTimeline.total_tasks})</option>
                <option value="COMPLETED">Completed ({taskTimeline.completed_count})</option>
                <option value="IN_PROGRESS">In Progress ({taskTimeline.in_progress_count})</option>
                <option value="BLOCKED">Blocked ({taskTimeline.blocked_count})</option>
                <option value="OVERDUE">Overdue Only ({taskTimeline.overdue_count})</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {taskTimeline.tasks
              .filter((t) => {
                if (taskStatusFilter === "ALL") return true;
                if (taskStatusFilter === "OVERDUE") return t.is_overdue;
                return t.task_status.toUpperCase() === taskStatusFilter.toUpperCase();
              })
              .map((t) => (
                <div key={t.id} className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs space-y-3 flex flex-col justify-between">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span
                        className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                          t.task_status === "COMPLETED"
                            ? "bg-emerald-100 text-emerald-800"
                            : t.task_status === "BLOCKED"
                            ? "bg-rose-100 text-rose-800"
                            : t.task_status === "IN_PROGRESS"
                            ? "bg-blue-100 text-blue-800"
                            : "bg-slate-100 text-slate-700"
                        }`}
                      >
                        {t.task_status}
                      </span>

                      {t.is_overdue && (
                        <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-rose-600 text-white flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3" /> Overdue
                        </span>
                      )}
                    </div>

                    <h4 className="font-bold text-sm text-slate-900">{t.title}</h4>
                    <p className="text-xs text-slate-600 line-clamp-2">{t.description}</p>

                    {/* Metadata Row */}
                    <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-100 text-[11px] text-slate-600">
                      <div className="flex items-center gap-1">
                        <User className="w-3 h-3 text-slate-400" />
                        <span>Owner: <strong className="text-slate-800">{t.owner || "Unassigned"}</strong></span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Calendar className="w-3 h-3 text-slate-400" />
                        <span>Deadline: <strong className="text-slate-800">{t.deadline || "None"}</strong></span>
                      </div>
                    </div>

                    {/* Dependencies if any */}
                    {t.dependencies.length > 0 && (
                      <div className="p-2 bg-indigo-50/50 border border-indigo-100 rounded text-[11px] text-indigo-900">
                        Depends on: <strong className="text-indigo-950">{t.dependencies.join(", ")}</strong>
                      </div>
                    )}
                  </div>

                  <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                    <span>p.{t.page_number || 1} • {t.document_filename || "Document"}</span>
                    <button
                      onClick={() => setInspectFinding(t as any)}
                      className="text-teal-700 font-semibold hover:underline"
                    >
                      View Citation
                    </button>
                  </div>
                </div>
              ))}
          </div>
        </div>
      ) : activeTab === "DEPENDENCIES" && depGraph ? (
        /* TAB 4: DEPENDENCY GRAPH & TOPOLOGY */
        <div className="space-y-4">
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Share2 className="w-4 h-4 text-indigo-600" />
                  Project Dependency Graph & Architectural Topology
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Directional prerequisite relationships mapped directly from extracted evidence.
                </p>
              </div>

              {depGraph.has_cycle ? (
                <span className="px-2.5 py-1 bg-rose-100 text-rose-800 border border-rose-300 rounded-md font-bold text-xs flex items-center gap-1">
                  <AlertOctagon className="w-3.5 h-3.5" /> Circular Dependency Detected!
                </span>
              ) : (
                <span className="px-2.5 py-1 bg-emerald-50 text-emerald-800 border border-emerald-300 rounded-md font-semibold text-xs flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Graph Valid (Acyclic)
                </span>
              )}
            </div>

            {/* Cycle Warning Details if any */}
            {depGraph.has_cycle && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 space-y-1">
                <strong>Circular dependency paths identified:</strong>
                <ul className="list-disc pl-4 space-y-0.5">
                  {depGraph.cycles.map((cy, i) => (
                    <li key={i}>{cy.join(" → ")}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Graph Nodes & Directional Edges Matrix */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Discovered Entity Relationships ({depGraph.edges.length})
            </h4>

            {depGraph.edges.length === 0 ? (
              <div className="p-10 bg-slate-50 rounded-xl text-center text-xs text-slate-500">
                No explicit inter-task dependencies detected in current project documentation.
              </div>
            ) : (
              <div className="space-y-3">
                {depGraph.edges.map((e) => {
                  const srcNode = depGraph.nodes.find((n) => n.id === e.source);
                  const tgtNode = depGraph.nodes.find((n) => n.id === e.target);

                  return (
                    <div
                      key={e.id}
                      className="p-4 bg-slate-50/70 hover:bg-slate-50 rounded-xl border border-slate-200 transition flex flex-col md:flex-row md:items-center justify-between gap-4 text-xs"
                    >
                      {/* Flow: Prerequisite -> Target */}
                      <div className="flex items-center gap-3 flex-wrap">
                        <div className="p-2.5 bg-white rounded-lg border border-slate-200 shadow-2xs min-w-44">
                          <span className="text-[10px] font-bold text-slate-400 block uppercase">Prerequisite</span>
                          <strong className="text-slate-900">{srcNode ? srcNode.label : e.source}</strong>
                        </div>

                        <div className="flex items-center gap-1 text-indigo-600 font-bold px-2">
                          <ArrowRight className="w-4 h-4" />
                          <span>{e.relationship_type}</span>
                        </div>

                        <div className="p-2.5 bg-white rounded-lg border border-slate-200 shadow-2xs min-w-44">
                          <span className="text-[10px] font-bold text-slate-400 block uppercase">Dependent Work</span>
                          <strong className="text-slate-900">{tgtNode ? tgtNode.label : e.target}</strong>
                        </div>
                      </div>

                      {/* Evidence */}
                      {e.source_evidence && (
                        <div className="text-right max-w-sm">
                          <span className="text-[10px] text-slate-400 block">p.{e.page_number || 1} • {e.document_filename || "Document"}</span>
                          <span className="italic text-slate-700 line-clamp-2">&ldquo;{e.source_evidence}&rdquo;</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      ) : activeTab === "RESPONSIBILITIES" && responsibilities ? (
        /* TAB 5: OWNERSHIP & TEAM RESPONSIBILITY WORKSPACE */
        <div className="space-y-6">
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Users className="w-4 h-4 text-purple-600" />
              Team Workload & Accountability Matrix
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Tasks assigned strictly to explicitly named individuals. Unassigned tasks are highlighted for allocation.
            </p>
          </div>

          {/* Unassigned Tasks Alert Box */}
          {responsibilities.unassigned_count > 0 && (
            <div className="bg-amber-50 p-5 rounded-xl border border-amber-200 shadow-2xs space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-amber-900 font-bold text-sm">
                  <UserX className="w-4 h-4 text-amber-600" />
                  Unassigned Project Tasks ({responsibilities.unassigned_count})
                </div>
                <span className="text-xs bg-amber-200 text-amber-900 font-bold px-2 py-0.5 rounded">
                  Requires Owner Allocation
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {responsibilities.unassigned_tasks.map((ut) => (
                  <div key={ut.id} className="bg-white p-3 rounded-lg border border-amber-200 text-xs space-y-1">
                    <h4 className="font-bold text-slate-900">{ut.title}</h4>
                    <p className="text-slate-600 line-clamp-2">{ut.description}</p>
                    {ut.deadline && (
                      <span className="text-[10px] text-slate-500 block">Target Deadline: {ut.deadline}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Owners Workload Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {responsibilities.owners.map((owner) => (
              <div key={owner.owner_name} className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                  <div>
                    <h4 className="font-bold text-base text-slate-900 flex items-center gap-1.5">
                      <User className="w-4 h-4 text-slate-500" />
                      {owner.owner_name}
                    </h4>
                    {owner.role && (
                      <span className="text-[11px] text-slate-500 font-medium">Platform Role: {owner.role}</span>
                    )}
                  </div>
                  <span className="text-xs font-bold bg-slate-100 px-2.5 py-1 rounded text-slate-800">
                    {owner.total_assigned} tasks
                  </span>
                </div>

                <div className="grid grid-cols-4 gap-2 text-center text-xs">
                  <div className="p-2 bg-emerald-50 rounded border border-emerald-100">
                    <span className="text-emerald-700 font-bold text-sm block">{owner.completed_count}</span>
                    <span className="text-[10px] text-emerald-800">Completed</span>
                  </div>
                  <div className="p-2 bg-blue-50 rounded border border-blue-100">
                    <span className="text-blue-700 font-bold text-sm block">{owner.in_progress_count}</span>
                    <span className="text-[10px] text-blue-800">In Progress</span>
                  </div>
                  <div className="p-2 bg-rose-50 rounded border border-rose-100">
                    <span className="text-rose-700 font-bold text-sm block">{owner.blocked_count}</span>
                    <span className="text-[10px] text-rose-800">Blocked</span>
                  </div>
                  <div className="p-2 bg-slate-50 rounded border border-slate-200">
                    <span className="text-slate-700 font-bold text-sm block">{owner.pending_count}</span>
                    <span className="text-[10px] text-slate-600">Pending</span>
                  </div>
                </div>

                <div className="space-y-1.5 pt-1">
                  <h5 className="text-[11px] font-bold uppercase text-slate-400">Assigned Deliverables:</h5>
                  {owner.tasks.map((task) => (
                    <div key={task.id} className="p-2 bg-slate-50 rounded border border-slate-100 text-xs flex items-center justify-between">
                      <span className="font-semibold text-slate-800 truncate pr-2">{task.title}</span>
                      <span className="text-[10px] font-bold text-slate-500 uppercase">{task.task_status}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : activeTab === "RISKS" && riskRegister ? (
        /* TAB 6: RISK REGISTER */
        <div className="space-y-6">
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs flex items-center justify-between flex-wrap gap-3">
            <div>
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-rose-600" />
                Project Risk Register & Blockers
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Consolidated risks and technical debt, distinguishing source facts from AI recommendations.
              </p>
            </div>
            <span className="text-xs font-bold px-2.5 py-1 rounded bg-rose-100 text-rose-800 border border-rose-300">
              Critical Risks: {riskRegister.critical_count}
            </span>
          </div>

          {/* Source Identified Risks */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Source-Extracted Risks ({riskRegister.source_risks.length})
            </h4>

            {riskRegister.source_risks.length === 0 ? (
              <div className="p-6 bg-white rounded-xl border text-center text-xs text-slate-500">
                No explicitly stated operational risks in indexed documents.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {riskRegister.source_risks.map((r) => (
                  <div key={r.id} className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs space-y-2.5 text-xs">
                    <div className="flex items-center justify-between">
                      <span
                        className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                          r.severity === "CRITICAL"
                            ? "bg-rose-100 text-rose-800 border border-rose-300"
                            : "bg-amber-100 text-amber-800 border border-amber-300"
                        }`}
                      >
                        Severity: {r.severity}
                      </span>
                      <span className="text-slate-500 text-[10px]">Likelihood: {r.likelihood}</span>
                    </div>

                    <h4 className="font-bold text-sm text-slate-900">{r.title}</h4>
                    <p className="text-slate-600">{r.description}</p>

                    {r.mitigation && (
                      <div className="p-2 bg-slate-50 rounded border text-slate-800">
                        Mitigation: <strong>{r.mitigation}</strong>
                      </div>
                    )}

                    {r.supporting_quotation && (
                      <blockquote className="bg-slate-50 p-2 rounded italic text-slate-700 border text-[11px] line-clamp-2">
                        &ldquo;{r.supporting_quotation}&rdquo;
                      </blockquote>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* AI Recommendations */}
          {riskRegister.ai_recommendations.length > 0 && (
            <div className="space-y-3 pt-4 border-t border-slate-200">
              <h4 className="text-xs font-bold uppercase tracking-wider text-purple-600 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5" />
                AI-Generated Recommendations ({riskRegister.ai_recommendations.length})
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {riskRegister.ai_recommendations.map((r) => (
                  <div key={r.id} className="bg-purple-50/40 rounded-xl border border-purple-200 p-5 shadow-2xs space-y-2 text-xs">
                    <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-purple-100 text-purple-800">
                      Recommendation
                    </span>
                    <h4 className="font-bold text-purple-950">{r.title}</h4>
                    <p className="text-purple-900">{r.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : activeTab === "CONFLICTS" ? (
        /* TAB 7: CONFLICTS RESOLVER WORKSPACE */
        <div className="space-y-4">
          {/* Workspace Filters */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2 flex-wrap text-xs">
              <span className="font-bold text-slate-700 flex items-center gap-1">
                <Filter className="w-3.5 h-3.5 text-slate-500" />
                Status:
              </span>
              {["ALL", "OPEN", "UNDER_REVIEW", "RESOLVED", "DISMISSED"].map((st) => (
                <button
                  key={st}
                  onClick={() => setConflictStatusFilter(st)}
                  className={`px-2.5 py-1 rounded-md font-semibold text-[11px] transition ${
                    conflictStatusFilter === st
                      ? "bg-slate-900 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {st.replace("_", " ")}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2 flex-wrap text-xs">
              <span className="font-bold text-slate-700">Severity:</span>
              {["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((sev) => (
                <button
                  key={sev}
                  onClick={() => setConflictSeverityFilter(sev)}
                  className={`px-2.5 py-1 rounded-md font-semibold text-[11px] transition ${
                    conflictSeverityFilter === sev
                      ? "bg-amber-700 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {sev}
                </button>
              ))}
            </div>
          </div>

          {(() => {
            const filteredConflicts = conflicts.filter((c) => {
              const statusMatch =
                conflictStatusFilter === "ALL" ||
                (c.conflict_status || c.status || "").toUpperCase() === conflictStatusFilter;
              const severityMatch =
                conflictSeverityFilter === "ALL" ||
                (c.severity || "MEDIUM").toUpperCase() === conflictSeverityFilter;
              return statusMatch && severityMatch;
            });

            if (filteredConflicts.length === 0) {
              return (
                <div className="bg-white p-16 rounded-xl border border-slate-200 text-center space-y-2">
                  <CheckCircle className="w-10 h-10 text-emerald-500 mx-auto" />
                  <h3 className="text-sm font-semibold text-slate-800">No Matching Contradictions</h3>
                  <p className="text-xs text-slate-500">
                    No cross-document inconsistencies match the selected filter criteria.
                  </p>
                </div>
              );
            }

            return (
              <div className="space-y-4">
                <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 flex items-start gap-2">
                  <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-bold text-amber-950">Evidence Conflict Management & Human Resolution</h4>
                    <p className="mt-0.5 text-amber-800">
                      Cross-document contradictions require human review. Resolutions update the active project state
                      and timeline non-destructively, preserving historical claims and source quotations in the audit trail.
                    </p>
                  </div>
                </div>

                {filteredConflicts.map((c) => {
                  const cStatus = (c.conflict_status || c.status || "OPEN").toUpperCase();
                  const cSeverity = (c.severity || "MEDIUM").toUpperCase();

                  const sevBadgeColor =
                    cSeverity === "CRITICAL"
                      ? "bg-rose-100 text-rose-800 border-rose-300"
                      : cSeverity === "HIGH"
                      ? "bg-orange-100 text-orange-800 border-orange-300"
                      : cSeverity === "LOW"
                      ? "bg-blue-100 text-blue-800 border-blue-300"
                      : "bg-amber-100 text-amber-800 border-amber-300";

                  const statusBadgeColor =
                    cStatus === "RESOLVED"
                      ? "bg-emerald-100 text-emerald-800 border-emerald-300"
                      : cStatus === "DISMISSED"
                      ? "bg-slate-100 text-slate-700 border-slate-300"
                      : cStatus === "UNDER_REVIEW"
                      ? "bg-purple-100 text-purple-800 border-purple-300"
                      : "bg-amber-100 text-amber-800 border-amber-300";

                  return (
                    <div key={c.id} className="bg-white rounded-xl border border-slate-200 p-6 shadow-2xs space-y-4">
                      {/* Conflict Header */}
                      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-100">
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded border ${sevBadgeColor}`}>
                            Severity: {cSeverity}
                          </span>
                          <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                            Type: {c.conflict_type}
                          </span>
                          <span className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded border ${statusBadgeColor}`}>
                            Status: {cStatus.replace("_", " ")}
                          </span>
                        </div>

                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleOpenHistory(c)}
                            className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 transition flex items-center gap-1"
                          >
                            <History className="w-3.5 h-3.5 text-slate-500" />
                            Audit Trail
                          </button>

                          {canReview && cStatus === "OPEN" && (
                            <button
                              onClick={() => handleStartReview(c.id)}
                              disabled={actionLoading}
                              className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-purple-50 text-purple-700 hover:bg-purple-100 border border-purple-200 transition disabled:opacity-50"
                            >
                              Start Review
                            </button>
                          )}

                          {canReview && (cStatus === "OPEN" || cStatus === "UNDER_REVIEW") && (
                            <>
                              <button
                                onClick={() => {
                                  setResolvingConflict(c);
                                  setResolutionChoice("CLAIM_A_SUPPORTED");
                                  setResolutionNotes("");
                                }}
                                className="px-3 py-1 text-xs font-bold rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white shadow-2xs transition flex items-center gap-1"
                              >
                                <Scale className="w-3.5 h-3.5" />
                                Resolve Contradiction
                              </button>

                              <button
                                onClick={() => {
                                  setDismissingConflict(c);
                                  setDismissalNotes("");
                                }}
                                className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
                              >
                                Dismiss
                              </button>
                            </>
                          )}
                        </div>
                      </div>

                      {/* Conflict Title & Description */}
                      <div>
                        <h3 className="text-sm font-bold text-slate-900">{c.title || c.description}</h3>
                        {c.title && c.description && c.title !== c.description && (
                          <p className="text-xs text-slate-600 mt-1">{c.description}</p>
                        )}
                      </div>

                      {/* Side-by-Side Source Comparison */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Claim A */}
                        <div className="bg-slate-50/80 p-4 rounded-xl border border-slate-200 space-y-2">
                          <div className="flex items-center justify-between text-xs text-slate-600 font-semibold pb-1.5 border-b border-slate-200">
                            <span className="flex items-center gap-1">
                              <FileText className="w-3.5 h-3.5 text-teal-600" />
                              {c.source_1_doc_filename || c.source_a_doc_filename || "Document A"}
                            </span>
                            <span className="bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-700 font-mono text-[11px]">
                              Page {c.source_1_page || c.source_a_page || 1}
                            </span>
                          </div>
                          <span className="text-[10px] font-bold uppercase tracking-wider text-teal-700 block">
                            Claim A Source Quotation:
                          </span>
                          <blockquote className="text-xs italic text-slate-800 bg-white p-3 rounded-lg border border-slate-200">
                            &ldquo;{c.source_1_quote || c.source_a_quote || "Quotation unavailable"}&rdquo;
                          </blockquote>
                        </div>

                        {/* Claim B */}
                        <div className="bg-slate-50/80 p-4 rounded-xl border border-slate-200 space-y-2">
                          <div className="flex items-center justify-between text-xs text-slate-600 font-semibold pb-1.5 border-b border-slate-200">
                            <span className="flex items-center gap-1">
                              <FileText className="w-3.5 h-3.5 text-teal-600" />
                              {c.source_2_doc_filename || c.source_b_doc_filename || "Document B"}
                            </span>
                            <span className="bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-700 font-mono text-[11px]">
                              Page {c.source_2_page || c.source_b_page || 1}
                            </span>
                          </div>
                          <span className="text-[10px] font-bold uppercase tracking-wider text-teal-700 block">
                            Claim B Source Quotation:
                          </span>
                          <blockquote className="text-xs italic text-slate-800 bg-white p-3 rounded-lg border border-slate-200">
                            &ldquo;{c.source_2_quote || c.source_b_quote || "Quotation unavailable"}&rdquo;
                          </blockquote>
                        </div>
                      </div>

                      {/* Resolution Summary Banner if Resolved */}
                      {cStatus === "RESOLVED" && (
                        <div className="p-4 bg-emerald-50/80 border border-emerald-200 rounded-xl text-xs space-y-1.5">
                          <div className="flex items-center gap-1.5 text-emerald-900 font-bold uppercase tracking-wide">
                            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                            Approved Human Resolution: {c.resolution_choice?.replace(/_/g, " ")}
                          </div>
                          <p className="text-emerald-950 font-medium">
                            <span className="font-semibold text-emerald-900">Rationale:</span> {c.resolution_notes}
                          </p>
                          <div className="text-[11px] text-emerald-700 flex items-center gap-3 pt-1">
                            <span>Resolved by: {c.resolver_name || "Authorized Reviewer"}</span>
                            {c.resolved_at && (
                              <span>• {new Date(c.resolved_at).toLocaleString()}</span>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Dismissal Summary Banner if Dismissed */}
                      {cStatus === "DISMISSED" && (
                        <div className="p-4 bg-slate-100 border border-slate-200 rounded-xl text-xs space-y-1">
                          <div className="flex items-center gap-1.5 text-slate-800 font-bold uppercase tracking-wide">
                            <Info className="w-4 h-4 text-slate-500" />
                            Contradiction Dismissed
                          </div>
                          <p className="text-slate-700 font-medium">{c.resolution_notes}</p>
                          {c.resolved_at && (
                            <p className="text-[11px] text-slate-500">Dismissed at: {new Date(c.resolved_at).toLocaleString()}</p>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })()}
        </div>
      ) : activeTab === "EVIDENCE_QUALITY" ? (
        /* TAB 8: EVIDENCE QUALITY & INTEGRITY METRICS DASHBOARD */
        <div className="space-y-6">
          {/* Top Headline Card */}
          <div className="bg-gradient-to-r from-teal-900 to-slate-900 text-white p-6 rounded-xl border border-teal-800 shadow-md">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
              <div className="space-y-2">
                <span className="text-xs font-bold uppercase tracking-widest text-teal-400 flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4" />
                  Deterministic Source Provenance Standard
                </span>
                <h3 className="text-2xl font-black tracking-tight">Evidence Coverage & Verification Reliability</h3>
                <p className="text-xs text-slate-300 max-w-xl">
                  Every factual finding displayed on the Knowledge Continuity platform is traceable to an exact passage in
                  an authorized project document. AI-derived assumptions are strictly partitioned from verified source facts.
                </p>
              </div>

              <div className="bg-white/10 backdrop-blur-xs p-5 rounded-xl border border-white/20 text-center shrink-0 min-w-[200px]">
                <div className="text-[11px] uppercase font-semibold text-teal-200">Overall Coverage</div>
                <div className="text-4xl font-black text-white mt-1">
                  {evidenceSummary ? `${evidenceSummary.coverage_percentage}%` : "100%"}
                </div>
                <div className="text-xs text-teal-300 mt-1 font-mono">
                  {evidenceSummary ? evidenceSummary.coverage_fraction : "0 / 0"}
                </div>
              </div>
            </div>
          </div>

          {/* Quality Breakdown Counters */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Verified Findings</div>
              <div className="text-2xl font-bold text-emerald-600 mt-1">
                {evidenceSummary ? evidenceSummary.verified_count : 0}
              </div>
              <div className="text-[10px] text-slate-500 mt-1">Full 8-point check passed</div>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Unsupported Claims</div>
              <div className="text-2xl font-bold text-rose-600 mt-1">
                {evidenceSummary ? evidenceSummary.unsupported_count : 0}
              </div>
              <div className="text-[10px] text-slate-500 mt-1">Missing source citation</div>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Needs Human Review</div>
              <div className="text-2xl font-bold text-amber-600 mt-1">
                {evidenceSummary ? evidenceSummary.needs_review_count : 0}
              </div>
              <div className="text-[10px] text-slate-500 mt-1">Ambiguous or partial quote</div>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Open Contradictions</div>
              <div className="text-2xl font-bold text-orange-600 mt-1">
                {evidenceSummary ? evidenceSummary.conflicted_count : 0}
              </div>
              <div className="text-[10px] text-slate-500 mt-1">Conflicting statements</div>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Broken Citations</div>
              <div className="text-2xl font-bold text-slate-700 mt-1">
                {evidenceSummary ? evidenceSummary.broken_citations_count : 0}
              </div>
              <div className="text-[10px] text-slate-500 mt-1">Orphaned/deleted documents</div>
            </div>
          </div>

          {/* Document Breakdown Table */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-2xs space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <FileCheck className="w-4 h-4 text-teal-600" />
                Document Provenance & Extraction Reliability
              </h4>
              <button
                onClick={handleReverify}
                disabled={isReverifying}
                className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-teal-50 text-teal-700 hover:bg-teal-100 border border-teal-200 transition flex items-center gap-1.5 disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isReverifying ? "animate-spin" : ""}`} />
                Re-run Full Integrity Check
              </button>
            </div>

            {evidenceSummary && evidenceSummary.by_document.length > 0 ? (
              <div className="overflow-x-auto border border-slate-100 rounded-lg">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                    <tr>
                      <th className="py-2.5 px-4">Document Filename</th>
                      <th className="py-2.5 px-4">Extracted Findings</th>
                      <th className="py-2.5 px-4">Verified Findings</th>
                      <th className="py-2.5 px-4">Evidence Coverage</th>
                      <th className="py-2.5 px-4">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {evidenceSummary.by_document.map((doc) => (
                      <tr key={doc.document_id} className="hover:bg-slate-50/50">
                        <td className="py-2.5 px-4 font-semibold text-slate-900 flex items-center gap-1.5">
                          <FileText className="w-3.5 h-3.5 text-teal-600" />
                          {doc.filename}
                        </td>
                        <td className="py-2.5 px-4">{doc.total_findings}</td>
                        <td className="py-2.5 px-4 font-medium text-emerald-600">{doc.verified_findings}</td>
                        <td className="py-2.5 px-4">
                          <div className="flex items-center gap-2">
                            <div className="w-24 bg-slate-100 h-2 rounded-full overflow-hidden">
                              <div
                                className="bg-teal-600 h-full rounded-full"
                                style={{ width: `${Math.min(doc.coverage_pct, 100)}%` }}
                              />
                            </div>
                            <span className="font-semibold text-[11px] text-slate-800">{doc.coverage_pct}%</span>
                          </div>
                        </td>
                        <td className="py-2.5 px-4">
                          {doc.coverage_pct >= 90 ? (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                              Reliable
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800">
                              Review Needed
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-8 text-center text-xs text-slate-500">
                No indexed document citations available yet.
              </div>
            )}
          </div>
        </div>
      ) : null}

      {/* Conflict Resolution Modal */}
      {resolvingConflict && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 animate-in fade-in duration-200">
          <div className="relative w-full max-w-2xl bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 bg-slate-900 text-white">
              <div className="flex items-center gap-2">
                <Scale className="w-5 h-5 text-teal-400" />
                <h3 className="font-bold text-base">Human Conflict Resolution Workspace</h3>
              </div>
              <button
                onClick={() => setResolvingConflict(null)}
                className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4 max-h-[80vh] overflow-y-auto text-xs">
              <div>
                <h4 className="font-bold text-sm text-slate-900">{resolvingConflict.title || resolvingConflict.description}</h4>
                <p className="text-slate-600 mt-1">{resolvingConflict.description}</p>
              </div>

              {/* Side-by-side comparison */}
              <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200">
                <div className="space-y-1">
                  <span className="font-bold text-teal-800 text-[11px] block">Claim A ({resolvingConflict.source_1_doc_filename || "Doc 1"})</span>
                  <blockquote className="bg-white p-2.5 rounded border border-slate-200 italic text-slate-800">
                    &ldquo;{resolvingConflict.source_1_quote || "Unavailable"}&rdquo;
                  </blockquote>
                </div>
                <div className="space-y-1">
                  <span className="font-bold text-teal-800 text-[11px] block">Claim B ({resolvingConflict.source_2_doc_filename || "Doc 2"})</span>
                  <blockquote className="bg-white p-2.5 rounded border border-slate-200 italic text-slate-800">
                    &ldquo;{resolvingConflict.source_2_quote || "Unavailable"}&rdquo;
                  </blockquote>
                </div>
              </div>

              {/* Resolution Choice Dropdown */}
              <div className="space-y-1.5">
                <label className="font-bold text-slate-800 block">Select Resolution Outcome:</label>
                <select
                  value={resolutionChoice}
                  onChange={(e) => setResolutionChoice(e.target.value as ResolutionChoice)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white font-medium text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                >
                  <option value="CLAIM_A_SUPPORTED">Claim A Supported (Claim A is verified truth; supersede Claim B)</option>
                  <option value="CLAIM_B_SUPPORTED">Claim B Supported (Claim B is verified truth; supersede Claim A)</option>
                  <option value="BOTH_VALID_DIFFERENT_CONTEXT">Both Valid in Different Contexts (Retain both with contextual note)</option>
                  <option value="NEITHER_SUPPORTED">Neither Supported (Reject both claims as unverified)</option>
                  <option value="INVESTIGATION_REQUIRED">Investigation Required (Disputed — flag for further team enquiry)</option>
                </select>
              </div>

              {/* Mandatory Resolution Explanation */}
              <div className="space-y-1.5">
                <label className="font-bold text-slate-800 block">
                  Mandatory Reviewer Explanation <span className="text-rose-500">*</span>:
                </label>
                <textarea
                  value={resolutionNotes}
                  onChange={(e) => setResolutionNotes(e.target.value)}
                  placeholder="Provide detailed rationale for why this resolution was chosen (min 5 characters)..."
                  rows={3}
                  className="w-full p-3 rounded-lg border border-slate-300 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              {/* Non-destructive notice */}
              <div className="p-3 bg-teal-50/60 border border-teal-200 rounded-lg text-teal-900 text-[11px] flex items-start gap-2">
                <Info className="w-4 h-4 text-teal-600 shrink-0 mt-0.5" />
                <span>
                  <strong>Non-Destructive Update:</strong> Neither original finding or document quotation will be deleted.
                  Both statements remain archived for historical transparency. The active reconstructed timeline and handover
                  dossier will reflect this approved resolution.
                </span>
              </div>
            </div>

            <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 flex justify-end gap-2">
              <button
                onClick={() => setResolvingConflict(null)}
                className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 text-xs font-semibold rounded-lg transition"
              >
                Cancel
              </button>
              <button
                onClick={handleApplyResolution}
                disabled={resolutionNotes.trim().length < 5 || actionLoading}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-lg transition disabled:opacity-50 flex items-center gap-1.5"
              >
                {actionLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                Confirm & Apply Resolution
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Conflict Dismissal Modal */}
      {dismissingConflict && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 animate-in fade-in duration-200">
          <div className="relative w-full max-w-md bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 bg-slate-900 text-white">
              <h3 className="font-bold text-base">Dismiss Contradiction</h3>
              <button
                onClick={() => setDismissingConflict(null)}
                className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4 text-xs">
              <p className="text-slate-600">
                Dismissing this contradiction removes the CONFLICTED status from the associated findings and marks the
                issue as resolved/ignored in the project records.
              </p>

              <div className="space-y-1.5">
                <label className="font-bold text-slate-800 block">
                  Dismissal Reason <span className="text-rose-500">*</span>:
                </label>
                <textarea
                  value={dismissalNotes}
                  onChange={(e) => setDismissalNotes(e.target.value)}
                  placeholder="Explain why this conflict is dismissed or not applicable (min 5 characters)..."
                  rows={3}
                  className="w-full p-3 rounded-lg border border-slate-300 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>
            </div>

            <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 flex justify-end gap-2">
              <button
                onClick={() => setDismissingConflict(null)}
                className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 text-xs font-semibold rounded-lg transition"
              >
                Cancel
              </button>
              <button
                onClick={handleApplyDismissal}
                disabled={dismissalNotes.trim().length < 5 || actionLoading}
                className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold rounded-lg transition disabled:opacity-50"
              >
                Confirm Dismissal
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Conflict Audit History Modal */}
      {viewingHistoryConflict && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 animate-in fade-in duration-200">
          <div className="relative w-full max-w-xl bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 bg-slate-900 text-white">
              <div className="flex items-center gap-2">
                <History className="w-5 h-5 text-teal-400" />
                <h3 className="font-bold text-base">Conflict Audit Trail & Review History</h3>
              </div>
              <button
                onClick={() => setViewingHistoryConflict(null)}
                className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4 max-h-[70vh] overflow-y-auto text-xs">
              <h4 className="font-bold text-slate-900">{viewingHistoryConflict.title || viewingHistoryConflict.description}</h4>

              {historyLoading ? (
                <div className="p-8 text-center text-slate-500">
                  <RefreshCw className="w-5 h-5 animate-spin mx-auto text-teal-600 mb-2" />
                  Loading audit logs...
                </div>
              ) : conflictHistory.length === 0 ? (
                <div className="p-8 text-center text-slate-500 bg-slate-50 rounded-xl">
                  No previous review or resolution activity recorded yet for this conflict.
                </div>
              ) : (
                <div className="space-y-3">
                  {conflictHistory.map((item) => (
                    <div key={item.id} className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                      <div className="flex items-center justify-between font-bold text-slate-900">
                        <span className="uppercase tracking-wider text-[11px] text-teal-700">{item.action}</span>
                        <span className="text-[11px] font-normal text-slate-500">
                          {new Date(item.created_at).toLocaleString()}
                        </span>
                      </div>
                      <div className="text-slate-700">
                        <span className="font-semibold">Actor:</span> {item.user_name || "System"}
                      </div>
                      {item.details && (
                        <div className="text-slate-600 bg-white p-2 rounded border border-slate-100 font-mono text-[10px] whitespace-pre-wrap">
                          {JSON.stringify(item.details, null, 2)}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 flex justify-end">
              <button
                onClick={() => setViewingHistoryConflict(null)}
                className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg transition"
              >
                Close History
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Evidence Inspector Modal */}
      {inspectFinding && (
        <EvidenceModal
          finding={inspectFinding}
          onClose={() => setInspectFinding(null)}
          onRefresh={loadAllReconstructedData}
        />
      )}

      {/* Human Review Modal */}
      {reviewFinding && currentProject && (
        <ReviewModal
          finding={reviewFinding}
          projectId={currentProject.id}
          onClose={() => setReviewFinding(null)}
          onSubmit={loadAllReconstructedData}
        />
      )}
    </div>
  );
}
