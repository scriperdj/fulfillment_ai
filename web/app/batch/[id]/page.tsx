"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { GlassCard } from "@/components/ui/GlassCard";
import {
    ArrowLeft,
    FileUp,
    CheckCircle2,
    XCircle,
    Clock,
    Loader2,
    AlertTriangle,
    Bot,
    BarChart3,
    RefreshCw,
    Mail,
    CreditCard,
    AlertCircle,
} from "lucide-react";
import { formatDistanceToNow, format } from "date-fns";
import { cn } from "@/lib/utils";
import type {
    BatchStatusResponse,
    PredictionResponse,
    DeviationResponse,
    AgentResponseRecord,
} from "@/lib/types";

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

const TABS = ["predictions", "deviations", "agent-responses"] as const;
type Tab = (typeof TABS)[number];

const TAB_LABELS: Record<Tab, string> = {
    predictions: "Predictions",
    deviations: "Deviations",
    "agent-responses": "Agent Responses",
};

const TAB_ICONS: Record<Tab, typeof BarChart3> = {
    predictions: BarChart3,
    deviations: AlertTriangle,
    "agent-responses": Bot,
};

const SEVERITY_BADGE: Record<string, string> = {
    critical: "text-critical-400 bg-critical-500/10 border-critical-500/20",
    warning: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
    info: "text-primary-400 bg-primary-500/10 border-primary-500/20",
    high: "text-critical-400 bg-critical-500/10 border-critical-500/20",
    medium: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
    low: "text-success-400 bg-success-500/10 border-success-500/20",
};

const AGENT_ICONS: Record<string, typeof Bot> = {
    shipment: RefreshCw,
    customer: Mail,
    payment: CreditCard,
    escalation: AlertCircle,
};

const AGENT_COLORS: Record<string, string> = {
    shipment: "text-primary-400 bg-primary-500/10 border-primary-500/20",
    customer: "text-ai-400 bg-ai-500/10 border-ai-500/20",
    payment: "text-success-400 bg-success-500/10 border-success-500/20",
    escalation: "text-critical-400 bg-critical-500/10 border-critical-500/20",
};

export default function BatchDetailPage() {
    const params = useParams();
    const batchId = params.id as string;
    const [activeTab, setActiveTab] = useState<Tab>("predictions");
    const [expandedAgent, setExpandedAgent] = useState<string | null>(null);

    const isTerminal = (status: string) => status === "completed" || status === "failed";

    const { data: status } = useSWR<BatchStatusResponse>(
        `/batch/${batchId}/status`,
        fetcher,
        {
            refreshInterval: (data) =>
                data && isTerminal(data.status) ? 0 : 5000,
        }
    );

    const { data: predictions } = useSWR<PredictionResponse[]>(
        activeTab === "predictions" ? `/batch/${batchId}/predictions` : null,
        fetcher
    );

    const { data: deviations } = useSWR<DeviationResponse[]>(
        activeTab === "deviations" ? `/batch/${batchId}/deviations` : null,
        fetcher
    );

    const { data: agentResponses } = useSWR<AgentResponseRecord[]>(
        activeTab === "agent-responses" ? `/batch/${batchId}/agent-responses` : null,
        fetcher
    );

    if (!status) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="h-8 w-8 animate-spin text-slate-500" />
            </div>
        );
    }

    const Icon = STATUS_ICON[status.status] || Clock;
    const badgeClass = STATUS_BADGE[status.status] || STATUS_BADGE.pending;

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center gap-4">
                <Link
                    href="/batch"
                    className="h-8 w-8 rounded-lg flex items-center justify-center bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
                >
                    <ArrowLeft className="h-4 w-4 text-slate-400" />
                </Link>
                <div className="flex-1">
                    <div className="flex items-center gap-3">
                        <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-100 to-slate-400">
                            {status.filename}
                        </h1>
                        <span className={cn("text-xs px-2 py-0.5 rounded-full border font-medium flex items-center gap-1", badgeClass)}>
                            <Icon className={cn("h-3 w-3", status.status === "running" && "animate-spin")} />
                            {status.status}
                        </span>
                    </div>
                    <div className="flex items-center gap-4 mt-1 text-xs text-slate-500">
                        <span>{status.row_count} rows</span>
                        {status.created_at && (
                            <span>Created {format(new Date(status.created_at), "MMM d, yyyy HH:mm")}</span>
                        )}
                        {status.completed_at && (
                            <span className="text-success-400">
                                Completed {formatDistanceToNow(new Date(status.completed_at), { addSuffix: true })}
                            </span>
                        )}
                        <span className="font-mono text-slate-600">{batchId.slice(0, 8)}...</span>
                    </div>
                </div>
            </div>

            {/* Error banner */}
            {status.error_message && (
                <GlassCard className="border-critical-500/20">
                    <div className="flex items-center gap-2">
                        <XCircle className="h-4 w-4 text-critical-400 flex-shrink-0" />
                        <p className="text-sm text-critical-400">{status.error_message}</p>
                    </div>
                </GlassCard>
            )}

            {/* Tab buttons */}
            <div className="flex gap-2">
                {TABS.map((tab) => {
                    const TabIcon = TAB_ICONS[tab];
                    return (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={cn(
                                "px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors flex items-center gap-1.5",
                                activeTab === tab
                                    ? "bg-primary-500/20 border-primary-500/30 text-primary-400"
                                    : "bg-white/5 border-white/10 text-slate-400 hover:bg-white/10"
                            )}
                        >
                            <TabIcon className="h-3.5 w-3.5" />
                            {TAB_LABELS[tab]}
                        </button>
                    );
                })}
            </div>

            {/* Tab content */}
            <GlassCard className="max-h-[600px] overflow-y-auto">
                {/* Predictions */}
                {activeTab === "predictions" && (
                    <div className="space-y-2">
                        {predictions && predictions.length > 0 ? (
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="text-xs text-slate-500 border-b border-white/5">
                                        <th className="text-left py-2 font-medium">Order ID</th>
                                        <th className="text-left py-2 font-medium">Delay Probability</th>
                                        <th className="text-left py-2 font-medium">Severity</th>
                                        <th className="text-left py-2 font-medium">Source</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {predictions.map((p) => (
                                        <tr key={p.id} className="border-b border-white/5 hover:bg-white/5">
                                            <td className="py-2 text-slate-200 font-mono text-xs">{p.order_id}</td>
                                            <td className="py-2">
                                                <div className="flex items-center gap-2">
                                                    <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden max-w-[120px]">
                                                        <div
                                                            className={cn(
                                                                "h-full rounded-full",
                                                                p.delay_probability > 0.7
                                                                    ? "bg-critical-400"
                                                                    : p.delay_probability > 0.4
                                                                    ? "bg-yellow-400"
                                                                    : "bg-success-400"
                                                            )}
                                                            style={{ width: `${p.delay_probability * 100}%` }}
                                                        />
                                                    </div>
                                                    <span className="text-xs text-slate-400">
                                                        {(p.delay_probability * 100).toFixed(0)}%
                                                    </span>
                                                </div>
                                            </td>
                                            <td className="py-2">
                                                <span className={cn("text-xs px-2 py-0.5 rounded-full border font-medium", SEVERITY_BADGE[p.severity] || "text-slate-400 bg-slate-500/10 border-slate-500/20")}>
                                                    {p.severity}
                                                </span>
                                            </td>
                                            <td className="py-2 text-xs text-slate-400">{p.source}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        ) : predictions && predictions.length === 0 ? (
                            <div className="py-12 text-center text-slate-500">
                                <BarChart3 className="h-12 w-12 mx-auto opacity-20 mb-2" />
                                <p>No predictions yet</p>
                                {!isTerminal(status.status) && (
                                    <p className="text-xs mt-1">Predictions will appear once processing completes</p>
                                )}
                            </div>
                        ) : (
                            <div className="flex items-center justify-center py-12">
                                <Loader2 className="h-6 w-6 animate-spin text-slate-500" />
                            </div>
                        )}
                    </div>
                )}

                {/* Deviations */}
                {activeTab === "deviations" && (
                    <div className="space-y-2">
                        {deviations && deviations.length > 0 ? (
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="text-xs text-slate-500 border-b border-white/5">
                                        <th className="text-left py-2 font-medium">Severity</th>
                                        <th className="text-left py-2 font-medium">Reason</th>
                                        <th className="text-left py-2 font-medium">Status</th>
                                        <th className="text-left py-2 font-medium">Created</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {deviations.map((d) => (
                                        <tr key={d.id} className="border-b border-white/5 hover:bg-white/5">
                                            <td className="py-2">
                                                <span className={cn("text-xs px-2 py-0.5 rounded-full border font-medium", SEVERITY_BADGE[d.severity] || "text-slate-400 bg-slate-500/10 border-slate-500/20")}>
                                                    {d.severity}
                                                </span>
                                            </td>
                                            <td className="py-2 text-slate-200 text-xs max-w-[300px] truncate">{d.reason}</td>
                                            <td className="py-2 text-xs text-slate-400">{d.status}</td>
                                            <td className="py-2 text-xs text-slate-500">
                                                {d.created_at ? formatDistanceToNow(new Date(d.created_at), { addSuffix: true }) : "—"}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        ) : deviations && deviations.length === 0 ? (
                            <div className="py-12 text-center text-slate-500">
                                <AlertTriangle className="h-12 w-12 mx-auto opacity-20 mb-2" />
                                <p>No deviations found</p>
                                {!isTerminal(status.status) && (
                                    <p className="text-xs mt-1">Deviations will appear once processing completes</p>
                                )}
                            </div>
                        ) : (
                            <div className="flex items-center justify-center py-12">
                                <Loader2 className="h-6 w-6 animate-spin text-slate-500" />
                            </div>
                        )}
                    </div>
                )}

                {/* Agent Responses */}
                {activeTab === "agent-responses" && (
                    <div className="space-y-3">
                        {agentResponses && agentResponses.length > 0 ? (
                            agentResponses.map((r) => {
                                const AgentIcon = AGENT_ICONS[r.agent_type] || Bot;
                                const colorClass = AGENT_COLORS[r.agent_type] || "text-slate-400 bg-slate-500/10 border-slate-500/20";
                                const isExpanded = expandedAgent === r.id;

                                return (
                                    <button
                                        key={r.id}
                                        onClick={() => setExpandedAgent(isExpanded ? null : r.id)}
                                        className="w-full text-left rounded-lg bg-white/5 border border-white/5 hover:bg-white/10 transition-colors p-3"
                                    >
                                        <div className="flex items-center gap-3">
                                            <div className={cn("h-8 w-8 rounded-lg flex items-center justify-center border flex-shrink-0", colorClass)}>
                                                <AgentIcon className="h-4 w-4" />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2">
                                                    <span className={cn("text-xs px-2 py-0.5 rounded-full border font-medium", colorClass)}>
                                                        {r.agent_type}
                                                    </span>
                                                    {r.created_at && (
                                                        <span className="text-xs text-slate-500">
                                                            {formatDistanceToNow(new Date(r.created_at), { addSuffix: true })}
                                                        </span>
                                                    )}
                                                </div>
                                                <p className="text-sm text-slate-200 mt-1 truncate">{r.action}</p>
                                            </div>
                                        </div>
                                        {isExpanded && r.details_json && (
                                            <pre className="text-xs text-slate-500 mt-3 bg-black/20 rounded p-2 overflow-auto max-h-48 font-mono">
                                                {JSON.stringify(r.details_json, null, 2)}
                                            </pre>
                                        )}
                                    </button>
                                );
                            })
                        ) : agentResponses && agentResponses.length === 0 ? (
                            <div className="py-12 text-center text-slate-500">
                                <Bot className="h-12 w-12 mx-auto opacity-20 mb-2" />
                                <p>No agent responses yet</p>
                                {!isTerminal(status.status) && (
                                    <p className="text-xs mt-1">Agent responses will appear once processing completes</p>
                                )}
                            </div>
                        ) : (
                            <div className="flex items-center justify-center py-12">
                                <Loader2 className="h-6 w-6 animate-spin text-slate-500" />
                            </div>
                        )}
                    </div>
                )}
            </GlassCard>
        </div>
    );
}
