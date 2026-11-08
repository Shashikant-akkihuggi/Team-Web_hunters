"use client";

import React from "react";
import { ExtractedFinding } from "@/lib/types";
import { CheckCircle2, AlertTriangle, XCircle, FileText, Bookmark, ShieldAlert, X } from "lucide-react";

interface EvidenceModalProps {
  finding: ExtractedFinding | null;
  onClose: () => void;
}

export function EvidenceModal({ finding, onClose }: EvidenceModalProps) {
  if (!finding) return null;

  const isVerified = finding.verification_status === "VERIFIED";
  const isConflicting = finding.verification_status === "CONFLICTING" || finding.verification_status === "CONFLICTED";
  const isUnsupported = finding.verification_status === "UNSUPPORTED";
  const flags = finding.flags || {};
  const firstRef = finding.evidence_refs && finding.evidence_refs.length > 0 ? finding.evidence_refs[0] : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 bg-slate-900 text-white">
          <div className="flex items-center gap-2">
            <Bookmark className="w-5 h-5 text-teal-400" />
            <h3 className="font-semibold text-lg">Evidence & Source Verification</h3>
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
              <span className="text-xs text-slate-500">ID: {finding.id.slice(0, 8)}</span>
            </div>
            <h4 className="text-base font-bold text-slate-900">{finding.title}</h4>
            <p className="text-sm text-slate-600 mt-1">{finding.description}</p>
          </div>

          {/* Verification Badge */}
          <div className="p-4 rounded-lg border bg-slate-50 flex items-start gap-3">
            {isVerified && <CheckCircle2 className="w-6 h-6 text-emerald-600 shrink-0 mt-0.5" />}
            {isConflicting && <ShieldAlert className="w-6 h-6 text-amber-600 shrink-0 mt-0.5" />}
            {isUnsupported && <XCircle className="w-6 h-6 text-rose-600 shrink-0 mt-0.5" />}
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-sm text-slate-900">
                  Verification Status: {finding.verification_status}
                </span>
                <span className="text-xs font-medium px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700">
                  Confidence: {Math.round(finding.confidence_score * 100)}%
                </span>
              </div>
              <p className="text-xs text-slate-600">
                {isVerified && "Verified with high similarity against authorized project source text."}
                {isConflicting && "Cross-finding anomaly detected: conflicting deadline or opposing statements found in source documentation."}
                {isUnsupported && "Direct supporting quotation could not be confirmed in the indexed page text."}
              </p>
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
                <p className="text-xs text-amber-700">• Missing explicit evidence quotation in source.</p>
              )}
            </div>
          )}

          {/* Source Document Citation */}
          <div className="border border-slate-200 rounded-lg p-4 bg-white space-y-3">
            <div className="flex items-center justify-between text-xs text-slate-500 font-medium pb-2 border-b border-slate-100">
              <div className="flex items-center gap-1.5 text-slate-700">
                <FileText className="w-4 h-4 text-teal-600" />
                <span className="font-semibold">{finding.document_filename || "Project Source Document"}</span>
              </div>
              <span className="px-2 py-0.5 bg-slate-100 rounded text-slate-700 font-semibold">
                Page {finding.page_number || 1}
              </span>
            </div>

            <div>
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-1">
                Supporting Verbatim Quotation:
              </span>
              <blockquote className="text-sm bg-teal-50/50 border-l-4 border-teal-500 p-3 italic text-slate-800 rounded-r-md">
                &ldquo;{finding.supporting_quotation || "No verbatim quotation recorded."}&rdquo;
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
              {finding.task_status && (
                <div>
                  <span className="font-semibold text-slate-700">Task Status:</span>{" "}
                  <span className="font-bold text-teal-700">{finding.task_status}</span>
                </div>
              )}
              {finding.priority && (
                <div>
                  <span className="font-semibold text-slate-700">Priority:</span>{" "}
                  <span className="font-bold text-slate-800">{finding.priority}</span>
                </div>
              )}
              {firstRef && (
                <div>
                  <span className="font-semibold text-slate-700">Evidence Match Score:</span>{" "}
                  <span className="font-medium text-emerald-700">{Math.round(firstRef.match_score * 100)}%</span>
                </div>
              )}
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
