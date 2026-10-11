
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Users } from "lucide-react";

export default function JoinTeam() {
  const navigate = useNavigate();

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#f7f8fa] px-6 text-slate-900">
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-8">
        <Users size={30} className="text-slate-700" />

        <h1 className="mt-5 text-2xl font-semibold">
          Join a team
        </h1>

        <p className="mt-3 text-sm leading-6 text-slate-500">
          Team invitation codes will be available when
          backend membership verification is implemented.
        </p>

        <div className="mt-6 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
          Joining a team is not enabled in this frontend prototype.
        </div>

        <button
          onClick={() => navigate("/workspace")}
          className="mt-6 flex items-center gap-2 text-sm font-medium"
        >
          <ArrowLeft size={17} />
          Back to workspace
        </button>
      </div>
    </main>
  );
}
