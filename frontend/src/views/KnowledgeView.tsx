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
} from "lucide-react";
import { ExtractedFinding, EntityType, VerificationStatus } from "@/lib/types";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { EvidenceModal } from "@/components/EvidenceModal";
import { ReviewModal } from "@/components/ReviewModal";

export function KnowledgeView() {
  const { currentProject, user } = useAuth();
  const [findings, setFindings] = useState<ExtractedFinding[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedType, setSelectedType] = useState<string>("ALL");
  const [selectedVerif, setSelectedVerif] = useState<string>("ALL");
  const [isReverifying, setIsReverifying] = useState(false);

  // Inspector & Review Modals
  const [inspectFinding, setInspectFinding] = useState<ExtractedFinding | null>(null);
  const [reviewFinding, setReviewFinding] = useState<ExtractedFinding | null>(null);

  const isIncoming = user?.role === "INCOMING_MEMBER";
  const canReview = user?.role === "ADMIN" || user?.role === "PROJECT_MANAGER";

  async function loadFindings() {
    if (!currentProject) return;
    setLoading(true);
    try {
      const data = await api.listFindings(currentProject.id, {
        entity_type: selectedType === "ALL" ? undefined : selectedType,
        verification_status: selectedVerif === "ALL" ? undefined : selectedVerif,
        search: search.trim() ? search.trim() : undefined,
      });
      setFindings(data);
    } catch (e) {
      console.warn("Failed to load findings:", e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadFindings();
  }, [currentProject, selectedType, selectedVerif]);

  async function handleReverify() {
    if (!currentProject) return;
    setIsReverifying(true);
    try {
      await api.reVerifyProject(currentProject.id);
      await loadFindings();
    } finally {
      setIsReverifying(false);
    }
  }

  async function handleReviewSubmit(findingId: string, reviewData: any) {
    if (!currentProject) return;
    await api.submitReview(currentProject.id, findingId, reviewData);
    await loadFindings();
  }

  const entityTypes: Array<{ id: string; label: string }> = [
    { id: "ALL", label: "All Types" },
    { id: "DECISION", label: "Decisions" },
    { id: "TASK", label: "Tasks" },
    { id: "DEADLINE", label: "Deadlines" },
    { id: "MILESTONE", label: "Milestones" },
    { id: "RISK", label: "Risks" },
    { id: "BLOCKER", label: "Blockers" },
    { id: "DEPENDENCY", label: "Dependencies" },
    { id: "QUESTION", label: "Questions" },
    { id: "CONTACT", label: "Contacts" },
  ];

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-2xs">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-slate-900">Project Knowledge Base</h2>
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-teal-50 text-teal-700 border border-teal-200">
              {findings.length} findings
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Reconstructed project state with bidirectional evidence citations and anomaly detection.
          </p>
        </div>

        {canReview && (
          <button
            onClick={handleReverify}
            disabled={isReverifying}
            className="flex items-center gap-1.5 px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition shrink-0"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isReverifying ? "animate-spin text-teal-600" : ""}`} />
            Run Evidence Verification
          </button>
        )}
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-3">
        <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
          {/* Search box */}
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search findings, owners, keywords..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && loadFindings()}
              className="w-full text-xs pl-9 pr-3 py-2 border border-slate-300 rounded-lg focus:outline-teal-600"
            />
          </div>

          {/* Verification Status Filter */}
          <div className="flex items-center gap-2 self-start sm:self-center">
            <span className="text-xs text-slate-500 font-semibold">Evidence:</span>
            <select
              value={selectedVerif}
              onChange={(e) => setSelectedVerif(e.target.value)}
              className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:outline-teal-600"
            >
              <option value="ALL">All Statuses</option>
              <option value="VERIFIED">Verified Only</option>
              <option value="CONFLICTING">Conflicting Only</option>
              <option value="UNSUPPORTED">Unsupported Only</option>
            </select>
          </div>
        </div>

        {/* Entity Type Filter Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
          {entityTypes.map((type) => (
            <button
              key={type.id}
              onClick={() => setSelectedType(type.id)}
              className={`px-3 py-1.5 rounded-lg font-medium transition whitespace-nowrap ${
                selectedType === type.id
                  ? "bg-slate-900 text-white font-semibold shadow-xs"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {type.label}
            </button>
          ))}
        </div>
      </div>

      {/* Findings Grid */}
      {loading ? (
        <div className="p-16 text-center text-xs text-slate-500">Retrieving knowledge findings...</div>
      ) : findings.length === 0 ? (
        <div className="bg-white p-16 rounded-xl border border-slate-200 text-center space-y-2">
          <BrainCircuit className="w-10 h-10 text-slate-300 mx-auto" />
          <h3 className="text-sm font-semibold text-slate-700">No findings matched criteria</h3>
          <p className="text-xs text-slate-500">Try adjusting your filters or search keywords.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {findings.map((f) => {
            const isVerified = f.verification_status === "VERIFIED";
            const isConflicting = f.verification_status === "CONFLICTING";
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
                          <AlertTriangle className="w-3 h-3" /> Conflicting
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-[11px] font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                          <XCircle className="w-3 h-3" /> Unsupported
                        </span>
                      )}

                      <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                        {f.status}
                      </span>
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

                  {/* Owner & Deadline Meta */}
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

      {/* Inspector Modal */}
      {inspectFinding && (
        <EvidenceModal
          finding={inspectFinding}
          onClose={() => setInspectFinding(null)}
        />
      )}

      {/* Review Modal */}
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
