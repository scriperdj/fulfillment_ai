"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { GlassCard } from "@/components/ui/GlassCard";
import { TrendingUp, TrendingDown, Activity, AlertTriangle, PackageCheck } from "lucide-react";

interface KPIDashboardResponse {
    total_predictions: number;
    avg_delay_probability: number;
    on_time_rate: number;
    high_risk_count: number;
}

export function KPIGrid() {
    const { data, error, isLoading } = useSWR<KPIDashboardResponse>("/kpi/dashboard", fetcher, { refreshInterval: 5000 });

    if (isLoading || error) {
        return (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {[1, 2, 3].map((i) => (
                    <GlassCard key={i} className="h-32 animate-pulse bg-white/5" />
                ))}
            </div>
        );
    }

    const kpi = data || {
        total_predictions: 0,
        avg_delay_probability: 0,
        on_time_rate: 0,
        high_risk_count: 0
    };

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <GlassCard animate>
                <div className="flex items-start justify-between">
                    <div>
                        <p className="text-sm font-medium text-slate-400">Total Orders Processed</p>
                        <h3 className="mt-2 text-3xl font-bold text-slate-100">{kpi.total_predictions.toLocaleString()}</h3>
                    </div>
                    <div className="rounded-lg bg-primary-500/20 p-2 border border-primary-500/30">
                        <PackageCheck className="h-6 w-6 text-primary-400" />
                    </div>
                </div>
                <div className="mt-4 flex items-center text-xs text-primary-400">
                    <Activity className="mr-1 h-3 w-3" />
                    <span>Real-time ingestion active</span>
                </div>
            </GlassCard>

            <GlassCard animate className="relative overflow-hidden">
                <div className="flex items-start justify-between">
                    <div>
                        <p className="text-sm font-medium text-slate-400">On-Time Delivery Rate</p>
                        <h3 className="mt-2 text-3xl font-bold text-slate-100">{(kpi.on_time_rate * 100).toFixed(1)}%</h3>
                    </div>
                    <div className={`rounded-lg p-2 border ${kpi.on_time_rate > 0.95 ? 'bg-success-500/20 border-success-500/30' : 'bg-warning-500/20 border-warning-500/30'}`}>
                        {kpi.on_time_rate > 0.95 ? (
                            <TrendingUp className="h-6 w-6 text-success-400" />
                        ) : (
                            <TrendingDown className="h-6 w-6 text-warning-400" />
                        )}
                    </div>
                </div>
                <div className="mt-4 h-1.5 w-full rounded-full bg-white/10">
                    <div
                        className={`h-1.5 rounded-full ${kpi.on_time_rate > 0.95 ? 'bg-success-500' : 'bg-warning-500'}`}
                        style={{ width: `${kpi.on_time_rate * 100}%` }}
                    />
                </div>
            </GlassCard>

            <GlassCard animate className={kpi.high_risk_count > 0 ? "border-critical-500/50 bg-critical-500/5" : ""}>
                <div className="flex items-start justify-between">
                    <div>
                        <p className="text-sm font-medium text-slate-400">Active High Risks</p>
                        <div className="flex items-baseline gap-2">
                            <h3 className="mt-2 text-3xl font-bold text-slate-100">{kpi.high_risk_count}</h3>
                            {kpi.high_risk_count > 0 && (
                                <span className="text-xs font-medium text-critical-400 animate-pulse">CRITICAL</span>
                            )}
                        </div>
                    </div>
                    <div className="rounded-lg bg-critical-500/20 p-2 border border-critical-500/30">
                        <AlertTriangle className="h-6 w-6 text-critical-400" />
                    </div>
                </div>
                <div className="mt-4 text-xs text-slate-400">
                    Orders with &gt;70% delay probability require immediate attention.
                </div>
            </GlassCard>
        </div>
    );
}
