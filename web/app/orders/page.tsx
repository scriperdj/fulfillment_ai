"use client";

import { useState, useEffect, Suspense, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { GlassCard } from "@/components/ui/GlassCard";
import Link from "next/link";
import { Search, Package, AlertCircle, AlertTriangle, Info, Bot } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { cn } from "@/lib/utils";
import type { OrderDetailResponse, DeviationResponse, AgentActivity, PaginatedResponse } from "@/lib/types";

const SEVERITY_STYLES: Record<string, string> = {
    critical: "text-critical-400 bg-critical-500/10 border-critical-500/20",
    warning: "text-warning-400 bg-warning-500/10 border-warning-500/20",
    info: "text-primary-400 bg-primary-500/10 border-primary-500/20",
};

const SEVERITY_ICONS: Record<string, typeof AlertCircle> = {
    critical: AlertCircle,
    warning: AlertTriangle,
    info: Info,
};

export default function OrdersPage() {
    return (
        <Suspense fallback={<GlassCard className="h-32 animate-pulse" />}>
            <OrdersContent />
        </Suspense>
    );
}

function OrdersContent() {
    const searchParams = useSearchParams();
    const urlSearch = searchParams.get("search") || "";
    const [query, setQuery] = useState(urlSearch);
    const [searchResult, setSearchResult] = useState<OrderDetailResponse | null>(null);
    const [searchError, setSearchError] = useState<string | null>(null);
    const [searching, setSearching] = useState(false);

    const { data: deviations } = useSWR<PaginatedResponse<DeviationResponse>>(
        "/deviations?limit=20",
        fetcher,
        { refreshInterval: 10000 }
    );

    const { data: agentActivities } = useSWR<AgentActivity[]>(
        "/agents/activity?limit=50",
        fetcher,
        { refreshInterval: 10000 }
    );

    const doSearch = useCallback(async (orderId: string) => {
        if (!orderId.trim()) return;
        setSearching(true);
        setSearchError(null);
        setSearchResult(null);

        try {
            const result = await fetcher<OrderDetailResponse>(`/orders/${orderId.trim()}`);
            setSearchResult(result);
        } catch {
            setSearchError(`Order "${orderId}" not found.`);
        } finally {
            setSearching(false);
        }
    }, []);

    // React to URL search param changes (e.g. from TopBar search or deviation links)
    useEffect(() => {
        if (urlSearch) {
            setQuery(urlSearch);
            doSearch(urlSearch);
        }
    }, [urlSearch, doSearch]);

    function handleSearch(e: React.FormEvent) {
        e.preventDefault();
        doSearch(query);
    }

    const latestPrediction = searchResult?.predictions?.[0];
    const delayProb = latestPrediction?.delay_probability || 0;

    // Extract unique orders from agent activity
    const activeOrders = (() => {
        if (!agentActivities?.length) return [];
        const seen = new Map<string, AgentActivity>();
        for (const a of agentActivities) {
            if (!seen.has(a.order_id)) {
                seen.set(a.order_id, a);
            }
        }
        return Array.from(seen.values());
    })();

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-100 to-slate-400">
                    Orders
                </h1>
            </div>

            {/* Search bar */}
            <GlassCard>
                <form onSubmit={handleSearch} className="flex gap-3">
                    <div className="relative flex-1">
                        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                        <input
                            type="text"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="Enter order ID to search..."
                            className="h-10 w-full rounded-lg border border-white/10 bg-black/20 pl-10 pr-4 text-sm text-slate-200 placeholder-slate-500 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                        />
                    </div>
                    <button
                        type="submit"
                        disabled={searching}
                        className="px-6 h-10 rounded-lg bg-primary-500/20 border border-primary-500/30 text-primary-400 text-sm font-medium hover:bg-primary-500/30 transition-colors disabled:opacity-50"
                    >
                        {searching ? "Searching..." : "Search"}
                    </button>
                </form>
            </GlassCard>

            {/* Search result */}
            {searchResult && (
                <GlassCard>
                    <div className="flex items-start justify-between">
                        <div className="flex items-center gap-4">
                            <div className="h-12 w-12 rounded-lg bg-primary-500/20 border border-primary-500/30 flex items-center justify-center">
                                <Package className="h-6 w-6 text-primary-400" />
                            </div>
                            <div>
                                <h3 className="text-lg font-semibold text-slate-100">
                                    Order #{searchResult.order_id}
                                </h3>
                                <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
                                    <span>{searchResult.predictions?.length || 0} predictions</span>
                                    <span className="text-slate-600">|</span>
                                    <span>{searchResult.deviations?.length || 0} deviations</span>
                                    <span className="text-slate-600">|</span>
                                    <span className="flex items-center gap-1">
                                        <Bot className="h-3 w-3" />
                                        {searchResult.agent_responses?.length || 0} agent responses
                                    </span>
                                </div>
                            </div>
                        </div>
                        <div className="flex items-center gap-3">
                            <span
                                className={cn(
                                    "text-xs px-2.5 py-1 rounded-full border font-medium",
                                    delayProb > 0.7
                                        ? "border-critical-500/30 bg-critical-500/10 text-critical-400"
                                        : delayProb > 0.5
                                          ? "border-warning-500/30 bg-warning-500/10 text-warning-400"
                                          : "border-success-500/30 bg-success-500/10 text-success-400"
                                )}
                            >
                                {delayProb > 0.5 ? "AT RISK" : "ON TRACK"} ({(delayProb * 100).toFixed(0)}%)
                            </span>
                            <Link
                                href={`/orders/${searchResult.order_id}`}
                                className="px-4 py-2 rounded-lg bg-primary-500/20 border border-primary-500/30 text-primary-400 text-xs font-medium hover:bg-primary-500/30 transition-colors"
                            >
                                View Full Details →
                            </Link>
                        </div>
                    </div>
                </GlassCard>
            )}

            {searchError && (
                <GlassCard className="border-warning-500/20">
                    <p className="text-sm text-warning-400">{searchError}</p>
                </GlassCard>
            )}

            {/* Active Orders from agent activity */}
            <GlassCard className="overflow-hidden">
                <h3 className="text-lg font-semibold text-slate-100 mb-4">Active Orders</h3>
                {activeOrders.length > 0 ? (
                    <div className="overflow-auto rounded-lg border border-white/5">
                        <table className="w-full text-left text-sm">
                            <thead className="bg-white/5 text-slate-400">
                                <tr>
                                    <th className="p-3 font-medium">Order ID</th>
                                    <th className="p-3 font-medium">Latest Agent</th>
                                    <th className="p-3 font-medium">Action</th>
                                    <th className="p-3 font-medium">Last Activity</th>
                                    <th className="p-3 font-medium text-right">Details</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5">
                                {activeOrders.map((activity) => (
                                    <tr key={activity.order_id} className="hover:bg-white/5 transition-colors">
                                        <td className="p-3">
                                            <span className="font-mono text-sm text-slate-200">
                                                {activity.order_id}
                                            </span>
                                        </td>
                                        <td className="p-3">
                                            <span className={cn(
                                                "text-xs px-2 py-0.5 rounded-full border font-medium",
                                                activity.agent_type === "escalation"
                                                    ? "text-critical-400 bg-critical-500/10 border-critical-500/20"
                                                    : activity.agent_type === "customer"
                                                      ? "text-ai-400 bg-ai-500/10 border-ai-500/20"
                                                      : activity.agent_type === "payment"
                                                        ? "text-success-400 bg-success-500/10 border-success-500/20"
                                                        : "text-primary-400 bg-primary-500/10 border-primary-500/20"
                                            )}>
                                                {activity.agent_type}
                                            </span>
                                        </td>
                                        <td className="p-3 text-slate-400 truncate max-w-[300px]" title={activity.action}>
                                            {activity.action}
                                        </td>
                                        <td className="p-3 text-slate-500 whitespace-nowrap">
                                            {formatDistanceToNow(new Date(activity.created_at), { addSuffix: true })}
                                        </td>
                                        <td className="p-3 text-right">
                                            <Link
                                                href={`/orders/${activity.order_id}`}
                                                className="text-primary-400 hover:text-primary-300 text-xs font-medium"
                                            >
                                                View →
                                            </Link>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <div className="py-8 text-center text-slate-500 rounded-lg border border-white/5">
                        <Package className="h-10 w-10 mx-auto opacity-20 mb-2" />
                        <p>No active orders with agent activity yet</p>
                        <p className="text-xs mt-1">Orders will appear here once agents process them</p>
                    </div>
                )}
            </GlassCard>

            {/* Recent deviations */}
            <GlassCard className="overflow-hidden">
                <h3 className="text-lg font-semibold text-slate-100 mb-4">Recent Deviations</h3>
                <div className="overflow-auto rounded-lg border border-white/5">
                    <table className="w-full text-left text-sm">
                        <thead className="bg-white/5 text-slate-400">
                            <tr>
                                <th className="p-3 font-medium">Severity</th>
                                <th className="p-3 font-medium">Reason</th>
                                <th className="p-3 font-medium">Detected</th>
                                <th className="p-3 font-medium">Status</th>
                                <th className="p-3 font-medium text-right">Action</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {(deviations?.items || []).map((d) => {
                                const Icon = SEVERITY_ICONS[d.severity] || Info;
                                const style = SEVERITY_STYLES[d.severity] || SEVERITY_STYLES.info;
                                return (
                                    <tr key={d.id} className="hover:bg-white/5 transition-colors">
                                        <td className="p-3">
                                            <span className={cn("inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border", style)}>
                                                <Icon className="h-3 w-3" />
                                                {d.severity.toUpperCase()}
                                            </span>
                                        </td>
                                        <td className="p-3 text-slate-400 truncate max-w-[300px]" title={d.reason}>
                                            {d.reason}
                                        </td>
                                        <td className="p-3 text-slate-500 whitespace-nowrap">
                                            {d.created_at
                                                ? formatDistanceToNow(new Date(d.created_at), { addSuffix: true })
                                                : "N/A"}
                                        </td>
                                        <td className="p-3">
                                            <span className="text-xs text-slate-400 font-mono bg-white/5 px-2 py-1 rounded">
                                                {d.status}
                                            </span>
                                        </td>
                                        <td className="p-3 text-right">
                                            <button
                                                onClick={() => {
                                                    const searchId = d.order_id || d.prediction_id;
                                                    setQuery(searchId);
                                                    doSearch(searchId);
                                                }}
                                                className="text-primary-400 hover:text-primary-300 text-xs font-medium"
                                            >
                                                Lookup →
                                            </button>
                                        </td>
                                    </tr>
                                );
                            })}
                            {(!deviations?.items || deviations.items.length === 0) && (
                                <tr>
                                    <td colSpan={5} className="p-8 text-center text-slate-500">
                                        No recent deviations.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </GlassCard>
        </div>
    );
}
