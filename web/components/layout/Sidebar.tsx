"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import {
    LayoutDashboard,
    Package,
    Bot,
    BookOpen,
    Settings,
    LogOut
} from "lucide-react";

const navigation = [
    { name: "Dashboard", href: "/", icon: LayoutDashboard },
    { name: "Orders", href: "/orders", icon: Package },
    { name: "Agents", href: "/agents", icon: Bot },
    { name: "Knowledge Base", href: "/knowledge", icon: BookOpen },
    { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
    const pathname = usePathname();

    return (
        <div className="flex h-screen flex-col justify-between border-r border-white/10 bg-glass-panel backdrop-blur-xl w-64 p-4">
            <div className="flex flex-col gap-8">
                <div className="flex items-center gap-2 px-2">
                    <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-primary-500 to-ai-500" />
                    <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary-400 to-ai-400">
                        Fulfillment AI
                    </span>
                </div>

                <nav className="flex flex-col gap-2">
                    {navigation.map((item) => {
                        const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
                        return (
                            <Link
                                key={item.name}
                                href={item.href}
                                className={cn(
                                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                                    isActive
                                        ? "bg-white/10 text-primary-400"
                                        : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
                                )}
                            >
                                <item.icon className="h-5 w-5" />
                                {item.name}
                            </Link>
                        );
                    })}
                </nav>
            </div>

            <div className="px-2">
                <button className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-400 hover:bg-white/5 hover:text-slate-200 transition-colors">
                    <LogOut className="h-5 w-5" />
                    Sign Out
                </button>
            </div>
        </div>
    );
}
