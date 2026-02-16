"use client";

import { useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Bell, Search, User } from "lucide-react";

const ROUTE_LABELS: Record<string, string> = {
    "/": "Dashboard",
    "/orders": "Orders",
    "/agents": "Agents",
    "/knowledge": "Knowledge Base",
    "/settings": "Settings",
};

function getBreadcrumb(pathname: string): string {
    if (ROUTE_LABELS[pathname]) return ROUTE_LABELS[pathname];
    if (pathname.startsWith("/orders/")) return "Order Detail";
    return "Page";
}

export function TopBar() {
    const router = useRouter();
    const pathname = usePathname();
    const [query, setQuery] = useState("");

    function handleSearch(e: React.FormEvent) {
        e.preventDefault();
        const q = query.trim();
        if (!q) return;
        router.push(`/orders?search=${encodeURIComponent(q)}`);
        setQuery("");
    }

    const breadcrumb = getBreadcrumb(pathname);

    return (
        <div className="flex h-16 w-full items-center justify-between border-b border-white/10 bg-glass-panel backdrop-blur-xl px-6">
            <div className="flex items-center gap-4 text-sm text-slate-400">
                <span className="font-medium text-slate-200">Operations</span>
                <span>/</span>
                <span>{breadcrumb}</span>
            </div>

            <div className="flex items-center gap-6">
                <form onSubmit={handleSearch} className="relative">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Search orders, risks..."
                        className="h-9 w-64 rounded-full border border-white/10 bg-black/20 pl-10 pr-4 text-sm text-slate-200 placeholder-slate-500 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    />
                </form>

                <button className="relative rounded-full p-2 hover:bg-white/5 transition-colors">
                    <Bell className="h-5 w-5 text-slate-400" />
                    <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-critical-500 animate-pulse" />
                </button>

                <div className="h-8 w-8 rounded-full bg-gradient-to-br from-slate-700 to-slate-800 flex items-center justify-center border border-white/10">
                    <User className="h-4 w-4 text-slate-300" />
                </div>
            </div>
        </div>
    );
}
