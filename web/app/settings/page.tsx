"use client";

import useSWR from "swr";
import { fetcher, API_BASE } from "@/lib/api";
import { GlassCard } from "@/components/ui/GlassCard";
import { Server, Activity, Globe, CheckCircle, XCircle } from "lucide-react";
import type { HealthResponse } from "@/lib/types";

export default function SettingsPage() {
    const { data: health, error, isLoading } = useSWR<HealthResponse>("/health", fetcher, {
        refreshInterval: 15000,
    });

    const isHealthy = !!health && !error;

    return (
        <div className="space-y-6">
            <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-100 to-slate-400">
                Settings
            </h1>

            {/* API Connection Status */}
            <GlassCard>
                <h3 className="text-lg font-semibold text-slate-100 mb-4 flex items-center gap-2">
                    <Server className="h-5 w-5 text-primary-400" />
                    API Connection
                </h3>
                <div className="space-y-4">
                    <div className="flex items-center gap-3">
                        {isLoading ? (
                            <div className="h-4 w-4 rounded-full bg-slate-500 animate-pulse" />
                        ) : isHealthy ? (
                            <CheckCircle className="h-5 w-5 text-success-400" />
                        ) : (
                            <XCircle className="h-5 w-5 text-critical-400" />
                        )}
                        <span className="text-sm text-slate-200">
                            {isLoading ? "Checking..." : isHealthy ? "Connected" : "Disconnected"}
                        </span>
                    </div>

                    <div className="space-y-3 text-sm">
                        <div className="flex justify-between border-b border-white/5 pb-2">
                            <span className="text-slate-500 flex items-center gap-2">
                                <Globe className="h-3.5 w-3.5" /> Backend URL
                            </span>
                            <span className="text-slate-200 font-mono text-xs">{API_BASE}</span>
                        </div>
                        <div className="flex justify-between border-b border-white/5 pb-2">
                            <span className="text-slate-500 flex items-center gap-2">
                                <Activity className="h-3.5 w-3.5" /> Health Status
                            </span>
                            <span className={isHealthy ? "text-success-400" : "text-critical-400"}>
                                {isLoading ? "..." : health?.status || "unreachable"}
                            </span>
                        </div>
                        {health?.version && (
                            <div className="flex justify-between border-b border-white/5 pb-2">
                                <span className="text-slate-500">Version</span>
                                <span className="text-slate-200 font-mono text-xs">{health.version}</span>
                            </div>
                        )}
                    </div>

                    {health && (
                        <div className="mt-4">
                            <p className="text-xs text-slate-500 mb-2">Full Health Response</p>
                            <pre className="text-xs text-slate-400 bg-black/20 rounded-lg p-3 overflow-auto max-h-48 font-mono">
                                {JSON.stringify(health, null, 2)}
                            </pre>
                        </div>
                    )}
                </div>
            </GlassCard>

            {/* System Info */}
            <GlassCard>
                <h3 className="text-lg font-semibold text-slate-100 mb-4">System Information</h3>
                <div className="space-y-3 text-sm">
                    <div className="flex justify-between border-b border-white/5 pb-2">
                        <span className="text-slate-500">Frontend Framework</span>
                        <span className="text-slate-200">Next.js (App Router)</span>
                    </div>
                    <div className="flex justify-between border-b border-white/5 pb-2">
                        <span className="text-slate-500">Backend Framework</span>
                        <span className="text-slate-200">FastAPI</span>
                    </div>
                    <div className="flex justify-between border-b border-white/5 pb-2">
                        <span className="text-slate-500">Agent System</span>
                        <span className="text-slate-200">LangGraph Multi-Agent</span>
                    </div>
                    <div className="flex justify-between border-b border-white/5 pb-2">
                        <span className="text-slate-500">Knowledge Base</span>
                        <span className="text-slate-200">ChromaDB Vector Store</span>
                    </div>
                </div>
            </GlassCard>
        </div>
    );
}
