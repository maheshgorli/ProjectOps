
import { useState, type FormEvent, type ChangeEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  UploadCloud,
  FileText,
  GitBranch,
  X,
  CheckCircle2,
  FolderOpen,
  CalendarDays,
} from "lucide-react";

type Project = {
  id: string;
  name: string;
  description?: string;
  type?: string;
  durationDays?: number;
  deadline?: string;
};

type SavedFile = {
  name: string;
  size: number;
};

type RequirementData = {
  projectId: string;
  details: string;
  githubUrl: string;
  files: SavedFile[];
};

function loadProject(): Project | null {
  try {
    const id = localStorage.getItem("projectops_active_project");
    const raw = localStorage.getItem("projectops_projects");
    const projects: Project[] = raw ? JSON.parse(raw) : [];
    return projects.find((project) => project.id === id) || null;
  } catch {
    return null;
  }
}

function loadRequirements(projectId: string): RequirementData | null {
  try {
    const raw = localStorage.getItem(
      `projectops_requirements_${projectId}`
    );
    return raw ? (JSON.parse(raw) as RequirementData) : null;
  } catch {
    return null;
  }
}

export default function Requirements() {
  const navigate = useNavigate();

  const [project] = useState<Project | null>(loadProject);
  const [saved] = useState(() =>
    loadRequirements(project?.id || "")
  );

  const [details, setDetails] = useState(saved?.details || "");
  const [githubUrl, setGithubUrl] = useState(saved?.githubUrl || "");
  const [files, setFiles] = useState<File[]>([]);
  const [savedFiles, setSavedFiles] = useState<SavedFile[]>(
    saved?.files || []
  );
  const [error, setError] = useState("");

  const allFiles = [
    ...savedFiles,
    ...files.map((file) => ({
      name: file.name,
      size: file.size,
    })),
  ];

  function handleFiles(e: ChangeEvent<HTMLInputElement>) {
    const selected = Array.from(e.target.files || []);
    const allowed = /\.(pdf|docx|txt|md)$/i;

    if (selected.some((file) => !allowed.test(file.name))) {
      setError("Please select PDF, DOCX, TXT or Markdown files.");
      e.target.value = "";
      return;
    }

    if (selected.some((file) => file.size > 10 * 1024 * 1024)) {
      setError("Each document must be 10 MB or smaller.");
      e.target.value = "";
      return;
    }

    setFiles((current) => [
      ...current.filter(
        (file) => !selected.some((item) => item.name === file.name)
      ),
      ...selected,
    ]);

    setSavedFiles((current) =>
      current.filter(
        (file) => !selected.some((item) => item.name === file.name)
      )
    );

    setError("");
    e.target.value = "";
  }

  function removeFile(name: string) {
    setFiles((current) =>
      current.filter((file) => file.name !== name)
    );
    setSavedFiles((current) =>
      current.filter((file) => file.name !== name)
    );
  }

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");

    if (!project) {
      setError("Create a project before continuing.");
      return;
    }

    if (!details.trim() && allFiles.length === 0 && !githubUrl.trim()) {
      setError("Add requirements, a document, or a GitHub repository.");
      return;
    }

    if (githubUrl.trim()) {
      try {
        const url = new URL(githubUrl.trim());
        const segments = url.pathname.split("/").filter(Boolean);

        if (
          url.protocol !== "https:" ||
          url.hostname.toLowerCase() !== "github.com" ||
          segments.length !== 2 ||
          !segments.every((segment) =>
            /^[a-zA-Z0-9_.-]+$/.test(segment)
          )
        ) {
          throw new Error("Invalid repository URL");
        }
      } catch {
        setError("Enter a valid GitHub repository URL.");
        return;
      }
    }

    const data: RequirementData = {
      projectId: project.id,
      details: details.trim(),
      githubUrl: githubUrl.trim(),
      files: allFiles,
    };

    try {
      localStorage.setItem(
        `projectops_requirements_${project.id}`,
        JSON.stringify(data)
      );
      navigate("/ai-plan");
    } catch {
      setError("Unable to save requirements in this browser.");
    }
  }

  if (!project) {
    return (
      <main className="min-h-screen bg-[#f7f8fa] p-10 text-slate-900">
        <h1 className="text-2xl font-semibold">
          No project selected
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
          <span className="text-lg font-semibold tracking-tight">
            ProjectOps
          </span>
          <span className="text-sm text-slate-500">
            Project setup
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-10">
        <button
          type="button"
          onClick={() => navigate("/add-members")}
          className="mb-7 flex items-center gap-2 text-sm text-slate-500 hover:text-slate-900"
        >
          <ArrowLeft size={16} />
          Back to members
        </button>

        <div className="mb-8">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Step 4 of 4
          </p>

          <h1 className="mt-3 text-3xl font-semibold tracking-tight">
            Add project requirements
          </h1>

          <p className="mt-3 text-sm leading-6 text-slate-500">
            Describe the work or provide a project document.
            ProjectOps will use this information to prepare
            a structured execution plan.
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.5fr)_minmax(300px,1fr)]">
            <div className="space-y-6">
              <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="mb-5">
                  <h2 className="text-base font-semibold">
                    Project documentation
                  </h2>
                  <p className="mt-1 text-xs text-slate-500">
                    Upload the files that describe your project.
                  </p>
                </div>

                <label className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 px-5 py-10 text-center transition hover:border-slate-500">
                  <UploadCloud size={29} className="text-slate-500" />
                  <span className="mt-3 text-sm font-medium">
                    Choose files to attach
                  </span>
                  <span className="mt-2 text-xs text-slate-500">
                    PDF, DOCX, TXT or MD · Up to 10 MB each
                  </span>

                  <input
                    type="file"
                    multiple
                    accept=".pdf,.docx,.txt,.md"
                    onChange={handleFiles}
                    className="sr-only"
                  />
                </label>

                <p className="mt-3 text-xs text-slate-500">
                  Prototype only: file names and sizes are saved,
                  not document contents.
                </p>
              </section>

              <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <h2 className="text-base font-semibold">
                  Written requirements
                </h2>
                <p className="mt-1 text-xs text-slate-500">
                  Add requirements manually if you don't have a document.
                </p>

                <textarea
                  value={details}
                  onChange={(e) => setDetails(e.target.value)}
                  rows={8}
                  placeholder="Describe expected features, target users, technical requirements, constraints, and deliverables..."
                  className="mt-5 w-full resize-y rounded-lg border border-slate-300 bg-white p-4 text-sm leading-6 outline-none focus:border-slate-600"
                />
              </section>

              <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="flex items-center gap-2">
                  <GitBranch size={19} className="text-slate-500" />
                  <h2 className="text-base font-semibold">
                    GitHub repository
                  </h2>
                  <span className="text-xs text-slate-400">
                    Optional
                  </span>
                </div>

                <p className="mt-2 text-xs text-slate-500">
                  Add a repository if development has already started.
                </p>

                <input
                  type="url"
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  placeholder="https://github.com/username/repository"
                  className="mt-4 w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-slate-600"
                />
              </section>
            </div>

            <aside className="space-y-5 lg:sticky lg:top-6">
              <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="mb-5 flex items-center gap-2">
                  <FolderOpen size={19} className="text-slate-500" />
                  <h2 className="text-base font-semibold">
                    Project overview
                  </h2>
                </div>

                <p className="text-sm font-semibold">{project.name}</p>
                <p className="mt-2 text-xs leading-5 text-slate-500">
                  {project.description || "No description provided."}
                </p>

                <div className="mt-5 space-y-3 border-t border-slate-100 pt-5">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Type</span>
                    <span>{project.type || "Not specified"}</span>
                  </div>

                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Duration</span>
                    <span>{project.durationDays || 0} days</span>
                  </div>

                  <div className="flex items-center justify-between text-sm">
                    <span className="flex items-center gap-1 text-slate-500">
                      <CalendarDays size={14} />
                      Deadline
                    </span>
                    <span>{project.deadline || "Not specified"}</span>
                  </div>
                </div>
              </section>

              <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="mb-5 flex items-center justify-between">
                  <h2 className="text-base font-semibold">
                    Attached documents
                  </h2>
                  <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs">
                    {allFiles.length}
                  </span>
                </div>

                {allFiles.length === 0 ? (
                  <p className="text-sm text-slate-500">
                    No documents selected yet.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {allFiles.map((file) => (
                      <div
                        key={file.name}
                        className="flex items-center gap-2 rounded-lg border border-slate-200 p-3"
                      >
                        <FileText size={18} className="shrink-0 text-slate-500" />
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-xs font-medium">
                            {file.name}
                          </p>
                          <p className="text-xs text-slate-400">
                            {(file.size / 1024).toFixed(1)} KB
                          </p>
                        </div>
                        <button
                          type="button"
                          aria-label={`Remove ${file.name}`}
                          onClick={() => removeFile(file.name)}
                          className="rounded p-1 text-slate-400 hover:text-rose-600"
                        >
                          <X size={16} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              <section className="rounded-xl border border-slate-200 bg-white p-6">
                <div className="flex items-start gap-2">
                  <CheckCircle2
                    size={19}
                    className="mt-0.5 shrink-0 text-emerald-600"
                  />
                  <div>
                    <h3 className="text-sm font-semibold">
                      Next: Project plan
                    </h3>
                    <p className="mt-2 text-xs leading-5 text-slate-500">
                      Review your inputs before preparing the
                      proposed project plan.
                    </p>
                  </div>
                </div>
              </section>
            </aside>
          </div>

          {error && (
            <p role="alert" className="mt-6 rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
              {error}
            </p>
          )}

          <div className="mt-8 flex items-center justify-between border-t border-slate-200 pt-6">
            <button
              type="button"
              onClick={() => navigate("/add-members")}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-5 py-3 text-sm font-medium hover:bg-slate-50"
            >
              <ArrowLeft size={17} />
              Back
            </button>

            <button
              type="submit"
              className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-5 py-3 text-sm font-medium text-white hover:bg-slate-700"
            >
              Continue to plan
              <ArrowRight size={17} />
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
