"use client";

import { useEffect, useState } from "react";
import { GlassCard } from "@/components/ui/GlassCard";
import { motion } from "framer-motion";

const NODES = [
    { id: "A", x: 100, y: 150, label: "North America (A)" },
    { id: "B", x: 400, y: 100, label: "Europe (B)" },
    { id: "C", x: 700, y: 150, label: "Asia (C)" },
    { id: "D", x: 250, y: 350, label: "South America (D)" },
    { id: "E", x: 550, y: 350, label: "Africa (E)" },
];

const CONNECTIONS = [
    ["A", "B"], ["B", "C"], ["A", "D"], ["B", "E"], ["C", "E"], ["D", "E"]
];

export function NetworkGraph() {
    const [activePackets, setActivePackets] = useState<{ id: number; path: string }[]>([]);

    // Simulate network traffic
    useEffect(() => {
        const interval = setInterval(() => {
            const id = Date.now();
            const pathIndex = Math.floor(Math.random() * CONNECTIONS.length);
            const path = `path-${CONNECTIONS[pathIndex][0]}-${CONNECTIONS[pathIndex][1]}`;

            setActivePackets(prev => [...prev, { id, path }]);

            // Cleanup old packets
            setTimeout(() => {
                setActivePackets(prev => prev.filter(p => p.id !== id));
            }, 2000);
        }, 800);

        return () => clearInterval(interval);
    }, []);

    return (
        <GlassCard className="h-[400px] relative flex flex-col items-center justify-center p-0 overflow-hidden">
            <div className="absolute top-4 left-4 z-10">
                <h3 className="text-lg font-semibold text-slate-100">Global Logistics Network</h3>
                <div className="flex items-center gap-2 mt-1">
                    <span className="h-2 w-2 rounded-full bg-success-500 animate-pulse" />
                    <span className="text-xs text-slate-400">All Nodes Operational</span>
                </div>
            </div>

            <svg className="w-full h-full" viewBox="0 0 800 450">
                <defs>
                    <radialGradient id="nodeGradient">
                        <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.8" />
                        <stop offset="100%" stopColor="#06b6d4" stopOpacity="0" />
                    </radialGradient>
                </defs>

                {/* Connections */}
                {CONNECTIONS.map(([startId, endId]) => {
                    const start = NODES.find(n => n.id === startId)!;
                    const end = NODES.find(n => n.id === endId)!;
                    return (
                        <line
                            key={`${startId}-${endId}`}
                            x1={start.x}
                            y1={start.y}
                            x2={end.x}
                            y2={end.y}
                            stroke="#1e293b"
                            strokeWidth="2"
                        />
                    );
                })}

                {/* Active Packets */}
                {activePackets.map(packet => {
                    const [startId, endId] = packet.path.replace('path-', '').split('-');
                    const start = NODES.find(n => n.id === startId)!;
                    const end = NODES.find(n => n.id === endId)!;

                    return (
                        <motion.circle
                            key={packet.id}
                            r="4"
                            fill="#fff"
                            initial={{ cx: start.x, cy: start.y, opacity: 0 }}
                            animate={{ cx: end.x, cy: end.y, opacity: [0, 1, 0] }}
                            transition={{ duration: 2, ease: "linear" }}
                        />
                    );
                })}

                {/* Nodes */}
                {NODES.map(node => (
                    <g key={node.id}>
                        <circle cx={node.x} cy={node.y} r="30" fill="url(#nodeGradient)" opacity="0.2" />
                        <circle cx={node.x} cy={node.y} r="6" fill="#06b6d4" className="animate-pulse" />
                        <text x={node.x} y={node.y + 20} textAnchor="middle" fill="#94a3b8" fontSize="12" className="select-none font-mono">
                            {node.label}
                        </text>
                    </g>
                ))}
            </svg>
        </GlassCard>
    );
}
