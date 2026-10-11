
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Users,
  UserPlus,
  Pencil,
  Trash2,
  Clock3,
  X,
  Check,
} from "lucide-react";

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
  description: string;
  members: Member[];
};

type Project = {
  id: string;
  teamId: string;
  name: string;
  durationDays: number;
  startDate: string;
  deadline: string;
};

const roles = [
  "Frontend Developer",
  "Backend Developer",
  "Full Stack Developer",
  "UI/UX Designer",
  "Database Developer",
  "AI/ML Developer",
  "QA / Tester",
  "Project Manager",
  "DevOps Engineer",
  "Other",
];

const skillOptions = [
  "React",
  "TypeScript",
  "JavaScript",
  "Python",
  "FastAPI",
  "Node.js",
  "SQL",
  "Git/GitHub",
  "UI/UX",
  "Testing",
  "Machine Learning",
  "Docker",
  "DevOps",
  "Documentation",
];

function loadTeam(): Team | null {
  try {
    const raw = localStorage.getItem("projectops_team");
    if (!raw) return null;
    const data = JSON.parse(raw) as Team;
    if (!data.id) return null;
    return { ...data, members: data.members || [] };
  } catch {
    return null;
  }
}

function loadProject(): Project | null {
  try {
    const projectId = localStorage.getItem(
      "projectops_active_project"
    );
    const raw = localStorage.getItem("projectops_projects");
    const projects: Project[] = raw ? JSON.parse(raw) : [];
    return projects.find((p) => p.id === projectId) || null;
  } catch {
    return null;
  }
}

const emptyForm = {
  name: "",
  email: "",
  role: "Frontend Developer",
  skills: [] as string[],
  weeklyHours: 20,
};

export default function AddMembers() {
  const navigate = useNavigate();

  const [team, setTeam] = useState<Team | null>(loadTeam);
  const [project] = useState<Project | null>(loadProject);

  const [form, setForm] = useState({ ...emptyForm });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState("");

  const members = team?.members || [];

  function updateForm<K extends keyof typeof emptyForm>(
    field: K,
    value: (typeof emptyForm)[K]
  ) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function toggleSkill(skill: string) {
    setForm((current) => ({
      ...current,
      skills: current.skills.includes(skill)
        ? current.skills.filter((item) => item !== skill)
        : [...current.skills, skill],
    }));
  }

  function saveMember(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");

    if (!team) return;

    if (!form.name.trim() || !form.email.trim()) {
      setError("Name and email are required.");
      return;
    }

    if (form.skills.length === 0) {
      setError("Select at least one technical skill.");
      return;
    }

    if (
      !Number.isFinite(form.weeklyHours) ||
      form.weeklyHours < 1 ||
      form.weeklyHours > 80
    ) {
      setError("Availability must be between 1 and 80 hours.");
      return;
    }

    const normalizedEmail = form.email.trim().toLowerCase();

    const duplicate = members.some(
      (member) =>
        member.email.toLowerCase() === normalizedEmail &&
        member.id !== editingId
    );

    if (duplicate) {
      setError("This email already belongs to a team member.");
      return;
    }

    const member: Member = {
      id: editingId || crypto.randomUUID(),
      name: form.name.trim(),
      email: normalizedEmail,
      role: form.role,
      skills: [...form.skills],
      weeklyHours: form.weeklyHours,
    };

    const updated: Team = {
      ...team,
      members: editingId
        ? members.map((m) => (m.id === editingId ? member : m))
        : [...members, member],
    };

    try {
      localStorage.setItem("projectops_team", JSON.stringify(updated));
      setTeam(updated);
      setForm({ ...emptyForm, skills: [] });
      setEditingId(null);
    } catch {
      setError("Unable to save the team member.");
    }
  }

  function editMember(member: Member) {
    setEditingId(member.id);
    setForm({
      name: member.name,
      email: member.email,
      role: member.role,
      skills: [...member.skills],
      weeklyHours: member.weeklyHours,
    });
    setError("");
  }

  function removeMember(id: string) {
    if (!team) return;

    const updated = {
      ...team,
      members: members.filter((member) => member.id !== id),
    };

    try {
      localStorage.setItem("projectops_team", JSON.stringify(updated));
      setTeam(updated);

      if (editingId === id) {
        setEditingId(null);
        setForm({ ...emptyForm, skills: [] });
      }
    } catch {
      setError("Unable to remove member.");
    }
  }

  if (!team || !project || project.teamId !== team.id) {
    return (
      <main className="min-h-screen bg-[#f7f8fa] p-10 text-slate-900">
        <h1 className="text-2xl font-semibold">
          Project setup is incomplete
        </h1>
        <p className="mt-3 text-slate-500">
          Create a team and project before adding members.
        </p>
        <button
          onClick={() => navigate("/workspace")}
          className="mt-5 rounded-lg bg-slate-900 px-5 py-3 text-white"
        >
          Go to Workspace
        </button>
      </main>
    );
  }

  const inputClass =
    "w-full rounded-lg border border-slate-300 bg-white " +
    "px-3 py-2.5 text-sm outline-none " +
    "focus:border-slate-600 focus:ring-2 focus:ring-slate-100";

  return (
    <div className="min-h-screen bg-[#f7f8fa] text-slate-900">
      <header className="border-b border-slate-200 bg-white px-6 py-5">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <span className="text-lg font-semibold tracking-tight">
            ProjectOps
          </span>
          <span className="text-sm text-slate-500">
            Team setup
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-10">
        <button
          onClick={() => navigate("/create-project")}
          className="mb-7 flex items-center gap-2 text-sm text-slate-500 hover:text-slate-900"
        >
          <ArrowLeft size={16} />
          Back to project
        </button>

        <div className="mb-8">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Step 3 of 4
          </p>

          <h1 className="mt-3 text-3xl font-semibold tracking-tight">
            Add your team members
          </h1>

          <p className="mt-3 text-sm text-slate-500">
            Define who is working on this project and how
            much time they can contribute.
          </p>
        </div>

        <div className="mb-7 flex flex-wrap items-center gap-5 rounded-xl border border-slate-200 bg-white px-6 py-4">
          <div className="flex items-center gap-3">
            <Users size={19} className="text-slate-500" />
            <div>
              <p className="text-xs text-slate-500">Team</p>
              <p className="text-sm font-semibold">{team.name}</p>
            </div>
          </div>

          <div className="hidden h-9 w-px bg-slate-200 sm:block" />

          <div>
            <p className="text-xs text-slate-500">Project</p>
            <p className="text-sm font-semibold">{project.name}</p>
          </div>

          <div className="hidden h-9 w-px bg-slate-200 sm:block" />

          <div className="flex items-center gap-2">
            <Clock3 size={18} className="text-slate-500" />
            <div>
              <p className="text-xs text-slate-500">Duration</p>
              <p className="text-sm font-semibold">
                {project.durationDays} calendar days
              </p>
            </div>
          </div>
        </div>

        <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <form
            onSubmit={saveMember}
            className="space-y-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
          >
            <div className="flex items-center justify-between border-b border-slate-100 pb-5">
              <div>
                <h2 className="text-base font-semibold">
                  {editingId ? "Edit member" : "New team member"}
                </h2>
                <p className="mt-1 text-xs text-slate-500">
                  Add skills and working availability.
                </p>
              </div>
              <UserPlus size={21} className="text-slate-500" />
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="member-name" className="mb-2 block text-sm font-medium">
                  Full name *
                </label>
                <input
                  id="member-name"
                  required
                  value={form.name}
                  onChange={(e) => updateForm("name", e.target.value)}
                  placeholder="Member name"
                  className={inputClass}
                />
              </div>

              <div>
                <label htmlFor="member-email" className="mb-2 block text-sm font-medium">
                  Email address *
                </label>
                <input
                  id="member-email"
                  type="email"
                  required
                  value={form.email}
                  onChange={(e) => updateForm("email", e.target.value)}
                  placeholder="name@example.com"
                  className={inputClass}
                />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="member-role" className="mb-2 block text-sm font-medium">
                  Primary role
                </label>
                <select
                  id="member-role"
                  value={form.role}
                  onChange={(e) => updateForm("role", e.target.value)}
                  className={inputClass}
                >
                  {roles.map((role) => (
                    <option key={role}>{role}</option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="weekly-hours" className="mb-2 block text-sm font-medium">
                  Availability (hours/week)
                </label>
                <input
                  id="weekly-hours"
                  type="number"
                  min={1}
                  max={80}
                  required
                  value={form.weeklyHours}
                  onChange={(e) =>
                    updateForm("weeklyHours", Number(e.target.value))
                  }
                  className={inputClass}
                />
              </div>
            </div>

            <div>
              <label className="mb-3 block text-sm font-medium">
                Technical skills *
              </label>

              <div className="flex flex-wrap gap-2">
                {skillOptions.map((skill) => {
                  const selected = form.skills.includes(skill);

                  return (
                    <button
                      key={skill}
                      type="button"
                      onClick={() => toggleSkill(skill)}
                      className={`rounded-md border px-3 py-1.5 text-xs font-medium transition ${
                        selected
                          ? "border-slate-900 bg-slate-900 text-white"
                          : "border-slate-200 bg-white text-slate-600 hover:border-slate-400"
                      }`}
                    >
                      {selected && <Check size={12} className="mr-1 inline" />}
                      {skill}
                    </button>
                  );
                })}
              </div>
            </div>

            {error && (
              <p role="alert" className="text-sm text-rose-600">
                {error}
              </p>
            )}

            <div className="flex flex-wrap gap-3 border-t border-slate-100 pt-5">
              <button
                type="submit"
                className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-slate-700"
              >
                {editingId ? <Check size={17} /> : <UserPlus size={17} />}
                {editingId ? "Save changes" : "Add to team"}
              </button>

              {editingId && (
                <button
                  type="button"
                  onClick={() => {
                    setEditingId(null);
                    setForm({ ...emptyForm, skills: [] });
                    setError("");
                  }}
                  className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2.5 text-sm hover:bg-slate-50"
                >
                  <X size={16} />
                  Cancel
                </button>
              )}
            </div>
          </form>

          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-100 pb-5">
              <div>
                <h2 className="text-base font-semibold">
                  Team members
                </h2>
                <p className="mt-1 text-xs text-slate-500">
                  Members added to this workspace
                </p>
              </div>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold">
                {members.length} members
              </span>
            </div>

            <div className="mt-5 space-y-3">
              {members.length === 0 && (
                <div className="rounded-lg border border-dashed border-slate-200 px-4 py-12 text-center">
                  <Users size={28} className="mx-auto text-slate-400" />
                  <p className="mt-3 text-sm font-medium">
                    No members added yet
                  </p>
                  <p className="mt-2 text-xs text-slate-500">
                    Use the form to add your first member.
                  </p>
                </div>
              )}

              {members.map((member) => (
                <div
                  key={member.id}
                  className="rounded-lg border border-slate-200 p-4 transition hover:border-slate-300"
                >
                  <div className="flex items-start gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-slate-100 text-sm font-semibold">
                      {member.name.slice(0, 1).toUpperCase()}
                    </div>

                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-sm">
                        {member.name}
                      </p>
                      <p className="truncate text-xs text-slate-500">
                        {member.email}
                      </p>
                      <p className="mt-2 text-xs text-slate-600">
                        {member.role}
                      </p>
                    </div>

                    <button
                      type="button"
                      onClick={() => editMember(member)}
                      aria-label={`Edit ${member.name}`}
                      className="rounded-md p-2 text-slate-500 hover:bg-slate-100"
                    >
                      <Pencil size={16} />
                    </button>

                    <button
                      type="button"
                      onClick={() => removeMember(member.id)}
                      aria-label={`Remove ${member.name}`}
                      className="rounded-md p-2 text-slate-500 hover:bg-rose-50 hover:text-rose-600"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>

                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {member.skills.map((skill) => (
                      <span
                        key={skill}
                        className="rounded bg-slate-100 px-2 py-1 text-[11px] text-slate-600"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>

                  <div className="mt-3 flex items-center gap-1.5 border-t border-slate-100 pt-3 text-xs text-slate-500">
                    <Clock3 size={14} />
                    {member.weeklyHours} hours/week
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>

        <div className="mt-8 flex items-center justify-between border-t border-slate-200 pt-6">
          <button
            type="button"
            onClick={() => navigate("/create-project")}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-5 py-3 text-sm font-medium hover:bg-slate-50"
          >
            <ArrowLeft size={17} />
            Back
          </button>

          <button
            type="button"
            disabled={members.length === 0}
            onClick={() => navigate("/requirements")}
            className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-5 py-3 text-sm font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Continue to requirements
            <ArrowRight size={17} />
          </button>
        </div>
      </main>
    </div>
  );
}
