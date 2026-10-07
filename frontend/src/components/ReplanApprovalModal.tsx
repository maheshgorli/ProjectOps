import React, { useState } from 'react';
import {
  ShieldAlert,
  X,
  CheckCircle,
  XCircle,
  Calendar,
  Sparkles,
  ArrowRight,
  UserCheck,
} from 'lucide-react';
import type { ReplanCandidate } from '../types/api';

interface ReplanApprovalModalProps {
  isOpen: boolean;
  onClose: () => void;
  candidate: ReplanCandidate | null;
  onApprove: (rationale: string, decidedBy: string) => Promise<void>;
  onReject: (rationale: string, decidedBy: string) => Promise<void>;
  isSubmitting: boolean;
}

export const ReplanApprovalModal: React.FC<ReplanApprovalModalProps> = ({
  isOpen,
  onClose,
  candidate,
  onApprove,
  onReject,
  isSubmitting,
}) => {
  const [decidedBy, setDecidedBy] = useState('Jane Doe (Human Operator)');
  const [rationale, setRationale] = useState(
    'Approved automated risk mitigation candidate to eliminate capacity overload.',
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen || !candidate) return null;

  const handleApprove = async () => {
    if (!decidedBy.trim() || rationale.trim().length < 3) {
      setErrorMessage('Please provide a valid operator name and rationale (min 3 chars).');
      return;
    }
    setErrorMessage(null);
    try {
      await onApprove(rationale, decidedBy);
      onClose();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Approval failed');
    }
  };

  const handleReject = async () => {
    if (!decidedBy.trim() || rationale.trim().length < 3) {
      setErrorMessage('Please provide a valid operator name and reason for rejection.');
      return;
    }
    setErrorMessage(null);
    try {
      await onReject(rationale, decidedBy);
      onClose();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Rejection failed');
    }
  };

  const finishDelta = candidate.finish_date_delta_days;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-md">
      <div className="glass-panel relative flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-amber-500/40 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 bg-amber-950/30 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/30">
              <ShieldAlert className="h-5 w-5" />
            </div>
            <div>
              <h2 className="font-display text-base font-bold text-white">
                Human Approval Gateway
              </h2>
              <p className="text-xs text-amber-300/80">
                Rule 4: Replanning requires human approval. Never silently change a plan.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* Version Comparison Card */}
          <div className="grid grid-cols-2 gap-3 rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <div className="border-r border-slate-800 pr-3">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                Baseline Snapshot
              </p>
              <p className="mt-1 font-display text-lg font-bold text-slate-200">
                v{candidate.baseline_version}
              </p>
              <div className="mt-2 flex items-center gap-1.5 text-xs text-slate-400">
                <Calendar className="h-3.5 w-3.5 text-slate-500" />
                <span>Finish: {candidate.baseline_finish_date}</span>
              </div>
            </div>

            <div className="pl-3">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-amber-400">
                Proposed Replan
              </p>
              <p className="mt-1 font-display text-lg font-bold text-amber-300">
                v{candidate.proposed_version}
              </p>
              <div className="mt-2 flex items-center gap-1.5 text-xs text-slate-400">
                <Calendar className="h-3.5 w-3.5 text-indigo-400" />
                <span>Finish: {candidate.proposed_finish_date}</span>
                <span
                  className={`ml-1 rounded px-1.5 py-0.5 text-[10px] font-bold ${
                    finishDelta <= 0
                      ? 'bg-emerald-950 text-emerald-300'
                      : 'bg-rose-950 text-rose-300'
                  }`}
                >
                  {finishDelta > 0 ? `+${finishDelta}d` : `${finishDelta}d`}
                </span>
              </div>
            </div>
          </div>

          {/* Mitigation Summary */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
            <div className="flex items-center gap-2 font-display text-xs font-bold text-slate-200">
              <Sparkles className="h-4 w-4 text-indigo-400" />
              <span>Resolved Risks & Mitigation Rationale</span>
              <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-bold text-emerald-300 border border-emerald-500/30">
                {candidate.resolved_risks_count} risk(s) mitigated
              </span>
            </div>
            <ul className="mt-2 space-y-1.5 text-xs text-slate-400">
              {candidate.mitigation_notes.map((note, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <ArrowRight className="h-3.5 w-3.5 text-indigo-400 shrink-0 mt-0.5" />
                  <span>{note}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Governance Form Inputs */}
          <div className="space-y-3">
            <div>
              <label className="flex items-center gap-1.5 text-xs font-semibold text-slate-300">
                <UserCheck className="h-3.5 w-3.5 text-indigo-400" />
                Decided By (Operator Name / Role):
              </label>
              <input
                type="text"
                value={decidedBy}
                onChange={(e) => setDecidedBy(e.target.value)}
                placeholder="e.g. Lead Engineer Jane Doe"
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3.5 py-2 text-xs text-slate-100 placeholder-slate-500 outline-none transition focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300">
                Decision Rationale & Governance Record:
              </label>
              <textarea
                value={rationale}
                onChange={(e) => setRationale(e.target.value)}
                rows={3}
                placeholder="Explain justification for approving or rejecting this candidate..."
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 p-3 text-xs text-slate-100 placeholder-slate-500 outline-none transition focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
            </div>
          </div>

          {errorMessage && (
            <div className="rounded-lg border border-rose-500/30 bg-rose-950/40 p-3 text-xs text-rose-300">
              {errorMessage}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between border-t border-slate-800 bg-slate-900/60 px-6 py-4">
          <button
            onClick={handleReject}
            disabled={isSubmitting}
            className="flex items-center gap-1.5 rounded-lg border border-rose-600/40 bg-rose-950/30 px-4 py-2 text-xs font-semibold text-rose-300 transition hover:bg-rose-900/50 hover:text-white disabled:opacity-50"
          >
            <XCircle className="h-3.5 w-3.5" />
            Reject Proposition
          </button>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              disabled={isSubmitting}
              className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-700 hover:text-white"
            >
              Cancel
            </button>
            <button
              onClick={handleApprove}
              disabled={isSubmitting}
              className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-bold text-white shadow-md shadow-emerald-600/30 transition hover:bg-emerald-500 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50"
            >
              <CheckCircle className="h-3.5 w-3.5" />
              {isSubmitting ? 'Saving Snapshot...' : `Approve & Activate v${candidate.proposed_version}`}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
