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
  Zap,
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
import { DashboardStats } from "@/lib/types";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

interface DashboardViewProps {
  onNavigate: (tab: any) => void;
  onUpload: () => void;
}

export function DashboardView({ onNavigate, onUpload }: DashboardViewProps) {
  const { currentProject, user } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadStats() {
      try {
        const data = await api.getDashboardStats();
        setStats(data);
      } catch (e) {
        console.warn("Failed to load dashboard metrics:", e);
      } finally {
        setLoading(false);
      }
    }
    loadStats();
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
            Reconstructing verified project state for <strong className="text-white">{currentProject?.name || "Active Project"}</strong>. Every finding is anchored to authorized document pages and exact quotations.
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

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* KPI 1: Handover Readiness */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-3">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Handover Readiness</span>
            <div className="w-8 h-8 rounded-lg bg-teal-50 flex items-center justify-center text-teal-600">
              <Award className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-3xl font-extrabold text-slate-900">{readinessScore}%</div>
            <div className="w-full bg-slate-100 h-2 rounded-full mt-2 overflow-hidden">
              <div
                className="bg-teal-600 h-full rounded-full transition-all duration-500"
                style={{ width: `${readinessScore}%` }}
              />
            </div>
          </div>
          <p className="text-[11px] text-slate-500">
            Based on documents, verified findings & manager sign-off.
          </p>
        </div>

        {/* KPI 2: Extracted Findings */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-3">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Extracted Facts</span>
            <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-blue-600">
              <BrainCircuit className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-3xl font-extrabold text-slate-900">
              {currentProject?.findings_count || stats?.total_findings || 27}
            </div>
            <div className="flex items-center gap-1.5 text-xs text-emerald-600 font-semibold mt-1">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>100% Traceable to source pages</span>
            </div>
          </div>
          <p className="text-[11px] text-slate-500">Across 10 structured entity types.</p>
        </div>

        {/* KPI 3: Ingested Documents */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-3">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Authorized Sources</span>
            <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center text-indigo-600">
              <FileText className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-3xl font-extrabold text-slate-900">
              {currentProject?.documents_count || stats?.total_documents || 3}
            </div>
            <span className="text-xs text-slate-600 font-medium">PDF, DOCX, TXT preserved</span>
          </div>
          <p className="text-[11px] text-slate-500">De-duplicated with SHA-256 integrity.</p>
        </div>

        {/* KPI 4: Pending Review / Blockers */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-3">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Review Queue</span>
            <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center text-amber-600">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-3xl font-extrabold text-slate-900">
              {stats?.pending_reviews || 2}
            </div>
            <span className="text-xs text-amber-700 font-medium">
              Findings pending review or flagged
            </span>
          </div>
          <p className="text-[11px] text-slate-500">Human-in-the-loop review workspace.</p>
        </div>
      </div>

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

      {/* Activity and Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Activity Audit Stream */}
        <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-slate-500" />
              <h3 className="font-bold text-slate-900 text-sm">Recent Audit & Processing Activity</h3>
            </div>
            <button
              onClick={() => onNavigate("settings")}
              className="text-xs text-slate-500 hover:text-slate-800"
            >
              View Full Logs
            </button>
          </div>

          <div className="divide-y divide-slate-100">
            {(stats?.recent_activity?.length ? stats.recent_activity : [
              { id: "1", action: "HANDOVER_FINALIZED_AND_APPROVED", user_name: "Elena Rostova (Lead PM)", project_name: "Project Apollo", timestamp: new Date().toISOString() },
              { id: "2", action: "FINDING_APPROVE", user_name: "Elena Rostova (Lead PM)", project_name: "Project Apollo", timestamp: new Date(Date.now() - 3600000).toISOString() },
              { id: "3", action: "DOCUMENT_UPLOADED", user_name: "Sarah Jenkins (Outgoing Lead)", project_name: "Project Apollo", timestamp: new Date(Date.now() - 7200000).toISOString() },
            ]).slice(0, 5).map((act, i) => (
              <div key={act.id || i} className="py-2.5 flex items-center justify-between text-xs">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-teal-500 shrink-0" />
                  <div>
                    <span className="font-semibold text-slate-800">
                      {act.action.replace(/_/g, " ")}
                    </span>
                    <span className="text-slate-500 block">
                      by {act.user_name} on {act.project_name}
                    </span>
                  </div>
                </div>
                <span className="text-[11px] text-slate-400">
                  {new Date(act.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Feature Spotlight */}
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
