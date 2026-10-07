import React, { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
} from 'recharts';
import { Users, AlertTriangle, CheckCircle2 } from 'lucide-react';
import type { ScheduleResult, Member } from '../types/api';

interface WorkloadChartProps {
  schedule: ScheduleResult | null;
  members: Member[];
}

export const WorkloadChart: React.FC<WorkloadChartProps> = ({ schedule, members }) => {
  const membersMap = useMemo(() => {
    const map = new Map<string, Member>();
    members.forEach((m) => map.set(m.id, m));
    return map;
  }, [members]);

  // Aggregate member workload data for chart
  const memberData = useMemo(() => {
    if (!schedule || !schedule.member_workloads) return [];

    return Object.entries(schedule.member_workloads).map(([memberId, workload]) => {
      const member = membersMap.get(memberId);
      const name = member?.name || memberId.slice(0, 8);
      const capacity = workload.capacity_hours_per_day;
      const peakHours = workload.peak_daily_hours;
      const isOverallocated = workload.is_overallocated;

      return {
        memberId,
        name,
        role: member?.role || 'Contributor',
        totalAssignedHours: workload.total_assigned_hours,
        peakHours,
        capacity,
        isOverallocated,
        overallocatedDates: workload.overallocated_dates,
      };
    });
  }, [schedule, membersMap]);

  const hasOverallocation = memberData.some((m) => m.isOverallocated);

  if (!schedule || memberData.length === 0) {
    return (
      <div className="glass-panel mx-6 flex h-64 flex-col items-center justify-center rounded-2xl p-6 text-center">
        <Users className="h-10 w-10 text-slate-600 mb-2" />
        <p className="text-xs text-slate-400">No member workload allocations found in schedule.</p>
      </div>
    );
  }

  return (
    <div className="mx-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
      {/* Chart: Peak Daily Allocation vs Capacity */}
      <div className="glass-panel rounded-2xl p-5 lg:col-span-2">
        <div className="flex items-center justify-between pb-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Users className="h-4 w-4" />
            </div>
            <div>
              <h3 className="font-display text-sm font-bold text-white">
                Member Capacity Utilization
              </h3>
              <p className="text-[11px] text-slate-400">
                Peak daily assigned hours vs. 8h daily capacity threshold
              </p>
            </div>
          </div>

          <div
            className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${
              hasOverallocation
                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
            }`}
          >
            {hasOverallocation ? (
              <>
                <AlertTriangle className="h-3.5 w-3.5 text-rose-400" />
                <span>OVERALLOCATION DETECTED</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                <span>CAPACITY BALANCED</span>
              </>
            )}
          </div>
        </div>

        {/* Recharts Bar Chart */}
        <div className="h-56 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={memberData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis stroke="#64748b" fontSize={11} tickLine={false} unit="h" />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="glass-card rounded-lg p-2.5 text-xs shadow-xl border border-slate-700">
                        <p className="font-bold text-white">{data.name}</p>
                        <p className="text-slate-400">Role: {data.role}</p>
                        <p className="mt-1 text-indigo-300">
                          Peak Daily: <span className="font-bold">{data.peakHours}h</span>
                        </p>
                        <p className="text-slate-400">Capacity Limit: {data.capacity}h/day</p>
                        <p className="text-slate-400">Total Work: {data.totalAssignedHours}h</p>
                        {data.isOverallocated && (
                          <p className="mt-1 text-rose-400 font-semibold">
                            ⚠️ Overallocated on {data.overallocatedDates.length} date(s)
                          </p>
                        )}
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <ReferenceLine y={8} stroke="#f43f5e" strokeDasharray="4 4" label={{ value: 'Capacity Cap (8h)', fill: '#f43f5e', fontSize: 10 }} />
              <Bar dataKey="peakHours" radius={[6, 6, 0, 0]}>
                {memberData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.isOverallocated ? '#f43f5e' : '#6366f1'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Roster & Workload Stats Card */}
      <div className="glass-panel flex flex-col justify-between rounded-2xl p-5">
        <div>
          <h4 className="font-display text-sm font-bold text-white">Team Member Workload</h4>
          <p className="text-[11px] text-slate-400">Daily capacity breakdown</p>

          <div className="mt-4 flex flex-col gap-2.5 max-h-[200px] overflow-y-auto pr-1">
            {memberData.map((m) => (
              <div
                key={m.memberId}
                className="flex items-center justify-between rounded-xl bg-slate-900/70 p-2.5 border border-slate-800 text-xs"
              >
                <div>
                  <p className="font-semibold text-slate-200">{m.name}</p>
                  <p className="text-[10px] text-slate-500">{m.role}</p>
                </div>
                <div className="text-right">
                  <span
                    className={`font-mono font-bold ${
                      m.isOverallocated ? 'text-rose-400' : 'text-indigo-300'
                    }`}
                  >
                    {m.peakHours}h peak
                  </span>
                  <p className="text-[10px] text-slate-400">{m.totalAssignedHours}h total</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-4 rounded-xl border border-slate-800/80 bg-slate-900/40 p-3 text-xs text-slate-400">
          <p className="text-[11px] leading-relaxed">
            <span className="font-semibold text-indigo-300">Rule 1 & 3:</span> Deterministic scheduler
            allocates task duration according to working days (Mon–Fri) and flags peak days
            exceeding daily capacity.
          </p>
        </div>
      </div>
    </div>
  );
};
