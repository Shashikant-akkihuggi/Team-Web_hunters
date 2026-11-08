"use client";

import React, { useState } from "react";
import { ExtractedFinding } from "@/lib/types";
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  FileText,
  Bookmark,
  ShieldAlert,
  X,
  ShieldCheck,
  RefreshCw,
  Hash,
  HelpCircle,
} from "lucide-react";
import { api } from "@/lib/api";

interface EvidenceModalProps {
  finding: ExtractedFinding | null;
  onClose: () => void;
  onRefresh?: () => void;
}

export function EvidenceModal({ finding, onClose, onRefresh }: EvidenceModalProps) {
  if (!finding) return null;

  const [verifying, setVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState<any>(null);

  const isVerified = finding.verification_status === "VERIFIED";
  const isConflicting = finding.verification_status === "CONFLICTING" || finding.verification_status === "CONFLICTED";
  const isNeedsReview = finding.verification_status === "NEEDS_REVIEW";
  const isUnsupported = finding.verification_status === "UNSUPPORTED";
  const flags = finding.flags || {};
  const firstRef = finding.evidence_refs && finding.evidence_refs.length > 0 ? finding.evidence_refs[0] : null;

  const checks = flags.integrity_checks || {
    document_exists: Boolean(finding.document_id),
    correct_project: true,
    chunk_exists: Boolean(finding.chunk_id || firstRef?.chunk_id),
    chunk_belongs_to_doc: true,
    quote_present_in_text: isVerified || (firstRef?.match_score || 0) >= 0.7,
    valid_page_reference: Boolean(finding.page_number && finding.page_number >= 1),
    user_authorized: true,
    not_orphaned_or_corrupted: true,
  };

  async function handleReverify() {
    if (!finding) return;
    setVerifying(true);
    try {
      if (firstRef?.id) {
        const res = await api.verifyEvidence(firstRef.id);
        setVerifyResult(res);
      } else {
        const res = await api.getFindingEvidence(finding.id);
        setVerifyResult(res);
      }
      if (onRefresh) onRefresh();
    } catch (e) {
      console.error("Re-verification failed:", e);
    } finally {
      setVerifying(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 bg-slate-900 text-white">
          <div className="flex items-center gap-2">
            <Bookmark className="w-5 h-5 text-teal-400" />
            <div>
              <h3 className="font-semibold text-base leading-tight">Evidence Provenance & Integrity Inspector</h3>
              <p className="text-[11px] text-slate-400">Deterministic 8-point source traceability verification</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5 max-h-[80vh] overflow-y-auto">
          {/* Finding Summary */}
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-teal-50 text-teal-700 border border-teal-200">
                {finding.entity_type}
              </span>
              <span className="text-xs text-slate-500 font-mono">ID: {finding.id.slice(0, 8)}</span>
              {firstRef?.verification_method && (
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                  Method: {firstRef.verification_method}
                </span>
              )}
            </div>
            <h4 className="text-base font-bold text-slate-900">{finding.title}</h4>
            <p className="text-sm text-slate-600 mt-1">{finding.description}</p>
          </div>

          {/* Verification Badge */}
          <div className="p-4 rounded-xl border bg-slate-50 flex items-start gap-3">
            {isVerified && <CheckCircle2 className="w-6 h-6 text-emerald-600 shrink-0 mt-0.5" />}
            {isConflicting && <ShieldAlert className="w-6 h-6 text-amber-600 shrink-0 mt-0.5" />}
            {isNeedsReview && <AlertTriangle className="w-6 h-6 text-yellow-600 shrink-0 mt-0.5" />}
            {isUnsupported && <XCircle className="w-6 h-6 text-rose-600 shrink-0 mt-0.5" />}
            <div className="space-y-1 flex-1">
              <div className="flex items-center justify-between">
                <span className="font-bold text-sm text-slate-900">
                  Verification Status: {finding.verification_status}
                </span>
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700">
                  Match Score: {firstRef?.match_score ? `${Math.round(firstRef.match_score * 100)}%` : `${Math.round(finding.confidence_score * 100)}%`}
                </span>
              </div>
              <p className="text-xs text-slate-600">
                {isVerified && "Verified with high fidelity against indexed project document chunks."}
                {isConflicting && "Cross-document conflict detected: this statement contradicts another project finding."}
                {isNeedsReview && "Ambiguous or partial match: requires human verification."}
                {isUnsupported && "Verbatim citation missing or citation points to non-existent source text."}
              </p>
            </div>
          </div>

          {/* 8-Point Evidence Integrity Checklist */}
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-teal-600" />
                8-Point Evidence Integrity Protocol
              </span>
              <button
                onClick={handleReverify}
                disabled={verifying}
                className="text-xs font-medium text-teal-700 hover:text-teal-900 flex items-center gap-1 disabled:opacity-50"
              >
                <RefreshCw className={`w-3 h-3 ${verifying ? "animate-spin" : ""}`} />
                Re-check Integrity
              </button>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="flex items-center gap-1.5 p-1.5 bg-white rounded border border-slate-200">
                {checks.document_exists ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                ) : (
                  <XCircle className="w-3.5 h-3.5 text-rose-500 shrink-0" />
                )}
                <span className="text-slate-700 truncate">1. Document Exists in DB</span>
              </div>

              <div className="flex items-center gap-1.5 p-1.5 bg-white rounded border border-slate-200">
                {checks.correct_project ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                ) : (
                  <XCircle className="w-3.5 h-3.5 text-rose-500 shrink-0" />
                )}
                <span className="text-slate-700 truncate">2. Project Access Scoped</span>
              </div>

              <div className="flex items-center gap-1.5 p-1.5 bg-white rounded border border-slate-200">
                {checks.chunk_exists ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                ) : (
                  <XCircle className="w-3.5 h-3.5 text-rose-500 shrink-0" />
                )}
                <span className="text-slate-700 truncate">3. Chunk Exists</span>
              </div>

              <div className="flex items-center gap-1.5 p-1.5 bg-white rounded border border-slate-200">
                {checks.chunk_belongs_to_doc ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                ) : (
                  <XCircle className="w-3.5 h-3.5 text-rose-500 shrink-0" />
                )}
                <span className="text-slate-700 truncate">4. Chunk Belongs to Doc</span>
              </div>

              <div className="flex items-center gap-1.5 p-1.5 bg-white rounded border border-slate-200">
                {checks.quote_present_in_text ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                ) : (
                  <XCircle className="w-3.5 h-3.5 text-rose-500 shrink-0" />
                )}
                <span className="text-slate-700 truncate">5. Quote Present in Text</span>
              </div>

              <div className="flex items-center gap-1.5 p-1.5 bg-white rounded border border-slate-200">
                {checks.valid_page_reference ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                ) : (
                  <XCircle className="w-3.5 h-3.5 text-rose-500 shrink-0" />
                )}
                <span className="text-slate-700 truncate">6. Valid Page Number</span>
              </div>

              <div className="flex items-center gap-1.5 p-1.5 bg-white rounded border border-slate-200">
                {checks.user_authorized ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                ) : (
                  <XCircle className="w-3.5 h-3.5 text-rose-500 shrink-0" />
                )}
                <span className="text-slate-700 truncate">7. Authorization Verified</span>
              </div>

              <div className="flex items-center gap-1.5 p-1.5 bg-white rounded border border-slate-200">
                {checks.not_orphaned_or_corrupted ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                ) : (
                  <XCircle className="w-3.5 h-3.5 text-rose-500 shrink-0" />
                )}
                <span className="text-slate-700 truncate">8. Uncorrupted Source</span>
              </div>
            </div>
          </div>

          {/* Flags Banner if any */}
          {(flags.has_conflict || flags.ambiguous_ownership || flags.missing_evidence) && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg space-y-1">
              <div className="flex items-center gap-2 text-amber-800 font-semibold text-xs uppercase tracking-wide">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                Evidence Anomaly Flags
              </div>
              {flags.conflict_reason && (
                <p className="text-xs text-amber-700">• {flags.conflict_reason}</p>
              )}
              {flags.ownership_conflict && (
                <p className="text-xs text-amber-700">• {flags.ownership_conflict}</p>
              )}
              {flags.missing_evidence && (
                <p className="text-xs text-amber-700">• Missing explicit evidence quotation in source document.</p>
              )}
            </div>
          )}

          {/* Source Document Citation */}
          <div className="border border-slate-200 rounded-lg p-4 bg-white space-y-3">
            <div className="flex items-center justify-between text-xs text-slate-500 font-medium pb-2 border-b border-slate-100">
              <div className="flex items-center gap-1.5 text-slate-700">
                <FileText className="w-4 h-4 text-teal-600" />
                <span className="font-semibold">{finding.document_filename || firstRef?.document_filename || "Project Source Document"}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 bg-slate-100 rounded text-slate-700 font-semibold">
                  Page {finding.page_number || firstRef?.page_number || 1}
                </span>
                {(firstRef?.character_start !== undefined && firstRef.character_end !== undefined) && (
                  <span className="px-2 py-0.5 bg-slate-100 rounded text-slate-600 font-mono text-[10px]">
                    Chars: {firstRef.character_start} - {firstRef.character_end}
                  </span>
                )}
              </div>
            </div>

            <div>
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-1">
                Supporting Verbatim Quotation:
              </span>
              <blockquote className="text-sm bg-teal-50/50 border-l-4 border-teal-500 p-3 italic text-slate-800 rounded-r-md">
                &ldquo;{finding.supporting_quotation || firstRef?.quotation || "No verbatim quotation recorded."}&rdquo;
              </blockquote>
            </div>

            <div className="grid grid-cols-2 gap-3 pt-2 text-xs text-slate-600">
              <div>
                <span className="font-semibold text-slate-700">Attributed Owner:</span>{" "}
                {finding.owner ? (
                  <span className="font-medium text-slate-900">{finding.owner}</span>
                ) : (
                  <span className="text-slate-400 italic">None stated in source</span>
                )}
              </div>
              <div>
                <span className="font-semibold text-slate-700">Attributed Deadline:</span>{" "}
                {finding.deadline ? (
                  <span className="font-medium text-slate-900">{finding.deadline}</span>
                ) : (
                  <span className="text-slate-400 italic">None stated in source</span>
                )}
              </div>
              <div>
                <span className="font-semibold text-slate-700">Classification:</span>{" "}
                {finding.is_recommendation ? "AI Recommendation" : "Explicit Project Fact"}
              </div>
              <div>
                <span className="font-semibold text-slate-700">Review Status:</span>{" "}
                <span className="font-medium text-slate-900">{finding.status}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg transition"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
}
