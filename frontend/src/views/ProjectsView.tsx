"use client";

import React, { useState } from "react";
import {
  FolderGit2,
  FolderPlus,
  Users,
  FileText,
  Calendar,
  Award,
  ArrowRight,
  CheckCircle2,
  Sparkles,
  Edit2,
  Archive,
  Trash2,
  X,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { Project } from "@/lib/types";
import { api } from "@/lib/api";

interface ProjectsViewProps {
  onNewProject: () => void;
  onSelectProject: (p: Project) => void;
}

export function ProjectsView({ onNewProject, onSelectProject }: ProjectsViewProps) {
  const { projects, currentProject, setCurrentProject, user, refreshProjects } = useAuth();
  const [filterStatus, setFilterStatus] = useState<string>("ALL");
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [deletingProjectId, setDeletingProjectId] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Edit form states
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [editCategory, setEditCategory] = useState("Engineering");
  const [editStatus, setEditStatus] = useState("ACTIVE");
  const [editTargetRole, setEditTargetRole] = useState("");

  const filteredProjects = projects.filter((p) => {
    if (filterStatus === "ALL") return true;
    return p.status === filterStatus;
  });

  const canManageProject = user?.role === "ADMIN" || user?.role === "PROJECT_MANAGER";
  const canDeleteProject = user?.role === "ADMIN";

  function openEditModal(p: Project) {
    setEditingProject(p);
    setEditName(p.name);
    setEditDesc(p.description || "");
    setEditCategory(p.category || p.domain || "Engineering");
    setEditStatus(p.status);
    setEditTargetRole(p.handover_role || "Incoming Team Member");
  }

  async function handleUpdateProject(e: React.FormEvent) {
    e.preventDefault();
    if (!editingProject || !editName.trim()) return;
    setActionLoading(true);
    try {
      await api.updateProject(editingProject.id, {
        name: editName.trim(),
        description: editDesc.trim(),
        category: editCategory,
        status: editStatus,
        handover_role: editTargetRole,
      });
      await refreshProjects();
      setEditingProject(null);
      setFeedbackMsg({ type: "success", text: "Project updated successfully." });
      setTimeout(() => setFeedbackMsg(null), 3000);
    } catch (err: any) {
      setFeedbackMsg({ type: "error", text: err.message || "Failed to update project." });
    } finally {
      setActionLoading(false);
    }
  }

  async function handleArchiveProject(projectId: string) {
    setActionLoading(true);
    try {
      await api.archiveProject(projectId);
      await refreshProjects();
      setFeedbackMsg({ type: "success", text: "Project archived successfully." });
      setTimeout(() => setFeedbackMsg(null), 3000);
    } catch (err: any) {
      setFeedbackMsg({ type: "error", text: err.message || "Failed to archive project." });
    } finally {
      setActionLoading(false);
    }
  }

  async function handleDeleteProject(projectId: string) {
    setActionLoading(true);
    try {
      await api.deleteProject(projectId);
      await refreshProjects();
      setDeletingProjectId(null);
      setFeedbackMsg({ type: "success", text: "Project deleted successfully." });
      setTimeout(() => setFeedbackMsg(null), 3000);
    } catch (err: any) {
      setFeedbackMsg({ type: "error", text: err.message || "Failed to delete project." });
    } finally {
      setActionLoading(false);
    }
  }

  const statuses = ["ALL", "ACTIVE", "PLANNING", "ON_HOLD", "COMPLETED", "ARCHIVED"];

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-2xs">
        <div>
          <h2 className="text-lg font-bold text-slate-900">Project Workspaces</h2>
          <p className="text-xs text-slate-500 mt-1">
            Manage active handover transitions, source documents, team member roles, and handover readiness.
          </p>
        </div>

        <button
          onClick={onNewProject}
          className="flex items-center gap-1.5 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold rounded-lg shadow-xs transition shrink-0"
        >
          <FolderPlus className="w-4 h-4" />
          Create New Project
        </button>
      </div>

      {feedbackMsg && (
        <div
          className={`p-3 rounded-lg text-xs font-medium border flex items-center justify-between ${
            feedbackMsg.type === "success"
              ? "bg-emerald-50 border-emerald-200 text-emerald-800"
              : "bg-red-50 border-red-200 text-red-800"
          }`}
        >
          <span>{feedbackMsg.text}</span>
          <button onClick={() => setFeedbackMsg(null)} className="text-slate-400 hover:text-slate-600">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
        {statuses.map((st) => (
          <button
            key={st}
            onClick={() => setFilterStatus(st)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              filterStatus === st
                ? "bg-slate-900 text-white shadow-xs"
                : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"
            }`}
          >
            {st}
          </button>
        ))}
      </div>

      {/* Projects Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filteredProjects.map((p) => {
          const isSelected = currentProject?.id === p.id;
          const score = p.readiness_score || 0;

          return (
            <div
              key={p.id}
              className={`bg-white rounded-xl p-5 border shadow-2xs hover:shadow-xs transition flex flex-col justify-between space-y-4 ${
                isSelected ? "border-teal-500 ring-2 ring-teal-500/20" : "border-slate-200"
              }`}
            >
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                    {p.category || p.domain || "Engineering"}
                  </span>
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded border ${
                        p.status === "ACTIVE"
                          ? "bg-teal-50 text-teal-800 border-teal-200"
                          : p.status === "COMPLETED"
                          ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                          : p.status === "ARCHIVED"
                          ? "bg-slate-100 text-slate-600 border-slate-300"
                          : "bg-amber-50 text-amber-800 border-amber-200"
                      }`}
                    >
                      {p.status}
                    </span>

                    {/* Action buttons on card */}
                    {canManageProject && (
                      <button
                        onClick={() => openEditModal(p)}
                        title="Edit Project"
                        className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                    )}

                    {canManageProject && p.status !== "ARCHIVED" && (
                      <button
                        onClick={() => handleArchiveProject(p.id)}
                        title="Archive Project"
                        className="p-1 rounded text-slate-400 hover:text-amber-600 hover:bg-amber-50 transition"
                      >
                        <Archive className="w-3.5 h-3.5" />
                      </button>
                    )}

                    {canDeleteProject && (
                      <button
                        onClick={() => setDeletingProjectId(p.id)}
                        title="Delete Project"
                        className="p-1 rounded text-slate-400 hover:text-red-600 hover:bg-red-50 transition"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>

                <div>
                  <h3 className="font-bold text-slate-900 text-base">{p.name}</h3>
                  <p className="text-xs text-slate-600 mt-1 line-clamp-2">
                    {p.description || "Evidence-backed knowledge handover initiative."}
                  </p>
                </div>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 space-y-1.5 text-xs text-slate-600">
                  <div className="flex items-center justify-between">
                    <span>Handover Role:</span>
                    <strong className="text-slate-800">{p.handover_role}</strong>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Target Date:</span>
                    <strong className="text-slate-800">
                      {p.target_handover_date || p.expected_completion_date
                        ? new Date(p.target_handover_date || p.expected_completion_date!).toLocaleDateString()
                        : "Immediate"}
                    </strong>
                  </div>
                </div>

                {/* Score bar */}
                <div className="space-y-1 pt-1">
                  <div className="flex items-center justify-between text-xs font-semibold">
                    <span className="text-slate-600">Readiness Score</span>
                    <span className="text-teal-700 font-bold">{score}%</span>
                  </div>
                  <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-teal-600 h-full rounded-full transition-all duration-300"
                      style={{ width: `${score}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* Card Footer */}
              <div className="flex items-center justify-between pt-3 border-t border-slate-100 text-xs">
                <div className="flex items-center gap-3 text-slate-500">
                  <span className="flex items-center gap-1" title="Documents">
                    <FileText className="w-3.5 h-3.5" />
                    {p.documents_count || 0}
                  </span>
                  <span className="flex items-center gap-1" title="Team Members">
                    <Users className="w-3.5 h-3.5" />
                    {p.members_count || 1}
                  </span>
                </div>

                <button
                  onClick={() => {
                    setCurrentProject(p);
                    onSelectProject(p);
                  }}
                  className={`flex items-center gap-1 px-3 py-1.5 rounded-lg font-semibold text-xs transition ${
                    isSelected
                      ? "bg-teal-600 text-white"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                  }`}
                >
                  {isSelected ? "Active Workspace" : "Select Project"}
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Edit Project Modal */}
      {editingProject && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 animate-in fade-in duration-200">
          <div className="relative w-full max-w-lg bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden">
            <div className="px-6 py-4 bg-slate-900 text-white flex justify-between items-center">
              <div className="flex items-center gap-2">
                <Edit2 className="w-5 h-5 text-teal-400" />
                <h3 className="font-semibold text-base">Edit Project Workspace</h3>
              </div>
              <button
                onClick={() => setEditingProject(null)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleUpdateProject} className="p-6 space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">Project Name</label>
                <input
                  type="text"
                  required
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:outline-teal-600"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">Description</label>
                <textarea
                  rows={2}
                  value={editDesc}
                  onChange={(e) => setEditDesc(e.target.value)}
                  className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:outline-teal-600"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">Category</label>
                  <select
                    value={editCategory}
                    onChange={(e) => setEditCategory(e.target.value)}
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
                  <label className="text-xs font-semibold text-slate-700 block mb-1">Status</label>
                  <select
                    value={editStatus}
                    onChange={(e) => setEditStatus(e.target.value)}
                    className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 bg-white focus:outline-teal-600"
                  >
                    <option value="PLANNING">PLANNING</option>
                    <option value="ACTIVE">ACTIVE</option>
                    <option value="ON_HOLD">ON_HOLD</option>
                    <option value="COMPLETED">COMPLETED</option>
                    <option value="ARCHIVED">ARCHIVED</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">Handover Role</label>
                <input
                  type="text"
                  value={editTargetRole}
                  onChange={(e) => setEditTargetRole(e.target.value)}
                  className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:outline-teal-600"
                />
              </div>

              <div className="pt-4 border-t border-slate-200 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setEditingProject(null)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold rounded-lg transition"
                >
                  {actionLoading ? "Saving..." : "Save Changes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      {deletingProjectId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 animate-in fade-in duration-200">
          <div className="relative w-full max-w-md bg-white rounded-xl shadow-2xl border border-slate-200 p-6 space-y-4">
            <div className="flex items-center gap-3 text-red-600">
              <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-base">Delete Project Workspace?</h3>
                <p className="text-xs text-slate-500">This action cannot be undone.</p>
              </div>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              Deleting this project will permanently remove all associated source documents, extracted findings, evidence citations, and generated handovers.
            </p>

            <div className="pt-3 border-t border-slate-100 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setDeletingProjectId(null)}
                className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-100"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={actionLoading}
                onClick={() => handleDeleteProject(deletingProjectId)}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-bold rounded-lg transition"
              >
                {actionLoading ? "Deleting..." : "Delete Project"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
