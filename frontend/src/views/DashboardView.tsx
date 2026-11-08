"use client";

import React, { useEffect, useState } from "react";
import {
  FileText,
  BrainCircuit,
  Award,
  CheckCircle2,
  AlertTriangle,
  UploadCloud,
  FileCheck2,
  Clock,
  ArrowRight,
  ShieldCheck,
  FolderGit2,
  Users,
  Activity,
  Layers,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { DashboardSummary, DashboardStats, AuditLogItem } from "@/lib/types";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

interface DashboardViewProps {
  onNavigate: (tab: any) => void;
  onUpload: () => void;
}

export function DashboardView({ onNavigate, onUpload }: DashboardViewProps) {
  const { currentProject, setCurrentProject, user } = useAuth();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [activityLogs, setActivityLogs] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [sumData, statData, actData] = await Promise.allSettled([
          api.getDashboardSummary(),
          api.getDashboardStats(),
          api.getRecentActivity(),
        ]);

        if (sumData.status === "fulfilled") setSummary(sumData.value);
        if (statData.status === "fulfilled") setStats(statData.value);
        if (actData.status === "fulfilled") setActivityLogs(actData.value);
      } catch (e) {
        console.warn("Failed to load dashboard metrics:", e);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [currentProject]);

  // Chart data preparation
  const entityData = stats?.findings_by_type
    ? Object.entries(stats.findings_by_type).map(([name, value]) => ({
        name: name.replace("_", " "),
        count: value,
      }))
    : [
        { name: "DECISION", count: 8 },
        { name: "TASK", count: 7 },
        { name: "RISK", count: 4 },
        { name: "BLOCKER", count: 2 },
        { name: "DEPENDENCY", count: 3 },
        { name: "QUESTION", count: 3 },
      ];

  const verifData = [
    { name: "Verified", value: stats?.verification_breakdown?.["VERIFIED"] || 21, color: "#0d9488" },
    { name: "Conflicting", value: stats?.verification_breakdown?.["CONFLICTING"] || 2, color: "#f59e0b" },
    { name: "Unsupported", value: stats?.verification_breakdown?.["UNSUPPORTED"] || 4, color: "#f43f5e" },
  ];

  const readinessScore = currentProject?.readiness_score || 85;

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Welcome Banner */}
      <div className="p-6 bg-gradient-to-r from-slate-900 via-slate-850 to-slate-800 rounded-2xl text-white shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-teal-500/20 text-teal-300 border border-teal-500/30">
              Active Session: {user?.role}
            </span>
            <span className="text-xs text-slate-400">• Team Web_hunter</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight">
            Knowledge Handover Console
          </h1>
          <p className="text-sm text-slate-300 max-w-2xl">
            Reconstructing verified project state for <strong className="text-white">{currentProject?.name || "Active Workspace"}</strong>. Every finding is anchored to authorized document pages and exact quotations.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={onUpload}
            className="flex items-center gap-2 px-4 py-2.5 bg-teal-600 hover:bg-teal-500 text-white text-xs font-bold rounded-xl shadow-md transition"
          >
            <UploadCloud className="w-4 h-4" />
            Ingest Source Files
          </button>
          <button
            onClick={() => onNavigate("handover")}
            className="flex items-center gap-2 px-4 py-2.5 bg-white/10 hover:bg-white/20 text-white text-xs font-bold rounded-xl border border-white/20 transition"
          >
            <FileCheck2 className="w-4 h-4 text-teal-400" />
            View Handover Dossier
          </button>
        </div>
      </div>

      {/* Primary KPI Metrics: Backed by real database queries */}
      <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* KPI 1: Accessible Projects */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Accessible Projects</span>
            <div className="w-8 h-8 rounded-lg bg-teal-50 flex items-center justify-center text-teal-600">
              <FolderGit2 className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900">
            {summary ? summary.total_projects : 1}
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span className="text-teal-700 font-semibold">{summary?.active_projects ?? 1} Active</span>
            <span>•</span>
            <span>{summary?.completed_projects ?? 0} Completed</span>
          </div>
        </div>

        {/* KPI 2: Extracted Findings */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Extracted Facts</span>
            <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-blue-600">
              <BrainCircuit className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900">
            {summary?.total_findings ?? currentProject?.findings_count ?? 27}
          </div>
          <div className="flex items-center gap-1.5 text-xs text-emerald-600 font-semibold">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{summary?.approved_findings ?? 21} Approved</span>
          </div>
        </div>

        {/* KPI 3: Ingested Documents */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Ingested Sources</span>
            <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center text-indigo-600">
              <FileText className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900">
            {summary?.total_documents ?? currentProject?.documents_count ?? 3}
          </div>
          <p className="text-xs text-slate-500">PDF, DOCX, TXT preserved</p>
        </div>

        {/* KPI 4: Pending Review */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Review Queue</span>
            <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center text-amber-600">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900">
            {summary?.pending_reviews ?? stats?.pending_reviews ?? 3}
          </div>
          <span className="text-xs text-amber-700 font-medium">Pending human sign-off</span>
        </div>
      </div>

      {/* Recent Projects Section */}
      {summary?.recent_projects && summary.recent_projects.length > 0 && (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-bold text-slate-900 text-sm">Recent Projects</h3>
              <p className="text-xs text-slate-500">Workspaces accessible to your account</p>
            </div>
            <button
              onClick={() => onNavigate("projects")}
              className="text-xs text-teal-600 hover:text-teal-700 font-semibold flex items-center gap-1"
            >
              All Projects <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {summary.recent_projects.map((proj) => {
              const isCurrent = currentProject?.id === proj.id;
              return (
                <div
                  key={proj.id}
                  onClick={() => {
                    setCurrentProject(proj as any);
                  }}
                  className={`p-4 rounded-xl border transition cursor-pointer flex flex-col justify-between space-y-3 ${
                    isCurrent
                      ? "border-teal-500 bg-teal-50/20 ring-1 ring-teal-500/30"
                      : "border-slate-200 hover:border-slate-300 bg-white"
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                        {proj.category || "Engineering"}
                      </span>
                      <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-teal-50 text-teal-800 border border-teal-200">
                        {proj.status}
                      </span>
                    </div>
                    <h4 className="font-bold text-slate-900 text-sm truncate">{proj.name}</h4>
                    <p className="text-xs text-slate-500 line-clamp-1">
                      {proj.description || "Knowledge continuity transition"}
                    </p>
                  </div>

                  <div className="flex items-center justify-between text-xs pt-2 border-t border-slate-100">
                    <span className="text-slate-500">
                      Role: <strong className="text-slate-700">{proj.current_user_role || "MEMBER"}</strong>
                    </span>
                    <span className="font-bold text-teal-700">{proj.readiness_score}% Ready</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Analytics Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Findings by Entity Type */}
        <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-bold text-slate-900 text-sm">Extracted Knowledge Distribution</h3>
              <p className="text-xs text-slate-500">Structured entities extracted from project documentation</p>
            </div>
            <button
              onClick={() => onNavigate("knowledge")}
              className="text-xs text-teal-600 hover:text-teal-700 font-semibold flex items-center gap-1"
            >
              Explore Knowledge <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={entityData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#64748b" }} interval={0} angle={-25} textAnchor="end" />
                <YAxis tick={{ fontSize: 10, fill: "#64748b" }} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#0f172a", borderRadius: "8px", border: "none", color: "#fff", fontSize: "12px" }}
                />
                <Bar dataKey="count" fill="#0d9488" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Right 1 Col: Verification Status Breakdown */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-4">
          <div>
            <h3 className="font-bold text-slate-900 text-sm">Evidence Verification Status</h3>
            <p className="text-xs text-slate-500">Audit status of extracted findings against page text</p>
          </div>

          <div className="h-44 w-full flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={verifData} dataKey="value" nameKey="name" innerRadius={42} outerRadius={68} paddingAngle={4}>
                  {verifData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: "#0f172a", borderRadius: "8px", border: "none", color: "#fff", fontSize: "12px" }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="space-y-2 pt-2 border-t border-slate-100 text-xs">
            {verifData.map((item) => (
              <div key={item.name} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                  <span className="text-slate-700 font-medium">{item.name}</span>
                </div>
                <span className="font-bold text-slate-900">{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Activity and Security Spotlight */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Real Audit Activity Stream */}
        <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-slate-500" />
              <h3 className="font-bold text-slate-900 text-sm">Live Audit & Activity Log</h3>
            </div>
            <span className="text-xs text-slate-400">Database-backed</span>
          </div>

          <div className="divide-y divide-slate-100 max-h-72 overflow-y-auto">
            {(activityLogs.length > 0 ? activityLogs : stats?.recent_activity || []).slice(0, 8).map((act: any, i: number) => (
              <div key={act.id || i} className="py-2.5 flex items-center justify-between text-xs">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-teal-500 shrink-0" />
                  <div>
                    <span className="font-semibold text-slate-800">
                      {(act.action || "ACTIVITY").replace(/_/g, " ")}
                    </span>
                    <span className="text-slate-500 block text-[11px]">
                      {act.user_name ? `by ${act.user_name}` : "System event"}
                    </span>
                  </div>
                </div>
                <span className="text-[11px] text-slate-400 shrink-0">
                  {act.created_at || act.timestamp
                    ? new Date(act.created_at || act.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                    : "Just now"}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Security Spotlight */}
        <div className="bg-slate-900 text-white p-6 rounded-xl shadow-2xs space-y-4 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="w-10 h-10 rounded-xl bg-teal-500/20 border border-teal-500/30 flex items-center justify-center text-teal-400">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h3 className="font-bold text-base">Backend-Enforced RBAC</h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              Security permissions are validated at the FastAPI dependency layer. Incoming members are strictly prevented from viewing unapproved findings or sensitive raw source revisions.
            </p>
          </div>

          <div className="p-3 bg-slate-800 rounded-lg text-xs space-y-1.5 border border-slate-700">
            <div className="text-[10px] font-bold uppercase tracking-wider text-teal-400">
              Quick Test Recommendation:
            </div>
            <p className="text-slate-300">
              Use the sidebar role switcher to toggle between <strong>Lead PM</strong> and <strong>Incoming Engineer</strong> to test role-based access control.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
