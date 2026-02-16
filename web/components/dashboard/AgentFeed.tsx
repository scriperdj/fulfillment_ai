"use client";

import { useState } from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { GlassCard } from "@/components/ui/GlassCard";
import { ActivityModal } from "@/components/ui/ActivityModal";
import { formatDistanceToNow } from "date-fns";
import { Bot, Mail, CreditCard, AlertCircle, RefreshCw } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import type { AgentActivity } from "@/lib/types";

const AGENT_ICONS: Record<string, any> = {
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

export function AgentFeed() {
    const [selectedActivity, setSelectedActivity] = useState<AgentActivity | null>(null);
    const { data: activities, error, isLoading } = useSWR<AgentActivity[]>("/agents/activity", fetcher, {
        refreshInterval: 3000,
    });

    if (isLoading) {
        return <GlassCard className="h-[400px] animate-pulse" />;
    }

    const feed = activities || [];

    return (
        <>
            <GlassCard className="h-[400px] flex flex-col">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                        <Bot className="h-5 w-5 text-ai-400" />
                        Live Agent Activity
                    </h3>
                    <span className="text-xs text-ai-400 animate-pulse bg-ai-500/10 px-2 py-1 rounded-full border border-ai-500/20">
                        ● AI Active
                    </span>
                </div>

                <div className="flex-1 overflow-y-auto pr-2 space-y-3 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
                    <AnimatePresence initial={false}>
                        {feed.map((activity) => {
                            const Icon = AGENT_ICONS[activity.agent_type] || Bot;
                            const colorClass = AGENT_COLORS[activity.agent_type] || "text-slate-400 bg-slate-500/10 border-slate-500/20";

                            return (
                                <motion.div
                                    key={activity.id}
                                    initial={{ opacity: 0, x: -20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    exit={{ opacity: 0, height: 0 }}
                                    onClick={() => setSelectedActivity(activity)}
                                    className="flex gap-3 p-3 rounded-lg bg-white/5 border border-white/5 hover:bg-white/10 transition-colors cursor-pointer"
                                >
                                    <div className={`mt-1 h-8 w-8 rounded-lg flex items-center justify-center border ${colorClass}`}>
                                        <Icon className="h-4 w-4" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-start justify-between">
                                            <p className="text-sm font-medium text-slate-200 truncate">
                                                Order #{activity.order_id}
                                            </p>
                                            <span className="text-xs text-slate-500 whitespace-nowrap ml-2">
                                                {formatDistanceToNow(new Date(activity.created_at), { addSuffix: true })}
                                            </span>
                                        </div>
                                        <p className="text-xs text-ai-300 mt-1 font-mono truncate">{activity.action}</p>
                                        {typeof activity.details?.reason === "string" && (
                                            <p className="text-xs text-slate-500 mt-1 truncate">
                                                {activity.details.reason}
                                            </p>
                                        )}
                                    </div>
                                </motion.div>
                            );
                        })}
                    </AnimatePresence>

                    {feed.length === 0 && (
                        <div className="h-full flex flex-col items-center justify-center text-slate-500">
                            <Bot className="h-12 w-12 opacity-20 mb-2" />
                            {error ? (
                                <>
                                    <p className="text-critical-400 text-sm">Failed to load agent activity</p>
                                    <p className="text-xs mt-1">Check that the backend is running</p>
                                </>
                            ) : (
                                <>
                                    <p>No recent activity</p>
                                    <p className="text-xs mt-1">Trigger an agent from the Agents page to see activity here</p>
                                </>
                            )}
                        </div>
                    )}
                </div>
            </GlassCard>

            <ActivityModal
                activity={selectedActivity}
                onClose={() => setSelectedActivity(null)}
            />
        </>
    );
}
