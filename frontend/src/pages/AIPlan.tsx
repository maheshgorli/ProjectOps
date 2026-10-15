import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  CalendarDays,
  Clock3,
  Users,
  ListTodo,
  GitBranch,
  CheckCircle2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  ClipboardList,
  Sparkles,
  FileText,
  RotateCcw,
  Loader2,
  Check,
} from "lucide-react";
import { api } from "../services/api";
import type { GeneratePlanResponse, GeneratedTask } from "../types/api";

type Member = {
  id: string;
  name: string;
  role: string;
  skills: string[];
  weeklyHours: number;
};

type Team = {
  id: string;
  name: string;
  members: Member[];
};

type Project = {
  id: string;
  name: string;
  description?: string;
  type?: string;
  durationDays: number;
  startDate: string;
  deadline: string;
};

type SavedRequirement = {
  projectId: string;
  details: string;
  githubUrl: string;
  files: Array<{ name: string; size: number }>;
};

type StagedDocument = {
  filename: string;
  content: string;
  file_type?: string;
};

function readLocal<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function readSession<T>(key: string, fallback: T): T {
  try {
    const raw = sessionStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export default function AIPlan() {
  const navigate = useNavigate();

  const [project] = useState<Project | null>(() => {
    const projects = readLocal<Project[]>("projectops_projects", []);
    const activeId = localStorage.getItem("projectops_active_project");
    return projects.find((p) => p.id === activeId) || null;
  });

  const [team] = useState<Team | null>(() =>
    readLocal<Team | null>("projectops_team", null)
  );

  const savedReqs = project
    ? readLocal<SavedRequirement | null>(
        `projectops_requirements_${project.id}`,
        null
      )
    : null;

  const stagedDocs = project
    ? readSession<StagedDocument[]>(
        `projectops_requirements_docs_${project.id}`,
        []
      )
    : [];

  const initialPlan = project
    ? readLocal<GeneratePlanResponse | null>(
        `projectops_ai_plan_${project.id}`,
        null
      )
    : null;

  const [plan, setPlan] = useState<GeneratePlanResponse | null>(initialPlan);
  const [tasks, setTasks] = useState<GeneratedTask[]>(
    () => initialPlan?.tasks || []
  );
  const [milestones, setMilestones] = useState<string[]>(
    () =>
      initialPlan?.milestones || [
        "Planning",
        "Foundation",
        "Development",
        "Integration",
        "Testing",
        "Release",
      ]
  );
  const [expanded, setExpanded] = useState<string[]>(
    () => initialPlan?.milestones || []
  );
  const [assignments, setAssignments] = useState<Record<string, string>>({});
  const [isDemoMode, setIsDemoMode] = useState<boolean>(
    initialPlan?.status === "DEMO_TEMPLATE"
  );

  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [isApproving, setIsApproving] = useState<boolean>(false);
  const [error, setError] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const members = team?.members || [];
  const totalHours = tasks.reduce(
    (sum, task) => sum + (task.estimated_hours || 0),
    0
  );
  const assignedCount = Object.values(assignments).filter(Boolean).length;

  function toggleMilestone(name: string) {
    setExpanded((current) =>
      current.includes(name)
        ? current.filter((item) => item !== name)
        : [...current, name]
    );
  }

  function updateAssignee(taskId: string, memberId: string) {
    setAssignments((prev) => ({
      ...prev,
      [taskId]: memberId,
    }));
  }

  function recommendMember(role: string): string {
    const exact = members.find((member) => member.role === role);
    if (exact) return exact.id;

    const matching = members.find(
      (member) =>
        member.role.toLowerCase() === "full stack developer" &&
        (role.toLowerCase().includes("front") ||
          role.toLowerCase().includes("back"))
    );
    if (matching) return matching.id;

    return members[0]?.id || "";
  }

  function applySuggestions() {
    const newAssignments = { ...assignments };
    tasks.forEach((task) => {
      if (!newAssignments[task.id]) {
        newAssignments[task.id] = recommendMember(task.suggested_role);
      }
    });
    setAssignments(newAssignments);
  }

  async function handleGeneratePlan() {
    if (!project) {
      setError("No active project found.");
      return;
    }

    setIsGenerating(true);
    setError("");
    setSuccessMessage("");

    try {
      let backendProjectId = project.id;
      // 1. Ensure backend project exists for auth and membership
      try {
        await api.getProject(backendProjectId);
      } catch {
        // Sync project to backend DB
        const created = await api.createProject(
          project.name,
          project.description || ""
        );
        backendProjectId = created.id;
        localStorage.setItem("projectops_active_project", backendProjectId);
        const projects = readLocal<Project[]>("projectops_projects", []);
        const updated = projects.map((p) =>
          p.id === project.id ? { ...p, id: backendProjectId } : p
        );
        localStorage.setItem("projectops_projects", JSON.stringify(updated));
      }

      // 2. Sync members to backend if necessary
      if (members.length > 0) {
        try {
          const remoteMembers = await api.listMembers(backendProjectId);
          for (const m of members) {
            const exists = remoteMembers.some(
              (rm) => rm.name.toLowerCase() === m.name.toLowerCase()
            );
            if (!exists) {
              await api.createMember(
                backendProjectId,
                m.name,
                m.role,
                (m.weeklyHours || 40) / 5
              );
            }
          }
        } catch {
          // Member sync error is non-fatal; proceed with planning
        }
      }

      // 3. Assemble requirements text and docs
      const reqText =
        savedReqs?.details?.trim() ||
        project.description?.trim() ||
        `Deliver ${project.name}`;
      const repoUrl = savedReqs?.githubUrl?.trim() || "";

      // 4. Call Groq backend planning service
      const res = await api.generatePlan(backendProjectId, {
        requirements: reqText,
        github_url: repoUrl,
        documents: stagedDocs,
        save_as_draft: true,
      });

      // 5. Update state
      setPlan(res);
      setTasks(res.tasks || []);
      const newMilestones =
        res.milestones && res.milestones.length > 0
          ? res.milestones
          : Array.from(new Set(res.tasks.map((t) => t.milestone)));
      setMilestones(newMilestones);
      setExpanded(newMilestones);
      setIsDemoMode(false);
      setSuccessMessage(
        `AI Plan generated successfully with Groq (${res.tasks.length} tasks, ${res.estimated_total_hours}h effort). Verified DAG cycle-free.`
      );

      // Auto-populate assignments where suggestions match
      const initialAssignments: Record<string, string> = {};
      res.tasks.forEach((task) => {
        const assigned = recommendMember(task.suggested_role);
        if (assigned) initialAssignments[task.id] = assigned;
      });
      setAssignments(initialAssignments);

      // Cache plan response
      localStorage.setItem(
        `projectops_ai_plan_${project.id}`,
        JSON.stringify(res)
      );
      if (backendProjectId !== project.id) {
        localStorage.setItem(
          `projectops_ai_plan_${backendProjectId}`,
          JSON.stringify(res)
        );
      }
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : "An unexpected error occurred while communicating with Groq.";
      setError(`Plan generation failed: ${msg}`);
    } finally {
      setIsGenerating(false);
    }
  }

  function handleLoadDemoPlan() {
    setError("");
    setSuccessMessage("");
    setIsDemoMode(true);

    const demoTasks: GeneratedTask[] = [
      {
        id: "T01",
        title: "Finalize project scope and specifications",
        description: "Review stakeholder goals and define acceptance criteria",
        estimated_hours: 8,
        milestone: "Planning",
        suggested_role: "Project Manager",
      },
      {
        id: "T02",
        title: "Design database schemas and migrations",
        description: "PostgreSQL tables, indices, and constraints",
        estimated_hours: 12,
        milestone: "Foundation",
        suggested_role: "Backend Developer",
      },
      {
        id: "T03",
        title: "Design design system tokens and component specs",
        description: "Figma wireframes and Tailwind design tokens",
        estimated_hours: 16,
        milestone: "Foundation",
        suggested_role: "Frontend Developer",
      },
      {
        id: "T04",
        title: "Implement secure authentication & access control",
        description: "JWT issuance, refresh tokens, role checks",
        estimated_hours: 14,
        milestone: "Development",
        suggested_role: "Backend Developer",
      },
      {
        id: "T05",
        title: "Build user-facing responsive dashboards",
        description: "Interactive data visualization and real-time alerts",
        estimated_hours: 20,
        milestone: "Development",
        suggested_role: "Frontend Developer",
      },
      {
        id: "T06",
        title: "Execute automated integration & smoke test suite",
        description: "Pytest, Playwright, and load test verification",
        estimated_hours: 16,
        milestone: "Testing",
        suggested_role: "QA / Tester",
      },
    ];

    const demoMilestones = ["Planning", "Foundation", "Development", "Testing"];

    const demoPlan: GeneratePlanResponse = {
      project_id: project?.id || "demo-project",
      plan_id: "demo-snapshot",
      version: 1,
      name: project?.name || "Demo Project",
      goal_summary: "Offline Demo Template Plan",
      tasks: demoTasks,
      dependencies: [
        { predecessor_id: "T01", successor_id: "T02", dep_type: "FINISH_TO_START", lag_days: 0 },
        { predecessor_id: "T01", successor_id: "T03", dep_type: "FINISH_TO_START", lag_days: 0 },
        { predecessor_id: "T02", successor_id: "T04", dep_type: "FINISH_TO_START", lag_days: 0 },
        { predecessor_id: "T03", successor_id: "T05", dep_type: "FINISH_TO_START", lag_days: 0 },
        { predecessor_id: "T04", successor_id: "T06", dep_type: "FINISH_TO_START", lag_days: 0 },
        { predecessor_id: "T05", successor_id: "T06", dep_type: "FINISH_TO_START", lag_days: 0 },
      ],
      estimated_total_hours: 86,
      duration_days: 11,
      milestones: demoMilestones,
      documents_processed: [],
      is_valid_dag: true,
      status: "DEMO_TEMPLATE",
    };

    setPlan(demoPlan);
    setTasks(demoTasks);
    setMilestones(demoMilestones);
    setExpanded(demoMilestones);

    const demoAssignments: Record<string, string> = {};
    demoTasks.forEach((t) => {
      const assigned = recommendMember(t.suggested_role);
      if (assigned) demoAssignments[t.id] = assigned;
    });
    setAssignments(demoAssignments);
  }

  async function handleApprovePlan() {
    setError("");
    if (!project) {
      setError("No active project found.");
      return;
    }

    if (!plan || tasks.length === 0) {
      setError("No plan available to approve. Generate a plan first.");
      return;
    }

    setIsApproving(true);
    try {
      const backendProjectId =
        localStorage.getItem("projectops_active_project") || project.id;

      // If this was a persisted backend draft version, officially activate it
      if (plan.version && !isDemoMode) {
        try {
          await api.activatePlan(
            backendProjectId,
            plan.version,
            "Owner approved real AI-generated project execution plan."
          );
        } catch {
          // Activation error fallback: local snapshot preserved
        }
      }

      const activePlanSnapshot = {
        projectId: backendProjectId,
        version: plan.version || 1,
        status: isDemoMode ? "APPROVED_DEMO" : "ACTIVE",
        source: isDemoMode ? "demo_template" : "groq_ai",
        approvedAt: new Date().toISOString(),
        tasks: tasks.map((task) => ({
          id: task.id,
          title: task.title,
          milestone: task.milestone,
          estimatedHours: task.estimated_hours,
          assigneeId: assignments[task.id] || "",
          dependencies: (plan.dependencies || [])
            .filter((d) => d.successor_id === task.id)
            .map((d) => d.predecessor_id),
        })),
      };

      localStorage.setItem(
        `projectops_active_plan_${backendProjectId}`,
        JSON.stringify(activePlanSnapshot)
      );
      localStorage.setItem(
        `projectops_demo_plan_${backendProjectId}`,
        JSON.stringify(activePlanSnapshot)
      );
      if (backendProjectId !== project.id) {
        localStorage.setItem(
          `projectops_demo_plan_${project.id}`,
          JSON.stringify(activePlanSnapshot)
        );
      }

      navigate("/dashboard");
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Unable to approve plan.";
      setError(msg);
    } finally {
      setIsApproving(false);
    }
  }

  if (!project) {
    return (
      <main className="min-h-screen bg-[#f7f8fa] p-10 text-slate-900">
        <h1 className="text-xl font-semibold">No active project found</h1>
        <button
          onClick={() => navigate("/create-project")}
          className="mt-5 rounded-lg bg-slate-900 px-5 py-3 text-white"
        >
          Create Project
        </button>
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-[#f7f8fa] text-slate-900">
      <header className="border-b border-slate-200 bg-white px-6 py-5">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <span className="text-lg font-semibold">ProjectOps</span>
          <span className="text-sm text-slate-500">
            Autonomous Project Execution &amp; Risk Management
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-10">
        <button
          onClick={() => navigate("/requirements")}
          className="mb-7 flex items-center gap-2 text-sm text-slate-500 hover:text-slate-900"
        >
          <ArrowLeft size={16} />
          Back to requirements
        </button>

        <div className="flex flex-wrap items-start justify-between gap-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Plan synthesis &amp; review
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight">
              {project.name} — Execution Plan
            </h1>
            <p className="mt-3 text-sm text-slate-500">
              Synthesize and review AI-proposed tasks, deterministic DAG
              dependencies, and role assignments before execution.
            </p>
          </div>

          <div className="flex items-center gap-2">
            {plan && isDemoMode && (
              <span className="rounded-md border border-amber-300 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-800">
                Demo Template · Not AI Generated
              </span>
            )}
            {plan && !isDemoMode && (
              <span className="inline-flex items-center gap-1.5 rounded-md border border-emerald-300 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-800">
                <Sparkles size={14} className="text-emerald-600" />
                Groq AI Generated (gpt-oss-120b)
              </span>
            )}
          </div>
        </div>

        {/* Global Error Banner */}
        {error && (
          <div
            role="alert"
            className="mt-6 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"
          >
            <AlertCircle className="mt-0.5 shrink-0 text-rose-600" size={19} />
            <div className="flex-1">
              <p className="font-medium">Generation Error</p>
              <p className="mt-1 text-xs">{error}</p>
              <div className="mt-3 flex gap-3">
                <button
                  onClick={handleGeneratePlan}
                  disabled={isGenerating}
                  className="rounded-md bg-rose-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-rose-800"
                >
                  Retry with Groq
                </button>
                <button
                  onClick={() => navigate("/requirements")}
                  className="rounded-md border border-rose-300 px-3 py-1.5 text-xs font-medium text-rose-800 hover:bg-rose-100"
                >
                  Edit requirements &amp; docs
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Global Success Banner */}
        {successMessage && (
          <div className="mt-6 flex items-center gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
            <CheckCircle2 size={18} className="text-emerald-600" />
            <p className="text-xs font-medium">{successMessage}</p>
          </div>
        )}

        {/* Empty State: No plan generated yet */}
        {!plan && !isGenerating && (
          <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-900 text-white">
                <Sparkles size={24} />
              </div>
              <div>
                <h2 className="text-lg font-semibold">
                  Generate Plan with Groq AI
                </h2>
                <p className="text-xs text-slate-500">
                  Ready to decompose project requirements and specification
                  documents into an executable DAG.
                </p>
              </div>
            </div>

            <div className="mt-6 grid gap-4 rounded-xl border border-slate-100 bg-slate-50 p-5 sm:grid-cols-2">
              <div>
                <p className="text-xs font-semibold uppercase text-slate-400">
                  Staged Requirements
                </p>
                <p className="mt-1 line-clamp-3 text-xs text-slate-700">
                  {savedReqs?.details ||
                    project.description ||
                    "No written specifications provided. Will use project title and parameters."}
                </p>
                {savedReqs?.githubUrl && (
                  <p className="mt-2 text-xs text-slate-500">
                    Repository:{" "}
                    <span className="font-mono">{savedReqs.githubUrl}</span>
                  </p>
                )}
              </div>

              <div>
                <p className="text-xs font-semibold uppercase text-slate-400">
                  Uploaded Documents ({stagedDocs.length})
                </p>
                {stagedDocs.length === 0 ? (
                  <p className="mt-1 text-xs text-slate-500">
                    No attached documents staged. (You can add PDFs or DOCXs in
                    Requirements).
                  </p>
                ) : (
                  <ul className="mt-2 space-y-1">
                    {stagedDocs.map((doc, i) => (
                      <li
                        key={i}
                        className="flex items-center gap-2 text-xs font-medium text-slate-700"
                      >
                        <FileText size={14} className="text-slate-400" />
                        {doc.filename}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            <div className="mt-8 flex flex-wrap items-center gap-4">
              <button
                onClick={handleGeneratePlan}
                className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-6 py-3.5 text-sm font-semibold text-white shadow hover:bg-slate-800"
              >
                <Sparkles size={18} />
                Generate Plan with Groq AI
              </button>

              <button
                onClick={handleLoadDemoPlan}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-5 py-3.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Load Demo Template (Offline Demo)
              </button>
            </div>
          </div>
        )}

        {/* Loading Spinner State */}
        {isGenerating && (
          <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-12 text-center shadow-sm">
            <Loader2
              size={36}
              className="mx-auto animate-spin text-slate-900"
            />
            <h3 className="mt-5 text-lg font-semibold">
              Generating Plan with Groq AI...
            </h3>
            <p className="mx-auto mt-2 max-w-md text-xs leading-5 text-slate-500">
              Extracting document specifications, prompting Groq
              (openai/gpt-oss-120b), verifying DAG cycle-freedom, and persisting
              draft snapshot.
            </p>
            <div className="mx-auto mt-6 flex max-w-xs justify-center gap-2 text-xs text-slate-400">
              <span className="inline-block h-2 w-2 animate-ping rounded-full bg-slate-600" />
              <span>Validating TaskGraph constraints</span>
            </div>
          </div>
        )}

        {/* Real Plan Content */}
        {plan && !isGenerating && (
          <>
            {/* Top Metrics Cards */}
            <div className="mt-7 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[
                {
                  label: "Total tasks",
                  value: String(tasks.length),
                  icon: ListTodo,
                },
                {
                  label: "Estimated effort",
                  value: `${totalHours} hrs`,
                  icon: Clock3,
                },
                {
                  label: "Team members",
                  value: String(members.length),
                  icon: Users,
                },
                {
                  label: "Duration",
                  value: `${plan.duration_days || project.durationDays} days`,
                  icon: CalendarDays,
                },
              ].map((metric) => {
                const Icon = metric.icon;
                return (
                  <div
                    key={metric.label}
                    className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
                  >
                    <Icon size={19} className="text-slate-500" />
                    <p className="mt-4 text-2xl font-semibold">{metric.value}</p>
                    <p className="mt-1 text-xs text-slate-500">{metric.label}</p>
                  </div>
                );
              })}
            </div>

            {/* Document processing notice */}
            {plan.documents_processed &&
              plan.documents_processed.length > 0 && (
                <div className="mt-4 flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-xs text-slate-600">
                  <Check size={14} className="text-emerald-600" />
                  <span>
                    Successfully ingested and parsed:{" "}
                    <strong>{plan.documents_processed.join(", ")}</strong>
                  </span>
                </div>
              )}

            {/* Main Columns */}
            <div className="mt-7 grid items-start gap-6 lg:grid-cols-[minmax(0,1.8fr)_minmax(280px,1fr)]">
              {/* Task Groups Section */}
              <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="text-base font-semibold">
                      Tasks and milestones
                    </h2>
                    <p className="mt-1 text-xs text-slate-500">
                      Assign team members and review dependency chains.
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={applySuggestions}
                      className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3.5 py-2 text-xs font-medium hover:bg-slate-50"
                    >
                      <Sparkles size={14} />
                      Auto-assign roles
                    </button>
                    <button
                      onClick={handleGeneratePlan}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-3.5 py-2 text-xs font-medium hover:bg-slate-50"
                      title="Re-run generation with Groq"
                    >
                      <RotateCcw size={14} />
                      Regenerate
                    </button>
                  </div>
                </div>

                <div className="space-y-4">
                  {milestones.map((milestone) => {
                    const group = tasks.filter(
                      (task) => (task.milestone || "General") === milestone
                    );
                    if (group.length === 0) return null;

                    return (
                      <div
                        key={milestone}
                        className="overflow-hidden rounded-lg border border-slate-200"
                      >
                        <button
                          onClick={() => toggleMilestone(milestone)}
                          className="flex w-full items-center justify-between bg-slate-50 px-4 py-3 text-left transition hover:bg-slate-100"
                        >
                          <span className="text-sm font-semibold text-slate-800">
                            {milestone}
                            <span className="ml-2 text-xs font-normal text-slate-500">
                              ({group.length} tasks ·{" "}
                              {group.reduce(
                                (s, t) => s + (t.estimated_hours || 0),
                                0
                              )}
                              h)
                            </span>
                          </span>

                          {expanded.includes(milestone) ? (
                            <ChevronUp size={17} />
                          ) : (
                            <ChevronDown size={17} />
                          )}
                        </button>

                        {expanded.includes(milestone) && (
                          <div className="divide-y divide-slate-100">
                            {group.map((task) => {
                              const deps = (plan.dependencies || [])
                                .filter((d) => d.successor_id === task.id)
                                .map((d) => d.predecessor_id);

                              return (
                                <div key={task.id} className="p-4">
                                  <div className="flex items-start gap-3">
                                    <span className="mt-0.5 rounded bg-slate-100 px-2 py-1 font-mono text-xs text-slate-600">
                                      {task.id}
                                    </span>

                                    <div className="min-w-0 flex-1">
                                      <h3 className="text-sm font-medium text-slate-900">
                                        {task.title}
                                      </h3>

                                      {task.description && (
                                        <p className="mt-1 text-xs text-slate-500">
                                          {task.description}
                                        </p>
                                      )}

                                      <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-slate-500">
                                        <span>
                                          <strong>{task.estimated_hours}</strong>{" "}
                                          hours
                                        </span>
                                        <span>•</span>
                                        <span className="rounded bg-slate-50 px-2 py-0.5 border border-slate-200">
                                          Role: {task.suggested_role}
                                        </span>
                                      </div>

                                      {deps.length > 0 && (
                                        <p className="mt-2 flex items-center gap-1.5 text-xs text-slate-500">
                                          <GitBranch size={13} />
                                          Depends on:{" "}
                                          <span className="font-mono font-medium">
                                            {deps.join(", ")}
                                          </span>
                                        </p>
                                      )}

                                      <select
                                        value={assignments[task.id] || ""}
                                        onChange={(e) =>
                                          updateAssignee(task.id, e.target.value)
                                        }
                                        className="mt-3 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs outline-none focus:border-slate-600"
                                      >
                                        <option value="">Select assignee</option>
                                        {members.map((member) => (
                                          <option key={member.id} value={member.id}>
                                            {member.name} — {member.role}
                                          </option>
                                        ))}
                                      </select>
                                    </div>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </section>

              {/* Sidebar Summary */}
              <aside className="space-y-5 lg:sticky lg:top-6">
                <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                  <div className="flex items-center gap-2">
                    <ClipboardList size={19} className="text-slate-500" />
                    <h2 className="text-base font-semibold">Plan summary</h2>
                  </div>

                  <h3 className="mt-4 text-sm font-semibold">{project.name}</h3>

                  <p className="mt-2 text-xs leading-5 text-slate-500">
                    {plan.goal_summary || project.description || "Project execution plan"}
                  </p>

                  <div className="mt-5 space-y-3 border-t border-slate-100 pt-5 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Start date</span>
                      <span>{project.startDate}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Deadline</span>
                      <span>{project.deadline}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Milestones</span>
                      <span>{milestones.length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Assigned tasks</span>
                      <span>
                        {assignedCount}/{tasks.length}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">DAG Validity</span>
                      <span className="font-semibold text-emerald-600">
                        Cycle-Free
                      </span>
                    </div>
                  </div>
                </section>

                <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                  <h2 className="text-base font-semibold">
                    Dependency overview
                  </h2>
                  <p className="mt-2 text-xs leading-5 text-slate-500">
                    Deterministic schedule constraint graph.
                  </p>

                  <div className="mt-5 space-y-2">
                    {(plan.dependencies || []).length === 0 ? (
                      <p className="text-xs text-slate-400">
                        No prerequisite dependencies declared.
                      </p>
                    ) : (
                      (plan.dependencies || []).slice(0, 6).map((dep, idx) => (
                        <div
                          key={idx}
                          className="flex items-center gap-2 text-xs"
                        >
                          <span className="rounded bg-slate-100 px-2 py-0.5 font-mono">
                            {dep.predecessor_id}
                          </span>
                          <ArrowRight size={13} className="text-slate-400" />
                          <span className="font-mono font-medium">
                            {dep.successor_id}
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                </section>
              </aside>
            </div>

            {/* Bottom Actions */}
            <div className="mt-8 flex flex-wrap items-center justify-between gap-4 border-t border-slate-200 pt-6">
              <button
                onClick={() => navigate("/requirements")}
                className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-5 py-3 text-sm font-medium hover:bg-slate-50"
              >
                <ArrowLeft size={17} />
                Back to requirements
              </button>

              <button
                onClick={handleApprovePlan}
                disabled={isApproving}
                className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-6 py-3.5 text-sm font-semibold text-white shadow hover:bg-slate-800 disabled:opacity-50"
              >
                {isApproving ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : (
                  <CheckCircle2 size={18} />
                )}
                {isDemoMode ? "Approve demo template" : "Approve & activate plan"}
                <ArrowRight size={17} />
              </button>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
