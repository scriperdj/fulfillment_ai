"use client";

import { useEffect, useRef } from "react";
import { X, Bot, Mail, CreditCard, AlertCircle, RefreshCw, Clock, Hash, Tag } from "lucide-react";
import { formatDistanceToNow, format } from "date-fns";
import { cn } from "@/lib/utils";
import type { AgentActivity } from "@/lib/types";

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

interface ActivityModalProps {
    activity: AgentActivity | null;
    onClose: () => void;
}

export function ActivityModal({ activity, onClose }: ActivityModalProps) {
    const overlayRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!activity) return;
        function handleKey(e: KeyboardEvent) {
            if (e.key === "Escape") onClose();
        }
        document.addEventListener("keydown", handleKey);
        return () => document.removeEventListener("keydown", handleKey);
    }, [activity, onClose]);

    if (!activity) return null;

    const Icon = AGENT_ICONS[activity.agent_type] || Bot;
    const colorClass = AGENT_COLORS[activity.agent_type] || "text-slate-400 bg-slate-500/10 border-slate-500/20";

    return (
        <div
            ref={overlayRef}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
            onClick={(e) => {
                if (e.target === overlayRef.current) onClose();
            }}
        >
            <div className="relative w-full max-w-lg mx-4 rounded-2xl border border-white/10 bg-slate-900/95 shadow-2xl">
                {/* Header */}
                <div className="flex items-center justify-between p-5 border-b border-white/10">
                    <div className="flex items-center gap-3">
                        <div className={cn("h-10 w-10 rounded-lg flex items-center justify-center border", colorClass)}>
                            <Icon className="h-5 w-5" />
                        </div>
                        <div>
                            <h2 className="text-lg font-semibold text-slate-100">
                                Agent Activity Detail
                            </h2>
                            <span className={cn("text-xs px-2 py-0.5 rounded-full border font-medium", colorClass)}>
                                {activity.agent_type}
                            </span>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="h-8 w-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-200 hover:bg-white/10 transition-colors"
                    >
                        <X className="h-4 w-4" />
                    </button>
                </div>

                {/* Body */}
                <div className="p-5 space-y-4 max-h-[60vh] overflow-y-auto">
                    {/* Metadata row */}
                    <div className="grid grid-cols-2 gap-3">
                        <div className="flex items-center gap-2 rounded-lg bg-white/5 border border-white/5 p-3">
                            <Hash className="h-4 w-4 text-slate-500 flex-shrink-0" />
                            <div>
                                <p className="text-[10px] uppercase tracking-wider text-slate-500">Order ID</p>
                                <p className="text-sm font-mono text-slate-200">{activity.order_id}</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-2 rounded-lg bg-white/5 border border-white/5 p-3">
                            <Clock className="h-4 w-4 text-slate-500 flex-shrink-0" />
                            <div>
                                <p className="text-[10px] uppercase tracking-wider text-slate-500">Timestamp</p>
                                <p className="text-sm text-slate-200">
                                    {format(new Date(activity.created_at), "MMM d, yyyy HH:mm:ss")}
                                </p>
                                <p className="text-[10px] text-slate-500">
                                    {formatDistanceToNow(new Date(activity.created_at), { addSuffix: true })}
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Action */}
                    <div>
                        <div className="flex items-center gap-2 mb-2">
                            <Tag className="h-4 w-4 text-slate-500" />
                            <p className="text-xs uppercase tracking-wider text-slate-500 font-medium">Action</p>
                        </div>
                        <div className="rounded-lg bg-white/5 border border-white/5 p-3">
                            <p className="text-sm text-slate-200 whitespace-pre-wrap break-words">{activity.action}</p>
                        </div>
                    </div>

                    {/* Details JSON */}
                    {activity.details && Object.keys(activity.details).length > 0 && (
                        <div>
                            <p className="text-xs uppercase tracking-wider text-slate-500 font-medium mb-2">Details</p>
                            <pre className="text-xs text-slate-300 bg-black/30 rounded-lg p-4 overflow-auto max-h-64 font-mono border border-white/5 whitespace-pre-wrap break-words">
                                {JSON.stringify(activity.details, null, 2)}
                            </pre>
                        </div>
                    )}

                    {/* Activity ID */}
                    <div className="pt-2 border-t border-white/5">
                        <p className="text-[10px] text-slate-600 font-mono">ID: {activity.id}</p>
                    </div>
                </div>
            </div>
        </div>
    );
}
