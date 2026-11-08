"use client";

import React, { useState, useRef } from "react";
import { UploadCloud, FileText, CheckCircle2, AlertCircle, X, Loader2, Sparkles } from "lucide-react";
import { api } from "@/lib/api";

interface UploadModalProps {
  projectId: string;
  onClose: () => void;
  onSuccess: () => void;
}

export function UploadModal({ projectId, onClose, onSuccess }: UploadModalProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const allowedExtensions = [".pdf", ".docx", ".txt"];

  function handleFileSelect(selectedFiles: FileList | null) {
    if (!selectedFiles) return;
    setError(null);
    const valid: File[] = [];

    for (let i = 0; i < selectedFiles.length; i++) {
      const file = selectedFiles[i];
      const ext = "." + file.name.split(".").pop()?.toLowerCase();
      if (allowedExtensions.includes(ext)) {
        if (file.size <= 25 * 1024 * 1024) {
          valid.push(file);
        } else {
          setError(`File ${file.name} exceeds the 25MB limit.`);
        }
      } else {
        setError(`File '${file.name}' has an unsupported extension (Supported: PDF, DOCX, TXT).`);
      }
    }
    setFiles((prev) => [...prev, ...valid]);
  }

  function removeFile(index: number) {
    setFiles((prev) => prev.filter((_, idx) => idx !== index));
  }

  async function handleUpload() {
    if (files.length === 0) return;
    setIsUploading(true);
    setUploadProgress(20);
    setError(null);

    const progressInterval = setInterval(() => {
      setUploadProgress((prev) => (prev < 90 ? prev + 15 : prev));
    }, 400);

    try {
      await api.uploadDocuments(projectId, files);
      clearInterval(progressInterval);
      setUploadProgress(100);
      onSuccess();
      onClose();
    } catch (err: any) {
      clearInterval(progressInterval);
      setError(err.message || "Failed to upload and index documents.");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex justify-between items-center">
          <div className="flex items-center gap-2">
            <UploadCloud className="w-5 h-5 text-teal-400" />
            <h3 className="font-semibold text-lg">Ingest Authorized Documents</h3>
          </div>
          <button onClick={onClose} disabled={isUploading} className="text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg flex items-center gap-2 text-rose-700 text-xs font-medium">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Drag & Drop Zone */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragOver(true);
            }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragOver(false);
              handleFileSelect(e.dataTransfer.files);
            }}
            onClick={() => inputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition ${
              isDragOver
                ? "border-teal-500 bg-teal-50/50"
                : "border-slate-300 hover:border-teal-500 hover:bg-slate-50"
            }`}
          >
            <input
              ref={inputRef}
              type="file"
              multiple
              accept=".pdf,.docx,.txt"
              className="hidden"
              onChange={(e) => handleFileSelect(e.target.files)}
            />
            <UploadCloud className="w-10 h-10 mx-auto text-slate-400 mb-2" />
            <p className="text-sm font-semibold text-slate-800">
              Drag & Drop project files here, or <span className="text-teal-600 underline">browse</span>
            </p>
            <p className="text-xs text-slate-500 mt-1">Supports PDF, DOCX, TXT (up to 25MB each)</p>
          </div>

          {/* Staged File List */}
          {files.length > 0 && (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block">
                Selected Documents ({files.length})
              </span>
              {files.map((file, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-2.5 rounded-lg border border-slate-200 bg-slate-50 text-xs"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <FileText className="w-4 h-4 text-teal-600 shrink-0" />
                    <span className="font-medium text-slate-800 truncate">{file.name}</span>
                    <span className="text-slate-400 font-mono">({(file.size / 1024).toFixed(1)} KB)</span>
                  </div>
                  {!isUploading && (
                    <button
                      onClick={() => removeFile(idx)}
                      className="text-slate-400 hover:text-rose-600 p-1"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Progress Bar during Upload */}
          {isUploading && (
            <div className="space-y-1.5 p-3 bg-slate-50 border border-slate-200 rounded-lg">
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold text-slate-700 flex items-center gap-1.5">
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-teal-600" />
                  Extracting text, chunking & verifying facts...
                </span>
                <span className="font-bold text-teal-700">{uploadProgress}%</span>
              </div>
              <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-teal-600 h-full rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* AI Notice */}
          <div className="p-3 bg-teal-50 border border-teal-200 rounded-lg text-xs text-teal-900 flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-teal-600 shrink-0 mt-0.5" />
            <span>
              Uploaded files will be parsed into page-level chunks with SHA-256 deduplication. Every finding is anchored to exact source pages.
            </span>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex justify-end gap-2">
          <button
            onClick={onClose}
            disabled={isUploading}
            className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-100 transition"
          >
            Cancel
          </button>
          <button
            onClick={handleUpload}
            disabled={files.length === 0 || isUploading}
            className="flex items-center gap-1.5 px-4 py-2 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white text-xs font-bold rounded-lg shadow-sm transition"
          >
            {isUploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Processing Pipeline...
              </>
            ) : (
              `Ingest ${files.length} Document${files.length > 1 ? "s" : ""}`
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
