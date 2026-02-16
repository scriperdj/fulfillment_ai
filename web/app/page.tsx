import { KPIGrid } from "@/components/dashboard/KPIGrid";
import { WarehousePerformance } from "@/components/dashboard/WarehousePerformance";
import { AgentFeed } from "@/components/dashboard/AgentFeed";
import { DeviationTable } from "@/components/dashboard/DeviationTable";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-100 to-slate-400">
          Operations Control Center
        </h1>
        <div className="flex items-center gap-2 text-sm text-slate-400 font-mono">
          <span className="h-2 w-2 rounded-full bg-success-500 animate-pulse" />
          SYSTEM ONLINE
        </div>
      </div>

      <KPIGrid />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[450px]">
        <div className="lg:col-span-2 h-full">
          <WarehousePerformance />
        </div>
        <div className="h-full">
          <AgentFeed />
        </div>
      </div>

      <div className="h-[400px]">
        <DeviationTable />
      </div>
    </div>
  );
}
