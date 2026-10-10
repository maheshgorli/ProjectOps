
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  FolderKanban,
  ListTodo,
  Clock3,
  AlertTriangle,
  CheckCircle2,
  LogOut,
  ArrowRight,
  CalendarDays,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";

type Member = {
  id: string;
  name: string;
  email: string;
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
  teamId: string;
  name: string;
  description: string;
  durationDays: number;
  deadline: string;
};

type Task = {
  id: string;
  title: string;
  milestone: string;
  estimatedHours: number;
  assigneeId: string;
};

type Plan = {
  projectId: string;
  tasks: Task[];
};

function readStorage<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const [team] = useState<Team | null>(() =>
    readStorage("projectops_team", null)
  );

  const [project] = useState<Project | null>(() => {
    const projects = readStorage<Project[]>(
      "projectops_projects",
      []
    );
    const id = localStorage.getItem("projectops_active_project");
    return projects.find((p) => p.id === id) || null;
  });

  const [plan] = useState<Plan | null>(() =>
    project
      ? readStorage(`projectops_demo_plan_${project.id}`, null)
      : null
  );

  // Frontend-only role preview. Real permissions will
  // come from backend membership records later.
  const [view, setView] = useState<"leader" | "member">("leader");

  const members = team?.members || [];
  const tasks = plan?.tasks || [];

  const currentMember = members.find(
    (member) =>
      member.email.toLowerCase() === user?.email.toLowerCase()
  );

  const myTasks = tasks.filter(
    (task) => task.assigneeId === currentMember?.id
  );

  const totalEffort = tasks.reduce(
    (sum, task) => sum + task.estimatedHours,
    0
  );

  const metrics =
    view === "leader"
      ? [
          { label: "Team members", value: members.length, icon: Users },
          { label: "Planned tasks", value: tasks.length, icon: ListTodo },
          { label: "Estimated effort", value: `${totalEffort}h`, icon: Clock3 },
          { label: "Duration", value: `${project?.durationDays || 0}d`, icon: CalendarDays },
        ]
      : [
          { label: "My tasks", value: myTasks.length, icon: ListTodo },
          {
            label: "Assigned effort",
            value: `${myTasks.reduce((s, t) => s + t.estimatedHours, 0)}h`,
            icon: Clock3,
          },
          { label: "Team members", value: members.length, icon: Users },
          { label: "Project tasks", value: tasks.length, icon: FolderKanban },
        ];

  return (
    <div className="min-h-screen bg-[#f7f8fa] text-slate-900">
      <div className="flex min-h-screen">
        <aside className="hidden w-64 flex-col border-r border-slate-200 bg-white p-5 md:flex">
          <div className="mb-10 text-xl font-semibold">
            ProjectOps
          </div>

          <div className="mb-7 rounded-lg bg-slate-50 p-3">
            <p className="text-xs text-slate-500">WORKSPACE</p>
            <p className="mt-1 text-sm font-semibold">
              {team?.name || "My Workspace"}
            </p>
          </div>

          <nav className="space-y-2">
            <div className="flex items-center gap-3 rounded-lg bg-slate-900 px-3 py-2.5 text-sm text-white">
              <LayoutDashboard size={18} />
              Overview
            </div>

            <button
              onClick={() => navigate("/create-project")}
              className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-600 hover:bg-slate-50"
            >
              <FolderKanban size={18} />
              Projects
            </button>

            <button
              onClick={() => navigate("/add-members")}
              className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-600 hover:bg-slate-50"
            >
              <Users size={18} />
              Team
            </button>

            <button
              onClick={() => navigate("/ai-plan")}
              className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-600 hover:bg-slate-50"
            >
              <ListTodo size={18} />
              Project Plan
            </button>
          </nav>

          <div className="mt-auto border-t border-slate-200 pt-5">
            <p className="mb-3 text-sm font-medium">
              {user?.name || "Demo User"}
            </p>

            <button
              onClick={() => {
                logout();
                navigate("/login");
              }}
              className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-900"
            >
              <LogOut size={17} />
              Sign out
            </button>
          </div>
        </aside>

        <div className="min-w-0 flex-1">
          <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-6 py-5">
            <div>
              <h1 className="text-lg font-semibold">
                {view === "leader"
                  ? "Project Overview"
                  : "My Dashboard"}
              </h1>

              <p className="mt-1 text-xs text-slate-500">
                {project?.name || "No project selected"}
              </p>
            </div>

            <div className="flex items-center gap-2">
              <label
                htmlFor="dashboard-view"
                className="text-xs text-slate-500"
              >
                Preview role
              </label>

              <select
                id="dashboard-view"
                value={view}
                onChange={(e) =>
                  setView(e.target.value as "leader" | "member")
                }
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
              >
                <option value="leader">Team Leader</option>
                <option value="member">Team Member</option>
              </select>
            </div>
          </header>

          <main className="mx-auto max-w-7xl p-6 lg:p-9">
            <div className="mb-8">
              <h2 className="text-2xl font-semibold">
                Welcome back, {user?.name || "there"}
              </h2>
              <p className="mt-2 text-sm text-slate-500">
                {view === "leader"
                  ? "Here's an overview of your team and project."
                  : "Here's the work assigned to you."}
              </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {metrics.map((metric) => {
                const Icon = metric.icon;

                return (
                  <div
                    key={metric.label}
                    className="rounded-xl border border-slate-200 bg-white p-5"
                  >
                    <Icon size={20} className="text-slate-500" />
                    <p className="mt-5 text-2xl font-semibold">
                      {metric.value}
                    </p>
                    <p className="mt-2 text-xs text-slate-500">
                      {metric.label}
                    </p>
                  </div>
                );
              })}
            </div>

            {!project && (
              <div className="mt-8 rounded-xl border border-slate-200 bg-white p-8">
                <FolderKanban size={28} className="text-slate-500" />
                <h3 className="mt-4 font-semibold">
                  No project created yet
                </h3>
                <p className="mt-2 text-sm text-slate-500">
                  Create a project to begin planning your team's work.
                </p>
                <button
                  onClick={() => navigate("/create-project")}
                  className="mt-5 rounded-lg bg-slate-900 px-5 py-3 text-sm text-white"
                >
                  Create project
                </button>
              </div>
            )}

            {project && (
              <div className="mt-7 grid gap-6 xl:grid-cols-[1.5fr_1fr]">
                <section className="rounded-xl border border-slate-200 bg-white p-6">
                  <div className="mb-5 flex items-center justify-between">
                    <h3 className="font-semibold">
                      {view === "leader"
                        ? "Project task overview"
                        : "My assigned tasks"}
                    </h3>
                    <ListTodo size={19} className="text-slate-500" />
                  </div>

                  {(view === "leader" ? tasks : myTasks).length === 0 ? (
                    <div className="py-10 text-center">
                      <p className="text-sm text-slate-500">
                        {view === "leader"
                          ? "No approved sample plan is available."
                          : currentMember
                            ? "No tasks have been assigned to you."
                            : "Your login email isn't linked to a team member."}
                      </p>
                    </div>
                  ) : (
                    <div className="divide-y divide-slate-100">
                      {(view === "leader" ? tasks : myTasks).map((task) => {
                        const assignee = members.find(
                          m => m.id === task.assigneeId
                        );

                        return (
                          <div
                            key={task.id}
                            className="flex items-center justify-between gap-4 py-4"
                          >
                            <div className="flex items-center gap-3">
                              <CheckCircle2
                                size={17}
                                className="text-slate-300"
                              />
                              <div>
                                <p className="text-sm font-medium">
                                  {task.title}
                                </p>
                                <p className="mt-1 text-xs text-slate-500">
                                  {task.milestone} · {task.estimatedHours}h
                                </p>
                              </div>
                            </div>

                            {view === "leader" && (
                              <span className="text-xs text-slate-500">
                                {assignee?.name || "Unassigned"}
                              </span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </section>

                <div className="space-y-6">
                  <section className="rounded-xl border border-slate-200 bg-white p-6">
                    <h3 className="font-semibold">
                      {view === "leader"
                        ? "Team workload"
                        : "My work summary"}
                    </h3>

                    {view === "leader" ? (
                      <div className="mt-5 space-y-5">
                        {members.map((member) => {
                          const effort = tasks
                            .filter(t => t.assigneeId === member.id)
                            .reduce((s, t) => s + t.estimatedHours, 0);

                          return (
                            <div key={member.id}>
                              <div className="mb-2 flex justify-between text-xs">
                                <span>{member.name}</span>
                                <span className="text-slate-500">
                                  {effort}h assigned
                                </span>
                              </div>

                              <div className="h-2 rounded-full bg-slate-100">
                                <div
                                  className="h-2 rounded-full bg-slate-800"
                                  style={{
                                    width: `${Math.min(
                                      100,
                                      member.weeklyHours > 0
                                        ? (effort / member.weeklyHours) * 100
                                        : 0
                                    )}%`,
                                  }}
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="mt-5 space-y-3 text-sm">
                        <p>Assigned tasks: {myTasks.length}</p>
                        <p>
                          Estimated effort:{" "}
                          {myTasks.reduce(
                            (sum, task) => sum + task.estimatedHours,
                            0
                          )} hours
                        </p>
                      </div>
                    )}
                  </section>

                  <section className="rounded-xl border border-slate-200 bg-white p-6">
                    <div className="flex items-center gap-2">
                      {view === "leader"
                        ? <AlertTriangle size={19} className="text-amber-600" />
                        : <Clock3 size={19} className="text-slate-500" />}
                      <h3 className="font-semibold">
                        {view === "leader"
                          ? "Risk monitoring"
                          : "Upcoming deadlines"}
                      </h3>
                    </div>

                    <p className="mt-3 text-sm leading-6 text-slate-500">
                      {view === "leader"
                        ? "Risk analysis will appear here when the backend is connected."
                        : "Your scheduled task deadlines will appear here when task scheduling is connected."}
                    </p>
                  </section>

                  <button
                    onClick={() => navigate("/ai-plan")}
                    className="flex w-full items-center justify-between rounded-xl bg-slate-900 px-5 py-4 text-sm font-medium text-white"
                  >
                    Open project plan
                    <ArrowRight size={17} />
                  </button>
                </div>
              </div>
            )}

            <p className="mt-8 text-xs text-slate-400">
              Frontend demo · Role switching is for UI preview only.
            </p>
          </main>
        </div>
      </div>
    </div>
  );
}
