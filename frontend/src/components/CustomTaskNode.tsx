import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import {
  Clock,
  User,
  AlertCircle,
  Flame,
  CheckCircle,
  PlayCircle,
  Ban,
} from 'lucide-react';
import type { Task, ScheduledTask, Member } from '../types/api';

export interface CustomTaskNodeData extends Record<string, unknown> {
  task: Task;
  scheduled?: ScheduledTask;
  member?: Member;
  isCritical: boolean;
}

export const CustomTaskNode = memo(({ data }: { data: CustomTaskNodeData }) => {
  const { task, scheduled, member, isCritical } = data;

  const statusIcons = {
    TODO: <Clock className="h-3 w-3 text-slate-400" />,
    IN_PROGRESS: <PlayCircle className="h-3 w-3 text-sky-400" />,
    BLOCKED: <Ban className="h-3 w-3 text-rose-400" />,
    COMPLETED: <CheckCircle className="h-3 w-3 text-emerald-400" />,
  };

  const statusStyles = {
    TODO: 'bg-slate-800/80 text-slate-300 border-slate-700',
    IN_PROGRESS: 'bg-sky-950/60 text-sky-300 border-sky-700/60',
    BLOCKED: 'bg-rose-950/60 text-rose-300 border-rose-700/60',
    COMPLETED: 'bg-emerald-950/60 text-emerald-300 border-emerald-700/60',
  };

  const totalFloat = scheduled?.total_float ?? 0;

  return (
    <div
      className={`glass-card relative min-w-[240px] max-w-[280px] rounded-xl p-3.5 shadow-xl transition-all duration-200 ${
        isCritical ? 'critical-glow' : 'hover:border-slate-600'
      }`}
    >
      {/* React Flow Connection Handles */}
      <Handle
        type="target"
        position={Position.Left}
        className="!h-2.5 !w-2.5 !border-2 !border-slate-900 !bg-indigo-400"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!h-2.5 !w-2.5 !border-2 !border-slate-900 !bg-indigo-400"
      />

      {/* Top Header: ID & Badges */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <span className="font-code text-[11px] font-bold text-slate-400">{task.id}</span>
          {isCritical && (
            <span className="flex items-center gap-1 rounded bg-rose-500/20 px-1.5 py-0.5 text-[9px] font-bold text-rose-400 border border-rose-500/30">
              <Flame className="h-2.5 w-2.5 text-rose-400" />
              CRITICAL
            </span>
          )}
        </div>

        {/* Status Pill */}
        <span
          className={`flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium ${
            statusStyles[task.status]
          }`}
        >
          {statusIcons[task.status]}
          {task.status}
        </span>
      </div>

      {/* Title */}
      <h4 className="mt-2 text-xs font-semibold text-white leading-snug line-clamp-2">
        {task.title}
      </h4>

      {/* Details Footer */}
      <div className="mt-3 flex items-center justify-between border-t border-slate-800/80 pt-2 text-[11px] text-slate-400">
        {/* Assignee */}
        <div className="flex items-center gap-1.5 truncate max-w-[120px]" title={member?.name || 'Unassigned'}>
          <User className="h-3 w-3 text-slate-500 shrink-0" />
          <span className="truncate">{member?.name || 'Unassigned'}</span>
        </div>

        {/* Hours & Slack */}
        <div className="flex items-center gap-2">
          <span>{task.estimated_hours}h</span>
          <span
            className={`rounded px-1.5 py-0.5 text-[10px] font-medium font-code ${
              isCritical
                ? 'bg-rose-950 text-rose-300'
                : totalFloat > 0
                ? 'bg-emerald-950/80 text-emerald-300'
                : 'bg-slate-800 text-slate-400'
            }`}
            title="Total Float / Slack"
          >
            {totalFloat > 0 ? `+${totalFloat}d` : '0d'}
          </span>
        </div>
      </div>

      {/* Overdue Warning Icon */}
      {task.is_overdue && (
        <div className="absolute -top-2 -right-2 flex h-5 w-5 items-center justify-center rounded-full bg-rose-600 text-white shadow-lg shadow-rose-600/50">
          <AlertCircle className="h-3 w-3" />
        </div>
      )}
    </div>
  );
});

CustomTaskNode.displayName = 'CustomTaskNode';
