"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { GlassCard } from "@/components/ui/GlassCard";
import type { KPIDashboardResponse } from "@/lib/types";
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
    PieChart, Pie,
} from "recharts";
import { Warehouse } from "lucide-react";

const BLOCK_COLORS: Record<string, string> = {
    A: "#06b6d4",
    B: "#8b5cf6",
    C: "#f59e0b",
    D: "#10b981",
    E: "#f43f5e",
};

const MODE_COLORS: Record<string, string> = {
    Ship: "#06b6d4",
    Flight: "#8b5cf6",
    Road: "#f59e0b",
};

const IMPORTANCE_COLORS: Record<string, string> = {
    Low: "#10b981",
    Medium: "#f59e0b",
    High: "#f43f5e",
};

const SEVERITY_COLORS: Record<string, string> = {
    critical: "#f43f5e",
    warning: "#f59e0b",
    info: "#06b6d4",
};

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number }>; label?: string }) => {
    if (active && payload?.length) {
        return (
            <div className="rounded-lg bg-slate-900/95 border border-white/10 px-3 py-2 text-xs">
                <p className="text-slate-300 font-medium">{label}</p>
                <p className="text-slate-100">Risk Score: {(payload[0].value * 100).toFixed(1)}%</p>
            </div>
        );
    }
    return null;
};

export function WarehousePerformance() {
    const { data, isLoading } = useSWR<KPIDashboardResponse>("/kpi/dashboard", fetcher, {
        refreshInterval: 10000,
    });

    if (isLoading) {
        return <GlassCard className="h-full animate-pulse" />;
    }

    const warehouseData = (data?.by_warehouse_block || []).map((item) => ({
        block: String(item.segment || "?"),
        risk: Number(item.avg_delay_probability || 0),
        count: Number(item.count || 0),
    }));

    const modeData = (data?.by_mode_of_shipment || []).map((item) => ({
        mode: String(item.segment || "?"),
        risk: Number(item.avg_delay_probability || 0),
        count: Number(item.count || 0),
    }));

    const importanceData = (data?.by_product_importance || []).map((item) => ({
        importance: String(item.segment || "?"),
        risk: Number(item.avg_delay_probability || 0),
        count: Number(item.count || 0),
    }));

    const severityData = Object.entries(data?.severity_breakdown || {}).map(([key, value]) => ({
        name: key.charAt(0).toUpperCase() + key.slice(1),
        value: Number(value),
        color: SEVERITY_COLORS[key] || "#64748b",
    }));

    return (
        <GlassCard className="h-full flex flex-col overflow-hidden">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                    <Warehouse className="h-5 w-5 text-primary-400" />
                    Warehouse Performance
                </h3>
                <span className="text-xs text-slate-400">Blocks A-E</span>
            </div>

            {/* Main bar chart - Risk by warehouse block */}
            <div className="flex-1 min-h-0">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={warehouseData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                        <XAxis
                            dataKey="block"
                            tick={{ fill: "#94a3b8", fontSize: 12 }}
                            axisLine={{ stroke: "#1e293b" }}
                            tickLine={false}
                            tickFormatter={(v) => `Block ${v}`}
                        />
                        <YAxis
                            tick={{ fill: "#64748b", fontSize: 11 }}
                            axisLine={false}
                            tickLine={false}
                            tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                            domain={[0, 1]}
                        />
                        <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
                        <Bar dataKey="risk" radius={[6, 6, 0, 0]} maxBarSize={48}>
                            {warehouseData.map((entry) => (
                                <Cell key={entry.block} fill={BLOCK_COLORS[entry.block] || "#64748b"} fillOpacity={0.8} />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </div>

            {/* Secondary row */}
            <div className="grid grid-cols-3 gap-4 mt-2 pt-3 border-t border-white/5">
                {/* Shipment mode breakdown */}
                <div>
                    <p className="text-xs text-slate-500 mb-2">By Shipment Mode</p>
                    <div className="space-y-1.5">
                        {modeData.map((m) => (
                            <div key={m.mode} className="flex items-center gap-2 text-xs">
                                <span className="h-2 w-2 rounded-full flex-shrink-0" style={{ backgroundColor: MODE_COLORS[m.mode] || "#64748b" }} />
                                <span className="text-slate-400 w-9">{m.mode}</span>
                                <div className="flex-1 h-1.5 rounded-full bg-white/5">
                                    <div
                                        className="h-1.5 rounded-full transition-all"
                                        style={{
                                            width: `${Math.min(m.risk * 100, 100)}%`,
                                            backgroundColor: MODE_COLORS[m.mode] || "#64748b",
                                        }}
                                    />
                                </div>
                                <span className="text-slate-500 w-9 text-right">{(m.risk * 100).toFixed(0)}%</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Product importance breakdown */}
                <div>
                    <p className="text-xs text-slate-500 mb-2">By Product Importance</p>
                    <div className="space-y-1.5">
                        {importanceData.map((p) => (
                            <div key={p.importance} className="flex items-center gap-2 text-xs">
                                <span className="h-2 w-2 rounded-full flex-shrink-0" style={{ backgroundColor: IMPORTANCE_COLORS[p.importance] || "#64748b" }} />
                                <span className="text-slate-400 w-12">{p.importance}</span>
                                <div className="flex-1 h-1.5 rounded-full bg-white/5">
                                    <div
                                        className="h-1.5 rounded-full transition-all"
                                        style={{
                                            width: `${Math.min(p.risk * 100, 100)}%`,
                                            backgroundColor: IMPORTANCE_COLORS[p.importance] || "#64748b",
                                        }}
                                    />
                                </div>
                                <span className="text-slate-500 w-9 text-right">{(p.risk * 100).toFixed(0)}%</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Severity breakdown */}
                <div className="flex items-center gap-3">
                    <div className="w-20 h-20">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={severityData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={18}
                                    outerRadius={32}
                                    dataKey="value"
                                    strokeWidth={0}
                                >
                                    {severityData.map((entry) => (
                                        <Cell key={entry.name} fill={entry.color} />
                                    ))}
                                </Pie>
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                    <div className="space-y-1">
                        {severityData.map((s) => (
                            <div key={s.name} className="flex items-center gap-2 text-xs">
                                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: s.color }} />
                                <span className="text-slate-400">{s.name}</span>
                                <span className="text-slate-500">{s.value}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </GlassCard>
    );
}
