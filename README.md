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

### 1. Backend Server
```bash
# From repository root or backend/
uv run uvicorn backend.app.main:app --reload --port 8001
# Or
cd backend
uv run uvicorn app.main:app --reload --port 8001
```

### 2. Frontend Development Server
```bash
# From repository root
npm run dev

# Or from frontend/
cd frontend
npm run dev
```

