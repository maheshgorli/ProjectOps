/**
 * ProjectOps API Client
 * Type-safe fetch wrappers for backend /api/v1 endpoints.
 */

import type {
  AgentLoopStatus,
  AIInfo,
  DecisionRecord,
  GoalDecompositionResponse,
  LoopStepResponse,
  Member,
  ProgressHistoryEvent,
  Project,
  ProjectPlan,
  ReplanCandidate,
  ReplanProposal,
  RiskAnalysis,
  ScheduleResult,
  TaskMerged,
  TaskStatusUpdateRequest,
} from '../types/api';

const BASE_URL = '/api/v1';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = res.statusText;
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || errJson.message || errorDetail;
    } catch {
      // ignore json parse error
    }
    throw new Error(errorDetail || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  // Projects
  async listProjects(): Promise<Project[]> {
    const res = await fetch(`${BASE_URL}/projects`);
    return handleResponse<Project[]>(res);
  },

  async getProject(projectId: string): Promise<Project> {
    const res = await fetch(`${BASE_URL}/projects/${projectId}`);
    return handleResponse<Project>(res);
  },

  async createProject(name: string, description: string = ''): Promise<Project> {
    const res = await fetch(`${BASE_URL}/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, description }),
    });
    return handleResponse<Project>(res);
  },

  async listMembers(projectId: string): Promise<Member[]> {
    const res = await fetch(`${BASE_URL}/projects/${projectId}/members`);
    return handleResponse<Member[]>(res);
  },

  async createMember(
    projectId: string,
    name: string,
    role: string,
    daily_capacity_hours: number = 8.0,
  ): Promise<Member> {
    const res = await fetch(`${BASE_URL}/projects/${projectId}/members`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, role, daily_capacity_hours }),
    });
    return handleResponse<Member>(res);
  },

  // Plans
  async getActivePlan(projectId: string): Promise<ProjectPlan | null> {
    const res = await fetch(`${BASE_URL}/projects/${projectId}/plans/active`);
    if (res.status === 404) return null;
    return handleResponse<ProjectPlan>(res);
  },

  async getPlanByVersion(projectId: string, version: number): Promise<ProjectPlan> {
    const res = await fetch(`${BASE_URL}/projects/${projectId}/plans/${version}`);
    return handleResponse<ProjectPlan>(res);
  },

  async listPlanVersions(projectId: string): Promise<{ versions: number[]; active_version: number | null }> {
    const res = await fetch(`${BASE_URL}/projects/${projectId}/plans`);
    return handleResponse<{ versions: number[]; active_version: number | null }>(res);
  },

  async createPlan(projectId: string, planData: unknown): Promise<ProjectPlan> {
    const res = await fetch(`${BASE_URL}/projects/${projectId}/plans`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(planData),
    });
    return handleResponse<ProjectPlan>(res);
  },

  // Task Execution States
  async getTasks(projectId: string): Promise<TaskMerged[]> {
    const res = await fetch(`${BASE_URL}/projects/${projectId}/tasks`);
    return handleResponse<TaskMerged[]>(res);
  },

  async getTask(projectId: string, taskId: string): Promise<TaskMerged> {
    const res = await fetch(`${BASE_URL}/projects/${projectId}/tasks/${taskId}`);
    return handleResponse<TaskMerged>(res);
  },

  async updateTaskStatus(
    projectId: string,
    taskId: string,
    payload: TaskStatusUpdateRequest,
  ): Promise<TaskMerged> {
    const res = await fetch(`${BASE_URL}/projects/${projectId}/tasks/${taskId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<TaskMerged>(res);
  },

  // Scheduling
  async getSchedule(projectId: string, version?: number): Promise<ScheduleResult> {
    const url = version
      ? `${BASE_URL}/projects/${projectId}/schedule?version=${version}`
      : `${BASE_URL}/projects/${projectId}/schedule`;
    const res = await fetch(url);
    return handleResponse<ScheduleResult>(res);
  },

  // Risks & Replanning
  async analyzeRisks(projectId: string, version?: number): Promise<RiskAnalysis> {
    const url = version
      ? `${BASE_URL}/projects/${projectId}/risks/analyze?version=${version}`
      : `${BASE_URL}/projects/${projectId}/risks/analyze`;
    const res = await fetch(url);
    return handleResponse<RiskAnalysis>(res);
  },

  async proposeReplan(projectId: string): Promise<ReplanCandidate> {
    const res = await fetch(`${BASE_URL}/projects/${projectId}/replan/propose`, {
      method: 'POST',
    });
    return handleResponse<ReplanCandidate>(res);
  },

  // Human Approval Gateway (Server-Side Proposals - Core Principle 4 & P0-1 fix)
  async listProposals(projectId: string, status?: string): Promise<ReplanProposal[]> {
    const url = status
      ? `${BASE_URL}/projects/${projectId}/replan/proposals?status=${status}`
      : `${BASE_URL}/projects/${projectId}/replan/proposals`;
    const res = await fetch(url);
    return handleResponse<ReplanProposal[]>(res);
  },

  async getProposal(projectId: string, proposalId: string): Promise<ReplanProposal> {
    const res = await fetch(`${BASE_URL}/projects/${projectId}/replan/proposals/${proposalId}`);
    return handleResponse<ReplanProposal>(res);
  },

  async approveReplan(
    projectId: string,
    proposalId: string,
    decisionRationale: string,
    decidedBy: string,
  ): Promise<{ status: string; proposal_id: string; previous_version: number; new_version: number; summary: string; plan: ProjectPlan }> {
    const res = await fetch(`${BASE_URL}/projects/${projectId}/replan/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        proposal_id: proposalId,
        decision_rationale: decisionRationale,
        decided_by: decidedBy,
      }),
    });
    return handleResponse(res);
  },

  async rejectReplan(
    projectId: string,
    proposalId: string,
    rationale: string,
    decidedBy: string,
  ): Promise<{ status: string; proposal_id: string; current_version: number }> {
    const res = await fetch(`${BASE_URL}/projects/${projectId}/replan/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        proposal_id: proposalId,
        rationale,
        decided_by: decidedBy,
      }),
    });
    return handleResponse(res);
  },

  // Autonomous Multi-Agent Loop
  async runAgentLoopStep(projectId: string, triggeredBy: string = 'manual'): Promise<LoopStepResponse> {
    const res = await fetch(`${BASE_URL}/projects/${projectId}/agent-loop/step?triggered_by=${triggeredBy}`, {
      method: 'POST',
    });
    return handleResponse<LoopStepResponse>(res);
  },

  async getAgentLoopStatus(projectId: string): Promise<AgentLoopStatus> {
    const res = await fetch(`${BASE_URL}/projects/${projectId}/agent-loop/status`);
    return handleResponse<AgentLoopStatus>(res);
  },

  // AI Assistant
  async getAiInfo(): Promise<AIInfo> {
    const res = await fetch(`${BASE_URL}/ai/info`);
    return handleResponse<AIInfo>(res);
  },

  async decomposeGoal(
    projectId: string,
    goal: string,
    availableRoles: string[] = ['lead', 'engineer', 'qa', 'devops'],
  ): Promise<GoalDecompositionResponse> {
    const res = await fetch(`${BASE_URL}/ai/decompose-goal`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        goal,
        context: `Project ID: ${projectId}. Available roles: ${availableRoles.join(', ')}`,
      }),
    });
    interface RawBackendResponse {
      goal?: string;
      tasks?: Array<{
        id: string;
        title: string;
        description?: string;
        estimated_hours?: number;
        suggested_assignee_role?: string;
        predecessor_ids?: string[];
      }>;
      dependencies?: Array<{
        predecessor_id: string;
        successor_id: string;
      }>;
      estimated_total_hours?: number;
      explanation?: string;
    }
    const data = await handleResponse<RawBackendResponse>(res);
    const depsBySuccessor: Record<string, string[]> = {};
    if (data.dependencies) {
      for (const d of data.dependencies) {
        if (!depsBySuccessor[d.successor_id]) {
          depsBySuccessor[d.successor_id] = [];
        }
        depsBySuccessor[d.successor_id].push(d.predecessor_id);
      }
    }
    const tasks = (data.tasks || []).map((t) => ({
      id: t.id,
      title: t.title,
      description: t.description || '',
      estimated_hours: t.estimated_hours || 8,
      suggested_assignee_role: t.suggested_assignee_role || 'engineer',
      predecessor_ids: t.predecessor_ids || depsBySuccessor[t.id] || [],
    }));
    return {
      goal: data.goal || goal,
      tasks,
      explanation:
        data.explanation ||
        `Decomposed into ${tasks.length} tasks and ${(data.dependencies || []).length} dependencies (Total ~${data.estimated_total_hours || 0} hrs).`,
    };
  },

  // History & Evidence Streams
  async getProgressHistory(projectId: string): Promise<ProgressHistoryEvent[]> {
    const res = await fetch(`${BASE_URL}/projects/${projectId}/history/progress`);
    return handleResponse<ProgressHistoryEvent[]>(res);
  },

  async getDecisions(projectId: string): Promise<DecisionRecord[]> {
    const res = await fetch(`${BASE_URL}/projects/${projectId}/decisions`);
    return handleResponse<DecisionRecord[]>(res);
  },
};
