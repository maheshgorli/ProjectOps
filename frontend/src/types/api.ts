/**
 * ProjectOps API TypeScript Definitions
 * Synchronized with backend OpenAPI schemas.
 */

export type TaskStatus = 'TODO' | 'IN_PROGRESS' | 'BLOCKED' | 'COMPLETED';

export type DependencyType =
  | 'FINISH_TO_START'
  | 'START_TO_START'
  | 'FINISH_TO_FINISH'
  | 'START_TO_FINISH';

export interface Project {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface Member {
  id: string;
  project_id: string;
  name: string;
  role: string;
  daily_capacity_hours: number;
}

export interface Task {
  id: string;
  title: string;
  description: string;
  status: TaskStatus;
  estimated_hours: number;
  assigned_to_id: string | null;
  due_date: string | null;
  start_date: string | null;
  completed_at: string | null;
  is_overdue: boolean;
}

export interface Dependency {
  predecessor_id: string;
  successor_id: string;
  dep_type: DependencyType;
  lag_days: number;
}

export interface ProjectPlan {
  id: string;
  project_id: string;
  version: number;
  name: string;
  target_completion_date: string | null;
  created_at: string;
  created_by: string;
  tasks: Task[];
  dependencies: Dependency[];
}

export interface ScheduledTask {
  task_id: string;
  early_start: string;
  early_finish: string;
  late_start: string;
  late_finish: string;
  duration_days: number;
  total_float: number;
  is_critical: boolean;
  is_overdue: boolean;
}

export interface MemberWorkload {
  member_id: string;
  capacity_hours_per_day: number;
  total_assigned_hours: number;
  daily_allocated_hours: Record<string, number>;
  peak_daily_hours: number;
  is_overallocated: boolean;
  overallocated_dates: string[];
}

export interface ScheduleResult {
  project_id: string;
  plan_version: number;
  project_start_date: string;
  project_finish_date: string;
  target_completion_date: string | null;
  is_feasible: boolean;
  critical_path: string[];
  tasks: Record<string, ScheduledTask>;
  member_workloads: Record<string, MemberWorkload>;
}

export interface DetectedRisk {
  risk_type: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  description: string;
  affected_task_ids: string[];
  metrics: Record<string, unknown>;
}

export interface RiskAnalysis {
  project_id: string;
  plan_version: number;
  health_score: number;
  is_at_risk: boolean;
  summary: string;
  risks: DetectedRisk[];
}

export interface ReplanCandidate {
  project_id: string;
  baseline_version: number;
  proposed_version: number;
  baseline_finish_date: string;
  proposed_finish_date: string;
  finish_date_delta_days: number;
  resolved_risks_count: number;
  mitigation_notes: string[];
  proposed_plan: ProjectPlan;
}

export interface DecisionRecord {
  id: string;
  project_id: string;
  plan_id: string | null;
  decision_type: string;
  summary: string;
  rationale: string;
  decided_by: string;
  recorded_at: string;
}

export interface ProgressHistoryEvent {
  id: string;
  project_id: string;
  task_id: string;
  previous_status: string | null;
  new_status: string;
  evidence_notes: string;
  recorded_by: string;
  recorded_at: string;
}

export interface AgentRun {
  id: string;
  project_id: string;
  loop_stage: 'PLAN' | 'EXECUTE' | 'OBSERVE' | 'REASON' | 'REPLAN' | 'APPROVE';
  status: 'SUCCESS' | 'RUNNING' | 'AWAITING_APPROVAL' | 'FAILED' | 'REJECTED' | 'HEALTHY';
  summary: string;
  details_json: string | null;
  triggered_by: string;
  recorded_at: string;
}

export interface AgentLoopStatus {
  project_id: string;
  active_plan_version: number | null;
  current_status: string;
  requires_human_approval: boolean;
  recent_runs: AgentRun[];
}

export interface LoopStepResponse {
  project_id: string;
  current_stage: string;
  status: string;
  health_score: number;
  is_at_risk: boolean;
  summary: string;
  detected_risks_count: number;
  actionable_tasks: string[];
  replan_candidate: ReplanCandidate | null;
  requires_human_approval: boolean;
}

export interface DecomposedTask {
  id: string;
  title: string;
  description: string;
  estimated_hours: number;
  suggested_assignee_role: string;
  predecessor_ids: string[];
}

export interface GoalDecompositionResponse {
  goal: string;
  tasks: DecomposedTask[];
  explanation: string;
}

export interface AIInfo {
  provider: string;
  model: string;
  is_mock: boolean;
}

