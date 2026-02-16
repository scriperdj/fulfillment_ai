"use client";

import { useState, useCallback, useRef } from "react";
import useSWR from "swr";
import Link from "next/link";
import { fetcher, uploadFile } from "@/lib/api";
import { GlassCard } from "@/components/ui/GlassCard";
import { FileUp, Upload, CheckCircle2, XCircle, Clock, Loader2 } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { cn } from "@/lib/utils";
import type { BatchListResponse, BatchUploadResponse } from "@/lib/types";

const STATUS_FILTERS = ["all", "queued", "running", "completed", "failed"] as const;

const STATUS_BADGE: Record<string, string> = {
    queued: "text-slate-300 bg-slate-500/10 border-slate-500/20",
    running: "text-primary-400 bg-primary-500/10 border-primary-500/20 animate-pulse",
    completed: "text-success-400 bg-success-500/10 border-success-500/20",
    failed: "text-critical-400 bg-critical-500/10 border-critical-500/20",
    processing: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
    pending: "text-slate-300 bg-slate-500/10 border-slate-500/20",
};

const STATUS_ICON: Record<string, typeof Clock> = {
    queued: Clock,
    running: Loader2,
    completed: CheckCircle2,
    failed: XCircle,
    processing: Loader2,
    pending: Clock,
};

function formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function BatchPage() {
    const [filter, setFilter] = useState<string>("all");
    const [dragOver, setDragOver] = useState(false);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);
    const [uploadResult, setUploadResult] = useState<BatchUploadResponse | null>(null);
    const [uploadError, setUploadError] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const { data, error: listError, mutate } = useSWR<BatchListResponse>(
        "/batch/",
        fetcher,
        { refreshInterval: 5000 }
    );

    const jobs = data?.jobs ?? [];
    const filteredJobs = jobs.filter(
        (j) => filter === "all" || j.status === filter
    );

    const handleFile = useCallback((file: File) => {
        if (!file.name.endsWith(".csv")) {
            setUploadError("Please select a .csv file");
            return;
        }
        setSelectedFile(file);
        setUploadError(null);
        setUploadResult(null);
    }, []);

    const handleDrop = useCallback(
        (e: React.DragEvent) => {
            e.preventDefault();
            setDragOver(false);
            const file = e.dataTransfer.files[0];
            if (file) handleFile(file);
        },
        [handleFile]
    );

    async function handleUpload() {
        if (!selectedFile) return;
        setUploading(true);
        setUploadError(null);
        setUploadResult(null);
        try {
            const result = await uploadFile<BatchUploadResponse>("/batch/upload", selectedFile);
            setUploadResult(result);
            setSelectedFile(null);
            mutate();
        } catch {
            setUploadError("Failed to upload CSV. Check the file format and try again.");
        } finally {
            setUploading(false);
        }
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-100 to-slate-400">
                    Batch Jobs
                </h1>
                <span className="text-xs text-slate-400 bg-white/5 px-2 py-1 rounded-full border border-white/10">
                    {jobs.length} job{jobs.length !== 1 && "s"}
                </span>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Batch Jobs Monitor (left 2/3) */}
                <div className="lg:col-span-2 space-y-4">
                    {/* Filter tabs */}
                    <div className="flex gap-2">
                        {STATUS_FILTERS.map((status) => (
                            <button
                                key={status}
                                onClick={() => setFilter(status)}
                                className={cn(
                                    "px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors",
                                    filter === status
                                        ? "bg-primary-500/20 border-primary-500/30 text-primary-400"
                                        : "bg-white/5 border-white/10 text-slate-400 hover:bg-white/10"
                                )}
                            >
                                {status.charAt(0).toUpperCase() + status.slice(1)}
                            </button>
                        ))}
                    </div>

                    {/* Job list */}
                    <GlassCard className="max-h-[700px] overflow-y-auto">
                        <div className="space-y-3">
                            {filteredJobs.map((job) => {
                                const Icon = STATUS_ICON[job.status] || Clock;
                                const badgeClass = STATUS_BADGE[job.status] || STATUS_BADGE.pending;

                                return (
                                    <Link
                                        key={job.batch_job_id}
                                        href={`/batch/${job.batch_job_id}`}
                                        className="flex items-center gap-3 p-3 rounded-lg bg-white/5 border border-white/5 hover:bg-white/10 transition-colors cursor-pointer"
                                    >
                                        <div className={cn("h-8 w-8 rounded-lg flex items-center justify-center border flex-shrink-0", badgeClass)}>
                                            <Icon className={cn("h-4 w-4", job.status === "running" && "animate-spin")} />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                <span className="text-sm font-medium text-slate-200 truncate">
                                                    {job.filename}
                                                </span>
                                                <span className={cn("text-xs px-2 py-0.5 rounded-full border font-medium", badgeClass)}>
                                                    {job.status}
                                                </span>
                                            </div>
                                            <div className="flex items-center gap-3 mt-1">
                                                <span className="text-xs text-slate-500">
                                                    {job.row_count} rows
                                                </span>
                                                {job.created_at && (
                                                    <span className="text-xs text-slate-500">
                                                        {formatDistanceToNow(new Date(job.created_at), { addSuffix: true })}
                                                    </span>
                                                )}
                                                {job.completed_at && (
                                                    <span className="text-xs text-success-400">
                                                        Completed {formatDistanceToNow(new Date(job.completed_at), { addSuffix: true })}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                        {job.error_message && (
                                            <span className="text-xs text-critical-400 truncate max-w-[200px]">
                                                {job.error_message}
                                            </span>
                                        )}
                                    </Link>
                                );
                            })}
                            {filteredJobs.length === 0 && (
                                <div className="py-12 text-center text-slate-500">
                                    <FileUp className="h-12 w-12 mx-auto opacity-20 mb-2" />
                                    {listError ? (
                                        <>
                                            <p className="text-critical-400 text-sm">Failed to load batch jobs</p>
                                            <p className="text-xs mt-1">Check that the backend API is running and accessible</p>
                                        </>
                                    ) : (
                                        <>
                                            <p>No batch jobs found</p>
                                            <p className="text-xs mt-1">Upload a CSV file to start a batch job</p>
                                        </>
                                    )}
                                </div>
                            )}
                        </div>
                    </GlassCard>
                </div>

                {/* Upload CSV Panel (right 1/3) */}
                <div className="space-y-4">
                    <GlassCard>
                        <h3 className="text-lg font-semibold text-slate-100 mb-4 flex items-center gap-2">
                            <Upload className="h-5 w-5 text-primary-400" />
                            Upload CSV
                        </h3>

                        {/* Drag and drop zone */}
                        <div
                            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                            onDragLeave={() => setDragOver(false)}
                            onDrop={handleDrop}
                            onClick={() => fileInputRef.current?.click()}
                            className={cn(
                                "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors",
                                dragOver
                                    ? "border-primary-400 bg-primary-500/10"
                                    : "border-white/10 hover:border-white/20 hover:bg-white/5"
                            )}
                        >
                            <FileUp className="h-10 w-10 mx-auto text-slate-500 mb-3" />
                            <p className="text-sm text-slate-300">
                                Drag & drop a CSV file here
                            </p>
                            <p className="text-xs text-slate-500 mt-1">
                                or click to browse
                            </p>
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept=".csv"
                                className="hidden"
                                onChange={(e) => {
                                    const file = e.target.files?.[0];
                                    if (file) handleFile(file);
                                    e.target.value = "";
                                }}
                            />
                        </div>

                        {/* Selected file info */}
                        {selectedFile && (
                            <div className="mt-4 p-3 rounded-lg bg-white/5 border border-white/5">
                                <div className="flex items-center justify-between">
                                    <span className="text-sm text-slate-200 truncate">{selectedFile.name}</span>
                                    <span className="text-xs text-slate-500 flex-shrink-0 ml-2">
                                        {formatFileSize(selectedFile.size)}
                                    </span>
                                </div>
                            </div>
                        )}

                        {/* Upload button */}
                        <button
                            onClick={handleUpload}
                            disabled={!selectedFile || uploading}
                            className="mt-4 w-full h-10 rounded-lg bg-primary-500/20 border border-primary-500/30 text-primary-400 text-sm font-medium hover:bg-primary-500/30 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                        >
                            {uploading ? (
                                <>
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                    Uploading...
                                </>
                            ) : (
                                "Upload & Process"
                            )}
                        </button>
                    </GlassCard>

                    {/* Upload result */}
                    {uploadResult && (
                        <GlassCard className="border-success-500/20">
                            <h4 className="text-sm font-medium text-success-400 mb-3 flex items-center gap-2">
                                <CheckCircle2 className="h-4 w-4" />
                                Upload Successful
                            </h4>
                            <div className="space-y-2 text-sm">
                                <div className="flex justify-between">
                                    <span className="text-slate-400">Job ID</span>
                                    <span className="text-slate-200 font-mono text-xs">{uploadResult.batch_job_id.slice(0, 8)}...</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-slate-400">File</span>
                                    <span className="text-slate-200">{uploadResult.filename}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-slate-400">Rows</span>
                                    <span className="text-slate-200">{uploadResult.row_count}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-slate-400">Status</span>
                                    <span className={cn("text-xs px-2 py-0.5 rounded-full border font-medium", STATUS_BADGE[uploadResult.status] || STATUS_BADGE.pending)}>
                                        {uploadResult.status}
                                    </span>
                                </div>
                            </div>
                        </GlassCard>
                    )}

                    {/* Upload error */}
                    {uploadError && (
                        <GlassCard className="border-critical-500/20">
                            <p className="text-sm text-critical-400">{uploadError}</p>
                        </GlassCard>
                    )}
                </div>
            </div>
        </div>
    );
}
