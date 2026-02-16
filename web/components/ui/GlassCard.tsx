import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { ReactNode } from "react";

interface GlassCardProps {
    children?: ReactNode;
    className?: string;
    animate?: boolean;
}

export function GlassCard({ children, className, animate = false }: GlassCardProps) {
    const baseClasses = cn(
        "rounded-xl p-6 shadow-lg backdrop-blur-md bg-glass border border-white/10 relative overflow-hidden",
        className
    );

    if (animate) {
        return (
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
                className={baseClasses}
            >
                {children}
            </motion.div>
        );
    }

    return <div className={baseClasses}>{children}</div>;
}
