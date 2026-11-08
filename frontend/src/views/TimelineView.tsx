"use client";

import React, { useEffect, useState } from "react";
import {
  Milestone,
  CheckCircle2,
  Calendar,
  Clock,
  AlertTriangle,
  FileText,
  User,
  Filter,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export function TimelineView() {
  const { currentProject } = useAuth();
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState<string>("ALL");

  useEffect(() => {
    async function loadTimeline() {
      if (!currentProject) return;
      setLoading(true);
      try {
        const data = await api.getTimeline(currentProject.id);
        setItems(data);
      } catch (e) {
        console.warn("Failed to load timeline:", e);
      } finally {
        setLoading(false);
      }
    }
    loadTimeline();
  }, [currentProject]);

  const filteredItems = items.filter((item) => {
    if (filterType === "ALL") return true;
    return item.entity_type === filterType;
  });

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-2xs">
        <div>
          <h2 className="text-lg font-bold text-slate-900">Project Chronology & Decision Timeline</h2>
          <p className="text-xs text-slate-500 mt-1">
            Chronological reconstruction of major architectural decisions, deadlines, and project milestones.
          </p>
        </div>

        {/* Filter buttons */}
        <div className="flex items-center gap-1.5 text-xs">
          {["ALL", "DECISION", "MILESTONE", "DEADLINE", "TASK"].map((t) => (
            <button
              key={t}
              onClick={() => setFilterType(t)}
              className={`px-3 py-1.5 rounded-lg font-semibold transition ${
                filterType === t
                  ? "bg-slate-900 text-white shadow-xs"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {t === "ALL" ? "All Timeline Events" : t}
            </button>
          ))}
        </div>
      </div>

      {/* Timeline Stream */}
      {loading ? (
        <div className="p-16 text-center text-xs text-slate-500">Loading chronological timeline...</div>
      ) : filteredItems.length === 0 ? (
        <div className="bg-white p-16 rounded-xl border border-slate-200 text-center space-y-2">
          <Milestone className="w-10 h-10 text-slate-300 mx-auto" />
          <h3 className="text-sm font-semibold text-slate-700">No timeline items recorded</h3>
          <p className="text-xs text-slate-500">Ingest source documents containing dates, decisions, or milestones.</p>
        </div>
      ) : (
        <div className="relative pl-6 space-y-6 before:absolute before:left-3 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
          {filteredItems.map((item, idx) => {
            const isDecision = item.entity_type === "DECISION";
            const isMilestone = item.entity_type === "MILESTONE";
            const isDeadline = item.entity_type === "DEADLINE";

            const badgeColor =
              isDecision ? "bg-teal-500 text-white" :
              isMilestone ? "bg-blue-600 text-white" :
              isDeadline ? "bg-amber-500 text-white" :
              "bg-slate-700 text-white";

            return (
              <div key={item.id || idx} className="relative group">
                {/* Timeline node icon */}
                <div
                  className={`absolute -left-6 top-1.5 w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold shadow-xs ${badgeColor}`}
                >
                  {isDecision ? "D" : isMilestone ? "M" : isDeadline ? "DL" : "T"}
                </div>

                {/* Card */}
                <div className="ml-3 bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-2.5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                        {item.entity_type}
                      </span>
                      {item.deadline && (
                        <span className="flex items-center gap-1 text-xs font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                          <Calendar className="w-3 h-3" />
                          Target: {item.deadline}
                        </span>
                      )}
                    </div>

                    <span className="text-[11px] text-slate-400 flex items-center gap-1">
                      <FileText className="w-3 h-3" />
                      Page {item.page_number || 1}
                    </span>
                  </div>

                  <h3 className="text-sm font-bold text-slate-900">{item.title}</h3>
                  <p className="text-xs text-slate-600 leading-relaxed">{item.description}</p>

                  <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs text-slate-500">
                    <div className="flex items-center gap-1">
                      <User className="w-3.5 h-3.5 text-slate-400" />
                      <span>Owner: <strong className="text-slate-700">{item.owner || "Team / Stated in Source"}</strong></span>
                    </div>

                    <span className="text-[11px] font-medium text-emerald-600 flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Status: {item.status}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
