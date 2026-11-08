"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { User, UserRole, Project } from "./types";
import { api, setToken, removeToken } from "./api";

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, full_name: string, password: string, role: string) => Promise<void>;
  logout: () => void;
  switchDemoRole: (role: UserRole) => Promise<void>;
  currentProject: Project | null;
  setCurrentProject: (p: Project | null) => void;
  projects: Project[];
  refreshProjects: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const DEMO_CREDENTIALS: Record<UserRole, { email: string; name: string; role: UserRole }> = {
  ADMIN: { email: "admin@knowledgecontinuity.io", name: "Alexander Vance (Admin)", role: "ADMIN" },
  PROJECT_MANAGER: { email: "pm@knowledgecontinuity.io", name: "Elena Rostova (Lead PM)", role: "PROJECT_MANAGER" },
  OUTGOING_MEMBER: { email: "outgoing@knowledgecontinuity.io", name: "Sarah Jenkins (Outgoing Lead)", role: "OUTGOING_MEMBER" },
  INCOMING_MEMBER: { email: "incoming@knowledgecontinuity.io", name: "Marcus Chen (Incoming Engineer)", role: "INCOMING_MEMBER" },
};

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProject, setCurrentProject] = useState<Project | null>(null);

  // Auto-login default user on mount
  useEffect(() => {
    async function initAuth() {
      try {
        const me = await api.getMe();
        setUser(me);
        await loadProjects();
      } catch {
        // Fallback to default PM user
        try {
          const res = await api.login("pm@knowledgecontinuity.io", "Password123!");
          setToken(res.access_token);
          setUser(res.user);
          await loadProjects();
        } catch {
          // If backend offline, set demo user
          setUser({
            id: "demo-pm",
            email: "pm@knowledgecontinuity.io",
            full_name: "Elena Rostova (Lead PM)",
            role: "PROJECT_MANAGER",
            is_active: true,
            created_at: new Date().toISOString(),
          });
        }
      } finally {
        setIsLoading(false);
      }
    }
    initAuth();
  }, []);

  async function loadProjects() {
    try {
      const list = await api.listProjects();
      setProjects(list);
      if (list.length > 0 && !currentProject) {
        setCurrentProject(list[0]);
      }
    } catch (e) {
      console.warn("Failed to load projects:", e);
    }
  }

  async function login(email: string, password: string) {
    setIsLoading(true);
    try {
      const res = await api.login(email, password);
      setToken(res.access_token);
      setUser(res.user);
      await loadProjects();
    } finally {
      setIsLoading(false);
    }
  }

  async function register(email: string, full_name: string, password: string, role: string) {
    setIsLoading(true);
    try {
      const res = await api.register(email, full_name, password, role);
      setToken(res.access_token);
      setUser(res.user);
      await loadProjects();
    } finally {
      setIsLoading(false);
    }
  }

  function logout() {
    removeToken();
    setUser(null);
  }

  async function switchDemoRole(role: UserRole) {
    setIsLoading(true);
    try {
      const creds = DEMO_CREDENTIALS[role];
      const res = await api.login(creds.email, "Password123!");
      setToken(res.access_token);
      setUser(res.user);
      await loadProjects();
    } catch {
      setUser({
        id: `demo-${role.toLowerCase()}`,
        email: DEMO_CREDENTIALS[role].email,
        full_name: DEMO_CREDENTIALS[role].name,
        role: role,
        is_active: true,
        created_at: new Date().toISOString(),
      });
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        login,
        register,
        logout,
        switchDemoRole,
        currentProject,
        setCurrentProject,
        projects,
        refreshProjects: loadProjects,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
