"use client";

import { useState } from "react";
import useSWR from "swr";
import { fetcher, postRequest } from "@/lib/api";
import { GlassCard } from "@/components/ui/GlassCard";
import { ActivityModal } from "@/components/ui/ActivityModal";
import { Bot, Mail, CreditCard, AlertCircle, RefreshCw, Send } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { cn } from "@/lib/utils";
import type { AgentActivity, AgentTriggerRequest, AgentTriggerResponse } from "@/lib/types";

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

const AGENT_TYPES = ["all", "shipment", "customer", "payment", "escalation"] as const;

export default function AgentsPage() {
    const [filter, setFilter] = useState<string>("all");
    const [selectedActivity, setSelectedActivity] = useState<AgentActivity | null>(null);

    // Trigger form state
    const [triggerOrderId, setTriggerOrderId] = useState("");
    const [triggerSeverity, setTriggerSeverity] = useState("warning");
    const [triggerReason, setTriggerReason] = useState("");
    const [triggerDelayProb, setTriggerDelayProb] = useState(0.5);
    const [triggerLoading, setTriggerLoading] = useState(false);
    const [triggerResult, setTriggerResult] = useState<AgentTriggerResponse | null>(null);
    const [triggerError, setTriggerError] = useState<string | null>(null);

    const { data: activities, error: activitiesError, mutate } = useSWR<AgentActivity[]>(
        "/agents/activity?limit=50",
        fetcher,
        { refreshInterval: 5000 }
    );

    const filteredActivities = (activities || []).filter(
        (a) => filter === "all" || a.agent_type === filter
    );

    async function handleTrigger(e: React.FormEvent) {
        e.preventDefault();
        if (!triggerOrderId.trim() || !triggerReason.trim()) return;

        setTriggerLoading(true);
        setTriggerError(null);
        setTriggerResult(null);

        try {
            const body: AgentTriggerRequest = {
                order_id: triggerOrderId.trim(),
                severity: triggerSeverity,
                reason: triggerReason.trim(),
                delay_probability: triggerDelayProb,
            };
            const result = await postRequest<AgentTriggerRequest, AgentTriggerResponse>("/agents/trigger", body);
            setTriggerResult(result);
            mutate();
        } catch {
            setTriggerError("Failed to trigger agent. Check the order ID and try again.");
        } finally {
            setTriggerLoading(false);
        }
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-100 to-slate-400">
                    Agent Activity
                </h1>
                <span className="text-xs text-ai-400 animate-pulse bg-ai-500/10 px-2 py-1 rounded-full border border-ai-500/20">
                    ● AI Agents Active
                </span>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Activity Feed (left 2/3) */}
                <div className="lg:col-span-2 space-y-4">
                    {/* Filter tabs */}
                    <div className="flex gap-2">
                        {AGENT_TYPES.map((type) => (
                            <button
                                key={type}
                                onClick={() => setFilter(type)}
                                className={cn(
                                    "px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors",
                                    filter === type
                                        ? "bg-primary-500/20 border-primary-500/30 text-primary-400"
                                        : "bg-white/5 border-white/10 text-slate-400 hover:bg-white/10"
                                )}
                            >
                                {type.charAt(0).toUpperCase() + type.slice(1)}
                            </button>
                        ))}
                    </div>

                    {/* Activity list */}
                    <GlassCard className="max-h-[700px] overflow-y-auto">
                        <div className="space-y-3">
                            {filteredActivities.map((activity) => {
                                const Icon = AGENT_ICONS[activity.agent_type] || Bot;
                                const colorClass = AGENT_COLORS[activity.agent_type] || "text-slate-400 bg-slate-500/10 border-slate-500/20";

                                return (
                                    <button
                                        key={activity.id}
                                        onClick={() => setSelectedActivity(activity)}
                                        className="w-full flex items-center gap-3 p-3 text-left rounded-lg bg-white/5 border border-white/5 hover:bg-white/10 transition-colors cursor-pointer"
                                    >
                                        <div className={cn("h-8 w-8 rounded-lg flex items-center justify-center border flex-shrink-0", colorClass)}>
                                            <Icon className="h-4 w-4" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                <span className={cn("text-xs px-2 py-0.5 rounded-full border font-medium", colorClass)}>
                                                    {activity.agent_type}
                                                </span>
                                                <span className="text-xs text-slate-500">
                                                    Order #{activity.order_id}
                                                </span>
                                            </div>
                                            <p className="text-sm text-slate-200 mt-1 truncate">{activity.action}</p>
                                        </div>
                                        <div className="flex items-center gap-2 flex-shrink-0">
                                            <span className="text-xs text-slate-500 whitespace-nowrap">
                                                {formatDistanceToNow(new Date(activity.created_at), { addSuffix: true })}
                                            </span>
                                        </div>
                                    </button>
                                );
                            })}
                            {filteredActivities.length === 0 && (
                                <div className="py-12 text-center text-slate-500">
                                    <Bot className="h-12 w-12 mx-auto opacity-20 mb-2" />
                                    {activitiesError ? (
                                        <>
                                            <p className="text-critical-400 text-sm">Failed to load agent activity</p>
                                            <p className="text-xs mt-1">Check that the backend API is running and accessible</p>
                                        </>
                                    ) : (
                                        <>
                                            <p>No agent activity found</p>
                                            <p className="text-xs mt-1">Use the Trigger Agent form to create agent activity</p>
                                        </>
                                    )}
                                </div>
                            )}
                        </div>
                    </GlassCard>
                </div>

                {/* Trigger Form (right 1/3) */}
                <div className="space-y-4">
                    <GlassCard>
                        <h3 className="text-lg font-semibold text-slate-100 mb-4 flex items-center gap-2">
                            <Send className="h-5 w-5 text-primary-400" />
                            Trigger Agent
                        </h3>
                        <form onSubmit={handleTrigger} className="space-y-4">
                            <div>
                                <label className="block text-xs text-slate-400 mb-1">Order ID</label>
                                <input
                                    type="text"
                                    value={triggerOrderId}
                                    onChange={(e) => setTriggerOrderId(e.target.value)}
                                    placeholder="e.g. ORD-001"
                                    className="w-full h-9 rounded-lg border border-white/10 bg-black/20 px-3 text-sm text-slate-200 placeholder-slate-500 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                                    required
                                />
                            </div>
                            <div>
                                <label className="block text-xs text-slate-400 mb-1">Severity</label>
                                <select
                                    value={triggerSeverity}
                                    onChange={(e) => setTriggerSeverity(e.target.value)}
                                    className="w-full h-9 rounded-lg border border-white/10 bg-black/20 px-3 text-sm text-slate-200 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                                >
                                    <option value="critical">Critical</option>
                                    <option value="warning">Warning</option>
                                    <option value="info">Info</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-xs text-slate-400 mb-1">Reason</label>
                                <textarea
                                    value={triggerReason}
                                    onChange={(e) => setTriggerReason(e.target.value)}
                                    placeholder="Describe the reason for triggering..."
                                    rows={3}
                                    className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 resize-none"
                                    required
                                />
                            </div>
                            <div>
                                <label className="block text-xs text-slate-400 mb-1">
                                    Delay Probability: {(triggerDelayProb * 100).toFixed(0)}%
                                </label>
                                <input
                                    type="range"
                                    min={0}
                                    max={1}
                                    step={0.05}
                                    value={triggerDelayProb}
                                    onChange={(e) => setTriggerDelayProb(parseFloat(e.target.value))}
                                    className="w-full accent-primary-500"
                                />
                            </div>
                            <button
                                type="submit"
                                disabled={triggerLoading}
                                className="w-full h-10 rounded-lg bg-primary-500/20 border border-primary-500/30 text-primary-400 text-sm font-medium hover:bg-primary-500/30 transition-colors disabled:opacity-50"
                            >
                                {triggerLoading ? "Triggering..." : "Trigger Agent"}
                            </button>
                        </form>
                    </GlassCard>

                    {/* Trigger result */}
                    {triggerResult && (
                        <GlassCard className="border-success-500/20">
                            <h4 className="text-sm font-medium text-success-400 mb-3">Agent Response</h4>
                            <div className="space-y-2">
                                {triggerResult.results.map((r, i) => (
                                    <div key={i} className="rounded-lg bg-white/5 p-3 border border-white/5">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className={cn("text-xs px-2 py-0.5 rounded-full border font-medium", AGENT_COLORS[r.agent_type] || "text-slate-400 bg-slate-500/10 border-slate-500/20")}>
                                                {r.agent_type}
                                            </span>
                                        </div>
                                        <p className="text-sm text-slate-200">{r.action}</p>
                                        {r.details && (
                                            <pre className="text-xs text-slate-500 mt-2 bg-black/20 rounded p-2 overflow-auto max-h-32 font-mono">
                                                {JSON.stringify(r.details, null, 2)}
                                            </pre>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </GlassCard>
                    )}

                    {triggerError && (
                        <GlassCard className="border-critical-500/20">
                            <p className="text-sm text-critical-400">{triggerError}</p>
                        </GlassCard>
                    )}
                </div>
            </div>

            <ActivityModal
                activity={selectedActivity}
                onClose={() => setSelectedActivity(null)}
            />
        </div>
    );
}
