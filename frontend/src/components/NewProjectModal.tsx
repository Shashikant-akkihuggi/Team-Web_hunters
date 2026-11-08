"use client";

import React, { useState } from "react";
import { FolderPlus, X, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

interface NewProjectModalProps {
  onClose: () => void;
  onSuccess: (newProj: any) => void;
}

export function NewProjectModal({ onClose, onSuccess }: NewProjectModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("Engineering");
  const [status, setStatus] = useState("ACTIVE");
  const [targetRole, setTargetRole] = useState("Senior Distributed Systems Engineer");
  const [startDate, setStartDate] = useState(new Date().toISOString().split("T")[0]);
  const [expectedCompletionDate, setExpectedCompletionDate] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const proj = await api.createProject({
        name: name.trim(),
        description: description.trim() || undefined,
        category,
        domain: category,
        status,
        start_date: startDate ? new Date(startDate).toISOString() : undefined,
        expected_completion_date: expectedCompletionDate ? new Date(expectedCompletionDate).toISOString() : undefined,
        handover_role: targetRole,
        target_handover_date: expectedCompletionDate ? new Date(expectedCompletionDate).toISOString() : undefined,
      });
      onSuccess(proj);
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to create project");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex justify-between items-center">
          <div className="flex items-center gap-2">
            <FolderPlus className="w-5 h-5 text-teal-400" />
            <h3 className="font-semibold text-lg">Initialize Handover Project</h3>
          </div>
          <button onClick={onClose} disabled={isSubmitting} className="text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-xs font-medium">
              {error}
            </div>
          )}

          <div>
            <label className="text-xs font-semibold text-slate-700 block mb-1">
              Project Name <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Project Apollo: Payments & Ingestion"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:outline-teal-600 font-medium"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-700 block mb-1">Description & Scope</label>
            <textarea
              rows={2}
              placeholder="Summary of project goals, architecture, and current transition context..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:outline-teal-600 text-slate-700"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">Category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 bg-white focus:outline-teal-600"
              >
                <option value="Engineering">Engineering</option>
                <option value="Product">Product</option>
                <option value="DevOps & Cloud">DevOps & Cloud</option>
                <option value="Data & AI">Data & AI</option>
                <option value="Security">Security</option>
                <option value="Operations">Operations</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">Initial Status</label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 bg-white focus:outline-teal-600"
              >
                <option value="ACTIVE">ACTIVE</option>
                <option value="PLANNING">PLANNING</option>
                <option value="ON_HOLD">ON_HOLD</option>
                <option value="COMPLETED">COMPLETED</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">Start Date</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:outline-teal-600 text-slate-700"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">Expected Completion</label>
              <input
                type="date"
                value={expectedCompletionDate}
                onChange={(e) => setExpectedCompletionDate(e.target.value)}
                className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:outline-teal-600 text-slate-700"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-700 block mb-1">
              Incoming Member Target Role
            </label>
            <input
              type="text"
              value={targetRole}
              onChange={(e) => setTargetRole(e.target.value)}
              placeholder="e.g. Lead Full-Stack Engineer"
              className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:outline-teal-600"
            />
          </div>

          {/* Footer */}
          <div className="pt-4 border-t border-slate-200 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-100 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !name.trim()}
              className="flex items-center gap-1.5 px-4 py-2 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white text-xs font-bold rounded-lg shadow-sm transition"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Creating...
                </>
              ) : (
                "Create Project"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
