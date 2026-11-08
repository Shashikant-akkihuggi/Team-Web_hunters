"use client";

import React, { useState } from "react";
import { ExtractedFinding } from "@/lib/types";
import { Check, X, HelpCircle, Edit3, MessageSquare } from "lucide-react";

interface ReviewModalProps {
  finding: ExtractedFinding | null;
  projectId: string;
  onClose: () => void;
  onSubmit: (findingId: string, reviewData: {
    action: "APPROVE" | "REJECT" | "EDIT" | "FLAG_INVESTIGATION";
    comment?: string;
    updated_title?: string;
    updated_description?: string;
    updated_owner?: string;
    updated_deadline?: string;
  }) => Promise<void>;
}

export function ReviewModal({ finding, onClose, onSubmit }: ReviewModalProps) {
  const [title, setTitle] = useState(finding?.title || "");
  const [description, setDescription] = useState(finding?.description || "");
  const [owner, setOwner] = useState(finding?.owner || "");
  const [deadline, setDeadline] = useState(finding?.deadline || "");
  const [comment, setComment] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!finding) return null;

  async function handleAction(action: "APPROVE" | "REJECT" | "EDIT" | "FLAG_INVESTIGATION") {
    setIsSubmitting(true);
    try {
      await onSubmit(finding!.id, {
        action,
        comment,
        updated_title: title !== finding!.title ? title : undefined,
        updated_description: description !== finding!.description ? description : undefined,
        updated_owner: owner !== (finding!.owner || "") ? owner : undefined,
        updated_deadline: deadline !== (finding!.deadline || "") ? deadline : undefined,
      });
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-xl bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex justify-between items-center">
          <div>
            <h3 className="font-semibold text-lg">Human Review & Sign-Off</h3>
            <p className="text-xs text-slate-400">Validate AI-extracted findings prior to handover inclusion</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <div className="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
          <div>
            <label className="text-xs font-semibold text-slate-700 block mb-1">Finding Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:outline-teal-600 font-medium"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-700 block mb-1">Description</label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:outline-teal-600 text-slate-700"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">Explicit Owner</label>
              <input
                type="text"
                placeholder="Unassigned / Null"
                value={owner}
                onChange={(e) => setOwner(e.target.value)}
                className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:outline-teal-600"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">Explicit Deadline</label>
              <input
                type="text"
                placeholder="None stated"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
                className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:outline-teal-600"
              />
            </div>
          </div>

          <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
            <span className="text-xs font-semibold text-slate-600 uppercase block mb-1">Supporting Evidence:</span>
            <p className="text-xs italic text-slate-700">&ldquo;{finding.supporting_quotation}&rdquo;</p>
            <p className="text-[11px] text-slate-500 mt-1">Source: {finding.document_filename || "Document"}, Page {finding.page_number || 1}</p>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-700 block mb-1 flex items-center gap-1">
              <MessageSquare className="w-3.5 h-3.5 text-slate-500" />
              Reviewer Notes / Justification
            </label>
            <input
              type="text"
              placeholder="e.g. Verified with architecture diagrams; approved for handover."
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:outline-teal-600"
            />
          </div>
        </div>

        {/* Actions Footer */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex flex-wrap items-center justify-between gap-2">
          <button
            onClick={() => handleAction("FLAG_INVESTIGATION")}
            disabled={isSubmitting}
            className="flex items-center gap-1.5 px-3 py-2 bg-amber-50 hover:bg-amber-100 text-amber-800 text-xs font-semibold rounded-lg border border-amber-300 transition"
          >
            <HelpCircle className="w-4 h-4 text-amber-600" />
            Flag for Investigation
          </button>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handleAction("REJECT")}
              disabled={isSubmitting}
              className="flex items-center gap-1 px-3 py-2 bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs font-semibold rounded-lg border border-rose-200 transition"
            >
              <X className="w-4 h-4" />
              Reject
            </button>
            <button
              onClick={() => handleAction("EDIT")}
              disabled={isSubmitting}
              className="flex items-center gap-1 px-3 py-2 bg-slate-200 hover:bg-slate-300 text-slate-800 text-xs font-semibold rounded-lg transition"
            >
              <Edit3 className="w-4 h-4" />
              Save Edits
            </button>
            <button
              onClick={() => handleAction("APPROVE")}
              disabled={isSubmitting}
              className="flex items-center gap-1 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold rounded-lg shadow-sm transition"
            >
              <Check className="w-4 h-4" />
              Approve Finding
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
