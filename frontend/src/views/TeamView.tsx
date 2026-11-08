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
  Trash2,
  AlertCircle,
  Search,
  CheckCircle2,
} from "lucide-react";
import { ProjectMember, UserRole, User } from "@/lib/types";
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
  const [success, setSuccess] = useState<string | null>(null);

  // Live user search state
  const [searchResults, setSearchResults] = useState<User[]>([]);
  const [searching, setSearching] = useState(false);

  const canManage = user?.role === "ADMIN" || user?.role === "PROJECT_MANAGER";
  const isAdmin = user?.role === "ADMIN";

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

  // Live user search effect
  useEffect(() => {
    if (!emailInput.trim() || emailInput.includes("@") && emailInput.length < 3) {
      setSearchResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        const results = await api.searchUsers(emailInput.trim());
        setSearchResults(results);
      } catch {
        setSearchResults([]);
      } finally {
        setSearching(false);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [emailInput]);

  async function handleAddMember(e: React.FormEvent) {
    e.preventDefault();
    if (!emailInput.trim() || !currentProject) return;
    setIsAdding(true);
    setError(null);
    setSuccess(null);
    try {
      await api.addMember(currentProject.id, emailInput.trim(), roleInput);
      setEmailInput("");
      setSearchResults([]);
      setSuccess(`Added member successfully.`);
      setTimeout(() => setSuccess(null), 3500);
      await loadMembers();
    } catch (err: any) {
      setError(err.message || "Failed to add project member");
    } finally {
      setIsAdding(false);
    }
  }

  async function handleRoleChange(userId: string, newRole: UserRole) {
    if (!currentProject) return;
    setError(null);
    try {
      await api.updateMemberRole(currentProject.id, userId, newRole);
      setSuccess("Member role updated successfully.");
      setTimeout(() => setSuccess(null), 3000);
      await loadMembers();
    } catch (err: any) {
      setError(err.message || "Failed to update member role");
    }
  }

  async function handleRemoveMember(userId: string) {
    if (!currentProject) return;
    if (!confirm("Are you sure you want to remove this member from the project?")) return;
    setError(null);
    try {
      await api.removeMember(currentProject.id, userId);
      setSuccess("Member removed from project.");
      setTimeout(() => setSuccess(null), 3000);
      await loadMembers();
    } catch (err: any) {
      setError(err.message || "Failed to remove member");
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
      title: "Project / System Admin",
      description: "Full workspace governance, role management, member additions, and handover deletion.",
      permissions: [
        "Manage project settings and archive",
        "Add and remove project members",
        "Assign and update roles (ADMIN, PM, OUTGOING, INCOMING)",
        "Review and approve handover dossiers",
        "Delete project workspace",
      ],
    },
    {
      role: "PROJECT_MANAGER",
      title: "Project Manager (Reviewer)",
      description: "Oversees handover quality, reviews AI findings, resolves anomalies, and approves handovers.",
      permissions: [
        "Create and manage project information",
        "Upload authorized project sources",
        "Review, edit, and sign off findings",
        "Generate and approve handover dossiers",
        "Add permitted project members",
      ],
    },
    {
      role: "OUTGOING_MEMBER",
      title: "Outgoing Team Lead / Member",
      description: "Uploads architecture documents, meeting notes, and knowledge dossier sources.",
      permissions: [
        "Upload and contribute source documents",
        "View extracted findings and verify evidence",
        "Contribute context, notes, and task progress",
        "Restricted from managerial sign-offs",
      ],
    },
    {
      role: "INCOMING_MEMBER",
      title: "Incoming Team Member",
      description: "Receives the verified handover package. Protected by backend-enforced redaction.",
      permissions: [
        "View manager-approved handover reports",
        "Inspect verified evidence citations & sources",
        "Read structured onboarding timeline (Day 1, Week 1)",
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

      {/* Feedback Alerts */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-800 text-xs font-medium flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-slate-400 hover:text-slate-600">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {success && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-xs font-medium flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{success}</span>
          </div>
          <button onClick={() => setSuccess(null)} className="text-slate-400 hover:text-slate-600">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Members List & Add Form */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Members Table */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 shadow-2xs p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h3 className="font-bold text-sm text-slate-900">Project Members ({members.length})</h3>
            <span className="text-xs text-slate-500 font-medium">{currentProject?.name}</span>
          </div>

          <div className="divide-y divide-slate-100">
            {members.map((m: any) => (
              <div key={m.id} className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-slate-100 text-slate-700 font-bold flex items-center justify-center shrink-0">
                    {m.user?.full_name?.charAt(0) || "U"}
                  </div>
                  <div>
                    <span className="font-bold text-slate-900 block">{m.user?.full_name || "Team Member"}</span>
                    <span className="text-slate-500 text-[11px]">{m.user?.email || "email"}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {/* Role select (allowed for ADMIN) */}
                  {isAdmin ? (
                    <select
                      value={m.role}
                      onChange={(e) => handleRoleChange(m.user_id, e.target.value as UserRole)}
                      className="text-xs border border-slate-200 rounded-md px-2 py-1 bg-white font-medium focus:outline-teal-500"
                    >
                      <option value="ADMIN">ADMIN</option>
                      <option value="PROJECT_MANAGER">PROJECT_MANAGER</option>
                      <option value="OUTGOING_MEMBER">OUTGOING_MEMBER</option>
                      <option value="INCOMING_MEMBER">INCOMING_MEMBER</option>
                    </select>
                  ) : (
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        m.role === "ADMIN"
                          ? "bg-purple-50 text-purple-700 border border-purple-200"
                          : m.role === "PROJECT_MANAGER"
                          ? "bg-teal-50 text-teal-700 border border-teal-200"
                          : m.role === "OUTGOING_MEMBER"
                          ? "bg-blue-50 text-blue-700 border border-blue-200"
                          : "bg-emerald-50 text-emerald-700 border border-emerald-200"
                      }`}
                    >
                      {m.role}
                    </span>
                  )}

                  {/* Remove Member button (allowed for ADMIN) */}
                  {isAdmin && members.length > 1 && (
                    <button
                      onClick={() => handleRemoveMember(m.user_id)}
                      title="Remove member"
                      className="p-1.5 rounded text-slate-400 hover:text-red-600 hover:bg-red-50 transition"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right 1 Col: Add Member Card with Live Search */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs p-6 space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <UserPlus className="w-4 h-4 text-teal-600" />
            <h3 className="font-bold text-sm text-slate-900">Add Registered Member</h3>
          </div>

          <form onSubmit={handleAddMember} className="space-y-3">
            <div className="relative">
              <label className="text-xs font-semibold text-slate-700 block mb-1">
                User Email <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
                <input
                  type="email"
                  required
                  placeholder="colleague@webhunter.org"
                  value={emailInput}
                  onChange={(e) => setEmailInput(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg pl-9 pr-3 py-2 focus:outline-teal-600"
                />
              </div>

              {/* Autocomplete Dropdown */}
              {searchResults.length > 0 && (
                <div className="absolute left-0 right-0 top-full mt-1 bg-white border border-slate-200 rounded-lg shadow-lg z-20 max-h-40 overflow-y-auto divide-y divide-slate-100">
                  {searchResults.map((u) => (
                    <button
                      key={u.id}
                      type="button"
                      onClick={() => {
                        setEmailInput(u.email);
                        setSearchResults([]);
                      }}
                      className="w-full text-left p-2 hover:bg-slate-50 transition text-xs flex items-center justify-between"
                    >
                      <span className="font-medium text-slate-900">{u.full_name}</span>
                      <span className="text-slate-500 text-[11px]">{u.email}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">Project Role</label>
              <select
                value={roleInput}
                onChange={(e) => setRoleInput(e.target.value as UserRole)}
                className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white focus:outline-teal-600 font-medium"
              >
                <option value="INCOMING_MEMBER">INCOMING_MEMBER (Recipient)</option>
                <option value="OUTGOING_MEMBER">OUTGOING_MEMBER (Contributor)</option>
                <option value="PROJECT_MANAGER">PROJECT_MANAGER (Reviewer)</option>
                <option value="ADMIN">ADMIN (Workspace Governor)</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={isAdding || !emailInput.trim()}
              className="w-full py-2 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white text-xs font-bold rounded-lg shadow-xs transition"
            >
              {isAdding ? "Adding..." : "Add to Project"}
            </button>
          </form>

          <p className="text-[11px] text-slate-500 pt-2 border-t border-slate-100">
            Adding an existing team member gives them immediate project access according to their role. Duplicate assignments are rejected automatically.
          </p>
        </div>
      </div>

      {/* Role Definitions Matrix */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs p-6 space-y-4">
        <h3 className="font-bold text-sm text-slate-900">Role-Based Permission Matrix</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {roleDefinitions.map((rd) => (
            <div key={rd.role} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2.5">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-teal-700 font-mono">
                  {rd.role}
                </span>
                <h4 className="font-bold text-slate-900 text-xs mt-0.5">{rd.title}</h4>
                <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">{rd.description}</p>
              </div>

              <div className="pt-2 border-t border-slate-200/60 space-y-1.5">
                {rd.permissions.map((perm, i) => (
                  <div key={i} className="flex items-start gap-1.5 text-[11px] text-slate-700">
                    <Check className="w-3 h-3 text-teal-600 shrink-0 mt-0.5" />
                    <span>{perm}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
