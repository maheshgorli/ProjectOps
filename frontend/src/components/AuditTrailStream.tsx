import { useState } from 'react';
import {
  History,
  GitCommit,
  ShieldCheck,
  Bot,
  User,
  ArrowRight,
} from 'lucide-react';
import type { ProgressHistoryEvent, DecisionRecord, AgentRun } from '../types/api';

interface AuditTrailStreamProps {
  progressHistory: ProgressHistoryEvent[];
  decisions: DecisionRecord[];
  agentRuns: AgentRun[];
}

export const AuditTrailStream: React.FC<AuditTrailStreamProps> = ({
  progressHistory,
  decisions,
  agentRuns,
}) => {
  const [activeTab, setActiveTab] = useState<'progress' | 'decisions' | 'agentRuns'>('progress');

  return (
    <div className="glass-panel mx-6 rounded-2xl p-5 mb-8">
      {/* Tab Navigation */}
      <div className="flex flex-wrap items-center justify-between border-b border-slate-800 pb-3 gap-2">
        <div className="flex items-center gap-2">
          <History className="h-4 w-4 text-indigo-400" />
          <h3 className="font-display text-sm font-bold text-white">
            Immutable Audit Trail & Evidence Stream
          </h3>
          <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] font-mono text-slate-400">
            Rule 5 (Append-Only)
          </span>
        </div>

        <div className="flex items-center gap-1 rounded-xl bg-slate-900/80 p-1 border border-slate-800">
          <button
            onClick={() => setActiveTab('progress')}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              activeTab === 'progress'
                ? 'bg-indigo-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <GitCommit className="h-3.5 w-3.5" />
            <span>Progress & GitHub Evidence ({progressHistory.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('decisions')}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              activeTab === 'decisions'
                ? 'bg-indigo-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <ShieldCheck className="h-3.5 w-3.5" />
            <span>Governance Decisions ({decisions.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('agentRuns')}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              activeTab === 'agentRuns'
                ? 'bg-indigo-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Bot className="h-3.5 w-3.5" />
            <span>Agent Runs ({agentRuns.length})</span>
          </button>
        </div>
      </div>

      {/* Tab 1: Progress & GitHub Evidence */}
      {activeTab === 'progress' && (
        <div className="mt-4 max-h-72 overflow-y-auto space-y-2 pr-1">
          {progressHistory.length === 0 ? (
            <p className="py-6 text-center text-xs text-slate-500">No progress history recorded yet.</p>
          ) : (
            progressHistory.map((ev) => {
              const isGithub = ev.recorded_by.startsWith('github:') || ev.evidence_notes.includes('[EVIDENCE]');
              return (
                <div
                  key={ev.id}
                  className="flex items-start justify-between rounded-xl bg-slate-900/60 p-3 border border-slate-800/80 text-xs gap-3 hover:border-slate-700 transition"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-code font-bold text-indigo-400">{ev.task_id}</span>
                      {isGithub && (
                        <span className="rounded bg-sky-500/20 px-1.5 py-0.5 text-[10px] font-bold text-sky-300 border border-sky-500/30">
                          GITHUB EVIDENCE
                        </span>
                      )}
                      <div className="flex items-center gap-1 text-[11px] text-slate-400">
                        <span>{ev.previous_status || 'INIT'}</span>
                        <ArrowRight className="h-3 w-3 text-slate-600" />
                        <span className="font-semibold text-slate-200">{ev.new_status}</span>
                      </div>
                    </div>
                    <p className="text-[11px] text-slate-300 font-mono leading-relaxed">
                      {ev.evidence_notes}
                    </p>
                  </div>

                  <div className="text-right shrink-0 text-[10px] text-slate-500">
                    <div className="flex items-center gap-1 justify-end">
                      <User className="h-3 w-3" />
                      <span>{ev.recorded_by}</span>
                    </div>
                    <p className="mt-0.5">{new Date(ev.recorded_at).toLocaleTimeString()}</p>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* Tab 2: Governance Decisions */}
      {activeTab === 'decisions' && (
        <div className="mt-4 max-h-72 overflow-y-auto space-y-2 pr-1">
          {decisions.length === 0 ? (
            <p className="py-6 text-center text-xs text-slate-500">No governance decisions recorded yet.</p>
          ) : (
            decisions.map((dec) => {
              const isApproved = dec.decision_type === 'REPLAN_APPROVED';
              return (
                <div
                  key={dec.id}
                  className="flex items-start justify-between rounded-xl bg-slate-900/60 p-3 border border-slate-800/80 text-xs gap-3 hover:border-slate-700 transition"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span
                        className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                          isApproved
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                            : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                        }`}
                      >
                        {dec.decision_type}
                      </span>
                      <span className="font-semibold text-slate-200">{dec.summary}</span>
                    </div>
                    <p className="text-[11px] text-slate-300 leading-relaxed">
                      <span className="text-slate-500 font-semibold">Rationale: </span>
                      {dec.rationale}
                    </p>
                  </div>

                  <div className="text-right shrink-0 text-[10px] text-slate-500">
                    <div className="flex items-center gap-1 justify-end font-medium text-slate-400">
                      <User className="h-3 w-3" />
                      <span>{dec.decided_by}</span>
                    </div>
                    <p className="mt-0.5">{new Date(dec.recorded_at).toLocaleDateString()}</p>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* Tab 3: Agent Runs */}
      {activeTab === 'agentRuns' && (
        <div className="mt-4 max-h-72 overflow-y-auto space-y-2 pr-1">
          {agentRuns.length === 0 ? (
            <p className="py-6 text-center text-xs text-slate-500">No agent runs recorded yet.</p>
          ) : (
            agentRuns.map((run) => (
              <div
                key={run.id}
                className="flex items-start justify-between rounded-xl bg-slate-900/60 p-3 border border-slate-800/80 text-xs gap-3 hover:border-slate-700 transition"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="rounded bg-indigo-500/20 px-1.5 py-0.5 text-[10px] font-bold text-indigo-300 border border-indigo-500/30">
                      STAGE: {run.loop_stage}
                    </span>
                    <span
                      className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                        run.status === 'SUCCESS' || run.status === 'HEALTHY'
                          ? 'text-emerald-400'
                          : run.status === 'AWAITING_APPROVAL'
                          ? 'text-amber-400'
                          : 'text-rose-400'
                      }`}
                    >
                      {run.status}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-300 leading-relaxed">{run.summary}</p>
                </div>

                <div className="text-right shrink-0 text-[10px] text-slate-500">
                  <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[9px] text-slate-400">
                    {run.triggered_by}
                  </span>
                  <p className="mt-1">{new Date(run.recorded_at).toLocaleTimeString()}</p>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};
