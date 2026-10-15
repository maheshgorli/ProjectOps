import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  CalendarDays,
  FolderKanban,
  Clock3,
  Loader2,
} from "lucide-react";
import { api } from "../services/api";

type Team = {
  id: string;
  name: string;
  description: string;
  members: unknown[];
};

type Project = {
  id: string;
  teamId: string;
  name: string;
  description: string;
  goal?: string;
  type: string;
  startDate: string;
  deadline: string;
  durationDays: number;
  priority: string;
  status: string;
};

function getTeam(): Team | null {
  try {
    const raw = localStorage.getItem("projectops_team");
    if (!raw) return null;
    const team = JSON.parse(raw) as Team;
    return team?.id ? team : null;
  } catch {
    return null;
  }
}

function todayLocal(): string {
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function calculateDuration(start: string, end: string): number {
  if (!start || !end) return 0;

  const startTime = Date.parse(`${start}T00:00:00Z`);
  const endTime = Date.parse(`${end}T00:00:00Z`);

  if (!Number.isFinite(startTime) || !Number.isFinite(endTime)) {
    return 0;
  }

  const days = Math.round(
    (endTime - startTime) / (1000 * 60 * 60 * 24)
  );

  return days >= 0 ? days + 1 : 0;
}

export default function CreateProject() {
  const navigate = useNavigate();

  const [team] = useState<Team | null>(() => {
    const existing = getTeam();
    if (existing) return existing;
    const fallback: Team = {
      id: "team-default",
      name: "Engineering Team",
      description: "Default workspace team",
      members: [],
    };
    try {
      localStorage.setItem("projectops_team", JSON.stringify(fallback));
    } catch {
      // ignore
    }
    return fallback;
  });

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [type, setType] = useState("Web Application");
  const [priority, setPriority] = useState("Medium");
  const [startDate, setStartDate] = useState(todayLocal());
  const [deadline, setDeadline] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const durationDays = calculateDuration(startDate, deadline);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");

    if (!name.trim()) {
      setError("Please enter a project name.");
      return;
    }

    if (!startDate || !deadline || deadline < startDate) {
      setError("Deadline must be on or after the start date.");
      return;
    }

    setIsSubmitting(true);
    try {
      // 1. Persist to real backend database via API
      const backendProject = await api.createProject(
        name.trim(),
        description.trim()
      );

      // 2. Mirror into local state for wizard navigation
      const project: Project = {
        id: backendProject.id,
        teamId: team?.id || "team-default",
        name: backendProject.name,
        description: backendProject.description || description.trim(),
        type,
        startDate,
        deadline,
        durationDays,
        priority,
        status: "Planning",
      };

      const raw = localStorage.getItem("projectops_projects");
      const parsed: unknown = raw ? JSON.parse(raw) : [];
      const projects: Project[] = Array.isArray(parsed) ? parsed : [];

      localStorage.setItem(
        "projectops_projects",
        JSON.stringify([...projects.filter((p) => p.id !== project.id), project])
      );

      localStorage.setItem("projectops_active_project", project.id);

      navigate("/add-members");
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Unable to create project in backend.";
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  }

  const inputClass =
    "w-full rounded-lg border border-slate-300 bg-white " +
    "px-4 py-3 text-sm text-slate-900 outline-none " +
    "focus:border-slate-600 focus:ring-2 focus:ring-slate-100";

  if (!team) {
    return (
      <main className="min-h-screen bg-[#f7f8fa] p-10 text-slate-900">
        <h1 className="text-2xl font-semibold">
          Create your team first
        </h1>
        <button
          onClick={() => navigate("/create-team")}
          className="mt-5 rounded-lg bg-slate-900 px-5 py-3 text-white"
        >
          Go to Create Team
        </button>
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-[#f7f8fa] text-slate-900">
      <header className="border-b border-slate-200 bg-white px-6 py-5">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <span className="text-lg font-semibold tracking-tight">
            ProjectOps
          </span>
          <span className="text-sm text-slate-500">
            Project setup
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-12">
        <button
          type="button"
          onClick={() => navigate("/create-team")}
          className="mb-8 inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-900"
        >
          <ArrowLeft size={16} />
          Back to team
        </button>

        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Step 2 of 4
        </p>

        <h1 className="mt-3 text-3xl font-semibold tracking-tight">
          Create your first project
        </h1>

        <p className="mt-3 text-sm leading-6 text-slate-500">
          Set the project scope and timeline. Requirements can be
          added in the following steps.
        </p>

        <div className="mt-6 flex items-center gap-3 rounded-lg border border-slate-200 bg-white p-4">
          <FolderKanban size={21} className="text-slate-500" />
          <div>
            <p className="text-xs text-slate-500">
              Creating project under
            </p>
            <p className="text-sm font-semibold">{team.name}</p>
          </div>
        </div>

        <form
          onSubmit={handleSubmit}
          className="mt-7 space-y-7 rounded-xl border border-slate-200 bg-white p-7 shadow-sm"
        >
          <section>
            <h2 className="mb-5 text-base font-semibold">
              Basic information
            </h2>

            <div className="space-y-5">
              <div>
                <label htmlFor="project-name" className="mb-2 block text-sm font-medium">
                  Project name *
                </label>
                <input
                  id="project-name"
                  required
                  maxLength={100}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. SmartCart E-Commerce Platform"
                  className={inputClass}
                />
              </div>

              <div>
                <label htmlFor="project-desc" className="mb-2 block text-sm font-medium">
                  Short description
                </label>
                <textarea
                  id="project-desc"
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Briefly describe your project..."
                  className={`${inputClass} resize-none`}
                />
              </div>

              <div className="grid gap-5 sm:grid-cols-2">
                <div>
                  <label htmlFor="project-type" className="mb-2 block text-sm font-medium">
                    Project type
                  </label>
                  <select
                    id="project-type"
                    value={type}
                    onChange={(e) => setType(e.target.value)}
                    className={inputClass}
                  >
                    <option>Web Application</option>
                    <option>Mobile Application</option>
                    <option>AI / Machine Learning</option>
                    <option>Data Science</option>
                    <option>Research Project</option>
                    <option>Software Development</option>
                    <option>Other</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="priority" className="mb-2 block text-sm font-medium">
                    Priority
                  </label>
                  <select
                    id="priority"
                    value={priority}
                    onChange={(e) => setPriority(e.target.value)}
                    className={inputClass}
                  >
                    <option>Low</option>
                    <option>Medium</option>
                    <option>High</option>
                    <option>Critical</option>
                  </select>
                </div>
              </div>
            </div>
          </section>

          <section className="border-t border-slate-100 pt-7">
            <div className="mb-5 flex items-center gap-2">
              <CalendarDays size={19} className="text-slate-600" />
              <h2 className="text-base font-semibold">
                Project timeline
              </h2>
            </div>

            <div className="grid gap-5 sm:grid-cols-2">
              <div>
                <label htmlFor="start-date" className="mb-2 block text-sm font-medium">
                  Start date *
                </label>
                <input
                  id="start-date"
                  type="date"
                  required
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className={inputClass}
                />
              </div>

              <div>
                <label htmlFor="end-date" className="mb-2 block text-sm font-medium">
                  Deadline *
                </label>
                <input
                  id="end-date"
                  type="date"
                  required
                  min={startDate}
                  value={deadline}
                  onChange={(e) => setDeadline(e.target.value)}
                  className={inputClass}
                />
              </div>
            </div>

            <div className="mt-5 flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-5 py-4">
              <div className="flex items-center gap-3">
                <Clock3 size={19} className="text-slate-500" />
                <div>
                  <p className="text-sm font-medium">
                    Project duration
                  </p>
                  <p className="text-xs text-slate-500">
                    Calculated from the selected dates
                  </p>
                </div>
              </div>

              <div className="text-right">
                <p className="text-xl font-semibold">
                  {durationDays > 0 ? durationDays : "—"}
                </p>
                <p className="text-xs text-slate-500">
                  calendar days
                </p>
              </div>
            </div>
          </section>

          {error && (
            <p role="alert" className="text-sm text-rose-600">
              {error}
            </p>
          )}

          <div className="flex justify-between gap-3 border-t border-slate-100 pt-6">
            <button
              type="button"
              onClick={() => navigate("/create-team")}
              className="rounded-lg border border-slate-300 px-5 py-3 text-sm font-medium hover:bg-slate-50"
            >
              Back
            </button>

            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-5 py-3 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
            >
              {isSubmitting ? (
                <Loader2 size={17} className="animate-spin" />
              ) : null}
              {isSubmitting ? "Creating..." : "Continue to members"}
              {!isSubmitting && <ArrowRight size={17} />}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
