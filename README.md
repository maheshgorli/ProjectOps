# ProjectOps

ProjectOps is an autonomous multi-agent project execution and risk management system.
Loop: **PLAN -> EXECUTE -> OBSERVE -> REASON -> REPLAN -> APPROVE -> EXECUTE**.

ProjectOps is **not** a Jira/Trello clone with a chatbot. The intelligence lives in the workflow, and deterministic code owns truth.

---

## Core Principles

1. **Deterministic code owns truth**: Dates, graphs, cycle checks, critical path (CPM), scheduling, workload, risk rules, impact analysis, and authorization are computed deterministically.
2. **LLM boundaries**: LLMs only perform goal decomposition, task descriptions, strategy ideas, and explanations. LLM outputs never write to the database directly without passing strict schema (Pydantic) and domain validation.
3. **Deterministic simulation**: Replans are simulated by the deterministic scheduler. The LLM explains computed numbers; it never invents them.
4. **Human governance gate**: Replanning requires human approval. Never silently mutate an active plan.
5. **Immutable snapshots**: Plans are immutable, versioned snapshots ($v_1 \to v_2$). Append-only audit trails for progress history, decisions, and agent runs.
6. **Evidence vs proof**: External activity (such as GitHub commits or PRs) is treated as evidence, never automatic proof of completion.

---

## Repository Structure

```text
projectops/
├── README.md
├── AGENTS.md                                   # Engineering rules
├── docs/                                       # Architecture, API conventions, ADRs
├── docker-compose.yml                          # Container services
├── .github/workflows/ci.yml                    # Automated CI pipeline
├── backend/
│   ├── pyproject.toml                          # Python 3.12+ project configuration
│   ├── app/
│   │   ├── main.py                             # FastAPI entry point
│   │   ├── core/                               # Config & logging
│   │   ├── domain/                             # PURE DOMAIN ENGINE (Zero I/O)
│   │   └── ...                                 # Future stage packages
│   └── tests/                                  # Pytest & Hypothesis test suite
└── frontend/                                   # Frontend web application
```

---

## Running Tests

ProjectOps requires Python 3.12+ and uses `uv` or `pytest`:

```bash
# Run the complete test suite
uv run pytest -v

# Run with test coverage
uv run pytest --cov=backend/app/domain

# Run linter and formatter checks
uv run ruff check .
uv run ruff format --check .
```

---

## Database Migrations

Alembic is the sole source of truth for the database schema. Tables are never automatically created in the application runtime.

```bash
# Apply all pending migrations (from repository root)
uv run alembic upgrade head

# Or using the migration runner script
uv run python scripts/migrate.py head

# Or from backend directory
cd backend
uv run alembic upgrade head
```

---

## Running the Application

### 1. Environment & Auth Configuration

Create a `.env` file in `backend/` or set environment variables in your shell:

```bash
# Required for signing JWTs (must be at least 32 characters)
AUTH_SECRET_KEY=change-this-to-a-secure-random-secret-key-32-chars-min

# LLM provider ("mock" for local dev without API keys, or "claude")
LLM_PROVIDER=mock
```

### 2. Backend Server

Run the FastAPI backend on port **8000** (matching Vite frontend proxy):

```bash
# From repository root
uv run uvicorn backend.app.main:app --reload --port 8000
```

### 3. Frontend Development Server

```bash
# From frontend/
cd frontend
npm run dev
```
The frontend is available at `http://localhost:5173`. Vite proxies `/api` calls directly to `http://127.0.0.1:8000`.

---

## Authentication & Authorization (Phase F)

ProjectOps enforces server-side authentication (Argon2id + signed HS256 JWT) and role-based access control (RBAC):

1. **Register**: Navigate to `http://localhost:5173/register` or `POST /api/v1/auth/register` with `{email, display_name, password}` (minimum 10 characters).
2. **Log In**: Navigate to `http://localhost:5173/login` or `POST /api/v1/auth/login` with `{email, password}` to receive a JWT Bearer token.
3. **Session Management**: Tokens are held in memory with `sessionStorage` fallback. Non-authenticated users are automatically redirected to `/login`.
4. **Project RBAC**:
   - Creating a project assigns the caller as **Owner**.
   - **404 vs 403 Policy**: Non-members querying any `/projects/{id}/*` route receive `404 Not Found` to prevent leaking project existence. Members attempting owner actions receive `403 Forbidden`.
   - **Attribution**: Identity fields (`decided_by`, `updated_by`, `created_by`, `recorded_by`) are derived strictly on the server from the authenticated JWT. Client attempts to forge these fields are rejected with `422 Unprocessable Entity`.

---

## Plan Activation Workflow

Plans are immutable versioned snapshots ($v_1 \to v_2$):

1. **Draft Creation**: `POST /api/v1/projects/{id}/plans` creates a draft plan snapshot (`is_active=False`) with server-assigned monotonically increasing versions.
2. **Approval-Gated Initial Activation**: `POST /api/v1/projects/{id}/plans/{version}/activate` (Owner only) activates the initial plan with a mandatory non-empty rationale. This writes an append-only decision record and backfills task execution states.
3. **Subsequent Plan Changes**: Once an active plan exists, direct activation is prohibited (HTTP 409). All changes must proceed through the deterministic simulation and human approval loop (`/replan/propose` $\to$ `/replan/approve`).


