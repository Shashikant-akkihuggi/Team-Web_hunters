"use client";

import React, { useState } from "react";
import { Sidebar, NavTab } from "@/components/Sidebar";
import { TopNav } from "@/components/TopNav";
import { UploadModal } from "@/components/UploadModal";
import { NewProjectModal } from "@/components/NewProjectModal";
import { AuthView } from "@/components/AuthView";
import { useAuth } from "@/lib/auth-context";

// Views
import { DashboardView } from "@/views/DashboardView";
import { ProjectsView } from "@/views/ProjectsView";
import { SourcesView } from "@/views/SourcesView";
import { KnowledgeView } from "@/views/KnowledgeView";
import { TimelineView } from "@/views/TimelineView";
import { RisksView } from "@/views/RisksView";
import { HandoverView } from "@/views/HandoverView";
import { ReviewView } from "@/views/ReviewView";
import { TeamView } from "@/views/TeamView";
import { SettingsView } from "@/views/SettingsView";

export default function Home() {
  const [activeTab, setActiveTab] = useState<NavTab>("dashboard");
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const { user, isLoading, currentProject, setCurrentProject, refreshProjects } = useAuth();

  // Authentication Loading State
  if (isLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-slate-900 text-white">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-teal-500/30 border-t-teal-400 rounded-full animate-spin"></div>
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Loading Knowledge Continuity Platform...
          </span>
        </div>
      </div>
    );
  }

  // Protected Routes: Require authenticated user
  if (!user) {
    return <AuthView />;
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-50">
      {/* 1. Left Navy Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onNewProject={() => setShowNewProjectModal(true)}
      />

      {/* 2. Main Workspace */}
      <div className="flex-1 flex flex-col h-full overflow-hidden min-w-0">
        <TopNav
          onNewProject={() => setShowNewProjectModal(true)}
          onUpload={() => setShowUploadModal(true)}
        />

        {/* View Container */}
        <main className="flex-1 overflow-y-auto p-6 lg:p-8">
          <div className="max-w-7xl mx-auto">
            {activeTab === "dashboard" && (
              <DashboardView
                onNavigate={(tab) => setActiveTab(tab)}
                onUpload={() => setShowUploadModal(true)}
              />
            )}

            {activeTab === "projects" && (
              <ProjectsView
                onNewProject={() => setShowNewProjectModal(true)}
                onSelectProject={(proj) => {
                  setCurrentProject(proj);
                  setActiveTab("dashboard");
                }}
              />
            )}

            {activeTab === "sources" && (
              <SourcesView onUpload={() => setShowUploadModal(true)} />
            )}

            {activeTab === "knowledge" && <KnowledgeView />}

            {activeTab === "timeline" && <TimelineView />}

            {activeTab === "risks" && <RisksView />}

            {activeTab === "handover" && <HandoverView />}

            {activeTab === "review" && <ReviewView />}

            {activeTab === "team" && <TeamView />}

            {activeTab === "settings" && <SettingsView />}
          </div>
        </main>
      </div>

      {/* Upload Modal */}
      {showUploadModal && currentProject && (
        <UploadModal
          projectId={currentProject.id}
          onClose={() => setShowUploadModal(false)}
          onSuccess={() => {
            refreshProjects();
          }}
        />
      )}

      {/* New Project Modal */}
      {showNewProjectModal && (
        <NewProjectModal
          onClose={() => setShowNewProjectModal(false)}
          onSuccess={async (newProj) => {
            await refreshProjects();
            setCurrentProject(newProj);
            setShowNewProjectModal(false);
          }}
        />
      )}
    </div>
  );
}
