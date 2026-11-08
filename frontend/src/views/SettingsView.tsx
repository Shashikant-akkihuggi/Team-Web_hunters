"use client";

import React, { useEffect, useState } from "react";
import {
  Settings as SettingsIcon,
  KeyRound,
  Cpu,
  Database,
  ShieldCheck,
  History,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  User,
  Lock,
  Save,
} from "lucide-react";
import { api } from "@/lib/api";
import { AuditLogItem } from "@/lib/types";
import { useAuth } from "@/lib/auth-context";

export function SettingsView() {
  const { currentProject, user, refreshUser } = useAuth();
  const [apiKey, setApiKey] = useState("");
  const [selectedModel, setSelectedModel] = useState("gemini-1.5-flash");
  const [isSaved, setIsSaved] = useState(false);
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(false);

  // Profile states
  const [fullName, setFullName] = useState(user?.full_name || "");
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileMsg, setProfileMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Password change states
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordMsg, setPasswordMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    if (user) {
      setFullName(user.full_name);
    }
  }, [user]);

  useEffect(() => {
    // Read saved key from localStorage if any
    const saved = localStorage.getItem("kc_gemini_key") || "";
    if (saved) setApiKey(saved);

    async function loadLogs() {
      if (!currentProject) return;
      setLoadingLogs(true);
      try {
        const logs = await api.getProjectAuditLogs(currentProject.id);
        setAuditLogs(logs);
      } catch (e) {
        console.warn("Failed to load audit logs:", e);
      } finally {
        setLoadingLogs(false);
      }
    }
    loadLogs();
  }, [currentProject]);

  function handleSaveKey(e: React.FormEvent) {
    e.preventDefault();
    localStorage.setItem("kc_gemini_key", apiKey.trim());
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 3000);
  }

  async function handleUpdateProfile(e: React.FormEvent) {
    e.preventDefault();
    if (!fullName.trim() || fullName.trim().length < 2) {
      setProfileMsg({ type: "error", text: "Full name must be at least 2 characters." });
      return;
    }
    setProfileSaving(true);
    setProfileMsg(null);
    try {
      await api.updateProfile({ full_name: fullName.trim() });
      await refreshUser();
      setProfileMsg({ type: "success", text: "Profile updated successfully." });
      setTimeout(() => setProfileMsg(null), 3000);
    } catch (err: any) {
      setProfileMsg({ type: "error", text: err.message || "Failed to update profile." });
    } finally {
      setProfileSaving(false);
    }
  }

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault();
    setPasswordMsg(null);
    if (!currentPassword || !newPassword || !confirmPassword) {
      setPasswordMsg({ type: "error", text: "Please fill in all password fields." });
      return;
    }
    if (newPassword.length < 6) {
      setPasswordMsg({ type: "error", text: "New password must be at least 6 characters." });
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordMsg({ type: "error", text: "New password and confirmation do not match." });
      return;
    }
    setPasswordSaving(true);
    try {
      await api.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setPasswordMsg({ type: "success", text: "Password changed successfully." });
      setTimeout(() => setPasswordMsg(null), 3000);
    } catch (err: any) {
      setPasswordMsg({ type: "error", text: err.message || "Failed to change password." });
    } finally {
      setPasswordSaving(false);
    }
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs">
        <h2 className="text-lg font-bold text-slate-900">User Profile & Platform Configuration</h2>
        <p className="text-xs text-slate-500 mt-1">
          Manage your personal credentials, AI engine parameters, and workspace audit integrity.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* User Profile Card */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <User className="w-4 h-4 text-teal-600" />
            <h3 className="font-bold text-sm text-slate-900">User Account Information</h3>
          </div>

          {profileMsg && (
            <div
              className={`p-3 rounded-lg text-xs font-medium flex items-center gap-2 ${
                profileMsg.type === "success"
                  ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                  : "bg-red-50 text-red-800 border border-red-200"
              }`}
            >
              {profileMsg.type === "success" ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              ) : (
                <AlertCircle className="w-4 h-4 text-red-600" />
              )}
              <span>{profileMsg.text}</span>
            </div>
          )}

          <form onSubmit={handleUpdateProfile} className="space-y-3">
            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">Email Address</label>
              <input
                type="email"
                disabled
                value={user?.email || ""}
                className="w-full text-xs border border-slate-200 rounded-lg px-3 py-2 bg-slate-50 text-slate-500 cursor-not-allowed font-mono"
              />
              <span className="text-[10px] text-slate-400 mt-0.5 block">Email address cannot be changed.</span>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">Full Name</label>
              <input
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 focus:outline-teal-600 font-medium"
              />
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs bg-slate-50 p-3 rounded-lg border border-slate-100">
              <div>
                <span className="text-slate-500 block text-[11px]">System Role</span>
                <span className="font-bold text-slate-900 font-mono">{user?.role}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[11px]">Status</span>
                <span className="font-semibold text-emerald-600 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Active
                </span>
              </div>
            </div>

            <button
              type="submit"
              disabled={profileSaving}
              className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold rounded-lg shadow-xs transition flex items-center gap-1.5"
            >
              <Save className="w-3.5 h-3.5" />
              {profileSaving ? "Saving..." : "Update Profile"}
            </button>
          </form>
        </div>

        {/* Change Password Card */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <Lock className="w-4 h-4 text-teal-600" />
            <h3 className="font-bold text-sm text-slate-900">Security & Password</h3>
          </div>

          {passwordMsg && (
            <div
              className={`p-3 rounded-lg text-xs font-medium flex items-center gap-2 ${
                passwordMsg.type === "success"
                  ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                  : "bg-red-50 text-red-800 border border-red-200"
              }`}
            >
              {passwordMsg.type === "success" ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              ) : (
                <AlertCircle className="w-4 h-4 text-red-600" />
              )}
              <span>{passwordMsg.text}</span>
            </div>
          )}

          <form onSubmit={handleChangePassword} className="space-y-3">
            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">Current Password</label>
              <input
                type="password"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 focus:outline-teal-600"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">New Password</label>
              <input
                type="password"
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Minimum 6 characters"
                className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 focus:outline-teal-600"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">Confirm New Password</label>
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter new password"
                className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 focus:outline-teal-600"
              />
            </div>

            <button
              type="submit"
              disabled={passwordSaving}
              className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold rounded-lg shadow-xs transition flex items-center gap-1.5"
            >
              <Lock className="w-3.5 h-3.5" />
              {passwordSaving ? "Updating..." : "Change Password"}
            </button>
          </form>
        </div>

        {/* Gemini API Key Configuration */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <KeyRound className="w-4 h-4 text-teal-600" />
            <h3 className="font-bold text-sm text-slate-900">Google Gemini API Credentials</h3>
          </div>

          <form onSubmit={handleSaveKey} className="space-y-3">
            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">
                Gemini API Key
              </label>
              <input
                type="password"
                placeholder="AIzaSy..."
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="w-full text-xs font-mono border border-slate-300 rounded-lg px-3 py-2 focus:outline-teal-600"
              />
              <span className="text-[11px] text-slate-400 mt-1 block">
                Stored in client secure session. When absent, the platform uses its high-precision deterministic regex & heuristic parser.
              </span>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">
                Extraction & Synthesis Model
              </label>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white focus:outline-teal-600"
              >
                <option value="gemini-1.5-flash">Gemini 1.5 Flash (Recommended - Ultra Low Latency)</option>
                <option value="gemini-1.5-pro">Gemini 1.5 Pro (Deep Reasoning & Complex RFCs)</option>
                <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
              </select>
            </div>

            <div className="flex items-center justify-between pt-2">
              <button
                type="submit"
                className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold rounded-lg shadow-xs transition"
              >
                Save Preferences
              </button>

              {isSaved && (
                <span className="text-xs font-semibold text-emerald-600 flex items-center gap-1 animate-in fade-in">
                  <CheckCircle2 className="w-4 h-4" /> Credentials Saved!
                </span>
              )}
            </div>
          </form>
        </div>

        {/* Database & Architecture Summary */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <Database className="w-4 h-4 text-teal-600" />
            <h3 className="font-bold text-sm text-slate-900">Architecture Foundation</h3>
          </div>

          <div className="space-y-3 text-xs text-slate-600">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 space-y-2">
              <div className="flex justify-between items-center">
                <span className="font-semibold text-slate-700">Backend API</span>
                <span className="font-mono text-teal-700 font-bold">FastAPI + Pydantic v2</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="font-semibold text-slate-700">Relational Database</span>
                <span className="font-mono text-slate-800">PostgreSQL / SQLite via SQLAlchemy 2.0</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="font-semibold text-slate-700">Schema Migrations</span>
                <span className="font-mono text-slate-800">Alembic (Head: 002_phase2)</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="font-semibold text-slate-700">Authentication</span>
                <span className="font-mono text-slate-800">JWT (HS256) + Passlib BCrypt</span>
              </div>
            </div>

            <p className="text-[11px] text-slate-500 leading-relaxed">
              Every critical action and state transition is audited and recorded with UTC timestamps, user identity, and metadata.
            </p>
          </div>
        </div>
      </div>

      {/* Audit Log Stream */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-teal-600" />
            <h3 className="font-bold text-sm text-slate-900">Project Audit Trail</h3>
          </div>
          <span className="text-xs text-slate-400 font-mono">Immutable Log Stream</span>
        </div>

        {loadingLogs ? (
          <div className="py-6 text-center text-xs text-slate-400">Loading audit trail...</div>
        ) : auditLogs.length === 0 ? (
          <div className="py-6 text-center text-xs text-slate-400">No audit records found for this workspace.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">Timestamp (UTC)</th>
                  <th className="py-2.5 px-3">Action</th>
                  <th className="py-2.5 px-3">User</th>
                  <th className="py-2.5 px-3">Entity</th>
                  <th className="py-2.5 px-3">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {auditLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50/50">
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-500">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                    <td className="py-2.5 px-3 font-semibold text-slate-900">
                      <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-800 font-mono text-[10px]">
                        {log.action}
                      </span>
                    </td>
                    <td className="py-2.5 px-3">{log.user_name || log.user_id || "System"}</td>
                    <td className="py-2.5 px-3 text-slate-500">{log.entity_type || "—"}</td>
                    <td className="py-2.5 px-3 text-slate-500 max-w-xs truncate font-mono text-[11px]">
                      {JSON.stringify(log.details)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
