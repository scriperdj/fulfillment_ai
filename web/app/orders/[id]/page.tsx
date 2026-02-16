"use client";

import { useParams } from "next/navigation";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { GlassCard } from "@/components/ui/GlassCard";
import { ResolutionTimeline, TimelineEvent } from "@/components/order/ResolutionTimeline";
import { Box, Truck } from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";

interface OrderDetailResponse {
    order_id: string;
    predictions: any[];
    deviations: any[];
    agent_responses: any[];
}

export default function OrderDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const { data: order, isLoading } = useSWR<OrderDetailResponse>(id ? `/orders/${id}` : null, fetcher);

    if (isLoading) {
        return (
            <div className="space-y-6 animate-pulse">
                <GlassCard className="h-32" />
                <div className="grid grid-cols-3 gap-6">
                    <GlassCard className="h-64 col-span-1" />
                    <GlassCard className="h-[600px] col-span-2" />
                </div>
            </div>
        );
    }

    if (!order) {
        return <div className="text-center text-slate-500 mt-20">Order not found</div>;
    }

    const events: TimelineEvent[] = [
        ...(order.predictions || []).map((p: any) => ({
            id: p.id,
            type: "prediction" as const,
            timestamp: p.created_at,
            title: `Risk Analysis: ${(p.delay_probability * 100).toFixed(0)}%`,
            description: `Source: ${p.source}`,
            severity: p.severity,
        })),
        ...(order.deviations || []).map((d: any) => ({
            id: d.id,
            type: "deviation" as const,
            timestamp: d.created_at,
            title: `${d.severity.toUpperCase()} Alert`,
            description: d.reason,
            severity: d.severity,
        })),
        ...(order.agent_responses || []).map((a: any) => ({
            id: a.id,
            type: "agent_response" as const,
            timestamp: a.created_at,
            title: `${a.agent_type.toUpperCase()} Intervention`,
            description: a.action,
            metadata: a.details_json,
        })),
    ];

    const latestPrediction = order.predictions?.[0];
    const delayProb = latestPrediction?.delay_probability || 0;
    const riskColor = delayProb > 0.7 ? "#f43f5e" : delayProb > 0.5 ? "#f59e0b" : "#10b981";

    const riskData = [
        { name: "Risk", value: delayProb },
        { name: "Safe", value: 1 - delayProb },
    ];

    return (
        <div className="space-y-6 max-w-7xl mx-auto">
            {/* Header */}
            <GlassCard className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
                        Order #{order.order_id}
                        <span className={`text-xs px-2 py-0.5 rounded-full border ${delayProb > 0.5 ? 'border-critical-500/30 bg-critical-500/10 text-critical-400' : 'border-success-500/30 bg-success-500/10 text-success-400'}`}>
                            {delayProb > 0.5 ? 'AT RISK' : 'ON TRACK'}
                        </span>
                    </h1>
                    <p className="text-sm text-slate-400 mt-1 flex items-center gap-4">
                        <span className="flex items-center gap-1"><Box className="h-3 w-3" /> SKU-99283</span>
                        <span className="flex items-center gap-1"><Truck className="h-3 w-3" /> Warehouse B</span>
                    </p>
                </div>
            </GlassCard>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Left Col: Metrics */}
                <div className="space-y-6">
                    <GlassCard className="h-[300px] flex flex-col items-center justify-center relative">
                        <div className="absolute top-4 left-4 text-sm font-medium text-slate-400">Delay Probability</div>
                        <ResponsiveContainer width="100%" height={200}>
                            <PieChart>
                                <Pie
                                    data={riskData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={60}
                                    outerRadius={80}
                                    startAngle={180}
                                    endAngle={0}
                                    paddingAngle={5}
                                    dataKey="value"
                                >
                                    <Cell key="risk" fill={riskColor} />
                                    <Cell key="safe" fill="#1e293b" />
                                </Pie>
                            </PieChart>
                        </ResponsiveContainer>
                        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-center mt-4">
                            <span className="text-4xl font-bold text-slate-100">{(delayProb * 100).toFixed(0)}%</span>
                        </div>
                    </GlassCard>

                    <GlassCard>
                        <h3 className="text-sm font-medium text-slate-400 mb-4">Metadata</h3>
                        <div className="space-y-3 text-sm">
                            <div className="flex justify-between border-b border-white/5 pb-2">
                                <span className="text-slate-500">Weight</span>
                                <span className="text-slate-200">1.2 kg</span>
                            </div>
                            <div className="flex justify-between border-b border-white/5 pb-2">
                                <span className="text-slate-500">Value</span>
                                <span className="text-slate-200">$450.00</span>
                            </div>
                            <div className="flex justify-between border-b border-white/5 pb-2">
                                <span className="text-slate-500">Service Level</span>
                                <span className="text-slate-200">Express</span>
                            </div>
                        </div>
                    </GlassCard>
                </div>

                {/* Right Col: Timeline */}
                <div className="lg:col-span-2">
                    <GlassCard className="h-full">
                        <h3 className="text-lg font-semibold text-slate-100 mb-6">Resolution Timeline</h3>
                        <ResolutionTimeline events={events} />
                    </GlassCard>
                </div>
            </div>
        </div>
    );
}
