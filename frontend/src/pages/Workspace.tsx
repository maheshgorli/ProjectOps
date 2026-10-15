import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  FolderKanban,
  Plus,
  ArrowRight,
  LogOut,
  Calendar,
  Users,
  CheckCircle2,
  Clock,
  ShieldCheck,
  ShieldAlert,
  Layers,
  FileText,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  AlertCircle,
  Sparkles,
} from "lucide-react";
import { useAuth } from "../context/useAuth";
import { api } from "../services/api";
import type { Project, LoginAuditRecord } from "../types/api";

export default function Workspace() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const [projects, setProjects] = useState<Project[]>([]);
  const [audits, setAudits] = useState<LoginAuditRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAudits, setShowAudits] = useState(false);

  async function fetchData(showRefreshIndicator = false) {
    if (showRefreshIndicator) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      const [projectsData, auditsData] = await Promise.all([
        api.listProjects(),
        api.getLoginAudit().catch((err) => {
          console.warn("Failed to fetch login audits:", err);
          return [] as LoginAuditRecord[];
        }),
      ]);
      setProjects(projectsData);
      setAudits(auditsData);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to load workspace data.";
      setError(msg);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }

  useEffect(() => {
    fetchData();
  }, []);

  function handleSelectProject(project: Project, targetPath = "/dashboard") {
    try {
      localStorage.setItem("projectops_active_project", project.id);
    } catch {
      // ignore
    }
    navigate(targetPath);
  }

  if (!user) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-slate-50">
        <button
          onClick={() => navigate("/login")}
          className="rounded-lg bg-slate-900 px-6 py-3 text-white font-medium hover:bg-slate-800"
        >
          Go to Login
        </button>
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-900 font-sans">
      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur px-6 py-4">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-white font-bold shadow-sm">
              PO
            </div>
            <div>
              <span className="text-lg font-bold tracking-tight text-slate-900">
                ProjectOps
              </span>
              <span className="ml-2 rounded bg-indigo-50 px-2 py-0.5 text-[11px] font-medium text-indigo-700">
                Workspace
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden sm:flex flex-col text-right">
              <span className="text-sm font-semibold text-slate-800">
                {user.display_name}
              </span>
              <span className="text-xs text-slate-500">{user.email}</span>
            </div>

            <button
              onClick={() => {
                logout();
                navigate("/login");
              }}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition"
              title="Sign out of ProjectOps"
            >
              <LogOut size={15} />
              <span>Sign out</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Workspace Content */}
      <main className="mx-auto max-w-6xl px-6 py-10">
        {/* Welcome & Action Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between pb-8 border-b border-slate-200">
          <div>
            <div className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-indigo-600">
              <Sparkles size={14} />
              Execution & Risk Command Center
            </div>
            <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-slate-900">
              Projects & Workspaces
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              Select an active project to resume execution, inspect dependency
              graphs, or run risk simulations.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={() => fetchData(true)}
              disabled={isRefreshing || isLoading}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 transition shadow-sm"
              title="Refresh projects"
            >
              <RefreshCw
                size={16}
                className={isRefreshing ? "animate-spin" : ""}
              />
              <span className="hidden sm:inline">Refresh</span>
            </button>

            <button
              onClick={() => navigate("/create-project")}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 transition"
            >
              <Plus size={17} />
              <span>New Project</span>
            </button>
          </div>
        </div>

        {/* Global Error Banner */}
        {error && (
          <div className="mt-6 flex items-center gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
            <AlertCircle size={18} className="shrink-0 text-rose-600" />
            <p>{error}</p>
          </div>
        )}

        {/* Loading Skeleton */}
        {isLoading ? (
          <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((n) => (
              <div
                key={n}
                className="animate-pulse rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
              >
                <div className="h-4 w-24 bg-slate-200 rounded mb-4" />
                <div className="h-6 w-3/4 bg-slate-200 rounded mb-2" />
                <div className="h-4 w-full bg-slate-100 rounded mb-6" />
                <div className="h-10 bg-slate-100 rounded" />
              </div>
            ))}
          </div>
        ) : projects.length === 0 ? (
          /* Empty State */
          <div className="mt-12 rounded-2xl border-2 border-dashed border-slate-200 bg-white p-12 text-center shadow-sm">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 mb-4">
              <FolderKanban size={28} />
            </div>
            <h2 className="text-xl font-bold text-slate-900">
              No projects in this workspace yet
            </h2>
            <p className="mx-auto mt-2 max-w-md text-sm text-slate-500 leading-relaxed">
              Transform your project specifications into deterministic DAG
              execution plans, detect schedule risks, and simulate recovery
              strategies with ProjectOps.
            </p>
            <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
              <button
                onClick={() => navigate("/create-project")}
                className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 transition"
              >
                <Plus size={18} />
                <span>Create Your First Project</span>
              </button>
            </div>
          </div>
        ) : (
          /* Projects Grid */
          <div className="mt-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Active Projects ({projects.length})
              </h2>
            </div>

            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {projects.map((project) => {
                const memberCount = project.members?.length || 0;
                const taskCount = project.task_count || 0;
                const hasPlan = Boolean(project.active_plan_version);

                return (
                  <div
                    key={project.id}
                    className="group relative flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition hover:border-indigo-300 hover:shadow-md"
                  >
                    <div>
                      {/* Top Badges */}
                      <div className="flex items-center justify-between gap-2">
                        <span
                          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                            hasPlan
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              : "bg-amber-50 text-amber-700 border border-amber-200"
                          }`}
                        >
                          <span
                            className={`h-1.5 w-1.5 rounded-full ${
                              hasPlan ? "bg-emerald-500" : "bg-amber-500"
                            }`}
                          />
                          {hasPlan
                            ? `Plan v${project.active_plan_version} Active`
                            : "Draft / No Plan"}
                        </span>

                        <span className="text-[11px] font-medium text-slate-400">
                          {new Date(project.created_at).toLocaleDateString(
                            undefined,
                            {
                              month: "short",
                              day: "numeric",
                            }
                          )}
                        </span>
                      </div>

                      {/* Title & Description */}
                      <h3 className="mt-4 text-lg font-bold text-slate-900 group-hover:text-indigo-600 transition">
                        {project.name}
                      </h3>

                      <p className="mt-1 text-sm text-slate-500 line-clamp-2 min-h-[2.5rem]">
                        {project.description ||
                          "No project description provided."}
                      </p>

                      {/* Metrics Pill Grid */}
                      <div className="mt-5 grid grid-cols-2 gap-2 border-t border-slate-100 pt-4 text-xs text-slate-600">
                        <div className="flex items-center gap-1.5">
                          <Layers size={14} className="text-slate-400" />
                          <span>
                            <strong>{taskCount}</strong> tasks
                          </span>
                        </div>

                        <div className="flex items-center gap-1.5">
                          <Users size={14} className="text-slate-400" />
                          <span>
                            <strong>{memberCount}</strong> members
                          </span>
                        </div>

                        {project.target_completion_date && (
                          <div className="col-span-2 flex items-center gap-1.5 text-slate-500">
                            <Calendar size={14} className="text-slate-400" />
                            <span>
                              Target:{" "}
                              <strong>{project.target_completion_date}</strong>
                            </span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="mt-6 pt-4 border-t border-slate-100 flex flex-col gap-2">
                      <button
                        onClick={() =>
                          handleSelectProject(project, "/dashboard")
                        }
                        className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-slate-900 px-4 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-indigo-600 transition"
                      >
                        <span>Continue Working</span>
                        <ArrowRight size={14} />
                      </button>

                      <div className="grid grid-cols-2 gap-2">
                        <button
                          onClick={() =>
                            handleSelectProject(project, "/ai-plan")
                          }
                          className="inline-flex items-center justify-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition"
                        >
                          <FileText size={13} />
                          <span>View Plan</span>
                        </button>

                        <button
                          onClick={() =>
                            handleSelectProject(project, "/requirements")
                          }
                          className="inline-flex items-center justify-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition"
                        >
                          <Sparkles size={13} />
                          <span>Specs</span>
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Security & Login Auditing Drawer */}
        <div className="mt-12 rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm">
          <button
            onClick={() => setShowAudits(!showAudits)}
            className="w-full flex items-center justify-between p-5 text-left bg-slate-50/50 hover:bg-slate-50 transition"
          >
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-50 text-indigo-700">
                <ShieldCheck size={20} />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  Authentication Hardening & Login Auditing
                </h3>
                <p className="text-xs text-slate-500">
                  Persistent audit log of recent authentication events
                  associated with your account.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
              <span>{showAudits ? "Hide history" : "View audit trail"}</span>
              {showAudits ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </div>
          </button>

          {showAudits && (
            <div className="p-5 border-t border-slate-200">
              {audits.length === 0 ? (
                <p className="text-sm text-slate-500 py-3 text-center">
                  No login audit records found for this account.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-200 text-slate-500">
                        <th className="pb-2.5 font-semibold">Status</th>
                        <th className="pb-2.5 font-semibold">Email</th>
                        <th className="pb-2.5 font-semibold">Timestamp</th>
                        <th className="pb-2.5 font-semibold">IP Address</th>
                        <th className="pb-2.5 font-semibold">Client / Device</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {audits.map((audit) => (
                        <tr key={audit.id} className="hover:bg-slate-50/60">
                          <td className="py-2.5">
                            <span
                              className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-[11px] font-semibold ${
                                audit.status === "SUCCESS"
                                  ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                  : "bg-rose-50 text-rose-700 border border-rose-200"
                              }`}
                            >
                              {audit.status === "SUCCESS" ? (
                                <CheckCircle2 size={12} />
                              ) : (
                                <ShieldAlert size={12} />
                              )}
                              {audit.status}
                            </span>
                          </td>
                          <td className="py-2.5 font-medium text-slate-700">
                            {audit.email}
                          </td>
                          <td className="py-2.5 text-slate-500">
                            <span className="inline-flex items-center gap-1">
                              <Clock size={12} className="text-slate-400" />
                              {new Date(audit.created_at).toLocaleString()}
                            </span>
                          </td>
                          <td className="py-2.5 font-mono text-slate-600">
                            {audit.ip_address || "127.0.0.1"}
                          </td>
                          <td className="py-2.5 text-slate-500 max-w-xs truncate" title={audit.user_agent ?? undefined}>
                            {audit.user_agent || "Browser Session"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
