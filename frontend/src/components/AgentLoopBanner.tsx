import React from 'react';
import {
  Play,
  RotateCcw,
  CheckCircle2,
  Clock,
  AlertOctagon,
  ArrowRight,
  ShieldAlert,
} from 'lucide-react';
import type { AgentLoopStatus, LoopStepResponse } from '../types/api';

interface AgentLoopBannerProps {
  loopStatus: AgentLoopStatus | null;
  lastStepResult: LoopStepResponse | null;
  onRunStep: () => void;
  onOpenApprovalModal: () => void;
  isRunningStep: boolean;
}

const STAGES = [
  { id: 'PLAN', label: '1. PLAN', desc: 'DAG & CPM Validation' },
  { id: 'EXECUTE', label: '2. EXECUTE', desc: 'Readiness & Actionability' },
  { id: 'OBSERVE', label: '3. OBSERVE', desc: 'Progress & Deadlines' },
  { id: 'REASON', label: '4. REASON', desc: 'Risk Rules & Health' },
  { id: 'REPLAN', label: '5. REPLAN', desc: 'Mitigation Simulation' },
  { id: 'APPROVE', label: '6. APPROVE', desc: 'Human Governance Gate' },
] as const;

export const AgentLoopBanner: React.FC<AgentLoopBannerProps> = ({
  loopStatus,
  lastStepResult,
  onRunStep,
  onOpenApprovalModal,
  isRunningStep,
}) => {
  const currentStage = lastStepResult?.current_stage || loopStatus?.recent_runs?.[0]?.loop_stage || 'PLAN';
  const isAwaitingApproval =
    loopStatus?.requires_human_approval ||
    lastStepResult?.requires_human_approval ||
    loopStatus?.current_status === 'AWAITING_APPROVAL';

  return (
    <div className="mx-6 mt-4 flex flex-col gap-3">
      {/* Loop Stepper Panel */}
      <div className="glass-panel flex flex-wrap items-center justify-between gap-4 rounded-xl px-5 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <RotateCcw className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Autonomous Multi-Agent Loop
              </span>
              <span
                className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                  isAwaitingApproval
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                    : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                }`}
              >
                {isAwaitingApproval ? 'AWAITING HUMAN APPROVAL' : 'AUTONOMOUS ACTIVE'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              Deterministic cycle enforcing human governance and zero unverified changes
            </p>
          </div>
        </div>

        {/* Stages Stepper */}
        <div className="flex flex-wrap items-center gap-1.5 overflow-x-auto py-1">
          {STAGES.map((s, idx) => {
            const isActive = currentStage === s.id;
            return (
              <React.Fragment key={s.id}>
                <div
                  className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs transition ${
                    isActive
                      ? 'border border-indigo-500/50 bg-indigo-500/20 font-semibold text-indigo-200 shadow-sm shadow-indigo-500/20'
                      : 'border border-slate-800 bg-slate-900/60 text-slate-400'
                  }`}
                  title={s.desc}
                >
                  {isActive ? (
                    <Clock className="h-3 w-3 text-indigo-400 animate-pulse" />
                  ) : (
                    <CheckCircle2 className="h-3 w-3 text-slate-600" />
                  )}
                  <span>{s.label}</span>
                </div>
                {idx < STAGES.length - 1 && (
                  <ArrowRight className="h-3 w-3 text-slate-700 shrink-0" />
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* Run Step Trigger Button */}
        <button
          onClick={onRunStep}
          disabled={isRunningStep}
          className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-indigo-600/30 transition hover:bg-indigo-500 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50"
        >
          <Play className={`h-3.5 w-3.5 ${isRunningStep ? 'animate-spin' : ''}`} />
          {isRunningStep ? 'Executing Cycle...' : 'Step Agent Loop'}
        </button>
      </div>

      {/* Human Approval Alert Banner (when REPLAN triggers) */}
      {isAwaitingApproval && (
        <div className="glass-panel flex flex-wrap items-center justify-between gap-4 rounded-xl border border-amber-500/40 bg-gradient-to-r from-amber-950/40 via-amber-900/20 to-slate-950 px-5 py-3 shadow-lg shadow-amber-950/30">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/30">
              <ShieldAlert className="h-5 w-5 text-amber-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-display text-sm font-bold text-amber-200">
                  Human Approval Required (Rule 4)
                </span>
                <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-amber-300">
                  GATEWAY HALTED
                </span>
              </div>
              <p className="text-xs text-slate-300">
                Deterministic risk engine simulated a candidate replan to mitigate project risks.
                Plans are never modified silently without explicit human authorization.
              </p>
            </div>
          </div>

          <button
            onClick={onOpenApprovalModal}
            className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-amber-500 to-amber-600 px-4 py-2 text-xs font-bold text-slate-950 shadow-md shadow-amber-500/30 transition hover:from-amber-400 hover:to-amber-500 hover:scale-[1.02] active:scale-[0.98]"
          >
            <AlertOctagon className="h-4 w-4" />
            Review & Approve Replan
          </button>
        </div>
      )}
    </div>
  );
};
