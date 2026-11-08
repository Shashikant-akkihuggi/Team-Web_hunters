"use client";

import React, { useEffect, useState } from "react";
import {
  FileCheck2,
  Download,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Sparkles,
  FileText,
  User,
  ShieldCheck,
  Calendar,
  Layers,
  HelpCircle,
  AlertOctagon,
  GitFork,
  ArrowRight,
  Printer,
  Loader2,
} from "lucide-react";
import { HandoverDossier } from "@/lib/types";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export function HandoverView() {
  const { currentProject, user } = useAuth();
  const [handovers, setHandovers] = useState<HandoverDossier[]>([]);
  const [selectedHandover, setSelectedHandover] = useState<HandoverDossier | null>(null);
  const [loading, setLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [customNotes, setCustomNotes] = useState("");

  const isIncoming = user?.role === "INCOMING_MEMBER";
  const canManage = user?.role === "ADMIN" || user?.role === "PROJECT_MANAGER";

  async function loadHandovers() {
    if (!currentProject) return;
    setLoading(true);
    try {
      const data = await api.listHandovers(currentProject.id);
      setHandovers(data);
      if (data.length > 0) {
        // Select the most recent approved handover or first available
        const approved = data.find((h) => h.status === "APPROVED" || h.status === "FINALIZED");
        setSelectedHandover(approved || data[0]);
      } else {
        setSelectedHandover(null);
      }
    } catch (e) {
      console.warn("Failed to load handovers:", e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadHandovers();
  }, [currentProject, user?.role]);

  async function handleGenerate() {
    if (!currentProject) return;
    setIsGenerating(true);
    try {
      const targetRole = currentProject.handover_role || "Incoming Team Member";
      const newHandover = await api.generateHandover(currentProject.id, targetRole, customNotes);
      await loadHandovers();
      setSelectedHandover(newHandover);
    } catch (err: any) {
      alert(err.message || "Failed to generate handover dossier.");
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleApprove() {
    if (!currentProject || !selectedHandover) return;
    setIsApproving(true);
    try {
      const updated = await api.approveHandover(currentProject.id, selectedHandover.id);
      await loadHandovers();
      setSelectedHandover(updated);
    } catch (err: any) {
      alert(err.message || "Failed to approve handover");
    } finally {
      setIsApproving(false);
    }
  }

  function handleDownloadPdf() {
    if (!currentProject || !selectedHandover) return;
    const url = api.getPdfDownloadUrl(currentProject.id, selectedHandover.id);
    window.open(url, "_blank");
  }

  const content = selectedHandover?.content_json;

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-2xs">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-slate-900">Project Handover Dossier</h2>
            {selectedHandover && (
              <span
                className={`text-xs font-bold uppercase px-2 py-0.5 rounded border ${
                  selectedHandover.status === "APPROVED"
                    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                    : "bg-amber-50 text-amber-700 border-amber-200"
                }`}
              >
                {selectedHandover.status}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Complete 13-section evidence-backed handover report for the incoming team member.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {selectedHandover && (
            <button
              onClick={handleDownloadPdf}
              className="flex items-center gap-1.5 px-3 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold rounded-lg shadow-xs transition"
            >
              <Download className="w-3.5 h-3.5" />
              Export PDF Report
            </button>
          )}

          {canManage && selectedHandover && selectedHandover.status !== "APPROVED" && (
            <button
              onClick={handleApprove}
              disabled={isApproving}
              className="flex items-center gap-1.5 px-3.5 py-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold rounded-lg shadow-xs transition"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              {isApproving ? "Approving..." : "Approve & Sign Off"}
            </button>
          )}

          {canManage && (
            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="flex items-center gap-1.5 px-3.5 py-2 bg-teal-50 hover:bg-teal-100 text-teal-800 border border-teal-200 text-xs font-bold rounded-lg transition"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Synthesizing Handover...
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5 text-teal-600" />
                  Generate New Handover
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Role Notice Banner */}
      {isIncoming && (
        <div className="p-4 bg-teal-50 border border-teal-200 rounded-xl flex items-center justify-between text-xs text-teal-900">
          <div className="flex items-center gap-2.5">
            <ShieldCheck className="w-5 h-5 text-teal-600 shrink-0" />
            <div>
              <span className="font-bold block">Authorized Incoming Member View</span>
              <span>
                You are viewing manager-approved handover knowledge. Unapproved drafts and internal reviews are securely restricted.
              </span>
            </div>
          </div>
          <span className="font-mono text-[11px] bg-white px-2 py-1 rounded border border-teal-200 font-semibold">
            Role: {user?.role}
          </span>
        </div>
      )}

      {loading ? (
        <div className="bg-white p-16 rounded-xl border border-slate-200 text-center text-xs text-slate-500">
          Loading handover package...
        </div>
      ) : !selectedHandover || !content ? (
        <div className="bg-white p-16 rounded-xl border border-slate-200 text-center space-y-4">
          <FileCheck2 className="w-12 h-12 text-slate-300 mx-auto" />
          <div className="space-y-1">
            <h3 className="text-sm font-bold text-slate-800">No Handover Report Generated Yet</h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              {canManage
                ? "Click 'Generate New Handover' above to synthesize all verified findings, decisions, risks, and onboarding tasks into an official report."
                : "The Project Manager is currently preparing and reviewing the official handover package. Please check back shortly."}
            </p>
          </div>
          {canManage && (
            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold rounded-lg transition"
            >
              Generate Handover Now
            </button>
          )}
        </div>
      ) : (
        /* The Complete 13-Section Interactive Dossier */
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          {/* Handover Dossier Cover Header */}
          <div className="bg-slate-900 text-white p-8 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-4">
              <span className="text-xs font-bold uppercase tracking-widest text-teal-400">
                Official Knowledge Handover Package
              </span>
              <span className="text-xs text-slate-400 font-mono">
                Generated: {new Date(selectedHandover.created_at).toLocaleDateString()}
              </span>
            </div>

            <div>
              <h1 className="text-2xl font-black tracking-tight">{selectedHandover.title}</h1>
              <p className="text-xs text-teal-300 mt-1">
                Target Role: <strong>{selectedHandover.target_role}</strong> • Project: <strong>{currentProject?.name}</strong>
              </p>
            </div>

            {/* Sign-off badge */}
            <div className="p-3 bg-slate-800/80 rounded-xl border border-slate-700 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>
                  Approval Status:{" "}
                  <strong className="text-white">
                    {content.review_and_approval_info?.approval_state || "APPROVED"}
                  </strong>
                </span>
              </div>
              <span className="text-slate-400 text-[11px]">
                Sign-off: {content.review_and_approval_info?.generated_by || "Lead Engineer"}
              </span>
            </div>
          </div>

          {/* Handover Body - 13 Sections */}
          <div className="p-8 space-y-8 divide-y divide-slate-100">
            {/* 1. Project Overview */}
            <section className="space-y-3 pt-2">
              <div className="flex items-center gap-2 text-teal-700 font-bold text-xs uppercase tracking-wider">
                <span className="w-6 h-6 rounded bg-teal-50 flex items-center justify-center text-teal-700 font-black">
                  1
                </span>
                Project Overview & Objectives
              </div>
              <p className="text-sm text-slate-800 leading-relaxed bg-slate-50/50 p-4 rounded-xl border border-slate-100">
                {content.project_overview}
              </p>
            </section>

            {/* 2. Current Project Status */}
            <section className="space-y-3 pt-6">
              <div className="flex items-center gap-2 text-teal-700 font-bold text-xs uppercase tracking-wider">
                <span className="w-6 h-6 rounded bg-teal-50 flex items-center justify-center text-teal-700 font-black">
                  2
                </span>
                Current Project Status & Delivery Pace
              </div>
              <p className="text-sm text-slate-800 leading-relaxed bg-slate-50/50 p-4 rounded-xl border border-slate-100">
                {content.current_status}
              </p>
            </section>

            {/* 3. Completed Work */}
            <section className="space-y-3 pt-6">
              <div className="flex items-center gap-2 text-teal-700 font-bold text-xs uppercase tracking-wider">
                <span className="w-6 h-6 rounded bg-teal-50 flex items-center justify-center text-teal-700 font-black">
                  3
                </span>
                Completed Accomplishments & Shipped Milestones
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {content.completed_work?.map((item, idx) => (
                  <div key={idx} className="p-3.5 bg-emerald-50/40 border border-emerald-200/60 rounded-xl space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-emerald-950">{item.title}</span>
                      <span className="text-[10px] text-emerald-700 font-semibold bg-emerald-100 px-1.5 py-0.5 rounded">
                        Page {item.evidence_page || 1}
                      </span>
                    </div>
                    <p className="text-xs text-slate-700">{item.description}</p>
                  </div>
                ))}
              </div>
            </section>

            {/* 4. Pending Tasks */}
            <section className="space-y-3 pt-6">
              <div className="flex items-center gap-2 text-teal-700 font-bold text-xs uppercase tracking-wider">
                <span className="w-6 h-6 rounded bg-teal-50 flex items-center justify-center text-teal-700 font-black">
                  4
                </span>
                Pending Tasks & Critical Work Items
              </div>
              <div className="space-y-2.5">
                {content.pending_tasks?.map((task, idx) => (
                  <div key={idx} className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl flex items-start justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-xs text-slate-900">{task.title}</span>
                        {task.deadline && (
                          <span className="text-[10px] font-semibold text-amber-800 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                            Due: {task.deadline}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-600">{task.description}</p>
                    </div>
                    <span className="text-xs text-slate-500 font-medium shrink-0">
                      Owner: <strong className="text-slate-800">{task.owner || "Unassigned"}</strong>
                    </span>
                  </div>
                ))}
              </div>
            </section>

            {/* 5. Task Ownership Matrix */}
            <section className="space-y-3 pt-6">
              <div className="flex items-center gap-2 text-teal-700 font-bold text-xs uppercase tracking-wider">
                <span className="w-6 h-6 rounded bg-teal-50 flex items-center justify-center text-teal-700 font-black">
                  5
                </span>
                Task Ownership & Ambiguity Matrix
              </div>
              <div className="overflow-x-auto border border-slate-200 rounded-xl">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200 text-[10px] uppercase">
                    <tr>
                      <th className="px-4 py-2.5">Deliverable</th>
                      <th className="px-4 py-2.5">Designated Owner</th>
                      <th className="px-4 py-2.5">Ambiguity Status</th>
                      <th className="px-4 py-2.5">Target Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {content.task_ownership?.map((row, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/50">
                        <td className="px-4 py-2.5 font-medium text-slate-900">{row.task}</td>
                        <td className="px-4 py-2.5 text-slate-700 font-semibold">{row.owner}</td>
                        <td className="px-4 py-2.5">
                          {row.has_ambiguity ? (
                            <span className="text-amber-700 bg-amber-50 px-2 py-0.5 rounded text-[10px] font-bold border border-amber-200">
                              Ambiguous
                            </span>
                          ) : (
                            <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded text-[10px] font-bold">
                              Clear
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-2.5 text-slate-500">{row.deadline}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            {/* 6. Important Decisions */}
            <section className="space-y-3 pt-6">
              <div className="flex items-center gap-2 text-teal-700 font-bold text-xs uppercase tracking-wider">
                <span className="w-6 h-6 rounded bg-teal-50 flex items-center justify-center text-teal-700 font-black">
                  6
                </span>
                Architectural & Strategic Decisions Record (ADR)
              </div>
              <div className="space-y-3">
                {content.important_decisions?.map((dec, idx) => (
                  <div key={idx} className="p-4 bg-teal-50/30 border border-teal-200/70 rounded-xl space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-slate-900 text-sm">{dec.decision}</span>
                      <span className="text-[10px] text-teal-800 font-semibold bg-teal-100 px-2 py-0.5 rounded">
                        Page {dec.page || 1}
                      </span>
                    </div>
                    <p className="text-xs text-slate-700">{dec.context}</p>
                    {dec.supporting_quote && (
                      <blockquote className="text-xs italic text-slate-600 border-l-2 border-teal-400 pl-2 mt-1">
                        &ldquo;{dec.supporting_quote}&rdquo;
                      </blockquote>
                    )}
                  </div>
                ))}
              </div>
            </section>

            {/* 7. Dependencies */}
            <section className="space-y-3 pt-6">
              <div className="flex items-center gap-2 text-teal-700 font-bold text-xs uppercase tracking-wider">
                <span className="w-6 h-6 rounded bg-teal-50 flex items-center justify-center text-teal-700 font-black">
                  7
                </span>
                External Services & System Couplings
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {content.dependencies?.map((dep, idx) => (
                  <div key={idx} className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs space-y-1">
                    <span className="font-bold text-slate-900 block">{dep.name}</span>
                    <p className="text-slate-600">{dep.details}</p>
                  </div>
                ))}
              </div>
            </section>

            {/* 8. Blockers */}
            <section className="space-y-3 pt-6">
              <div className="flex items-center gap-2 text-rose-700 font-bold text-xs uppercase tracking-wider">
                <span className="w-6 h-6 rounded bg-rose-50 flex items-center justify-center text-rose-700 font-black">
                  8
                </span>
                Active Impediments & Blockers
              </div>
              <div className="space-y-2">
                {content.blockers?.map((b, idx) => (
                  <div key={idx} className="p-3 bg-rose-50/60 border border-rose-200 rounded-xl flex items-center justify-between text-xs">
                    <div>
                      <span className="font-bold text-rose-950 block">{b.blocker}</span>
                      <p className="text-rose-800 mt-0.5">{b.impact}</p>
                    </div>
                    <span className="text-[10px] font-bold uppercase px-2 py-1 bg-rose-200 text-rose-900 rounded shrink-0">
                      Immediate Escalation
                    </span>
                  </div>
                ))}
              </div>
            </section>

            {/* 9. Risks */}
            <section className="space-y-3 pt-6">
              <div className="flex items-center gap-2 text-amber-700 font-bold text-xs uppercase tracking-wider">
                <span className="w-6 h-6 rounded bg-amber-50 flex items-center justify-center text-amber-700 font-black">
                  9
                </span>
                Risk Register & Recommended Mitigations
              </div>
              <div className="space-y-2.5">
                {content.risks?.map((r, idx) => (
                  <div key={idx} className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-1 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-900">{r.risk}</span>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-800">
                        {r.severity}
                      </span>
                    </div>
                    <p className="text-slate-600">{r.details}</p>
                    <p className="text-[11px] text-teal-800 font-medium">💡 Mitigation: {r.mitigation}</p>
                  </div>
                ))}
              </div>
            </section>

            {/* 10. Unresolved Questions */}
            <section className="space-y-3 pt-6">
              <div className="flex items-center gap-2 text-teal-700 font-bold text-xs uppercase tracking-wider">
                <span className="w-6 h-6 rounded bg-teal-50 flex items-center justify-center text-teal-700 font-black">
                  10
                </span>
                Unresolved Questions & Open RFCs
              </div>
              <div className="space-y-2">
                {content.unresolved_questions?.map((q, idx) => (
                  <div key={idx} className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs space-y-1">
                    <span className="font-bold text-slate-900 block">? {q.question}</span>
                    <p className="text-slate-600">{q.context}</p>
                  </div>
                ))}
              </div>
            </section>

            {/* 11. Recommended Next Actions */}
            <section className="space-y-3 pt-6">
              <div className="flex items-center gap-2 text-teal-700 font-bold text-xs uppercase tracking-wider">
                <span className="w-6 h-6 rounded bg-teal-50 flex items-center justify-center text-teal-700 font-black">
                  11
                </span>
                Recommended Onboarding Plan (Day 1, Week 1, Month 1)
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {content.recommended_next_actions?.map((act, idx) => (
                  <div key={idx} className="p-4 bg-teal-50/40 border border-teal-200 rounded-xl space-y-2">
                    <span className="text-xs font-bold text-teal-900 uppercase tracking-wider block">
                      {act.timeframe}
                    </span>
                    <p className="text-xs text-slate-700 leading-relaxed">{act.action}</p>
                    {act.deliverable && (
                      <span className="text-[11px] text-teal-700 block font-semibold pt-1">
                        🎯 Deliverable: {act.deliverable}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </section>

            {/* 12. Evidence References Audit */}
            <section className="space-y-3 pt-6">
              <div className="flex items-center gap-2 text-teal-700 font-bold text-xs uppercase tracking-wider">
                <span className="w-6 h-6 rounded bg-teal-50 flex items-center justify-center text-teal-700 font-black">
                  12
                </span>
                Evidence Traceability Audit Table
              </div>
              <div className="overflow-x-auto border border-slate-200 rounded-xl max-h-72 overflow-y-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200 text-[10px] uppercase sticky top-0">
                    <tr>
                      <th className="px-4 py-2.5">Entity</th>
                      <th className="px-4 py-2.5">Source Doc</th>
                      <th className="px-4 py-2.5">Page</th>
                      <th className="px-4 py-2.5">Verbatim Citation</th>
                      <th className="px-4 py-2.5">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {content.evidence_references?.map((ref, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/50">
                        <td className="px-4 py-2.5 font-bold text-slate-900">{ref.title}</td>
                        <td className="px-4 py-2.5 text-slate-600">{ref.source_doc}</td>
                        <td className="px-4 py-2.5 font-mono text-slate-700">p.{ref.page_number}</td>
                        <td className="px-4 py-2.5 italic text-slate-600 max-w-xs truncate">
                          &ldquo;{ref.quotation}&rdquo;
                        </td>
                        <td className="px-4 py-2.5">
                          <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                            {ref.verification_status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            {/* 13. Review and Approval Information */}
            <section className="space-y-3 pt-6">
              <div className="flex items-center gap-2 text-teal-700 font-bold text-xs uppercase tracking-wider">
                <span className="w-6 h-6 rounded bg-teal-50 flex items-center justify-center text-teal-700 font-black">
                  13
                </span>
                Review, Governance & Sign-Off Record
              </div>
              <div className="p-4 bg-slate-900 text-white rounded-xl space-y-2 text-xs">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-[11px]">
                  <div>
                    <span className="text-slate-400 block">Generated By:</span>
                    <strong className="text-white">{content.review_and_approval_info?.generated_by}</strong>
                  </div>
                  <div>
                    <span className="text-slate-400 block">Target Role:</span>
                    <strong className="text-white">{content.review_and_approval_info?.target_role}</strong>
                  </div>
                  <div>
                    <span className="text-slate-400 block">Approval State:</span>
                    <strong className="text-teal-400">{content.review_and_approval_info?.approval_state}</strong>
                  </div>
                  <div>
                    <span className="text-slate-400 block">Approved At:</span>
                    <strong className="text-white">
                      {content.review_and_approval_info?.approved_at
                        ? new Date(content.review_and_approval_info.approved_at).toLocaleDateString()
                        : "Immediate"}
                    </strong>
                  </div>
                </div>
                {content.review_and_approval_info?.notes && (
                  <p className="text-slate-300 pt-2 border-t border-slate-800 text-[11px]">
                    <strong>Managerial Sign-Off Note:</strong> {content.review_and_approval_info.notes}
                  </p>
                )}
              </div>
            </section>
          </div>
        </div>
      )}
    </div>
  );
}
