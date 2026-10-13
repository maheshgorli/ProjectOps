/**
 * ProjectOps API Client
 * Type-safe fetch wrappers for backend /api/v1 endpoints with JWT authentication.
 */

import type {
  AgentLoopStatus,
  AIInfo,
  AuthTokenResponse,
  AuthUser,
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

/**
 * Token Storage Security Trade-off:
 * The JWT access token is stored in memory with a sessionStorage fallback to preserve
 * sessions across page refreshes within the same browser tab (NOT localStorage).
 * Trade-off: While sessionStorage isolates the token to the tab, it is still vulnerable
 * to XSS if an attacker executes arbitrary JavaScript in the origin.
 * Production hardening: Move to HttpOnly, SameSite cookies with server-side CSRF protection.
 */
let inMemoryToken: string | null = sessionStorage.getItem('projectops_token');

export function setAuthToken(token: string | null): void {
  inMemoryToken = token;
  if (token) {
    sessionStorage.setItem('projectops_token', token);
  } else {
    sessionStorage.removeItem('projectops_token');
  }
}

export function getAuthToken(): string | null {
  return inMemoryToken;
}

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

async function authFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (inMemoryToken) {
    headers.set('Authorization', `Bearer ${inMemoryToken}`);
  }
  if (!headers.has('Content-Type') && options.body && typeof options.body === 'string') {
    headers.set('Content-Type', 'application/json');
  }

  const res = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (res.status === 401 && !endpoint.startsWith('/auth/login')) {
    setAuthToken(null);
    localStorage.removeItem('projectops_user');
    window.dispatchEvent(new CustomEvent('projectops:unauthorized'));
  }

  return handleResponse<T>(res);
}

export const api = {
  // Authentication
  async register(
    email: string,
    displayName: string,
    password: string,
  ): Promise<AuthUser> {
    return authFetch<AuthUser>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        email: email.trim().toLowerCase(),
        display_name: displayName.trim(),
        password,
      }),
    });
  },

  async login(email: string, password: string): Promise<AuthTokenResponse> {
    const data = await authFetch<AuthTokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        email: email.trim().toLowerCase(),
        password,
      }),
    });
    setAuthToken(data.access_token);
    return data;
  },

  async getMe(): Promise<AuthUser> {
    return authFetch<AuthUser>('/auth/me');
  },

  // Projects
  async listProjects(): Promise<Project[]> {
    return authFetch<Project[]>('/projects');
  },

  async getProject(projectId: string): Promise<Project> {
    return authFetch<Project>(`/projects/${projectId}`);
  },

  async createProject(name: string, description: string = ''): Promise<Project> {
    return authFetch<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify({ name, description }),
    });
  },

  async listMembers(projectId: string): Promise<Member[]> {
    return authFetch<Member[]>(`/projects/${projectId}/members`);
  },

  async createMember(
    projectId: string,
    name: string,
    role: string,
    daily_capacity_hours: number = 8.0,
  ): Promise<Member> {
    return authFetch<Member>(`/projects/${projectId}/members`, {
      method: 'POST',
      body: JSON.stringify({ name, role, daily_capacity_hours }),
    });
  },

  // Plans
  async getActivePlan(projectId: string): Promise<ProjectPlan | null> {
    try {
      return await authFetch<ProjectPlan>(`/projects/${projectId}/plans/active`);
    } catch (err: unknown) {
      if (err instanceof Error && err.message.includes('404')) {
        return null;
      }
      throw err;
    }
  },

  async getPlanByVersion(projectId: string, version: number): Promise<ProjectPlan> {
    return authFetch<ProjectPlan>(`/projects/${projectId}/plans/${version}`);
  },

  async listPlanVersions(
    projectId: string,
  ): Promise<{ versions: number[]; active_version: number | null }> {
    return authFetch<{ versions: number[]; active_version: number | null }>(
      `/projects/${projectId}/plans/versions`,
    );
  },

  async createPlan(projectId: string, planData: unknown): Promise<ProjectPlan> {
    return authFetch<ProjectPlan>(`/projects/${projectId}/plans`, {
      method: 'POST',
      body: JSON.stringify(planData),
    });
  },

  async activatePlan(
    projectId: string,
    version: number,
    rationale: string,
  ): Promise<ProjectPlan> {
    return authFetch<ProjectPlan>(`/projects/${projectId}/plans/${version}/activate`, {
      method: 'POST',
      body: JSON.stringify({ rationale }),
    });
  },

  // Task Execution States
  async getTasks(projectId: string): Promise<TaskMerged[]> {
    return authFetch<TaskMerged[]>(`/projects/${projectId}/tasks`);
  },

  async getTask(projectId: string, taskId: string): Promise<TaskMerged> {
    return authFetch<TaskMerged>(`/projects/${projectId}/tasks/${taskId}`);
  },

  async updateTaskStatus(
    projectId: string,
    taskId: string,
    payload: TaskStatusUpdateRequest,
  ): Promise<TaskMerged> {
    return authFetch<TaskMerged>(`/projects/${projectId}/tasks/${taskId}/status`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  // Scheduling
  async getSchedule(projectId: string, version?: number): Promise<ScheduleResult> {
    const url = version
      ? `/projects/${projectId}/schedule?version=${version}`
      : `/projects/${projectId}/schedule`;
    return authFetch<ScheduleResult>(url);
  },

  // Risks & Replanning
  async analyzeRisks(projectId: string, version?: number): Promise<RiskAnalysis> {
    const url = version
      ? `/projects/${projectId}/risks/analyze?version=${version}`
      : `/projects/${projectId}/risks/analyze`;
    return authFetch<RiskAnalysis>(url);
  },

  async proposeReplan(projectId: string): Promise<ReplanCandidate> {
    return authFetch<ReplanCandidate>(`/projects/${projectId}/replan/propose`, {
      method: 'POST',
    });
  },

  // Human Approval Gateway (Server-Side Proposals)
  async listProposals(projectId: string, status?: string): Promise<ReplanProposal[]> {
    const url = status
      ? `/projects/${projectId}/replan/proposals?status=${status}`
      : `/projects/${projectId}/replan/proposals`;
    return authFetch<ReplanProposal[]>(url);
  },

  async getProposal(projectId: string, proposalId: string): Promise<ReplanProposal> {
    return authFetch<ReplanProposal>(`/projects/${projectId}/replan/proposals/${proposalId}`);
  },

  async approveReplan(
    projectId: string,
    proposalId: string,
    decisionRationale: string,
  ): Promise<{
    status: string;
    proposal_id: string;
    previous_version: number;
    new_version: number;
    summary: string;
    plan: ProjectPlan;
  }> {
    return authFetch(`/projects/${projectId}/replan/approve`, {
      method: 'POST',
      body: JSON.stringify({
        proposal_id: proposalId,
        decision_rationale: decisionRationale,
      }),
    });
  },

  async rejectReplan(
    projectId: string,
    proposalId: string,
    rationale: string,
  ): Promise<{ status: string; proposal_id: string; current_version: number }> {
    return authFetch(`/projects/${projectId}/replan/reject`, {
      method: 'POST',
      body: JSON.stringify({
        proposal_id: proposalId,
        rationale,
      }),
    });
  },

  // Autonomous Multi-Agent Loop
  async runAgentLoopStep(projectId: string): Promise<LoopStepResponse> {
    return authFetch<LoopStepResponse>(`/projects/${projectId}/agent-loop/step`, {
      method: 'POST',
    });
  },

  async getAgentLoopStatus(projectId: string): Promise<AgentLoopStatus> {
    return authFetch<AgentLoopStatus>(`/projects/${projectId}/agent-loop/status`);
  },

  // AI Assistant
  async getAiInfo(): Promise<AIInfo> {
    return authFetch<AIInfo>('/ai/info');
  },

  async decomposeGoal(
    projectId: string,
    goal: string,
    availableRoles: string[] = ['lead', 'engineer', 'qa', 'devops'],
  ): Promise<GoalDecompositionResponse> {
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

    const data = await authFetch<RawBackendResponse>(
      `/projects/${projectId}/ai/decompose-goal`,
      {
        method: 'POST',
        body: JSON.stringify({
          goal,
          context: `Project ID: ${projectId}. Available roles: ${availableRoles.join(', ')}`,
        }),
      },
    );

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
    return authFetch<ProgressHistoryEvent[]>(`/projects/${projectId}/history/progress`);
  },

  async getDecisions(projectId: string): Promise<DecisionRecord[]> {
    return authFetch<DecisionRecord[]>(`/projects/${projectId}/decisions`);
  },
};
