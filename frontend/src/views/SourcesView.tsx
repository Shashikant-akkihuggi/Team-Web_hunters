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
  Search,
  Filter,
  RefreshCw,
  Copy,
  ChevronRight,
  BookOpen,
  FileCode,
  AlertTriangle,
  Loader2,
} from "lucide-react";
import { DocumentItem, DocumentChunk, DocumentContent } from "@/lib/types";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

interface SourcesViewProps {
  onUpload: () => void;
}

export function SourcesView({ onUpload }: SourcesViewProps) {
  const { currentProject, user } = useAuth();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);

  // Search & Filtering
  const [searchQuery, setSearchQuery] = useState("");
  const [formatFilter, setFormatFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");

  // Document Viewer Modal States
  const [inspectingDoc, setInspectingDoc] = useState<DocumentItem | null>(null);
  const [docContent, setDocContent] = useState<DocumentContent | null>(null);
  const [docChunks, setDocChunks] = useState<DocumentChunk[]>([]);
  const [loadingViewer, setLoadingViewer] = useState(false);
  const [viewerTab, setViewerTab] = useState<"pages" | "full" | "chunks">("pages");
  const [selectedPageNum, setSelectedPageNum] = useState<number>(1);
  const [copied, setCopied] = useState(false);

  // Deletion Confirmation Dialog
  const [deletingDoc, setDeletingDoc] = useState<DocumentItem | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Action status message
  const [actionMsg, setActionMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [retryingDocId, setRetryingDocId] = useState<string | null>(null);

  const canUpload = user?.role === "ADMIN" || user?.role === "PROJECT_MANAGER" || user?.role === "OUTGOING_MEMBER";
  const canDelete = user?.role === "ADMIN" || user?.role === "PROJECT_MANAGER";

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

  async function handleOpenViewer(doc: DocumentItem) {
    setInspectingDoc(doc);
    setLoadingViewer(true);
    setViewerTab("pages");
    setSelectedPageNum(1);
    try {
      const [contentData, chunksData] = await Promise.allSettled([
        api.getDocumentContent(doc.id),
        api.getDocumentChunks(currentProject!.id, doc.id),
      ]);

      if (contentData.status === "fulfilled") {
        setDocContent(contentData.value);
      } else {
        setDocContent(null);
      }

      if (chunksData.status === "fulfilled") {
        setDocChunks(chunksData.value);
      } else {
        setDocChunks([]);
      }
    } catch (e) {
      console.warn("Failed to load document content:", e);
    } finally {
      setLoadingViewer(false);
    }
  }

  async function handleRetry(docId: string) {
    setRetryingDocId(docId);
    try {
      await api.retryDocument(docId);
      setActionMsg({ type: "success", text: "Reprocessing completed successfully." });
      setTimeout(() => setActionMsg(null), 3000);
      await loadDocs();
      if (inspectingDoc?.id === docId) {
        const updated = await api.getDocument(docId);
        handleOpenViewer(updated);
      }
    } catch (err: any) {
      setActionMsg({ type: "error", text: err.message || "Retry processing failed." });
    } finally {
      setRetryingDocId(null);
    }
  }

  async function handleDeleteConfirm() {
    if (!deletingDoc || !currentProject) return;
    setDeleting(true);
    try {
      await api.deleteDocument(currentProject.id, deletingDoc.id);
      setDeletingDoc(null);
      setActionMsg({ type: "success", text: `Document '${deletingDoc.filename}' deleted successfully.` });
      setTimeout(() => setActionMsg(null), 3000);
      await loadDocs();
    } catch (err: any) {
      setActionMsg({ type: "error", text: err.message || "Failed to delete document." });
    } finally {
      setDeleting(false);
    }
  }

  function copyTextToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  // Filtered documents
  const filteredDocuments = documents.filter((doc) => {
    const matchesSearch =
      doc.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (doc.file_type && doc.file_type.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesFormat =
      formatFilter === "ALL" || doc.file_type.toLowerCase() === formatFilter.toLowerCase();

    const matchesStatus =
      statusFilter === "ALL" ||
      doc.status.toUpperCase() === statusFilter.toUpperCase() ||
      (doc.processing_status && doc.processing_status.toUpperCase() === statusFilter.toUpperCase());

    return matchesSearch && matchesFormat && matchesStatus;
  });

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-2xs">
        <div>
          <h2 className="text-lg font-bold text-slate-900">Project Knowledge Sources</h2>
          <p className="text-xs text-slate-500 mt-1">
            Ingest authorized PDF, DOCX, and TXT documentation. Text is partitioned into page-level chunks with cryptographic integrity and full provenance.
          </p>
        </div>

        {canUpload && (
          <button
            onClick={onUpload}
            className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold rounded-lg shadow-xs transition shrink-0"
          >
            <UploadCloud className="w-4 h-4" />
            Upload Documents
          </button>
        )}
      </div>

      {actionMsg && (
        <div
          className={`p-3 rounded-lg text-xs font-medium border flex items-center justify-between ${
            actionMsg.type === "success"
              ? "bg-emerald-50 border-emerald-200 text-emerald-800"
              : "bg-red-50 border-red-200 text-red-800"
          }`}
        >
          <span>{actionMsg.text}</span>
          <button onClick={() => setActionMsg(null)} className="text-slate-400 hover:text-slate-600">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
        {/* Search Input */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
          <input
            type="text"
            placeholder="Search documents by filename or extension..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full text-xs pl-9 pr-3 py-2 border border-slate-300 rounded-lg focus:outline-teal-600"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 md:pb-0">
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg text-xs">
            <span className="text-[11px] font-semibold text-slate-500 px-1">Format:</span>
            {["ALL", "PDF", "DOCX", "TXT"].map((fmt) => (
              <button
                key={fmt}
                onClick={() => setFormatFilter(fmt)}
                className={`px-2 py-0.5 rounded text-[11px] font-semibold transition ${
                  formatFilter === fmt
                    ? "bg-white text-slate-900 shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                {fmt}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg text-xs">
            <span className="text-[11px] font-semibold text-slate-500 px-1">Status:</span>
            {["ALL", "PROCESSED", "FAILED"].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-2 py-0.5 rounded text-[11px] font-semibold transition ${
                  statusFilter === st
                    ? "bg-white text-slate-900 shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Documents Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
            Ingested Documents ({filteredDocuments.length})
          </span>
          <span className="text-xs text-slate-500">
            {currentProject?.name}
          </span>
        </div>

        {loading ? (
          <div className="py-12 text-center text-xs text-slate-400">Loading ingested files...</div>
        ) : filteredDocuments.length === 0 ? (
          <div className="p-12 text-center space-y-3">
            <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
              <FileText className="w-6 h-6" />
            </div>
            <p className="text-sm font-semibold text-slate-700">No matching documents found</p>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              Upload project architecture documents, runbooks, meeting minutes or sprint logs to extract structured findings.
            </p>
            {canUpload && (
              <button
                onClick={onUpload}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold rounded-lg shadow-xs transition"
              >
                <UploadCloud className="w-3.5 h-3.5" />
                Upload First File
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">Document</th>
                  <th className="py-3 px-3">Format</th>
                  <th className="py-3 px-3">Size</th>
                  <th className="py-3 px-3">Pages</th>
                  <th className="py-3 px-3">Chunks</th>
                  <th className="py-3 px-3">Characters</th>
                  <th className="py-3 px-3">Status</th>
                  <th className="py-3 px-3">Upload Date</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {filteredDocuments.map((doc) => {
                  const isFailed = doc.status === "FAILED" || doc.processing_status === "FAILED";
                  const isProcessing = doc.status === "PROCESSING" || doc.processing_status === "PROCESSING";
                  const isProcessed = doc.status === "PROCESSED" || doc.status === "COMPLETED";

                  return (
                    <tr key={doc.id} className="hover:bg-slate-50/60 transition">
                      {/* Document Name */}
                      <td className="py-3 px-4 font-semibold text-slate-900 max-w-xs">
                        <div className="flex items-center gap-2">
                          <FileText
                            className={`w-4 h-4 shrink-0 ${
                              doc.file_type === "pdf"
                                ? "text-rose-600"
                                : doc.file_type === "docx"
                                ? "text-blue-600"
                                : "text-slate-600"
                            }`}
                          />
                          <span className="truncate block" title={doc.filename}>
                            {doc.filename}
                          </span>
                        </div>
                        {isFailed && doc.error_message && (
                          <span className="text-[10px] text-red-600 block mt-0.5 truncate max-w-xs">
                            {doc.error_message}
                          </span>
                        )}
                      </td>

                      {/* Format */}
                      <td className="py-3 px-3">
                        <span
                          className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded border ${
                            doc.file_type === "pdf"
                              ? "bg-rose-50 text-rose-700 border-rose-200"
                              : doc.file_type === "docx"
                              ? "bg-blue-50 text-blue-700 border-blue-200"
                              : "bg-slate-100 text-slate-700 border-slate-200"
                          }`}
                        >
                          {doc.file_type.toUpperCase()}
                        </span>
                      </td>

                      {/* Size */}
                      <td className="py-3 px-3 text-slate-500 font-mono text-[11px]">
                        {(doc.file_size / 1024).toFixed(1)} KB
                      </td>

                      {/* Pages */}
                      <td className="py-3 px-3 font-semibold text-slate-800">
                        {doc.page_count || 1}
                      </td>

                      {/* Chunks */}
                      <td className="py-3 px-3">
                        <span className="inline-flex items-center gap-1 font-semibold text-teal-700 bg-teal-50 px-2 py-0.5 rounded-full border border-teal-200 text-[11px]">
                          <Layers className="w-3 h-3" />
                          {doc.chunk_count || doc.chunks_count || 0}
                        </span>
                      </td>

                      {/* Characters */}
                      <td className="py-3 px-3 text-slate-500 font-mono text-[11px]">
                        {doc.extracted_character_count ? doc.extracted_character_count.toLocaleString() : "—"}
                      </td>

                      {/* Status */}
                      <td className="py-3 px-3">
                        {isProcessed && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
                            <CheckCircle2 className="w-3 h-3" />
                            Processed
                          </span>
                        )}
                        {isProcessing && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase text-teal-700 bg-teal-50 border border-teal-200 px-2 py-0.5 rounded-full">
                            <Loader2 className="w-3 h-3 animate-spin" />
                            Processing
                          </span>
                        )}
                        {isFailed && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase text-red-700 bg-red-50 border border-red-200 px-2 py-0.5 rounded-full">
                            <AlertCircle className="w-3 h-3" />
                            Failed
                          </span>
                        )}
                      </td>

                      {/* Date */}
                      <td className="py-3 px-3 text-slate-400 font-mono text-[11px] whitespace-nowrap">
                        {new Date(doc.created_at).toLocaleDateString()}
                      </td>

                      {/* Actions */}
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {/* Inspect Document */}
                          <button
                            onClick={() => handleOpenViewer(doc)}
                            title="Inspect Extracted Text & Chunks"
                            className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-700 transition"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>

                          {/* Retry (if failed) */}
                          {isFailed && canUpload && (
                            <button
                              onClick={() => handleRetry(doc.id)}
                              disabled={retryingDocId === doc.id}
                              title="Retry Document Processing"
                              className="p-1.5 rounded-lg border border-amber-200 bg-amber-50 hover:bg-amber-100 text-amber-700 transition"
                            >
                              <RefreshCw
                                className={`w-3.5 h-3.5 ${retryingDocId === doc.id ? "animate-spin" : ""}`}
                              />
                            </button>
                          )}

                          {/* Delete Document */}
                          {canDelete && (
                            <button
                              onClick={() => setDeletingDoc(doc)}
                              title="Delete Document"
                              className="p-1.5 rounded-lg border border-slate-200 hover:border-red-200 hover:bg-red-50 text-slate-400 hover:text-red-600 transition"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ========================================================================= */}
      {/* DOCUMENT VIEWER & INSPECTOR MODAL */}
      {/* ========================================================================= */}
      {inspectingDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 animate-in fade-in duration-200">
          <div className="relative w-full max-w-4xl max-h-[90vh] bg-white rounded-xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden">
            {/* Header */}
            <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between shrink-0">
              <div className="flex items-center gap-3 min-w-0">
                <FileText className="w-5 h-5 text-teal-400 shrink-0" />
                <div className="min-w-0">
                  <h3 className="font-semibold text-base truncate">{inspectingDoc.filename}</h3>
                  <div className="flex items-center gap-2 text-xs text-slate-400 mt-0.5">
                    <span className="uppercase font-mono text-[10px]">{inspectingDoc.file_type}</span>
                    <span>•</span>
                    <span>{(inspectingDoc.file_size / 1024).toFixed(1)} KB</span>
                    <span>•</span>
                    <span>{inspectingDoc.page_count} Pages</span>
                    <span>•</span>
                    <span>{docChunks.length} Chunks</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {inspectingDoc.status === "FAILED" && canUpload && (
                  <button
                    onClick={() => handleRetry(inspectingDoc.id)}
                    disabled={retryingDocId === inspectingDoc.id}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold rounded-lg transition"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${retryingDocId === inspectingDoc.id ? "animate-spin" : ""}`} />
                    Retry Processing
                  </button>
                )}
                <button
                  onClick={() => setInspectingDoc(null)}
                  className="text-slate-400 hover:text-white p-1 rounded-lg"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Error banner if failed */}
            {inspectingDoc.status === "FAILED" && (
              <div className="p-3 bg-red-50 border-b border-red-200 text-xs text-red-800 flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                <div>
                  <strong className="block font-semibold">Processing Failed:</strong>
                  <span>{inspectingDoc.processing_error || inspectingDoc.error_message || "Unknown error."}</span>
                </div>
              </div>
            )}

            {/* Sub-tabs */}
            <div className="flex items-center justify-between px-6 border-b border-slate-200 bg-slate-50 shrink-0">
              <div className="flex gap-4">
                <button
                  onClick={() => setViewerTab("pages")}
                  className={`py-3 text-xs font-semibold border-b-2 flex items-center gap-1.5 transition ${
                    viewerTab === "pages"
                      ? "border-teal-600 text-teal-700"
                      : "border-transparent text-slate-500 hover:text-slate-800"
                  }`}
                >
                  <BookOpen className="w-3.5 h-3.5" />
                  Page Navigator ({docContent?.pages?.length || inspectingDoc.page_count || 1})
                </button>

                <button
                  onClick={() => setViewerTab("full")}
                  className={`py-3 text-xs font-semibold border-b-2 flex items-center gap-1.5 transition ${
                    viewerTab === "full"
                      ? "border-teal-600 text-teal-700"
                      : "border-transparent text-slate-500 hover:text-slate-800"
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" />
                  Full Extracted Text
                </button>

                <button
                  onClick={() => setViewerTab("chunks")}
                  className={`py-3 text-xs font-semibold border-b-2 flex items-center gap-1.5 transition ${
                    viewerTab === "chunks"
                      ? "border-teal-600 text-teal-700"
                      : "border-transparent text-slate-500 hover:text-slate-800"
                  }`}
                >
                  <Layers className="w-3.5 h-3.5" />
                  Text Chunks ({docChunks.length})
                </button>
              </div>

              {docContent && (
                <button
                  onClick={() => copyTextToClipboard(docContent.full_text)}
                  className="flex items-center gap-1 text-xs text-slate-600 hover:text-slate-900 font-medium py-1 px-2 rounded hover:bg-slate-200 transition"
                >
                  <Copy className="w-3.5 h-3.5" />
                  {copied ? "Copied!" : "Copy Full Text"}
                </button>
              )}
            </div>

            {/* Viewer Content Body */}
            <div className="flex-1 overflow-y-auto p-6">
              {loadingViewer ? (
                <div className="py-16 text-center text-xs text-slate-400">Loading document text...</div>
              ) : viewerTab === "pages" ? (
                <div className="space-y-4">
                  {/* Page selector buttons */}
                  {docContent?.pages && docContent.pages.length > 1 && (
                    <div className="flex items-center gap-1.5 overflow-x-auto pb-2 border-b border-slate-100">
                      <span className="text-[11px] font-semibold text-slate-400 mr-1">Pages:</span>
                      {docContent.pages.map((p) => (
                        <button
                          key={p.page_number}
                          onClick={() => setSelectedPageNum(p.page_number)}
                          className={`px-3 py-1 rounded text-xs font-semibold transition ${
                            selectedPageNum === p.page_number
                              ? "bg-teal-600 text-white shadow-xs"
                              : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                          }`}
                        >
                          Page {p.page_number}
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Selected Page Text */}
                  {(() => {
                    const currentPage = docContent?.pages?.find((p) => p.page_number === selectedPageNum) ||
                      docContent?.pages?.[0];

                    if (!currentPage) {
                      return (
                        <div className="p-8 text-center text-xs text-slate-400 bg-slate-50 rounded-xl border border-slate-200">
                          No page text available.
                        </div>
                      );
                    }

                    return (
                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-xs text-slate-500">
                          <span className="font-semibold text-slate-700">
                            Page {currentPage.page_number} of {docContent?.pages?.length || 1}
                          </span>
                          <span className="font-mono text-[11px]">
                            {currentPage.char_count.toLocaleString()} characters
                          </span>
                        </div>
                        <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl font-mono text-xs text-slate-800 whitespace-pre-wrap leading-relaxed max-h-[50vh] overflow-y-auto select-text">
                          {currentPage.extracted_text}
                        </div>
                      </div>
                    );
                  })()}
                </div>
              ) : viewerTab === "full" ? (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span className="font-semibold text-slate-700">Full Normalized Document Text</span>
                    <span className="font-mono text-[11px]">
                      {docContent?.extracted_character_count?.toLocaleString() || 0} characters
                    </span>
                  </div>
                  <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl font-mono text-xs text-slate-800 whitespace-pre-wrap leading-relaxed max-h-[55vh] overflow-y-auto select-text">
                    {docContent?.full_text || "No text available."}
                  </div>
                </div>
              ) : (
                /* Chunks Tab */
                <div className="space-y-3">
                  <div className="text-xs text-slate-500">
                    Document partitioned into <strong className="text-slate-800">{docChunks.length}</strong> semantic chunks with character offsets.
                  </div>

                  <div className="space-y-3 max-h-[55vh] overflow-y-auto pr-1">
                    {docChunks.map((chunk) => (
                      <div
                        key={chunk.id}
                        className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-2 text-xs"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 rounded font-mono font-bold bg-teal-50 text-teal-800 border border-teal-200 text-[10px]">
                              Chunk #{chunk.chunk_index}
                            </span>
                            <span className="text-slate-500 font-medium">
                              Page {chunk.page_start || chunk.page_number}
                              {chunk.page_end && chunk.page_end !== (chunk.page_start || chunk.page_number)
                                ? ` - ${chunk.page_end}`
                                : ""}
                            </span>
                          </div>
                          <span className="text-[11px] font-mono text-slate-400">
                            Offset: {chunk.char_start} - {chunk.char_end}
                          </span>
                        </div>

                        <div className="p-2.5 bg-white border border-slate-200 rounded-lg font-mono text-[11px] text-slate-700 whitespace-pre-wrap leading-relaxed">
                          {chunk.text_content}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* DELETE CONFIRMATION MODAL */}
      {/* ========================================================================= */}
      {deletingDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 animate-in fade-in duration-200">
          <div className="relative w-full max-w-md bg-white rounded-xl shadow-2xl border border-slate-200 p-6 space-y-4">
            <div className="flex items-center gap-3 text-red-600">
              <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-base">Delete Document?</h3>
                <p className="text-xs text-slate-500 truncate max-w-xs">{deletingDoc.filename}</p>
              </div>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              Are you sure you want to delete this document? All associated page text, generated chunks, and extracted knowledge findings anchored to this document will be permanently removed.
            </p>

            <div className="pt-3 border-t border-slate-100 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setDeletingDoc(null)}
                className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-100"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={deleting}
                onClick={handleDeleteConfirm}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-bold rounded-lg transition"
              >
                {deleting ? "Deleting..." : "Delete Document"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
