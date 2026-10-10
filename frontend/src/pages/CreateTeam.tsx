
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, UsersRound } from "lucide-react";

export default function CreateTeam() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();

    if (!name.trim()) {
      setError("Please enter a team name.");
      return;
    }

    const team = {
      id: crypto.randomUUID(),
      name: name.trim(),
      description: description.trim(),
      members: [],
    };

    try {
      localStorage.setItem("projectops_team", JSON.stringify(team));
      navigate("/create-project");
    } catch {
      setError("Unable to save your team.");
    }
  }

  return (
    <div className="min-h-screen bg-[#f7f8fa] text-slate-900">
      <header className="border-b border-slate-200 bg-white px-8 py-5">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <span className="text-lg font-semibold tracking-tight">
            ProjectOps
          </span>
          <span className="text-sm text-slate-500">
            Workspace setup
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-6 py-14">
        <button
          onClick={() => navigate("/workspace")}
          className="mb-8 flex items-center gap-2 text-sm text-slate-500 hover:text-slate-900"
        >
          <ArrowLeft size={16} />
          Back to workspace
        </button>

        <div className="mb-9">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Step 1 of 4
          </p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight">
            Create your team
          </h1>
          <p className="mt-3 leading-6 text-slate-500">
            Set up a shared workspace for the people working
            together on your projects.
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-xl border border-slate-200 bg-white p-7 shadow-sm"
        >
          <div className="mb-7 flex items-center gap-3 border-b border-slate-100 pb-6">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-slate-100">
              <UsersRound size={21} />
            </div>
            <div>
              <h2 className="text-sm font-semibold">Team details</h2>
              <p className="text-xs text-slate-500">
                These can be updated later.
              </p>
            </div>
          </div>

          <div className="space-y-6">
            <div>
              <label htmlFor="team-name" className="mb-2 block text-sm font-medium">
                Team name <span className="text-rose-500">*</span>
              </label>
              <input
                id="team-name"
                required
                maxLength={80}
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Code Innovators"
                className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-slate-600"
              />
            </div>

            <div>
              <label htmlFor="team-description" className="mb-2 block text-sm font-medium">
                Team description
              </label>
              <textarea
                id="team-description"
                rows={4}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What does your team work on?"
                className="w-full resize-none rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-slate-600"
              />
              <p className="mt-2 text-xs text-slate-400">
                A short description helps people recognize your workspace.
              </p>
            </div>
          </div>

          {error && (
            <p role="alert" className="mt-5 text-sm text-rose-600">
              {error}
            </p>
          )}

          <div className="mt-8 flex justify-end border-t border-slate-100 pt-6">
            <button
              type="submit"
              disabled={!name.trim()}
              className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-5 py-3 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-40"
            >
              Continue to project
              <ArrowRight size={17} />
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
