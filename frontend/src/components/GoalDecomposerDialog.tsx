import { useEffect, useState } from 'react';
import {
  Sparkles,
  X,
  CheckCircle,
  Clock,
  Layers,
} from 'lucide-react';
import { api } from '../services/api';
import type { AIInfo, DecomposedTask } from '../types/api';

interface GoalDecomposerDialogProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  onPlanCreated: () => void;
}

export const GoalDecomposerDialog: React.FC<GoalDecomposerDialogProps> = ({
  isOpen,
  onClose,
  projectId,
  onPlanCreated,
}) => {
  const [goal, setGoal] = useState(
    'Build authentication API with JWT tokens, OAuth integration, and rate limiting.',
  );
  const [isDecomposing, setIsDecomposing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [decomposedTasks, setDecomposedTasks] = useState<DecomposedTask[]>([]);
  const [explanation, setExplanation] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [aiInfo, setAiInfo] = useState<AIInfo | null>(null);

  useEffect(() => {
    if (isOpen) {
      api.getAiInfo().then(setAiInfo).catch(() => {});
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleDecompose = async () => {
    if (!goal.trim()) return;
    setIsDecomposing(true);
    setError(null);
    try {
      const res = await api.decomposeGoal(projectId, goal);
      setDecomposedTasks(res.tasks);
      setExplanation(res.explanation);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Decomposition failed');
    } finally {
      setIsDecomposing(false);
    }
  };

  const handleCreatePlanFromTasks = async () => {
    if (decomposedTasks.length === 0) return;
    setIsSaving(true);
    setError(null);
    try {
      // Build tasks payload
      const tasks = decomposedTasks.map((t) => ({
        id: t.id,
        title: t.title,
        description: t.description,
        estimated_hours: t.estimated_hours,
        status: 'TODO',
      }));

      // Build dependencies payload
      const dependencies: { predecessor_id: string; successor_id: string; dep_type: string }[] = [];
      decomposedTasks.forEach((t) => {
        t.predecessor_ids.forEach((predId) => {
          dependencies.push({
            predecessor_id: predId,
            successor_id: t.id,
            dep_type: 'FINISH_TO_START',
          });
        });
      });

      // Get latest version
      const verRes = await api.listPlanVersions(projectId);
      const nextVersion = (verRes.active_version || 0) + 1;

      await api.createPlan(projectId, {
        version: nextVersion,
        name: `AI Goal Plan v${nextVersion}`,
        created_by: 'AI Goal Assistant',
        tasks,
        dependencies,
      });

      onPlanCreated();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create plan');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-md">
      <div className="glass-panel relative flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-indigo-500/40 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 bg-indigo-950/30 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-display text-base font-bold text-white">
                  AI Goal Decomposer Assistant
                </h2>
                {aiInfo && (
                  <span
                    className={`inline-flex items-center rounded-md px-2 py-0.5 text-[10px] font-medium border ${
                      aiInfo.is_mock
                        ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                        : 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                    }`}
                  >
                    {aiInfo.is_mock ? 'Mock AI' : `Claude (${aiInfo.model})`}
                  </span>
                )}
              </div>
              <p className="text-xs text-indigo-300/80">
                Rule 2: Decomposes natural language goals into DAG tasks validated by domain engine
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

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* Goal Input Field */}
          <div>
            <label className="text-xs font-semibold text-slate-300">
              Project Goal / Objective:
            </label>
            <textarea
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              rows={3}
              placeholder="Describe what you want to achieve..."
              className="mt-1.5 w-full rounded-xl border border-slate-700 bg-slate-900 p-3.5 text-xs text-slate-100 placeholder-slate-500 outline-none transition focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
            <div className="mt-2 flex justify-end">
              <button
                onClick={handleDecompose}
                disabled={isDecomposing || !goal.trim()}
                className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-indigo-600/30 transition hover:bg-indigo-500 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50"
              >
                <Sparkles className={`h-3.5 w-3.5 ${isDecomposing ? 'animate-spin' : ''}`} />
                {isDecomposing ? 'Decomposing Goal...' : 'Decompose into Tasks'}
              </button>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="rounded-lg border border-rose-500/30 bg-rose-950/40 p-3 text-xs text-rose-300">
              {error}
            </div>
          )}

          {/* Results Preview */}
          {decomposedTasks.length > 0 && (
            <div className="space-y-4">
              {explanation && (
                <div className="rounded-xl border border-indigo-500/20 bg-indigo-950/30 p-3.5 text-xs text-indigo-200 leading-relaxed">
                  <span className="font-semibold text-white">Strategy Rationale: </span>
                  {explanation}
                </div>
              )}

              <div>
                <div className="flex items-center justify-between pb-2">
                  <span className="font-display text-xs font-bold text-slate-200">
                    Generated Task DAG ({decomposedTasks.length} tasks)
                  </span>
                  <span className="text-[11px] text-slate-400">Validated against cyclic dependencies</span>
                </div>

                <div className="space-y-2">
                  {decomposedTasks.map((t) => (
                    <div
                      key={t.id}
                      className="rounded-xl border border-slate-800 bg-slate-900/70 p-3 text-xs space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-code font-bold text-indigo-400">{t.id}</span>
                          <span className="font-semibold text-slate-200">{t.title}</span>
                        </div>
                        <div className="flex items-center gap-2 text-slate-400 text-[11px]">
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {t.estimated_hours}h
                          </span>
                          <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-300">
                            {t.suggested_assignee_role}
                          </span>
                        </div>
                      </div>

                      <p className="text-[11px] text-slate-400">{t.description}</p>

                      {t.predecessor_ids.length > 0 && (
                        <div className="flex items-center gap-1.5 text-[10px] text-slate-500 pt-1">
                          <Layers className="h-3 w-3" />
                          <span>Predecessors:</span>
                          <span className="font-code text-slate-400">
                            {t.predecessor_ids.join(', ')}
                          </span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-slate-800 bg-slate-900/60 px-6 py-4">
          <button
            onClick={onClose}
            className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-700 hover:text-white"
          >
            Cancel
          </button>

          <button
            onClick={handleCreatePlanFromTasks}
            disabled={isSaving || decomposedTasks.length === 0}
            className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-bold text-white shadow-md shadow-emerald-600/30 transition hover:bg-emerald-500 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50"
          >
            <CheckCircle className="h-4 w-4" />
            {isSaving ? 'Saving Immutable Plan...' : 'Activate as New Plan Version'}
          </button>
        </div>
      </div>
    </div>
  );
};
