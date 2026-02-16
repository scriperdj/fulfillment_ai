"use client";

import { GlassCard } from "@/components/ui/GlassCard";
import { format } from "date-fns";
import { CheckCircle, AlertOctagon, Bot, Clock, ArrowDown } from "lucide-react";
import { motion } from "framer-motion";

export interface TimelineEvent {
    id: string;
    type: "prediction" | "deviation" | "agent_response";
    timestamp: string;
    title: string;
    description: string;
    metadata?: any;
    severity?: string;
    agent_type?: string;
}

interface ResolutionTimelineProps {
    events: TimelineEvent[];
}

const EVENT_ICONS = {
    prediction: Clock,
    deviation: AlertOctagon,
    agent_response: Bot,
};

const EVENT_COLORS = {
    prediction: "bg-slate-500",
    deviation: "bg-critical-500",
    agent_response: "bg-ai-500",
};

export function ResolutionTimeline({ events }: ResolutionTimelineProps) {
    if (!events || events.length === 0) {
        return (
            <GlassCard className="h-full flex items-center justify-center text-slate-500">
                No events recorded for this order.
            </GlassCard>
        );
    }

    // Sort events by timestamp ascending
    const sortedEvents = [...events].sort((a, b) =>
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    return (
        <div className="relative pl-8 space-y-8 before:absolute before:inset-0 before:left-3.5 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-slate-700 before:via-ai-500/50 before:to-transparent">
            {sortedEvents.map((event, index) => {
                const Icon = EVENT_ICONS[event.type] || Clock;
                const colorClass = EVENT_COLORS[event.type] || "bg-slate-500";
                const isLast = index === sortedEvents.length - 1;

                return (
                    <motion.div
                        key={event.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="relative"
                    >
                        <div className={`absolute -left-[2.1rem] mt-1.5 h-4 w-4 rounded-full border-2 border-void ${colorClass} ring-4 ring-void z-10`} />

                        <GlassCard className={`p-4 ${event.type === 'agent_response' ? 'border-ai-500/30 bg-ai-500/5' : ''}`}>
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-xs font-mono text-slate-500">
                                    {format(new Date(event.timestamp), "MMM d, HH:mm:ss")}
                                </span>
                                <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border ${event.type === 'deviation' ? 'border-critical-500/30 text-critical-400 bg-critical-500/10' :
                                    event.type === 'agent_response' ? 'border-ai-500/30 text-ai-400 bg-ai-500/10' :
                                        'border-slate-700 text-slate-400 bg-slate-800'
                                    }`}>
                                    <Icon className="h-3 w-3" />
                                    {event.type.replace('_', ' ').toUpperCase()}
                                </div>
                            </div>

                            <h4 className="text-sm font-semibold text-slate-200 mb-1">{event.title}</h4>
                            <p className="text-sm text-slate-400">{event.description}</p>

                            {event.metadata && (
                                <div className="mt-3 bg-black/20 rounded p-2 text-xs font-mono text-slate-500 overflow-x-auto">
                                    <pre>{JSON.stringify(event.metadata, null, 2)}</pre>
                                </div>
                            )}
                        </GlassCard>

                        {!isLast && (
                            <ArrowDown className="absolute left-[1.2rem] -bottom-6 h-4 w-4 text-slate-600 -translate-x-1/2" />
                        )}
                    </motion.div>
                );
            })}

            <div className="relative">
                <div className="absolute -left-[2.1rem] mt-1.5 h-4 w-4 rounded-full border-2 border-void bg-success-500 ring-4 ring-void z-10 animate-pulse" />
                <p className="text-sm text-slate-500 italic">Monitoring active...</p>
            </div>
        </div>
    );
}
