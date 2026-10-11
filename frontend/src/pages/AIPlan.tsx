
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft, ArrowRight, CalendarDays, Clock3,
  Users, ListTodo, GitBranch, CheckCircle2,
  AlertCircle, ChevronDown, ChevronUp,
  ClipboardList, Sparkles
} from "lucide-react";

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

type Task = {
  id: string;
  title: string;
  milestone: string;
  estimatedHours: number;
  role: string;
  dependencies: string[];
  assigneeId: string;
};

const sampleTasks: Omit<Task, "assigneeId">[] = [
  {
    id: "T01",
    title: "Finalize project requirements",
    milestone: "Planning",
    estimatedHours: 8,
    role: "Project Manager",
    dependencies: []
  },
  {
    id: "T02",
    title: "Design database schema",
    milestone: "Foundation",
    estimatedHours: 12,
    role: "Database Developer",
    dependencies: ["T01"]
  },
  {
    id: "T03",
    title: "Design UI screens and components",
    milestone: "Foundation",
    estimatedHours: 20,
    role: "Frontend Developer",
    dependencies: ["T01"]
  },
  {
    id: "T04",
    title: "Implement authentication API",
    milestone: "Development",
    estimatedHours: 16,
    role: "Backend Developer",
    dependencies: ["T02"]
  },
  {
    id: "T05",
    title: "Build product catalog interface",
    milestone: "Development",
    estimatedHours: 24,
    role: "Frontend Developer",
    dependencies: ["T03"]
  },
  {
    id: "T06",
    title: "Develop product and order APIs",
    milestone: "Development",
    estimatedHours: 28,
    role: "Backend Developer",
    dependencies: ["T02"]
  },
  {
    id: "T07",
    title: "Integrate frontend and backend",
    milestone: "Integration",
    estimatedHours: 18,
    role: "Full Stack Developer",
    dependencies: ["T04", "T05", "T06"]
  },
  {
    id: "T08",
    title: "Test application functionality",
    milestone: "Testing",
    estimatedHours: 20,
    role: "QA / Tester",
    dependencies: ["T07"]
  },
  {
    id: "T09",
    title: "Prepare deployment and documentation",
    milestone: "Release",
    estimatedHours: 12,
    role: "DevOps Engineer",
    dependencies: ["T08"]
  }
];

const milestones = [
  "Planning", "Foundation", "Development",
  "Integration", "Testing", "Release"
];

function readLocal<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) as T : fallback;
  } catch {
    return fallback;
  }
}

export default function AIPlan() {
  const navigate = useNavigate();

  const [project] = useState<Project | null>(() => {
    const projects = readLocal<Project[]>("projectops_projects", []);
    const activeId = localStorage.getItem("projectops_active_project");
    return projects.find(p => p.id === activeId) || null;
  });

  const [team] = useState<Team | null>(() =>
    readLocal<Team | null>("projectops_team", null)
  );

  const [tasks, setTasks] = useState<Task[]>(() =>
    sampleTasks.map(task => ({
      ...task,
      assigneeId: ""
    }))
  );

  const [expanded, setExpanded] = useState<string[]>(
    milestones
  );
  const [error, setError] = useState("");

  const members = team?.members || [];
  const totalHours = tasks.reduce(
    (sum, task) => sum + task.estimatedHours, 0
  );

  const assignedCount = tasks.filter(
    task => task.assigneeId
  ).length;

  function toggleMilestone(name: string) {
    setExpanded(current =>
      current.includes(name)
        ? current.filter(item => item !== name)
        : [...current, name]
    );
  }

  function updateAssignee(taskId: string, memberId: string) {
    setTasks(current =>
      current.map(task =>
        task.id === taskId
          ? { ...task, assigneeId: memberId }
          : task
      )
    );
  }

  function recommendMember(role: string): string {
    const exact = members.find(
      member => member.role === role
    );

    if (exact) return exact.id;

    const matching = members.find(member =>
      member.role === "Full Stack Developer" &&
      (role.includes("Frontend") || role.includes("Backend"))
    );

    return matching?.id || "";
  }

  function applySuggestions() {
    setTasks(current =>
      current.map(task => ({
        ...task,
        assigneeId: task.assigneeId || recommendMember(task.role)
      }))
    );
  }

  function savePlan() {
    setError("");

    if (!project) {
      setError("No active project found.");
      return;
    }

    if (tasks.some(task => !task.assigneeId)) {
      setError(
        "Assign every task before approving the sample plan."
      );
      return;
    }

    const plan = {
      projectId: project.id,
      status: "APPROVED_DEMO",
      source: "sample_frontend",
      approvedAt: new Date().toISOString(),
      tasks
    };

    try {
      localStorage.setItem(
        `projectops_demo_plan_${project.id}`,
        JSON.stringify(plan)
      );
      navigate("/dashboard");
    } catch {
      setError("Unable to save this sample plan.");
    }
  }

  if (!project) {
    return (
      <main className="min-h-screen bg-[#f7f8fa] p-10 text-slate-900">
        <h1 className="text-xl font-semibold">
          No active project found
        </h1>
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
          <span className="text-lg font-semibold">
            ProjectOps
          </span>
          <span className="text-sm text-slate-500">
            Project planning
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
              Plan review
            </p>

            <h1 className="mt-3 text-3xl font-semibold tracking-tight">
              Project execution plan
            </h1>

            <p className="mt-3 text-sm text-slate-500">
              Review the proposed tasks, dependencies
              and assignments before starting execution.
            </p>
          </div>

          <span className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">
            Sample plan · Not AI generated
          </span>
        </div>

        <div className="mt-7 rounded-lg border border-blue-200 bg-blue-50 px-5 py-4 text-sm text-blue-900">
          <div className="flex items-start gap-3">
            <AlertCircle className="mt-0.5 shrink-0" size={19} />
            <p>
              This is an illustrative e-commerce execution plan.
              Your uploaded documents have not been processed.
              AI task generation will be connected later.
            </p>
          </div>
        </div>

        <div className="mt-7 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            {
              label: "Total tasks",
              value: String(tasks.length),
              icon: ListTodo
            },
            {
              label: "Estimated effort",
              value: `${totalHours} hrs`,
              icon: Clock3
            },
            {
              label: "Team members",
              value: String(members.length),
              icon: Users
            },
            {
              label: "Duration",
              value: `${project.durationDays} days`,
              icon: CalendarDays
            }
          ].map(metric => {
            const Icon = metric.icon;

            return (
              <div
                key={metric.label}
                className="rounded-xl border border-slate-200 bg-white p-5"
              >
                <Icon size={19} className="text-slate-500" />
                <p className="mt-4 text-2xl font-semibold">
                  {metric.value}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  {metric.label}
                </p>
              </div>
            );
          })}
        </div>

        <div className="mt-7 grid items-start gap-6 lg:grid-cols-[minmax(0,1.8fr)_minmax(280px,1fr)]">
          <section className="rounded-xl border border-slate-200 bg-white p-6">
            <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold">
                  Tasks and milestones
                </h2>
                <p className="mt-1 text-xs text-slate-500">
                  Assign tasks and review prerequisite work.
                </p>
              </div>

              <button
                onClick={applySuggestions}
                className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2 text-xs font-medium hover:bg-slate-50"
              >
                <Sparkles size={15} />
                Suggest assignments
              </button>
            </div>

            <div className="space-y-4">
              {milestones.map(milestone => {
                const group = tasks.filter(
                  task => task.milestone === milestone
                );

                return (
                  <div
                    key={milestone}
                    className="overflow-hidden rounded-lg border border-slate-200"
                  >
                    <button
                      onClick={() => toggleMilestone(milestone)}
                      className="flex w-full items-center justify-between bg-slate-50 px-4 py-3 text-left"
                    >
                      <span className="text-sm font-semibold">
                        {milestone}
                        <span className="ml-2 text-xs font-normal text-slate-500">
                          ({group.length} tasks)
                        </span>
                      </span>

                      {expanded.includes(milestone)
                        ? <ChevronUp size={17} />
                        : <ChevronDown size={17} />}
                    </button>

                    {expanded.includes(milestone) && (
                      <div className="divide-y divide-slate-100">
                        {group.map(task => (
                          <div key={task.id} className="p-4">
                            <div className="flex items-start gap-3">
                              <span className="mt-0.5 rounded bg-slate-100 px-2 py-1 text-xs text-slate-500">
                                {task.id}
                              </span>

                              <div className="min-w-0 flex-1">
                                <h3 className="text-sm font-medium">
                                  {task.title}
                                </h3>

                                <p className="mt-2 text-xs text-slate-500">
                                  {task.estimatedHours} hours · {task.role}
                                </p>

                                {task.dependencies.length > 0 && (
                                  <p className="mt-2 flex items-center gap-1.5 text-xs text-slate-500">
                                    <GitBranch size={13} />
                                    Depends on {task.dependencies.join(", ")}
                                  </p>
                                )}

                                <select
                                  value={task.assigneeId}
                                  onChange={e =>
                                    updateAssignee(task.id, e.target.value)
                                  }
                                  className="mt-3 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs outline-none focus:border-slate-600"
                                >
                                  <option value="">Select assignee</option>
                                  {members.map(member => (
                                    <option key={member.id} value={member.id}>
                                      {member.name} — {member.role}
                                    </option>
                                  ))}
                                </select>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </section>

          <aside className="space-y-5 lg:sticky lg:top-6">
            <section className="rounded-xl border border-slate-200 bg-white p-6">
              <div className="flex items-center gap-2">
                <ClipboardList size={19} className="text-slate-500" />
                <h2 className="text-base font-semibold">
                  Plan summary
                </h2>
              </div>

              <h3 className="mt-5 text-sm font-semibold">
                {project.name}
              </h3>

              <p className="mt-2 text-xs leading-5 text-slate-500">
                {project.description || "Project execution planning"}
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
                  <span>{assignedCount}/{tasks.length}</span>
                </div>
              </div>
            </section>

            <section className="rounded-xl border border-slate-200 bg-white p-6">
              <h2 className="text-base font-semibold">
                Dependency overview
              </h2>

              <p className="mt-2 text-xs leading-5 text-slate-500">
                Dependencies determine which tasks must
                finish before other tasks can start.
              </p>

              <div className="mt-5 space-y-3">
                {tasks.filter(t => t.dependencies.length > 0)
                  .slice(0, 5)
                  .map(task => (
                    <div
                      key={task.id}
                      className="flex items-center gap-2 text-xs"
                    >
                      <span className="rounded bg-slate-100 px-2 py-1">
                        {task.dependencies.join(", ")}
                      </span>
                      <ArrowRight size={13} className="text-slate-400" />
                      <span className="font-medium">{task.id}</span>
                    </div>
                  ))}
              </div>
            </section>
          </aside>
        </div>

        {error && (
          <p role="alert" className="mt-6 rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            {error}
          </p>
        )}

        <div className="mt-8 flex flex-wrap items-center justify-between gap-4 border-t border-slate-200 pt-6">
          <button
            onClick={() => navigate("/requirements")}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-5 py-3 text-sm font-medium"
          >
            <ArrowLeft size={17} />
            Back
          </button>

          <button
            onClick={savePlan}
            disabled={members.length === 0}
            className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-5 py-3 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-40"
          >
            <CheckCircle2 size={18} />
            Approve sample plan
            <ArrowRight size={17} />
          </button>
        </div>
      </main>
    </div>
  );
}
