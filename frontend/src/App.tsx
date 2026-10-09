import { useState, useEffect, useCallback } from 'react';
import {
  GitFork,
  Users,
  AlertTriangle,
  RefreshCw,
  Flame,
  ShieldCheck,
  CheckCircle2,
  Layers,
  Sparkles,
} from 'lucide-react';

import { api } from './services/api';
import type {
  Project,
  Member,
  ProjectPlan,
  ScheduleResult,
  RiskAnalysis,
  AgentLoopStatus,
  LoopStepResponse,
  ReplanCandidate,
  ProgressHistoryEvent,
  DecisionRecord,
  AgentRun,
} from './types/api';

import { Header } from './components/Header';
import { AgentLoopBanner } from './components/AgentLoopBanner';
import { DependencyGraph } from './components/DependencyGraph';
import { WorkloadChart } from './components/WorkloadChart';
import { AuditTrailStream } from './components/AuditTrailStream';
import { ReplanApprovalModal } from './components/ReplanApprovalModal';
import { GoalDecomposerDialog } from './components/GoalDecomposerDialog';
import { VersionHistoryDrawer } from './components/VersionHistoryDrawer';

export function App() {
  // Core Entities State
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [activePlan, setActivePlan] = useState<ProjectPlan | null>(null);
  const [versionsList, setVersionsList] = useState<number[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [schedule, setSchedule] = useState<ScheduleResult | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [riskAnalysis, setRiskAnalysis] = useState<RiskAnalysis | null>(null);

  // Autonomous Agent Loop State
  const [loopStatus, setLoopStatus] = useState<AgentLoopStatus | null>(null);
  const [lastStepResult, setLastStepResult] = useState<LoopStepResponse | null>(null);
  const [replanCandidate, setReplanCandidate] = useState<ReplanCandidate | null>(null);

  // Audit Trail State
  const [progressHistory, setProgressHistory] = useState<ProgressHistoryEvent[]>([]);
  const [decisions, setDecisions] = useState<DecisionRecord[]>([]);
  const [agentRuns, setAgentRuns] = useState<AgentRun[]>([]);

  // Navigation & Modal UI State
  const [activeTab, setActiveTab] = useState<'dag' | 'workload' | 'risks'>('dag');
  const [isGoalDecomposerOpen, setIsGoalDecomposerOpen] = useState(false);
  const [isVersionHistoryOpen, setIsVersionHistoryOpen] = useState(false);
  const [isApprovalModalOpen, setIsApprovalModalOpen] = useState(false);

  // Status & Loading Flags
  const [isLoading, setIsLoading] = useState(true);
  const [isRunningStep, setIsRunningStep] = useState(false);
  const [isSubmittingApproval, setIsSubmittingApproval] = useState(false);
  const [toastMessage, setToastMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showToast = (text: string, type: 'success' | 'error' | 'info' = 'info') => {
    setToastMessage({ text, type });
    setTimeout(() => setToastMessage(null), 5000);
  };

  // 1. Fetch Project Details
  const loadProjectDetails = useCallback(async (project: Project, targetVersion?: number) => {
    setIsLoading(true);
    try {
      // Parallel loading of primary resources
      const [membersData, versionsData, loopStatusData, historyData, decisionsData] = await Promise.all([
        api.listMembers(project.id).catch(() => []),
        api.listPlanVersions(project.id).catch(() => ({ versions: [], active_version: null })),
        api.getAgentLoopStatus(project.id).catch(() => null),
        api.getProgressHistory(project.id).catch(() => []),
        api.getDecisions(project.id).catch(() => []),
      ]);

      setMembers(membersData);
      setVersionsList(versionsData.versions || []);
      setLoopStatus(loopStatusData);
      setProgressHistory(historyData);
      setDecisions(decisionsData);
      if (loopStatusData?.recent_runs) {
        setAgentRuns(loopStatusData.recent_runs);
      }

      const verToLoad = targetVersion || versionsData.active_version || undefined;
      setSelectedVersion(verToLoad ?? null);

      if (verToLoad) {
        const [planData, scheduleData, riskData] = await Promise.all([
          api.getPlanByVersion(project.id, verToLoad).catch(() => null),
          api.getSchedule(project.id, verToLoad).catch(() => null),
          api.analyzeRisks(project.id, verToLoad).catch(() => null),
        ]);
        setActivePlan(planData);
        setSchedule(scheduleData);
        setRiskAnalysis(riskData);
      } else {
        const activePlanData = await api.getActivePlan(project.id).catch(() => null);
        setActivePlan(activePlanData);
        if (activePlanData) {
          const [sched, risks] = await Promise.all([
            api.getSchedule(project.id, activePlanData.version).catch(() => null),
            api.analyzeRisks(project.id, activePlanData.version).catch(() => null),
          ]);
          setSchedule(sched);
          setRiskAnalysis(risks);
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load project details';
      showToast(msg, 'error');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 2. Fetch Projects on Mount
  const loadProjects = useCallback(async () => {
    try {
      setIsLoading(true);
      const projList = await api.listProjects();
      setProjects(projList);

      if (projList.length > 0) {
        const current = selectedProject
          ? projList.find((p) => p.id === selectedProject.id) || projList[0]
          : projList[0];
        setSelectedProject(current);
        await loadProjectDetails(current);
      } else {
        setSelectedProject(null);
        setActivePlan(null);
        setIsLoading(false);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load projects';
      showToast(msg, 'error');
      setIsLoading(false);
    }
  }, [selectedProject, loadProjectDetails]);

  useEffect(() => {
    loadProjects();
  }, []);

  // Switch project handler
  const handleSelectProject = (project: Project) => {
    setSelectedProject(project);
    loadProjectDetails(project);
  };

  // Select historical plan version
  const handleSelectVersion = (version: number) => {
    if (!selectedProject) return;
    loadProjectDetails(selectedProject, version);
  };

  // Run Next Stage in Autonomous Multi-Agent Loop
  const handleRunLoopStep = async () => {
    if (!selectedProject) return;
    setIsRunningStep(true);
    try {
      const result = await api.runAgentLoopStep(selectedProject.id, 'manual_operator');
      setLastStepResult(result);

      if (result.replan_candidate) {
        setReplanCandidate(result.replan_candidate);
      }

      if (result.requires_human_approval && result.replan_candidate) {
        setIsApprovalModalOpen(true);
        showToast('Autonomous replan proposed! Human approval required before activating.', 'info');
      } else {
        showToast(`Loop stage '${result.current_stage}' completed: ${result.summary}`, 'success');
      }

      // Reload project state to reflect updated data
      await loadProjectDetails(selectedProject);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error executing agent loop stage';
      showToast(msg, 'error');
    } finally {
      setIsRunningStep(false);
    }
  };

  // Manual Trigger: Propose Replan Candidate
  const handleProposeReplan = async () => {
    if (!selectedProject) return;
    setIsLoading(true);
    try {
      const candidate = await api.proposeReplan(selectedProject.id);
      setReplanCandidate(candidate);
      setIsApprovalModalOpen(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to generate replan proposal';
      showToast(msg, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  // Human Approval Action (Server Proposal ID - Core Principle 4 & P0-1 fix)
  const handleApproveReplan = async (rationale: string, decidedBy: string) => {
    if (!selectedProject || !replanCandidate) return;
    if (!replanCandidate.proposal_id) {
      showToast('Missing server proposal ID. Please re-propose replan.', 'error');
      return;
    }
    setIsSubmittingApproval(true);
    try {
      const result = await api.approveReplan(
        selectedProject.id,
        replanCandidate.proposal_id,
        rationale,
        decidedBy,
      );
      showToast(`Plan v${result.new_version} approved & activated successfully!`, 'success');
      setIsApprovalModalOpen(false);
      setReplanCandidate(null);
      await loadProjectDetails(selectedProject, result.new_version);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to approve replan';
      showToast(msg, 'error');
    } finally {
      setIsSubmittingApproval(false);
    }
  };

  // Human Rejection Action
  const handleRejectReplan = async (rationale: string, decidedBy: string) => {
    if (!selectedProject || !replanCandidate) return;
    if (!replanCandidate.proposal_id) {
      showToast('Missing server proposal ID. Please re-propose replan.', 'error');
      return;
    }
    setIsSubmittingApproval(true);
    try {
      await api.rejectReplan(selectedProject.id, replanCandidate.proposal_id, rationale, decidedBy);
      showToast('Replan proposal rejected. Current baseline remains active.', 'info');
      setIsApprovalModalOpen(false);
      setReplanCandidate(null);
      await loadProjectDetails(selectedProject);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to reject replan';
      showToast(msg, 'error');
    } finally {
      setIsSubmittingApproval(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500/30">
      {/* Toast Notification Banner */}
      {toastMessage && (
        <div
          className={`fixed bottom-6 right-6 z-50 flex items-center gap-2.5 rounded-xl px-4 py-3 text-sm shadow-2xl backdrop-blur-xl transition-all border ${
            toastMessage.type === 'success'
              ? 'border-emerald-500/40 bg-emerald-950/90 text-emerald-200'
              : toastMessage.type === 'error'
              ? 'border-rose-500/40 bg-rose-950/90 text-rose-200'
              : 'border-indigo-500/40 bg-slate-900/90 text-slate-200'
          }`}
        >
          {toastMessage.type === 'success' && <CheckCircle2 className="h-4 w-4 text-emerald-400" />}
          {toastMessage.type === 'error' && <AlertTriangle className="h-4 w-4 text-rose-400" />}
          {toastMessage.type === 'info' && <ShieldCheck className="h-4 w-4 text-indigo-400" />}
          <span>{toastMessage.text}</span>
        </div>
      )}

      {/* Top Application Header */}
      <Header
        projects={projects}
        selectedProject={selectedProject}
        onSelectProject={handleSelectProject}
        activeVersion={activePlan?.version ?? selectedVersion}
        riskAnalysis={riskAnalysis}
        onOpenGoalDecomposer={() => setIsGoalDecomposerOpen(true)}
        onRefresh={() => selectedProject && loadProjectDetails(selectedProject)}
        isLoading={isLoading}
      />

      {/* Main Container */}
      <main className="flex-1 pb-16">
        {selectedProject ? (
          <>
            {/* Autonomous Multi-Agent Loop Stepper & Gate Banner */}
            <AgentLoopBanner
              loopStatus={loopStatus}
              lastStepResult={lastStepResult}
              onRunStep={handleRunLoopStep}
              onOpenApprovalModal={() => {
                if (lastStepResult?.replan_candidate) {
                  setReplanCandidate(lastStepResult.replan_candidate);
                }
                setIsApprovalModalOpen(true);
              }}
              isRunningStep={isRunningStep}
            />

            {/* Navigation Tabs Bar */}
            <div className="mx-6 mt-6 flex flex-wrap items-center justify-between border-b border-slate-800 pb-3 gap-4">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setActiveTab('dag')}
                  className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold tracking-wide transition ${
                    activeTab === 'dag'
                      ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
                      : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
                  }`}
                >
                  <GitFork className="h-3.5 w-3.5" />
                  Dependency Graph (DAG)
                  {schedule?.critical_path && schedule.critical_path.length > 0 && (
                    <span className="flex items-center gap-1 rounded-md bg-rose-500/20 px-1.5 py-0.5 text-[10px] text-rose-300 font-mono">
                      <Flame className="h-2.5 w-2.5" />
                      {schedule.critical_path.length} CPM
                    </span>
                  )}
                </button>

                <button
                  onClick={() => setActiveTab('workload')}
                  className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold tracking-wide transition ${
                    activeTab === 'workload'
                      ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
                      : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
                  }`}
                >
                  <Users className="h-3.5 w-3.5" />
                  Workload & Capacity
                  {schedule &&
                    Object.values(schedule.member_workloads || {}).some((w) => w.is_overallocated) && (
                      <span className="rounded-md bg-amber-500/20 px-1.5 py-0.5 text-[10px] text-amber-300 font-mono">
                        Overallocated
                      </span>
                    )}
                </button>

                <button
                  onClick={() => setActiveTab('risks')}
                  className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold tracking-wide transition ${
                    activeTab === 'risks'
                      ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
                      : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
                  }`}
                >
                  <AlertTriangle className="h-3.5 w-3.5" />
                  Deterministic Risk Engine
                  {riskAnalysis && riskAnalysis.risks.length > 0 && (
                    <span
                      className={`rounded-md px-1.5 py-0.5 text-[10px] font-mono ${
                        riskAnalysis.is_at_risk
                          ? 'bg-rose-500/20 text-rose-300'
                          : 'bg-slate-800 text-slate-300'
                      }`}
                    >
                      {riskAnalysis.risks.length} Detected
                    </span>
                  )}
                </button>
              </div>

              {/* Auxiliary Tab Controls */}
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setIsVersionHistoryOpen(true)}
                  className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-xs text-slate-300 hover:border-slate-700 hover:text-white transition"
                >
                  <Layers className="h-3.5 w-3.5 text-slate-400" />
                  <span>Version History ({versionsList.length})</span>
                </button>

                {riskAnalysis?.is_at_risk && (
                  <button
                    onClick={handleProposeReplan}
                    className="flex items-center gap-1.5 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-1.5 text-xs font-semibold text-amber-300 hover:bg-amber-500/20 transition"
                  >
                    <Sparkles className="h-3.5 w-3.5" />
                    Simulate Replan
                  </button>
                )}
              </div>
            </div>

            {/* Tab Views */}
            <div className="mt-4">
              {activeTab === 'dag' && (
                <DependencyGraph
                  plan={activePlan}
                  schedule={schedule}
                  members={members}
                />
              )}

              {activeTab === 'workload' && (
                <WorkloadChart
                  schedule={schedule}
                  members={members}
                />
              )}

              {activeTab === 'risks' && (
                <div className="mx-6 rounded-2xl glass-panel p-6 border border-slate-800">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-6">
                    <div>
                      <h3 className="font-display text-base font-bold text-white flex items-center gap-2">
                        <AlertTriangle className="h-5 w-5 text-amber-400" />
                        Deterministic Risk Rule Analysis
                      </h3>
                      <p className="text-xs text-slate-400 mt-1">
                        Rule 1: Evaluated by deterministic rules engine (Zero LLM hallucinations).
                      </p>
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-2 rounded-xl bg-slate-900/90 px-3 py-1.5 border border-slate-800">
                        <span className="text-xs text-slate-400">Health Score:</span>
                        <span
                          className={`font-mono text-sm font-bold ${
                            (riskAnalysis?.health_score ?? 100) >= 80
                              ? 'text-emerald-400'
                              : (riskAnalysis?.health_score ?? 100) >= 50
                              ? 'text-amber-400'
                              : 'text-rose-400'
                          }`}
                        >
                          {riskAnalysis?.health_score ?? 100}/100
                        </span>
                      </div>

                      <button
                        onClick={handleProposeReplan}
                        className="flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 px-4 py-2 text-xs font-bold text-slate-950 shadow-lg shadow-amber-500/20 hover:brightness-110 transition"
                      >
                        <Sparkles className="h-3.5 w-3.5" />
                        Generate Mitigation Candidate
                      </button>
                    </div>
                  </div>

                  {riskAnalysis?.risks && riskAnalysis.risks.length > 0 ? (
                    <div className="space-y-3">
                      {riskAnalysis.risks.map((risk, idx) => (
                        <div
                          key={idx}
                          className={`rounded-xl border p-4 transition ${
                            risk.severity === 'CRITICAL'
                              ? 'border-rose-500/40 bg-rose-950/20'
                              : risk.severity === 'HIGH'
                              ? 'border-amber-500/40 bg-amber-950/20'
                              : 'border-slate-800 bg-slate-900/60'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2.5">
                              <span
                                className={`rounded-md px-2 py-0.5 text-[10px] font-bold font-mono uppercase tracking-wider ${
                                  risk.severity === 'CRITICAL'
                                    ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                                    : risk.severity === 'HIGH'
                                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                    : 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                                }`}
                              >
                                {risk.severity}
                              </span>
                              <span className="text-xs font-mono font-medium text-slate-400">
                                {risk.risk_type}
                              </span>
                            </div>
                            <span className="text-[11px] text-slate-400">
                              {risk.affected_task_ids.length} Affected Task(s)
                            </span>
                          </div>

                          <p className="mt-2 text-sm text-slate-200">{risk.description}</p>

                          {risk.affected_task_ids.length > 0 && (
                            <div className="mt-3 flex flex-wrap gap-1.5 pt-2 border-t border-slate-800/60">
                              <span className="text-[11px] text-slate-400 mr-1">Impacted:</span>
                              {risk.affected_task_ids.map((tid) => (
                                <span
                                  key={tid}
                                  className="rounded bg-slate-800/80 px-2 py-0.5 font-mono text-[10px] text-slate-300"
                                >
                                  {tid}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center py-12 text-center">
                      <CheckCircle2 className="h-10 w-10 text-emerald-400 mb-2" />
                      <h4 className="text-sm font-semibold text-slate-200">No Active Risks Detected</h4>
                      <p className="text-xs text-slate-400 mt-1 max-w-sm">
                        All tasks are within member capacity limits and on schedule along the critical path.
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Audit Trail & Evidence Stream (Rule 5 & Rule 6) */}
            <div className="mt-8">
              <AuditTrailStream
                progressHistory={progressHistory}
                decisions={decisions}
                agentRuns={agentRuns}
              />
            </div>
          </>
        ) : (
          /* Empty / Initial State */
          <div className="mx-auto mt-20 max-w-2xl px-6 text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 shadow-2xl">
              <Layers className="h-8 w-8" />
            </div>
            <h2 className="mt-6 font-display text-2xl font-bold tracking-tight text-white">
              Welcome to ProjectOps
            </h2>
            <p className="mt-3 text-sm text-slate-400 leading-relaxed">
              Autonomous multi-agent project execution & risk management system.
              Enforcing deterministic scheduling truth, immutable versioned plans, and strict human governance.
            </p>

            <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
              <button
                onClick={loadProjects}
                className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 px-5 py-2.5 text-sm font-bold text-white shadow-xl shadow-indigo-500/25 hover:brightness-110 transition"
              >
                <RefreshCw className="h-4 w-4" />
                Reload Projects
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Human Approval Gateway Modal (Rule 4) */}
      <ReplanApprovalModal
        isOpen={isApprovalModalOpen}
        onClose={() => setIsApprovalModalOpen(false)}
        candidate={replanCandidate}
        onApprove={handleApproveReplan}
        onReject={handleRejectReplan}
        isSubmitting={isSubmittingApproval}
      />

      {/* AI Goal Decomposer Modal (Rule 2) */}
      {selectedProject && (
        <GoalDecomposerDialog
          isOpen={isGoalDecomposerOpen}
          onClose={() => setIsGoalDecomposerOpen(false)}
          projectId={selectedProject.id}
          onPlanCreated={() => {
            setIsGoalDecomposerOpen(false);
            loadProjectDetails(selectedProject);
            showToast('New plan version synthesized and validated!', 'success');
          }}
        />
      )}

      {/* Immutable Plan Version History Drawer (Rule 5) */}
      <VersionHistoryDrawer
        isOpen={isVersionHistoryOpen}
        onClose={() => setIsVersionHistoryOpen(false)}
        versions={versionsList}
        activeVersion={activePlan?.version ?? null}
        selectedPlan={activePlan}
        onSelectVersion={handleSelectVersion}
      />
    </div>
  );
}

export default App;
