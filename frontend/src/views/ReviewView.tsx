"use client";

import React, { useEffect, useState } from "react";
import {
  CheckSquare,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  HelpCircle,
  AlertTriangle,
  FileText,
  Clock,
  History,
  ShieldAlert,
} from "lucide-react";
import { ExtractedFinding, ReviewLog } from "@/lib/types";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { ReviewModal } from "@/components/ReviewModal";
import { EvidenceModal } from "@/components/EvidenceModal";

export function ReviewView() {
  const { currentProject, user } = useAuth();
  const [queue, setQueue] = useState<ExtractedFinding[]>([]);
  const [history, setHistory] = useState<ReviewLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedReviewFinding, setSelectedReviewFinding] = useState<ExtractedFinding | null>(null);
  const [selectedInspectFinding, setSelectedInspectFinding] = useState<ExtractedFinding | null>(null);

  const canReview = user?.role === "ADMIN" || user?.role === "PROJECT_MANAGER";

  async function loadReviewData() {
    if (!currentProject || !canReview) return;
    setLoading(true);
    try {
      const [queueData, historyData] = await Promise.all([
        api.getReviewQueue(currentProject.id),
        api.getReviewHistory(currentProject.id),
      ]);
      setQueue(queueData);
      setHistory(historyData);
    } catch (e) {
      console.warn("Failed to load review data:", e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadReviewData();
  }, [currentProject, user?.role]);

  async function handleReviewSubmit(findingId: string, reviewData: any) {
    if (!currentProject) return;
    await api.submitReview(currentProject.id, findingId, reviewData);
    await loadReviewData();
  }

  if (!canReview) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-12 text-center max-w-xl mx-auto space-y-4 shadow-sm animate-in fade-in duration-300">
        <div className="w-12 h-12 rounded-full bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600 mx-auto">
          <ShieldAlert className="w-6 h-6" />
        </div>
        <h3 className="text-base font-bold text-slate-900">Restricted Access: Manager Review Workspace</h3>
        <p className="text-xs text-slate-600 leading-relaxed">
          Your current session role is <strong>{user?.role}</strong>. In accordance with platform governance, the review and approval workspace is restricted to Project Managers and Administrators.
        </p>
        <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-500">
          Incoming team members receive only verified and manager-approved handover artifacts.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-slate-900">Human Review & Approval Workspace</h2>
            <span className="text-xs font-bold px-2 py-0.5 rounded bg-teal-50 text-teal-700 border border-teal-200">
              {queue.length} Pending
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Validate AI extractions, resolve conflicting deadlines, correct owner assignments, and sign off for handover inclusion.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-semibold text-slate-600 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200">
          <ShieldCheck className="w-4 h-4 text-teal-600" />
          <span>Authorized Reviewer: {user?.full_name}</span>
        </div>
      </div>

      {/* Review Queue */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-sm text-slate-800 uppercase tracking-wider text-xs">
            Findings Pending Managerial Action ({queue.length})
          </h3>
          <span className="text-xs text-slate-500">
            Approved findings automatically populate the Handover Dossier
          </span>
        </div>

        {loading ? (
          <div className="p-12 text-center text-xs text-slate-500 bg-white rounded-xl border border-slate-200">
            Loading review queue...
          </div>
        ) : queue.length === 0 ? (
          <div className="bg-white p-12 rounded-xl border border-slate-200 text-center space-y-2">
            <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto" />
            <h3 className="text-sm font-bold text-slate-800">Review Queue Cleared!</h3>
            <p className="text-xs text-slate-500">
              All extracted findings have been reviewed and approved. Handover generation is fully unlocked.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3.5">
            {queue.map((finding) => {
              const isConflicting = finding.verification_status === "CONFLICTING";
              const flags = finding.flags || {};

              return (
                <div
                  key={finding.id}
                  className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs hover:border-slate-300 transition space-y-3"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-teal-50 text-teal-700 border border-teal-200">
                        {finding.entity_type}
                      </span>
                      <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                        finding.status === "FLAGGED" ? "bg-amber-100 text-amber-800" :
                        finding.status === "UNDER_INVESTIGATION" ? "bg-purple-100 text-purple-800" :
                        "bg-slate-100 text-slate-700"
                      }`}>
                        {finding.status}
                      </span>

                      {isConflicting && (
                        <span className="flex items-center gap-1 text-[11px] font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                          Conflict Detected
                        </span>
                      )}
                    </div>

                    <span className="text-xs text-slate-500 flex items-center gap-1">
                      <FileText className="w-3.5 h-3.5" />
                      {finding.document_filename || "Document"}, Page {finding.page_number || 1}
                    </span>
                  </div>

                  <div>
                    <h4 className="text-sm font-bold text-slate-900">{finding.title}</h4>
                    <p className="text-xs text-slate-600 mt-0.5">{finding.description}</p>
                  </div>

                  {/* Conflict warning banner */}
                  {flags.has_conflict && flags.conflict_reason && (
                    <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-900">
                      <strong>Anomaly Flag:</strong> {flags.conflict_reason}
                    </div>
                  )}

                  {/* Supporting quotation */}
                  <div className="bg-slate-50 p-3 rounded-lg border border-slate-200/70 text-xs text-slate-700 italic">
                    &ldquo;{finding.supporting_quotation}&rdquo;
                  </div>

                  {/* Action Row */}
                  <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                    <div className="flex items-center gap-4 text-xs text-slate-600">
                      <span>Owner: <strong className="text-slate-800">{finding.owner || "None"}</strong></span>
                      <span>Deadline: <strong className="text-slate-800">{finding.deadline || "None"}</strong></span>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setSelectedInspectFinding(finding)}
                        className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-lg transition"
                      >
                        Inspect Evidence
                      </button>

                      <button
                        onClick={() => setSelectedReviewFinding(finding)}
                        className="flex items-center gap-1.5 px-4 py-1.5 bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs rounded-lg shadow-xs transition"
                      >
                        <CheckSquare className="w-3.5 h-3.5" />
                        Review & Sign-Off
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Review History Audit Trail */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs p-6 space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
          <History className="w-4 h-4 text-teal-600" />
          <h3 className="font-bold text-sm text-slate-900">Managerial Review History & Audit Log</h3>
        </div>

        {history.length === 0 ? (
          <div className="text-xs text-slate-500 py-4 text-center">No reviews logged yet.</div>
        ) : (
          <div className="divide-y divide-slate-100 max-h-72 overflow-y-auto">
            {history.map((log) => (
              <div key={log.id} className="py-2.5 flex items-start justify-between text-xs gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                      log.action === "APPROVE" ? "bg-emerald-100 text-emerald-800" :
                      log.action === "REJECT" ? "bg-rose-100 text-rose-800" :
                      log.action === "FLAG_INVESTIGATION" ? "bg-amber-100 text-amber-800" :
                      "bg-blue-100 text-blue-800"
                    }`}>
                      {log.action}
                    </span>
                    <span className="font-semibold text-slate-800">{log.reviewer_name}</span>
                  </div>
                  {log.comment && <p className="text-slate-600 italic">&ldquo;{log.comment}&rdquo;</p>}
                </div>
                <span className="text-[11px] text-slate-400 shrink-0">
                  {new Date(log.created_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Evidence Inspector Modal */}
      {selectedInspectFinding && (
        <EvidenceModal
          finding={selectedInspectFinding}
          onClose={() => setSelectedInspectFinding(null)}
        />
      )}

      {/* Human Review Modal */}
      {selectedReviewFinding && currentProject && (
        <ReviewModal
          finding={selectedReviewFinding}
          projectId={currentProject.id}
          onClose={() => setSelectedReviewFinding(null)}
          onSubmit={handleReviewSubmit}
        />
      )}
    </div>
  );
}
