"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { GlassCard } from "@/components/ui/GlassCard";
import { TrendingUp, TrendingDown, Activity, AlertTriangle, PackageCheck, Gauge, PackageX } from "lucide-react";
import type { KPIDashboardResponse } from "@/lib/types";

export function KPIGrid() {
    const { data, error, isLoading } = useSWR<KPIDashboardResponse>("/kpi/dashboard", fetcher, { refreshInterval: 5000 });

    if (isLoading || error) {
        return (
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
                {[1, 2, 3, 4, 5].map((i) => (
                    <GlassCard key={i} className="h-32 animate-pulse bg-white/5" />
                ))}
            </div>
        );
    }

    const kpi = data || {
        total_predictions: 0,
        avg_delay_probability: 0,
        on_time_rate: 0,
        high_risk_count: 0,
        fulfillment_gap_count: 0,
        severity_breakdown: {},
        by_warehouse_block: [],
        by_mode_of_shipment: [],
        by_product_importance: [],
    };

    const avgDelayPct = kpi.avg_delay_probability * 100;

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {/* Total Orders Processed */}
            <GlassCard animate>
                <div className="flex items-start justify-between">
                    <div>
                        <p className="text-xs font-medium text-slate-400">Orders Processed</p>
                        <h3 className="mt-2 text-2xl font-bold text-slate-100">{kpi.total_predictions.toLocaleString()}</h3>
                    </div>
                    <div className="rounded-lg bg-primary-500/20 p-2 border border-primary-500/30">
                        <PackageCheck className="h-5 w-5 text-primary-400" />
                    </div>
                </div>
                <div className="mt-3 flex items-center text-xs text-primary-400">
                    <Activity className="mr-1 h-3 w-3" />
                    <span>30-day rolling window</span>
                </div>
            </GlassCard>

            {/* Avg Delay Probability */}
            <GlassCard animate>
                <div className="flex items-start justify-between">
                    <div>
                        <p className="text-xs font-medium text-slate-400">Avg Delay Probability</p>
                        <h3 className="mt-2 text-2xl font-bold text-slate-100">{avgDelayPct.toFixed(1)}%</h3>
                    </div>
                    <div className={`rounded-lg p-2 border ${avgDelayPct > 50 ? 'bg-critical-500/20 border-critical-500/30' : avgDelayPct > 30 ? 'bg-warning-500/20 border-warning-500/30' : 'bg-success-500/20 border-success-500/30'}`}>
                        <Gauge className={`h-5 w-5 ${avgDelayPct > 50 ? 'text-critical-400' : avgDelayPct > 30 ? 'text-warning-400' : 'text-success-400'}`} />
                    </div>
                </div>
                <div className="mt-3 h-1.5 w-full rounded-full bg-white/10">
                    <div
                        className={`h-1.5 rounded-full ${avgDelayPct > 50 ? 'bg-critical-500' : avgDelayPct > 30 ? 'bg-warning-500' : 'bg-success-500'}`}
                        style={{ width: `${Math.min(avgDelayPct, 100)}%` }}
                    />
                </div>
            </GlassCard>

            {/* On-Time Delivery Rate */}
            <GlassCard animate className="relative overflow-hidden">
                <div className="flex items-start justify-between">
                    <div>
                        <p className="text-xs font-medium text-slate-400">On-Time Rate</p>
                        <h3 className="mt-2 text-2xl font-bold text-slate-100">{(kpi.on_time_rate * 100).toFixed(1)}%</h3>
                    </div>
                    <div className={`rounded-lg p-2 border ${kpi.on_time_rate > 0.95 ? 'bg-success-500/20 border-success-500/30' : 'bg-warning-500/20 border-warning-500/30'}`}>
                        {kpi.on_time_rate > 0.95 ? (
                            <TrendingUp className="h-5 w-5 text-success-400" />
                        ) : (
                            <TrendingDown className="h-5 w-5 text-warning-400" />
                        )}
                    </div>
                </div>
                <div className="mt-3 h-1.5 w-full rounded-full bg-white/10">
                    <div
                        className={`h-1.5 rounded-full ${kpi.on_time_rate > 0.95 ? 'bg-success-500' : 'bg-warning-500'}`}
                        style={{ width: `${kpi.on_time_rate * 100}%` }}
                    />
                </div>
            </GlassCard>

            {/* Active High Risks */}
            <GlassCard animate className={kpi.high_risk_count > 0 ? "border-critical-500/50 bg-critical-500/5" : ""}>
                <div className="flex items-start justify-between">
                    <div>
                        <p className="text-xs font-medium text-slate-400">High Risk Orders</p>
                        <div className="flex items-baseline gap-2">
                            <h3 className="mt-2 text-2xl font-bold text-slate-100">{kpi.high_risk_count}</h3>
                            {kpi.high_risk_count > 0 && (
                                <span className="text-[10px] font-medium text-critical-400 animate-pulse">CRITICAL</span>
                            )}
                        </div>
                    </div>
                    <div className="rounded-lg bg-critical-500/20 p-2 border border-critical-500/30">
                        <AlertTriangle className="h-5 w-5 text-critical-400" />
                    </div>
                </div>
                <div className="mt-3 text-xs text-slate-500">
                    &gt;70% delay probability
                </div>
            </GlassCard>

            {/* Fulfillment Gap */}
            <GlassCard animate className={kpi.fulfillment_gap_count > 0 ? "border-warning-500/50 bg-warning-500/5" : ""}>
                <div className="flex items-start justify-between">
                    <div>
                        <p className="text-xs font-medium text-slate-400">Fulfillment Gap</p>
                        <div className="flex items-baseline gap-2">
                            <h3 className="mt-2 text-2xl font-bold text-slate-100">{kpi.fulfillment_gap_count}</h3>
                            {kpi.fulfillment_gap_count > 0 && (
                                <span className="text-[10px] font-medium text-warning-400 animate-pulse">AT RISK</span>
                            )}
                        </div>
                    </div>
                    <div className="rounded-lg bg-warning-500/20 p-2 border border-warning-500/30">
                        <PackageX className="h-5 w-5 text-warning-400" />
                    </div>
                </div>
                <div className="mt-3 text-xs text-slate-500">
                    Shipped but likely delayed
                </div>
            </GlassCard>
        </div>
    );
}
