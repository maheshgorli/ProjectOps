import React from 'react';
import {
  Sparkles,
  RefreshCw,
  GitCommit,
  ShieldCheck,
  AlertTriangle,
  FolderGit2,
} from 'lucide-react';
import type { Project, RiskAnalysis } from '../types/api';

interface HeaderProps {
  projects: Project[];
  selectedProject: Project | null;
  onSelectProject: (p: Project) => void;
  activeVersion: number | null;
  riskAnalysis: RiskAnalysis | null;
  onOpenGoalDecomposer: () => void;
  onRefresh: () => void;
  isLoading: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  projects,
  selectedProject,
  onSelectProject,
  activeVersion,
  riskAnalysis,
  onOpenGoalDecomposer,
  onRefresh,
  isLoading,
}) => {
  const health = riskAnalysis?.health_score ?? 100;
  const isAtRisk = riskAnalysis?.is_at_risk ?? false;

  return (
    <header className="glass-panel sticky top-0 z-40 border-b border-slate-800/80 px-6 py-3.5 backdrop-blur-xl">
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* Left: Branding & Project Selector */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 via-indigo-600 to-purple-700 shadow-lg shadow-indigo-500/20">
              <FolderGit2 className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-display text-lg font-bold tracking-tight text-white">
                  Project<span className="text-indigo-400">Ops</span>
                </span>
                <span className="rounded-full bg-indigo-500/10 px-2 py-0.5 text-[10px] font-semibold text-indigo-300 border border-indigo-500/20">
                  AUTONOMOUS AGENT
                </span>
              </div>
              <p className="text-xs text-slate-400">Deterministic Execution & Risk Intelligence</p>
            </div>
          </div>

          <div className="h-6 w-px bg-slate-800" />

          {/* Project Dropdown */}
          <div className="flex items-center gap-2">
            <label htmlFor="project-select" className="text-xs font-medium text-slate-400">
              Project:
            </label>
            <select
              id="project-select"
              value={selectedProject?.id || ''}
              onChange={(e) => {
                const found = projects.find((p) => p.id === e.target.value);
                if (found) onSelectProject(found);
              }}
              className="rounded-lg border border-slate-700/80 bg-slate-900/90 px-3 py-1.5 text-xs font-medium text-slate-200 outline-none transition focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Right: Metrics Badges & Action Buttons */}
        <div className="flex items-center gap-3">
          {/* Active Version Pill */}
          <div className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-1.5 text-xs text-slate-300">
            <GitCommit className="h-3.5 w-3.5 text-indigo-400" />
            <span className="text-slate-400">Snapshot:</span>
            <span className="font-semibold text-indigo-300">
              {activeVersion ? `v${activeVersion}` : 'None'}
            </span>
          </div>

          {/* Health Score Pill */}
          <div
            className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
              isAtRisk
                ? 'border-rose-500/30 bg-rose-950/40 text-rose-300'
                : health >= 80
                ? 'border-emerald-500/30 bg-emerald-950/40 text-emerald-300'
                : 'border-amber-500/30 bg-amber-950/40 text-amber-300'
            }`}
          >
            {isAtRisk ? (
              <AlertTriangle className="h-3.5 w-3.5 text-rose-400" />
            ) : (
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
            )}
            <span>Health Score:</span>
            <span className="font-bold">{health.toFixed(0)}/100</span>
          </div>

          {/* AI Goal Decomposer Trigger */}
          <button
            onClick={onOpenGoalDecomposer}
            className="flex items-center gap-1.5 rounded-lg border border-indigo-500/30 bg-gradient-to-r from-indigo-600/80 to-purple-600/80 px-3.5 py-1.5 text-xs font-semibold text-white shadow-md shadow-indigo-600/20 transition hover:from-indigo-500 hover:to-purple-500 hover:scale-[1.02] active:scale-[0.98]"
          >
            <Sparkles className="h-3.5 w-3.5 text-indigo-200" />
            AI Goal Assistant
          </button>

          {/* Refresh Button */}
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="rounded-lg border border-slate-700/80 bg-slate-800/80 p-2 text-slate-300 transition hover:bg-slate-700 hover:text-white disabled:opacity-50"
            title="Refresh Project State"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin text-indigo-400' : ''}`} />
          </button>
        </div>
      </div>
    </header>
  );
};
