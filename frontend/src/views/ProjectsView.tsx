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
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { Project } from "@/lib/types";

interface ProjectsViewProps {
  onNewProject: () => void;
  onSelectProject: (p: Project) => void;
}

export function ProjectsView({ onNewProject, onSelectProject }: ProjectsViewProps) {
  const { projects, currentProject, setCurrentProject, user } = useAuth();
  const [filterStatus, setFilterStatus] = useState<string>("ALL");

  const filteredProjects = projects.filter((p) => {
    if (filterStatus === "ALL") return true;
    return p.status === filterStatus;
  });

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
                    {p.domain}
                  </span>
                  <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-teal-50 text-teal-800 border border-teal-200">
                    {p.status}
                  </span>
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
                      {p.target_handover_date
                        ? new Date(p.target_handover_date).toLocaleDateString()
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
                  <span className="flex items-center gap-1">
                    <FileText className="w-3.5 h-3.5" />
                    {p.documents_count || 3}
                  </span>
                  <span className="flex items-center gap-1">
                    <Users className="w-3.5 h-3.5" />
                    {p.members_count || 4}
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
    </div>
  );
}
