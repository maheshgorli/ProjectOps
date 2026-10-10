
import { useNavigate } from "react-router-dom";
import { ArrowRight, LogOut, Plus, Users } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function Workspace() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  if (!user) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-gray-50">
        <button
          onClick={() => navigate("/login")}
          className="rounded-lg bg-slate-900 px-6 py-3 text-white"
        >
          Go to Login
        </button>
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-[#f7f8fa] text-slate-900">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-8 py-5">
        <span className="text-xl font-semibold tracking-tight">
          ProjectOps
        </span>

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
      </header>

      <main className="mx-auto max-w-4xl px-6 py-20">
        <p className="text-sm font-medium text-slate-500">
          WORKSPACE SETUP
        </p>

        <h1 className="mt-3 text-3xl font-semibold tracking-tight">
          Welcome, {user.name}
        </h1>

        <p className="mt-3 text-slate-500">
          Create a workspace for your team or join one
          you've been invited to.
        </p>

        <div className="mt-10 grid gap-5 md:grid-cols-2">
          <button
            onClick={() => navigate("/create-team")}
            className="group rounded-xl border border-slate-200 bg-white p-7 text-left transition hover:border-slate-400 hover:shadow-sm"
          >
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-slate-100">
              <Plus size={22} />
            </div>

            <h2 className="mt-6 text-lg font-semibold">
              Create a new team
            </h2>

            <p className="mt-2 text-sm leading-6 text-slate-500">
              Start a workspace, organize members,
              and create your first project.
            </p>

            <span className="mt-7 flex items-center gap-2 text-sm font-medium">
              Create team
              <ArrowRight
                size={17}
                className="transition group-hover:translate-x-1"
              />
            </span>
          </button>

          <button
            onClick={() => navigate("/join-team")}
            className="group rounded-xl border border-slate-200 bg-white p-7 text-left transition hover:border-slate-400 hover:shadow-sm"
          >
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-slate-100">
              <Users size={22} />
            </div>

            <h2 className="mt-6 text-lg font-semibold">
              Join an existing team
            </h2>

            <p className="mt-2 text-sm leading-6 text-slate-500">
              Enter an invitation code shared by your
              team leader.
            </p>

            <span className="mt-7 flex items-center gap-2 text-sm font-medium">
              Join team
              <ArrowRight
                size={17}
                className="transition group-hover:translate-x-1"
              />
            </span>
          </button>
        </div>
      </main>
    </div>
  );
}
