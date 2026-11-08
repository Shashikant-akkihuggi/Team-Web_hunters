"use client";

import React, { useEffect, useState } from "react";
import {
  Users2,
  UserPlus,
  ShieldCheck,
  Shield,
  Check,
  X,
  Lock,
  Mail,
  Calendar,
  Sparkles,
} from "lucide-react";
import { ProjectMember, UserRole } from "@/lib/types";
import { api } from "@/lib/api";
import { useAuth, DEMO_CREDENTIALS } from "@/lib/auth-context";

export function TeamView() {
  const { currentProject, user, switchDemoRole } = useAuth();
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [emailInput, setEmailInput] = useState("");
  const [roleInput, setRoleInput] = useState<UserRole>("INCOMING_MEMBER");
  const [isAdding, setIsAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canManage = user?.role === "ADMIN" || user?.role === "PROJECT_MANAGER";

  async function loadMembers() {
    if (!currentProject) return;
    setLoading(true);
    try {
      const data = await api.listMembers(currentProject.id);
      setMembers(data);
    } catch (e) {
      console.warn("Failed to load members:", e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadMembers();
  }, [currentProject]);

  async function handleAddMember(e: React.FormEvent) {
    e.preventDefault();
    if (!emailInput.trim() || !currentProject) return;
    setIsAdding(true);
    setError(null);
    try {
      await api.addMember(currentProject.id, emailInput.trim(), roleInput);
      setEmailInput("");
      await loadMembers();
    } catch (err: any) {
      setError(err.message || "Failed to add project member");
    } finally {
      setIsAdding(false);
    }
  }

  const roleDefinitions: Array<{
    role: UserRole;
    title: string;
    description: string;
    permissions: string[];
  }> = [
    {
      role: "ADMIN",
      title: "System Administrator",
      description: "Full platform administration, security auditing, and workspace governance.",
      permissions: [
        "Full CRUD access to all projects",
        "Upload and delete source files",
        "Perform human review & sign-offs",
        "Approve & export handover dossiers",
        "Manage project members & permissions",
      ],
    },
    {
      role: "PROJECT_MANAGER",
      title: "Project Manager (Reviewer)",
      description: "Oversees handover quality, reviews AI findings, resolves anomalies, and approves handovers.",
      permissions: [
        "Create and manage projects",
        "Upload authorized project sources",
        "Review, edit, and sign off findings",
        "Generate and approve handover dossiers",
        "Add incoming and outgoing team members",
      ],
    },
    {
      role: "OUTGOING_MEMBER",
      title: "Outgoing Team Lead / Member",
      description: "Uploads architecture documents, meeting notes, and knowledge dossier sources.",
      permissions: [
        "Upload and contribute source documents",
        "View extracted findings and verify evidence",
        "Contribute context and notes",
        "Restricted from managerial sign-offs",
      ],
    },
    {
      role: "INCOMING_MEMBER",
      title: "Incoming Team Member",
      description: "Receives the verified handover package. Protected by backend-enforced redaction.",
      permissions: [
        "View manager-approved handover reports",
        "Inspect verified evidence citations",
        "Read onboarding plan (Day 1, Week 1, Month 1)",
        "Restricted from review workspace & unapproved drafts",
      ],
    },
  ];

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs">
        <h2 className="text-lg font-bold text-slate-900">Team Governance & Role-Based Access Control</h2>
        <p className="text-xs text-slate-500 mt-1">
          Permissions are strictly enforced on the FastAPI backend, ensuring sensitive unapproved drafts and internal audit queues remain restricted.
        </p>
      </div>

      {/* Role Testing Interactive Switcher */}
      <div className="bg-slate-900 text-white p-6 rounded-xl shadow-2xs space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-teal-400" />
            <h3 className="font-bold text-sm">Interactive RBAC Role Tester</h3>
          </div>
          <span className="text-xs text-slate-400">
            Active: <strong className="text-teal-400">{user?.role}</strong> ({user?.full_name})
          </span>
        </div>
        <p className="text-xs text-slate-300">
          Switch persona instantly to experience the platform through each team member's security boundaries:
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {(["ADMIN", "PROJECT_MANAGER", "OUTGOING_MEMBER", "INCOMING_MEMBER"] as UserRole[]).map((r) => {
            const isCurrent = user?.role === r;
            const cred = DEMO_CREDENTIALS[r];

            return (
              <button
                key={r}
                onClick={() => switchDemoRole(r)}
                className={`p-3.5 rounded-xl border text-left transition ${
                  isCurrent
                    ? "bg-teal-500/20 border-teal-500 text-white shadow-xs"
                    : "bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-750 hover:text-white"
                }`}
              >
                <div className="text-xs font-bold">{cred.name}</div>
                <div className="text-[10px] text-teal-400 font-mono mt-0.5">{r}</div>
                <div className="text-[11px] text-slate-400 mt-1 truncate">{cred.email}</div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Members List & Add Form */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Members Table */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 shadow-2xs p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h3 className="font-bold text-sm text-slate-900">Project Members ({members.length})</h3>
            <span className="text-xs text-slate-500 font-medium">{currentProject?.name}</span>
          </div>

          <div className="divide-y divide-slate-100">
            {(members.length > 0 ? members : [
              { id: "1", user: { full_name: "Elena Rostova (Lead PM)", email: "pm@knowledgecontinuity.io" }, role: "PROJECT_MANAGER", joined_at: new Date().toISOString() },
              { id: "2", user: { full_name: "Sarah Jenkins (Outgoing Lead)", email: "outgoing@knowledgecontinuity.io" }, role: "OUTGOING_MEMBER", joined_at: new Date().toISOString() },
              { id: "3", user: { full_name: "Marcus Chen (Incoming Engineer)", email: "incoming@knowledgecontinuity.io" }, role: "INCOMING_MEMBER", joined_at: new Date().toISOString() },
              { id: "4", user: { full_name: "Alexander Vance (Admin)", email: "admin@knowledgecontinuity.io" }, role: "ADMIN", joined_at: new Date().toISOString() },
            ]).map((m: any, idx: number) => (
              <div key={m.id || idx} className="py-3 flex items-center justify-between text-xs">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-slate-100 text-slate-700 font-bold flex items-center justify-center shrink-0">
                    {m.user?.full_name?.charAt(0) || "U"}
                  </div>
                  <div>
                    <span className="font-bold text-slate-900 block">{m.user?.full_name || "Team Member"}</span>
                    <span className="text-slate-500 text-[11px]">{m.user?.email || "email"}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                    m.role === "ADMIN" ? "bg-purple-50 text-purple-700 border border-purple-200" :
                    m.role === "PROJECT_MANAGER" ? "bg-teal-50 text-teal-700 border border-teal-200" :
                    m.role === "OUTGOING_MEMBER" ? "bg-blue-50 text-blue-700 border border-blue-200" :
                    "bg-emerald-50 text-emerald-700 border border-emerald-200"
                  }`}>
                    {m.role}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right 1 Col: Add Member Form */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs p-6 space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <UserPlus className="w-4 h-4 text-teal-600" />
            <h3 className="font-bold text-sm text-slate-900">Add Project Member</h3>
          </div>

          {canManage ? (
            <form onSubmit={handleAddMember} className="space-y-3">
              {error && (
                <div className="p-2.5 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-xs">
                  {error}
                </div>
              )}

              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">User Email</label>
                <input
                  type="email"
                  required
                  placeholder="colleague@knowledgecontinuity.io"
                  value={emailInput}
                  onChange={(e) => setEmailInput(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 focus:outline-teal-600"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">Project Role</label>
                <select
                  value={roleInput}
                  onChange={(e) => setRoleInput(e.target.value as UserRole)}
                  className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 focus:outline-teal-600 bg-white"
                >
                  <option value="INCOMING_MEMBER">Incoming Member</option>
                  <option value="OUTGOING_MEMBER">Outgoing Member</option>
                  <option value="PROJECT_MANAGER">Project Manager</option>
                  <option value="ADMIN">Administrator</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={isAdding || !emailInput.trim()}
                className="w-full py-2 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white font-bold text-xs rounded-lg shadow-xs transition"
              >
                {isAdding ? "Assigning..." : "Assign Role to Project"}
              </button>
            </form>
          ) : (
            <p className="text-xs text-slate-500">
              Only Project Managers or Admins can assign project roles.
            </p>
          )}
        </div>
      </div>

      {/* Permissions Matrix */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs p-6 space-y-4">
        <h3 className="font-bold text-sm text-slate-900">Role Permissions Architecture</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {roleDefinitions.map((def) => (
            <div key={def.role} className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2.5">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-teal-700 block">
                  {def.role}
                </span>
                <h4 className="font-bold text-slate-900 text-xs">{def.title}</h4>
              </div>
              <p className="text-[11px] text-slate-600 leading-relaxed">{def.description}</p>
              <ul className="space-y-1 pt-2 border-t border-slate-200 text-[11px] text-slate-700">
                {def.permissions.map((p, i) => (
                  <li key={i} className="flex items-start gap-1.5">
                    <Check className="w-3.5 h-3.5 text-teal-600 shrink-0 mt-0.5" />
                    <span>{p}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
