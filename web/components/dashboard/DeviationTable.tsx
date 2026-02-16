"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { GlassCard } from "@/components/ui/GlassCard";
import { AlertCircle, AlertTriangle, Info } from "lucide-react";
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { cn } from "@/lib/utils";

interface Deviation {
    id: string;
    prediction_id: string;
    severity: "critical" | "warning" | "info";
    reason: string;
    status: string;
    created_at: string;
}

const SEVERITY_ICONS = {
    critical: AlertCircle,
    warning: AlertTriangle,
    info: Info,
};

const SEVERITY_STYLES = {
    critical: "text-critical-400 bg-critical-500/10 border-critical-500/20",
    warning: "text-warning-400 bg-warning-500/10 border-warning-500/20",
    info: "text-primary-400 bg-primary-500/10 border-primary-500/20",
};

interface PaginatedResponse<T> {
    items: T[];
    total: number;
    skip: number;
    limit: number;
}

export function DeviationTable() {
    const { data, isLoading } = useSWR<PaginatedResponse<Deviation>>("/deviations", fetcher, {
        refreshInterval: 5000,
    });

    if (isLoading) {
        return <GlassCard className="h-[300px] animate-pulse" />;
    }

    const list = data?.items || [];

    return (
        <GlassCard className="h-full overflow-hidden flex flex-col">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-slate-100">Active Deviation Queue</h3>
                <span className="text-xs text-slate-400">{list.length} pending actions</span>
            </div>

            <div className="flex-1 overflow-auto rounded-lg border border-white/5">
                <table className="w-full text-left text-sm">
                    <thead className="bg-white/5 text-slate-400">
                        <tr>
                            <th className="p-3 font-medium">Severity</th>
                            <th className="p-3 font-medium">Order ID / Reason</th>
                            <th className="p-3 font-medium">Detected</th>
                            <th className="p-3 font-medium">Status</th>
                            <th className="p-3 font-medium text-right">Action</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                        {list.map((deviation) => {
                            const Icon = SEVERITY_ICONS[deviation.severity] || Info;
                            const style = SEVERITY_STYLES[deviation.severity] || SEVERITY_STYLES.info;

                            return (
                                <tr key={deviation.id} className="hover:bg-white/5 transition-colors">
                                    <td className="p-3">
                                        <span className={cn("inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border", style)}>
                                            <Icon className="h-3 w-3" />
                                            {deviation.severity.toUpperCase()}
                                        </span>
                                    </td>
                                    <td className="p-3">
                                        <div className="font-mono text-slate-200 text-xs mb-1">
                                            ID: {deviation.prediction_id.slice(0, 8)}...
                                        </div>
                                        <div className="text-slate-400 truncate max-w-[300px]" title={deviation.reason}>
                                            {deviation.reason}
                                        </div>
                                    </td>
                                    <td className="p-3 text-slate-500 whitespace-nowrap">
                                        {formatDistanceToNow(new Date(deviation.created_at), { addSuffix: true })}
                                    </td>
                                    <td className="p-3">
                                        <span className="text-xs text-slate-400 font-mono bg-white/5 px-2 py-1 rounded">
                                            {deviation.status}
                                        </span>
                                    </td>
                                    <td className="p-3 text-right">
                                        <Link
                                            href={`/orders/${deviation.prediction_id}`}
                                            className="text-primary-400 hover:text-primary-300 text-xs font-medium"
                                        >
                                            View Details →
                                        </Link>
                                    </td>
                                </tr>
                            );
                        })}

                        {list.length === 0 && (
                            <tr>
                                <td colSpan={5} className="p-8 text-center text-slate-500">
                                    No active deviations. System healthy.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </GlassCard>
    );
}
