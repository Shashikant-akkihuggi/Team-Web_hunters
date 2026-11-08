"use client";

import React from "react";
import { useAuth } from "@/lib/auth-context";
import { FolderPlus, UploadCloud, ShieldAlert, Award, Calendar, ExternalLink } from "lucide-react";

interface TopNavProps {
  onNewProject: () => void;
  onUpload: () => void;
}

export function TopNav({ onNewProject, onUpload }: TopNavProps) {
  const { currentProject, user } = useAuth();
  const isIncoming = user?.role === "INCOMING_MEMBER";

  const score = currentProject?.readiness_score || 0;
  const scoreColor =
    score >= 80 ? "text-emerald-700 bg-emerald-50 border-emerald-200" :
    score >= 50 ? "text-teal-700 bg-teal-50 border-teal-200" :
    "text-amber-700 bg-amber-50 border-amber-200";

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between shrink-0 shadow-2xs z-20">
      {/* Left: Project title & metadata */}
      <div className="flex items-center gap-4 min-w-0">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-slate-900 truncate">
              {currentProject?.name || "Select or Create a Project"}
            </h2>
            <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
              {currentProject?.domain || "Engineering"}
            </span>
          </div>
          <div className="flex items-center gap-3 text-xs text-slate-500 mt-0.5">
            <span className="flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5 text-slate-400" />
              Target: {currentProject?.target_handover_date ? new Date(currentProject.target_handover_date).toLocaleDateString() : "Immediate Sprint"}
            </span>
            <span>•</span>
            <span>Handover Role: <strong className="text-slate-700 font-medium">{currentProject?.handover_role || "Incoming Engineer"}</strong></span>
          </div>
        </div>
      </div>

      {/* Right: Readiness Score & Action Buttons */}
      <div className="flex items-center gap-3">
        {/* Handover Readiness Score Pill */}
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-semibold ${scoreColor}`}>
          <Award className="w-4 h-4" />
          <span>Handover Readiness:</span>
          <span className="font-bold text-sm">{score}%</span>
        </div>

        {/* Action Buttons */}
        {!isIncoming && (
          <button
            onClick={onUpload}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold rounded-lg shadow-xs transition"
          >
            <UploadCloud className="w-4 h-4" />
            Ingest Sources
          </button>
        )}

        <button
          onClick={onNewProject}
          className="flex items-center gap-1.5 px-3 py-1.5 border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg transition"
        >
          <FolderPlus className="w-4 h-4 text-slate-500" />
          New Project
        </button>
      </div>
    </header>
  );
}
