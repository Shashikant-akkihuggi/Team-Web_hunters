"use client";

import React, { useEffect, useState } from "react";
import {
  FileText,
  UploadCloud,
  Trash2,
  Eye,
  CheckCircle2,
  AlertCircle,
  Clock,
  Layers,
  FileCheck,
  X,
  Hash,
} from "lucide-react";
import { DocumentItem, DocumentChunk } from "@/lib/types";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

interface SourcesViewProps {
  onUpload: () => void;
}

export function SourcesView({ onUpload }: SourcesViewProps) {
  const { currentProject, user } = useAuth();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDocForChunks, setSelectedDocForChunks] = useState<DocumentItem | null>(null);
  const [chunks, setChunks] = useState<DocumentChunk[]>([]);
  const [loadingChunks, setLoadingChunks] = useState(false);

  const isIncoming = user?.role === "INCOMING_MEMBER";

  async function loadDocs() {
    if (!currentProject) return;
    setLoading(true);
    try {
      const data = await api.listDocuments(currentProject.id);
      setDocuments(data);
    } catch (e) {
      console.warn("Failed to load documents:", e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDocs();
  }, [currentProject]);

  async function handleInspectChunks(doc: DocumentItem) {
    setSelectedDocForChunks(doc);
    setLoadingChunks(true);
    try {
      const data = await api.getDocumentChunks(currentProject!.id, doc.id);
      setChunks(data);
    } catch (e) {
      console.warn("Failed to load chunks:", e);
    } finally {
      setLoadingChunks(false);
    }
  }

  async function handleDelete(docId: string) {
    if (!confirm("Are you sure you want to delete this document and its extracted findings?")) return;
    try {
      await api.deleteDocument(currentProject!.id, docId);
      await loadDocs();
    } catch (err: any) {
      alert(err.message || "Failed to delete document");
    }
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-2xs">
        <div>
          <h2 className="text-lg font-bold text-slate-900">Project Knowledge Sources</h2>
          <p className="text-xs text-slate-500 mt-1">
            Ingest authorized PDF, DOCX, and TXT documentation. Text is partitioned into page-level chunks with SHA-256 deduplication.
          </p>
        </div>

        {!isIncoming && (
          <button
            onClick={onUpload}
            className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold rounded-lg shadow-xs transition shrink-0"
          >
            <UploadCloud className="w-4 h-4" />
            Upload Documents
          </button>
        )}
      </div>

      {/* Documents Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
            Ingested Source Files ({documents.length})
          </span>
          <span className="text-xs text-slate-500">
            PyMuPDF & python-docx Parser Active
          </span>
        </div>

        {loading ? (
          <div className="p-12 text-center text-xs text-slate-500">Loading ingested sources...</div>
        ) : documents.length === 0 ? (
          <div className="p-12 text-center space-y-3">
            <FileText className="w-10 h-10 text-slate-300 mx-auto" />
            <h3 className="text-sm font-semibold text-slate-700">No project sources uploaded yet</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              Upload architectural decision records, handover dossiers, or sprint post-mortems to initiate knowledge extraction.
            </p>
            {!isIncoming && (
              <button
                onClick={onUpload}
                className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold rounded-lg shadow-xs transition"
              >
                Upload First File
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200 uppercase text-[10px]">
                <tr>
                  <th className="px-5 py-3">Document</th>
                  <th className="px-4 py-3">Format</th>
                  <th className="px-4 py-3">Pages / Chunks</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Integrity (SHA-256)</th>
                  <th className="px-4 py-3">Uploaded</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-50/70 transition">
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-teal-50 border border-teal-200 flex items-center justify-center text-teal-700 font-bold uppercase text-[10px] shrink-0">
                          {doc.file_type}
                        </div>
                        <div className="min-w-0">
                          <span className="font-bold text-slate-900 block truncate">
                            {doc.filename}
                          </span>
                          <span className="text-[11px] text-slate-400">
                            {(doc.file_size / 1024).toFixed(1)} KB
                          </span>
                        </div>
                      </div>
                    </td>

                    <td className="px-4 py-3.5">
                      <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-medium uppercase text-[10px]">
                        {doc.file_type}
                      </span>
                    </td>

                    <td className="px-4 py-3.5 text-slate-700 font-medium">
                      <span>{doc.page_count} pages</span>
                      <span className="text-slate-400 block text-[11px]">{doc.chunks_count || 1} chunks indexed</span>
                    </td>

                    <td className="px-4 py-3.5">
                      {doc.status === "COMPLETED" ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          <CheckCircle2 className="w-3 h-3" /> Indexed
                        </span>
                      ) : doc.status === "PROCESSING" ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-teal-50 text-teal-700 border border-teal-200 animate-pulse">
                          <Clock className="w-3 h-3" /> Processing
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                          <AlertCircle className="w-3 h-3" /> Failed
                        </span>
                      )}
                    </td>

                    <td className="px-4 py-3.5 text-[11px] font-mono text-slate-500">
                      <div className="flex items-center gap-1">
                        <Hash className="w-3 h-3 text-slate-400" />
                        <span>{doc.file_hash.slice(0, 12)}...</span>
                      </div>
                    </td>

                    <td className="px-4 py-3.5 text-slate-500 text-[11px]">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </td>

                    <td className="px-4 py-3.5 text-right space-x-2">
                      <button
                        onClick={() => handleInspectChunks(doc)}
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs transition"
                        title="Inspect Page Chunks"
                      >
                        <Layers className="w-3.5 h-3.5 text-slate-500" />
                        Chunks
                      </button>

                      {!isIncoming && (
                        <button
                          onClick={() => handleDelete(doc.id)}
                          className="inline-flex items-center p-1.5 rounded-md hover:bg-rose-50 text-slate-400 hover:text-rose-600 transition"
                          title="Delete Document"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Chunks Inspector Slide-over / Modal */}
      {selectedDocForChunks && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 animate-in fade-in duration-200">
          <div className="relative w-full max-w-3xl bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[85vh]">
            <div className="px-6 py-4 bg-slate-900 text-white flex justify-between items-center">
              <div className="flex items-center gap-2">
                <Layers className="w-5 h-5 text-teal-400" />
                <div>
                  <h3 className="font-semibold text-base">Page-Level Chunks Inspector</h3>
                  <p className="text-xs text-slate-400">{selectedDocForChunks.filename}</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedDocForChunks(null)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-4 flex-1">
              {loadingChunks ? (
                <div className="p-8 text-center text-xs text-slate-500">Loading chunk breakdown...</div>
              ) : chunks.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-500">No chunks found for this document.</div>
              ) : (
                chunks.map((c, i) => (
                  <div key={c.id || i} className="border border-slate-200 rounded-lg p-4 bg-slate-50/50 space-y-2">
                    <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
                      <span className="flex items-center gap-1.5">
                        <span className="px-2 py-0.5 rounded bg-teal-100 text-teal-800 font-bold">
                          Page {c.page_number}
                        </span>
                        <span className="text-slate-400">• Chunk #{c.chunk_index}</span>
                      </span>
                      <span className="text-[11px] text-slate-500 font-mono">
                        Chars {c.char_start} - {c.char_end}
                      </span>
                    </div>
                    <pre className="text-xs text-slate-800 font-sans whitespace-pre-wrap leading-relaxed bg-white p-3 rounded border border-slate-200">
                      {c.text_content}
                    </pre>
                  </div>
                ))
              )}
            </div>

            <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 flex justify-end">
              <button
                onClick={() => setSelectedDocForChunks(null)}
                className="px-4 py-2 bg-slate-900 text-white rounded-lg text-xs font-semibold hover:bg-slate-800 transition"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
