import React from 'react';
import { GitCommit, Calendar, User, CheckCircle2, X } from 'lucide-react';
import type { ProjectPlan } from '../types/api';

interface VersionHistoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  versions: number[];
  activeVersion: number | null;
  selectedPlan: ProjectPlan | null;
  onSelectVersion: (version: number) => void;
}

export const VersionHistoryDrawer: React.FC<VersionHistoryDrawerProps> = ({
  isOpen,
  onClose,
  versions,
  activeVersion,
  selectedPlan,
  onSelectVersion,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/70 backdrop-blur-sm">
      <div className="glass-panel h-full w-full max-w-md border-l border-slate-800 p-6 shadow-2xl flex flex-col justify-between">
        <div>
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                <GitCommit className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-display text-sm font-bold text-white">Plan Version History</h3>
                <p className="text-[11px] text-slate-400">Rule 5: Immutable versioned snapshots</p>
              </div>
            </div>

            <button
              onClick={onClose}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Versions List */}
          <div className="mt-4 space-y-2.5 max-h-[calc(100vh-250px)] overflow-y-auto pr-1">
            {versions.map((ver) => {
              const isActive = ver === activeVersion;
              const isSelected = selectedPlan?.version === ver;

              return (
                <div
                  key={ver}
                  onClick={() => onSelectVersion(ver)}
                  className={`cursor-pointer rounded-xl p-3.5 border transition-all text-xs ${
                    isSelected
                      ? 'border-indigo-500 bg-indigo-950/40 shadow-md shadow-indigo-950/50'
                      : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-display text-sm font-bold text-white">Version {ver}</span>
                    {isActive && (
                      <span className="flex items-center gap-1 rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-bold text-emerald-300 border border-emerald-500/30">
                        <CheckCircle2 className="h-3 w-3" />
                        ACTIVE
                      </span>
                    )}
                  </div>

                  {isSelected && selectedPlan && (
                    <div className="mt-2 space-y-1 text-[11px] text-slate-400 border-t border-slate-800/80 pt-2">
                      <p className="text-slate-200 font-medium">{selectedPlan.name}</p>
                      <div className="flex items-center gap-1.5">
                        <User className="h-3 w-3 text-slate-500" />
                        <span>Created by: {selectedPlan.created_by}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Calendar className="h-3 w-3 text-slate-500" />
                        <span>Tasks: {selectedPlan.tasks.length} tasks</span>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        <div className="border-t border-slate-800 pt-4 text-center">
          <p className="text-[11px] text-slate-500">
            Past plan snapshots are permanent and cannot be modified or deleted.
          </p>
        </div>
      </div>
    </div>
  );
};
