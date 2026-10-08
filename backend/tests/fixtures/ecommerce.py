"""Golden E-Commerce Application fixture.

4 members:
- Alice: Frontend, React, TypeScript (8h/day)
- Bob: Backend, Python, FastAPI, JWT (8h/day)
- Charlie: Database, SQL, PostgreSQL (8h/day)
- David: Testing, Pytest, Playwright (8h/day)

16 tasks across Database, Backend, Frontend, Testing, and Deployment.
Core critical chain:
Database Schema (T-DB-01) -> Backend API (T-BE-02) -> Frontend Integration (T-FE-03)
-> Integration Testing (T-QA-02) -> Deployment (T-OPS-01)
30-day project deadline.
"""

from datetime import date

from backend.app.domain.models import Dependency, DependencyType, Member, Task, TaskStatus

PROJECT_START_DATE = date(2026, 11, 2)  # Monday
PROJECT_DEADLINE = date(2026, 12, 11)  # 30 working days from start


def get_ecommerce_members() -> dict[str, Member]:
    """Return the 4 team members for the E-Commerce scenario."""
    return {
        "m-alice": Member(
            id="m-alice",
            name="Alice",
            role="Frontend Engineer",
            skills=["Frontend", "React", "TypeScript"],
            daily_capacity_hours=8.0,
            max_parallel_tasks=1,
        ),
        "m-bob": Member(
            id="m-bob",
            name="Bob",
            role="Backend Engineer",
            skills=["Backend", "Python", "FastAPI", "JWT"],
            daily_capacity_hours=8.0,
            max_parallel_tasks=1,
        ),
        "m-charlie": Member(
            id="m-charlie",
            name="Charlie",
            role="Database Administrator",
            skills=["Database", "SQL", "PostgreSQL"],
            daily_capacity_hours=8.0,
            max_parallel_tasks=1,
        ),
        "m-david": Member(
            id="m-david",
            name="David",
            role="QA Automation Engineer",
            skills=["Testing", "Pytest", "Playwright"],
            daily_capacity_hours=8.0,
            max_parallel_tasks=1,
        ),
    }


def get_ecommerce_tasks() -> dict[str, Task]:
    """Return the 16 tasks for the E-Commerce scenario."""
    return {
        # --- Database Tasks (Charlie) ---
        "T-DB-01": Task(
            id="T-DB-01",
            title="Database Schema Design",
            description="Entity relationship diagram, PostgreSQL DDL schemas, and migrations.",
            duration_working_days=3,
            estimated_hours=24.0,
            required_skills=["Database", "SQL", "PostgreSQL"],
            assigned_to_id="m-charlie",
            status=TaskStatus.TODO,
        ),
        "T-DB-02": Task(
            id="T-DB-02",
            title="Migration Scripts & Tables",
            description="Alembic migration generation and automated rollback verification.",
            duration_working_days=2,
            estimated_hours=16.0,
            required_skills=["Database", "SQL"],
            assigned_to_id="m-charlie",
            status=TaskStatus.TODO,
        ),
        "T-DB-03": Task(
            id="T-DB-03",
            title="Seed Data & Indexes",
            description="Catalog seed fixtures and performance B-Tree indices.",
            duration_working_days=2,
            estimated_hours=16.0,
            required_skills=["Database", "PostgreSQL"],
            assigned_to_id="m-charlie",
            status=TaskStatus.TODO,
        ),
        # --- Backend Tasks (Bob) ---
        "T-BE-01": Task(
            id="T-BE-01",
            title="Core Domain Models",
            description="SQLAlchemy ORM models and pure business domain logic.",
            duration_working_days=2,
            estimated_hours=16.0,
            required_skills=["Backend", "Python"],
            assigned_to_id="m-bob",
            status=TaskStatus.TODO,
        ),
        "T-BE-02": Task(
            id="T-BE-02",
            title="Backend API",
            description="FastAPI CRUD routes, validation schemas, and service layer.",
            duration_working_days=4,
            estimated_hours=32.0,
            required_skills=["Backend", "Python", "FastAPI"],
            assigned_to_id="m-bob",
            status=TaskStatus.TODO,
        ),
        "T-BE-03": Task(
            id="T-BE-03",
            title="Auth & JWT Middleware",
            description="User authentication, password hashing, and JWT bearer tokens.",
            duration_working_days=3,
            estimated_hours=24.0,
            required_skills=["Backend", "JWT"],
            assigned_to_id="m-bob",
            status=TaskStatus.TODO,
        ),
        "T-BE-04": Task(
            id="T-BE-04",
            title="Payment Gateway Integration",
            description="Stripe checkout sessions and webhook processing.",
            duration_working_days=3,
            estimated_hours=24.0,
            required_skills=["Backend", "Python"],
            assigned_to_id="m-bob",
            status=TaskStatus.TODO,
        ),
        "T-BE-05": Task(
            id="T-BE-05",
            title="Notification Service",
            description="Transactional email dispatch and queue workers.",
            duration_working_days=2,
            estimated_hours=16.0,
            required_skills=["Backend", "Python"],
            assigned_to_id="m-bob",
            status=TaskStatus.TODO,
        ),
        # --- Frontend Tasks (Alice) ---
        "T-FE-01": Task(
            id="T-FE-01",
            title="UI Component Library",
            description="Atomic React components, typography tokens, and Tailwind theme.",
            duration_working_days=3,
            estimated_hours=24.0,
            required_skills=["Frontend", "React"],
            assigned_to_id="m-alice",
            status=TaskStatus.TODO,
        ),
        "T-FE-02": Task(
            id="T-FE-02",
            title="Catalog & Product Views",
            description="Product listing pages, search filters, and responsive grids.",
            duration_working_days=3,
            estimated_hours=24.0,
            required_skills=["Frontend", "React", "TypeScript"],
            assigned_to_id="m-alice",
            status=TaskStatus.TODO,
        ),
        "T-FE-03": Task(
            id="T-FE-03",
            title="Frontend Integration",
            description="TanStack Query API integration and state management.",
            duration_working_days=4,
            estimated_hours=32.0,
            required_skills=["Frontend", "React", "TypeScript"],
            assigned_to_id="m-alice",
            status=TaskStatus.TODO,
        ),
        "T-FE-04": Task(
            id="T-FE-04",
            title="Checkout & Payment Flow",
            description="Shopping cart drawer and Stripe payment form modal.",
            duration_working_days=3,
            estimated_hours=24.0,
            required_skills=["Frontend", "React"],
            assigned_to_id="m-alice",
            status=TaskStatus.TODO,
        ),
        # --- Testing Tasks (David) ---
        "T-QA-01": Task(
            id="T-QA-01",
            title="Unit Test Suite",
            description="Backend pytest suite and frontend Vitest component tests.",
            duration_working_days=2,
            estimated_hours=16.0,
            required_skills=["Testing", "Pytest"],
            assigned_to_id="m-david",
            status=TaskStatus.TODO,
        ),
        "T-QA-02": Task(
            id="T-QA-02",
            title="Integration Testing",
            description="End-to-end integration test scenarios across services.",
            duration_working_days=4,
            estimated_hours=32.0,
            required_skills=["Testing", "Playwright"],
            assigned_to_id="m-david",
            status=TaskStatus.TODO,
        ),
        "T-QA-03": Task(
            id="T-QA-03",
            title="E2E User Journey Tests",
            description="Full automated checkout flows and browser test automation.",
            duration_working_days=3,
            estimated_hours=24.0,
            required_skills=["Testing", "Playwright"],
            assigned_to_id="m-david",
            status=TaskStatus.TODO,
        ),
        # --- Deployment Tasks (Bob) ---
        "T-OPS-01": Task(
            id="T-OPS-01",
            title="Deployment",
            description=(
                "Production container build, environment secret injection, and release cutover."
            ),
            duration_working_days=2,
            estimated_hours=16.0,
            required_skills=["Backend", "Python"],
            assigned_to_id="m-bob",
            status=TaskStatus.TODO,
        ),
    }


def get_ecommerce_dependencies() -> list[Dependency]:
    """Return the precedence dependencies for the E-Commerce scenario."""
    return [
        # Database chain
        Dependency("T-DB-01", "T-DB-02", DependencyType.FINISH_TO_START),
        Dependency("T-DB-02", "T-DB-03", DependencyType.FINISH_TO_START),
        # Database to Backend
        Dependency("T-DB-01", "T-BE-01", DependencyType.FINISH_TO_START),
        Dependency("T-BE-01", "T-BE-02", DependencyType.FINISH_TO_START),
        Dependency("T-DB-02", "T-BE-02", DependencyType.FINISH_TO_START),
        Dependency("T-BE-01", "T-BE-03", DependencyType.FINISH_TO_START),
        Dependency("T-BE-02", "T-BE-04", DependencyType.FINISH_TO_START),
        Dependency("T-BE-02", "T-BE-05", DependencyType.FINISH_TO_START),
        # Frontend chain
        Dependency("T-FE-01", "T-FE-02", DependencyType.FINISH_TO_START),
        Dependency("T-FE-02", "T-FE-03", DependencyType.FINISH_TO_START),
        Dependency("T-BE-02", "T-FE-03", DependencyType.FINISH_TO_START),  # Core Handover
        Dependency("T-FE-03", "T-FE-04", DependencyType.FINISH_TO_START),
        Dependency("T-BE-04", "T-FE-04", DependencyType.FINISH_TO_START),
        # Testing chain
        Dependency("T-BE-02", "T-QA-01", DependencyType.FINISH_TO_START),
        Dependency("T-FE-03", "T-QA-02", DependencyType.FINISH_TO_START),  # Core Handover
        Dependency("T-QA-01", "T-QA-02", DependencyType.FINISH_TO_START),
        Dependency("T-QA-02", "T-QA-03", DependencyType.FINISH_TO_START),
        Dependency("T-FE-04", "T-QA-03", DependencyType.FINISH_TO_START),
        # Deployment chain
        Dependency("T-QA-02", "T-OPS-01", DependencyType.FINISH_TO_START),  # Core Handover
        Dependency("T-QA-03", "T-OPS-01", DependencyType.FINISH_TO_START),
    ]
